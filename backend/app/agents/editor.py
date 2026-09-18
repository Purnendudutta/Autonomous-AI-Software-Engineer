"""
Code Modification Engine and Implementation Agent Node.

Executes planned code changes via surgical SEARCH/REPLACE blocks or full file creation,
with automatic backups and unified Git diff generation.
"""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from app.agents.patcher import create_file_backup, get_workspace_git_diff
from app.agents.prompts import (
    IMPLEMENTATION_SYSTEM_PROMPT,
    SearchReplaceBlock,
    extract_code_block,
    extract_search_replace_blocks,
)
from app.agents.state import AgentState, AppliedChange, PlanStep
from app.api.dependencies import get_llm_provider
from app.core.logging import get_logger
from app.core.security import PathTraversalError, safe_path
from app.llm.provider import Message

logger = get_logger(__name__)


def apply_search_replace_edit(
    original_content: str,
    blocks: list[SearchReplaceBlock],
) -> tuple[bool, str, str]:
    """
    Apply a list of SearchReplaceBlocks sequentially to original content.

    Returns:
        (success, updated_content, error_message)
    """
    if not blocks:
        return False, original_content, "No SEARCH/REPLACE blocks found in LLM response."

    content = original_content

    for idx, block in enumerate(blocks, start=1):
        search_text = block.search
        replace_text = block.replace

        # 1. Try exact match
        if search_text in content:
            content = content.replace(search_text, replace_text, 1)
            continue

        # 2. Try normalized line endings (CRLF vs LF)
        norm_content = content.replace("\r\n", "\n")
        norm_search = search_text.replace("\r\n", "\n")
        norm_replace = replace_text.replace("\r\n", "\n")

        if norm_search in norm_content:
            norm_content = norm_content.replace(norm_search, norm_replace, 1)
            content = norm_content
            continue

        # 3. Try stripped lines match
        lines = content.splitlines()
        search_lines = [l.strip() for l in search_text.splitlines() if l.strip()]

        found = False
        if search_lines:
            for i in range(len(lines) - len(search_lines) + 1):
                window = [lines[i + j].strip() for j in range(len(search_lines))]
                if window == search_lines:
                    # Replace slice
                    lines[i : i + len(search_lines)] = replace_text.splitlines()
                    content = "\n".join(lines) + ("\n" if content.endswith("\n") else "")
                    found = True
                    break

        if not found:
            return (
                False,
                original_content,
                f"Block {idx} failed: Target SEARCH snippet was not found in the file.",
            )

    return True, content, ""


async def implementation_node(state: AgentState) -> dict[str, Any]:
    """
    Executes code modifications outlined in the execution_plan steps.
    """
    workspace_path = state.get("workspace_path")
    plan_obj = state.get("execution_plan")
    task_id = state.get("task_id", "unknown")

    logger.info("implementation_node_started", task_id=task_id, workspace=workspace_path)

    if not workspace_path:
        logger.error("implementation_missing_workspace", task_id=task_id)
        return {"applied_changes": [], "git_diff": ""}

    root = Path(workspace_path).resolve()
    if not root.exists():
        logger.error("workspace_path_not_found", path=str(root))
        return {"applied_changes": [], "git_diff": ""}

    steps: list[PlanStep] = plan_obj.get("steps", []) if plan_obj else []
    if not steps:
        # Fallback to general task description modification
        steps = [{
            "step_number": 1,
            "action": "modify_code",
            "target_file": plan_obj.get("target_files", ["main.py"])[0] if plan_obj and plan_obj.get("target_files") else "main.py",
            "description": state.get("task_description", "Implement changes"),
            "rationale": "Direct implementation",
            "status": "pending",
        }]

    applied_changes: list[AppliedChange] = []
    llm = get_llm_provider()

    for step in steps:
        raw_action = str(step.get("action", "modify_code")).lower().replace("-", "_").replace(" ", "_")
        if any(act in raw_action for act in ("modify", "edit", "update", "change", "patch", "fix", "code", "write")):
            action = "modify_code"
        elif any(act in raw_action for act in ("create", "add", "new")):
            action = "create_file"
        elif any(act in raw_action for act in ("read", "test", "verify", "run")):
            continue
        else:
            action = "modify_code"

        target_file_rel = step.get("target_file", "")
        if not target_file_rel or target_file_rel == "unknown":
            tf_list = plan_obj.get("target_files", []) if plan_obj else []
            if tf_list and tf_list[0] != "unknown":
                target_file_rel = tf_list[0]
            else:
                continue

        try:
            target_path = safe_path(root, target_file_rel)
        except PathTraversalError as exc:
            logger.error("security_violation_in_step", step=step.get("step_number"), error=str(exc))
            continue

        # Read existing file content if it exists
        is_new_file = not target_path.is_file()
        existing_content = ""
        if not is_new_file:
            try:
                existing_content = target_path.read_text(encoding="utf-8", errors="replace")
                create_file_backup(target_path)
            except Exception as exc:
                logger.warning("failed_reading_target_file", file=target_file_rel, error=str(exc))

        prompt = f"""Target File Path: {target_file_rel}
Status: {'New file to create' if is_new_file else 'Existing file'}

Planned Step:
Step {step.get('step_number')}: {step.get('description')}
Rationale: {step.get('rationale')}

Existing File Content:
```
{existing_content if existing_content else '(empty file)'}
```

Output the required SEARCH/REPLACE blocks or the complete new file content:"""

        try:
            response = await llm.complete(
                messages=[
                    Message(role="system", content=IMPLEMENTATION_SYSTEM_PROMPT),
                    Message(role="user", content=prompt),
                ],
                temperature=0.1,
                max_tokens=3072,
            )
            response_text = response.content
        except Exception as exc:
            logger.error("llm_edit_call_failed", step=step.get("step_number"), error=str(exc))
            err_msg = str(exc)
            if any(keyword in err_msg.lower() for keyword in ("auth", "401", "key", "quota", "credit", "429", "model", "404")):
                raise RuntimeError(f"LLM code edit failed: {err_msg}") from exc
            continue

        # 1. If it's a new file or full rewrite code block
        code_block = extract_code_block(response_text)
        blocks = extract_search_replace_blocks(response_text)

        target_path.parent.mkdir(parents=True, exist_ok=True)

        if is_new_file or (not blocks and code_block):
            new_content = code_block if code_block is not None else response_text.strip()
            target_path.write_text(new_content, encoding="utf-8")
            applied_changes.append({
                "file_path": target_file_rel,
                "change_type": "create" if is_new_file else "modify",
                "lines_added": len(new_content.splitlines()),
                "lines_removed": len(existing_content.splitlines()),
                "diff": f"+ {len(new_content.splitlines())} lines written",
            })
            step["status"] = "completed"
            logger.info("file_updated_via_full_write", file=target_file_rel)

        elif blocks:
            success, updated_content, err_msg = apply_search_replace_edit(existing_content, blocks)
            if success:
                target_path.write_text(updated_content, encoding="utf-8")
                applied_changes.append({
                    "file_path": target_file_rel,
                    "change_type": "modify",
                    "lines_added": max(0, len(updated_content.splitlines()) - len(existing_content.splitlines())),
                    "lines_removed": max(0, len(existing_content.splitlines()) - len(updated_content.splitlines())),
                    "diff": f"Applied {len(blocks)} SEARCH/REPLACE block(s)",
                })
                step["status"] = "completed"
                logger.info("file_updated_via_search_replace", file=target_file_rel, blocks=len(blocks))
            else:
                logger.warning("search_replace_failed_falling_back_to_full_block", file=target_file_rel, error=err_msg)
                if code_block:
                    target_path.write_text(code_block, encoding="utf-8")
                    applied_changes.append({
                        "file_path": target_file_rel,
                        "change_type": "modify",
                        "lines_added": len(code_block.splitlines()),
                        "lines_removed": len(existing_content.splitlines()),
                        "diff": f"Fallback full write ({len(code_block.splitlines())} lines)",
                    })
                    step["status"] = "completed"

    # Compute overall git diff
    diff_data = get_workspace_git_diff(root)
    git_diff = diff_data.get("diff", "")

    # Fallback: if git_diff is empty but applied_changes were made, synthesize unified diff using difflib
    if not git_diff and applied_changes:
        diff_chunks: list[str] = []
        for change in applied_changes:
            rel = change.get("file_path", "")
            if not rel:
                continue
            t_path = root / rel
            bak_path = t_path.with_suffix(t_path.suffix + ".bak")

            old_lines: list[str] = []
            if bak_path.is_file():
                try:
                    old_lines = bak_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                except Exception:
                    old_lines = []

            new_lines: list[str] = []
            if t_path.is_file():
                try:
                    new_lines = t_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
                except Exception:
                    new_lines = []

            chunk = "".join(difflib.unified_diff(
                old_lines,
                new_lines,
                fromfile=f"a/{rel}",
                tofile=f"b/{rel}",
            ))
            if chunk.strip():
                diff_chunks.append(chunk.strip())
            else:
                desc = change.get("diff", "File modified")
                diff_chunks.append(f"--- a/{rel}\n+++ b/{rel}\n@@ -1,1 +1,1 @@\n+ {desc}")

        git_diff = "\n\n".join(diff_chunks)

    logger.info(
        "implementation_node_completed",
        files_modified=len(applied_changes),
        lines_added=diff_data.get("lines_added", 0) or len(git_diff.splitlines()),
        lines_removed=diff_data.get("lines_removed", 0),
    )

    return {
        "applied_changes": applied_changes,
        "git_diff": git_diff,
    }
