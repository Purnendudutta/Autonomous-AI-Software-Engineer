"""
Task Understanding, Code Retrieval, and Structured Planning agent nodes.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.prompts import (
    PLANNER_SYSTEM_PROMPT,
    TASK_UNDERSTANDING_SYSTEM_PROMPT,
    extract_json_from_response,
)
from app.agents.state import AgentState, ExecutionPlan, PlanStep
from app.api.dependencies import get_embedding_provider, get_llm_provider
from app.core.logging import get_logger
from app.database.session import get_session_factory
from app.llm.provider import Message
from app.rag.retriever import CodebaseRetriever

logger = get_logger(__name__)


async def task_understanding(state: AgentState) -> dict[str, Any]:
    """
    Analyzes the user's task description to classify intent, extract target
    symbols, and generate targeted search queries for Codebase RAG.
    """
    task_desc = state.get("task_description", "")
    repo_summary = state.get("repository_summary", "")
    task_id = state.get("task_id", "unknown")

    logger.info("task_understanding_started", task_id=task_id, task_desc=task_desc[:60])

    llm = get_llm_provider()
    user_prompt = f"""Repository Summary:
{repo_summary}

User Task Request:
{task_desc}

Analyze this task and return the required JSON schema."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=TASK_UNDERSTANDING_SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.warning("task_understanding_llm_failed_using_heuristic", error=str(exc))
        data = {}

    task_intent = data.get("task_intent") or ("bug_fix" if any(w in task_desc.lower() for w in ("fix", "bug", "error", "fail")) else "feature")
    identified_symbols = data.get("target_symbols") or []
    suggested_queries = data.get("rag_search_queries") or [task_desc]

    logger.info(
        "task_understanding_completed",
        task_intent=task_intent,
        symbols_count=len(identified_symbols),
        queries_count=len(suggested_queries),
    )

    return {
        "task_intent": task_intent,
        "identified_symbols": identified_symbols,
        "suggested_search_queries": suggested_queries,
    }


async def code_retrieval(state: AgentState) -> dict[str, Any]:
    """
    Retrieves the most relevant code chunks from pgvector using the queries
    generated in task_understanding.
    """
    snapshot_id = state.get("snapshot_id")
    task_id = state.get("task_id", "unknown")
    queries = state.get("suggested_search_queries") or [state.get("task_description", "")]
    embedding_provider = get_embedding_provider()

    logger.info("code_retrieval_started", task_id=task_id, snapshot_id=snapshot_id)

    if not snapshot_id:
        return {"retrieved_chunks": [], "rag_context_formatted": "No repository snapshot available."}

    all_chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()

    session_factory = get_session_factory()
    async with session_factory() as session:
        retriever = CodebaseRetriever(session=session, embedding_provider=embedding_provider)

        for q in queries[:3]:
            try:
                results = await retriever.search(
                    snapshot_id=snapshot_id,
                    query=q,
                    limit=4,
                    similarity_threshold=0.25,
                )
                for r in results:
                    if r.id not in seen_chunk_ids:
                        seen_chunk_ids.add(r.id)
                        all_chunks.append(r.model_dump())
            except Exception as exc:
                logger.warning("retrieval_query_failed", query=q, error=str(exc))

    # Format code context for LLM prompt
    formatted_chunks: list[str] = []
    for idx, c in enumerate(all_chunks, start=1):
        formatted_chunks.append(
            f"--- [Chunk {idx}] File: {c['file_path']} (L{c['start_line']}-L{c['end_line']}) | Symbol: {c.get('symbol_name') or 'N/A'} ---\n{c['content']}"
        )

    rag_context = "\n\n".join(formatted_chunks) if formatted_chunks else "No relevant code chunks found."

    logger.info("code_retrieval_completed", total_chunks=len(all_chunks))

    return {
        "retrieved_chunks": all_chunks,
        "rag_context_formatted": rag_context,
    }


def discover_workspace_files(workspace_path: str, max_files: int = 80) -> list[str]:
    """Return sorted relative file paths inside the workspace, excluding ignored directories."""
    import os
    from pathlib import Path
    from app.repository.analyzer import IGNORED_DIRECTORIES, is_ignored_file

    if not workspace_path:
        return []
    root = Path(workspace_path).resolve()
    if not root.exists():
        return []

    found: list[str] = []
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")]
        current = Path(dirpath)
        for fname in sorted(filenames):
            if fname.endswith(".bak") or fname.startswith("."):
                continue
            fpath = current / fname
            if is_ignored_file(fpath, root):
                continue
            try:
                found.append(str(fpath.relative_to(root)).replace("\\", "/"))
            except ValueError:
                continue
            if len(found) >= max_files:
                return found
    return found


def select_best_target_file(
    workspace_path: str,
    task_description: str,
    primary_language: str = "Python",
) -> str:
    """Pick the best target file from the workspace based on the task description."""
    import re
    from pathlib import Path

    files = discover_workspace_files(workspace_path)
    desc_lower = task_description.lower()

    for f in files:
        fname = Path(f).name.lower()
        if f.lower() in desc_lower or (len(fname) > 3 and fname in desc_lower):
            return f

    explicit_match = re.search(r"\b([a-zA-Z0-9_\-/]+\.(?:py|java|js|ts|html|css|md|cpp|c))\b", task_description)
    if explicit_match:
        return explicit_match.group(1).lstrip("/")

    if any(w in desc_lower for w in ("readme", "documentation", "markdown", "project guide")):
        for f in files:
            if Path(f).name.lower() == "readme.md":
                return f
        return "README.md"

    source_exts = (".py", ".java", ".js", ".ts", ".cpp", ".c", ".go", ".rs")
    non_test_source_files = [
        f for f in files
        if f.endswith(source_exts)
        and "test" not in f.lower()
        and not Path(f).name.startswith("__")
        and Path(f).name.lower() not in ("setup.py", "conftest.py")
    ]

    words = [
        w for w in re.findall(r"[a-zA-Z]{3,}", desc_lower)
        if w not in ("add", "fix", "create", "write", "function", "method", "file", "code", "test", "the", "and", "for", "with")
    ]
    for f in non_test_source_files:
        if any(w in f.lower() for w in words):
            return f

    if non_test_source_files:
        return non_test_source_files[0]

    any_source = [f for f in files if f.endswith(source_exts) and not Path(f).name.startswith("__")]
    if any_source:
        return any_source[0]

    lang = (primary_language or "Python").lower()
    if "java" in lang and "javascript" not in lang:
        return "Solution.java"
    elif "javascript" in lang:
        return "index.js"
    elif "typescript" in lang:
        return "index.ts"
    return "main.py"


def build_fallback_execution_plan(
    workspace_path: str,
    task_description: str,
    primary_language: str = "Python",
    task_intent: str = "feature",
) -> ExecutionPlan:
    """Create a structured ExecutionPlan grounded in actual workspace files."""
    target_file = select_best_target_file(workspace_path, task_description, primary_language)
    files = discover_workspace_files(workspace_path)

    test_files = [f for f in files if "test" in f.lower() and f.endswith((".py", ".js", ".ts", ".java"))]
    target_files = [target_file]
    if test_files and target_file.endswith(".py"):
        target_files.append(test_files[0])

    steps: list[PlanStep] = [
        {
            "step_number": 1,
            "action": "modify_code",
            "target_file": target_file,
            "description": f"Implement requested changes in `{target_file}`: {task_description}",
            "rationale": "Fulfills the engineering task specification with modular, well-documented code.",
            "status": "pending",
        }
    ]

    if test_files and target_file.endswith(".py") and target_file != test_files[0]:
        steps.append({
            "step_number": 2,
            "action": "modify_code",
            "target_file": test_files[0],
            "description": f"Add unit test assertions in `{test_files[0]}` to verify `{target_file}`",
            "rationale": "Ensures automated test verification passes in the isolated sandbox.",
            "status": "pending",
        })

    return {
        "task_type": task_intent or "feature",
        "root_cause_analysis": (
            f"Analyzed repository workspace ({len(files)} files indexed, primary language: {primary_language}). "
            f"Selected `{target_file}` as the primary target module to implement: \"{task_description}\"."
        ),
        "architecture_overview": (
            f"Modular implementation in `{target_file}` adhering to {primary_language} conventions, "
            "with type annotations, docstrings, and automated verification."
        ),
        "target_files": target_files,
        "steps": steps,
        "test_strategy": [
            f"Verify syntax and execution of `{target_file}`",
            "Run automated test suite in isolated sandbox",
        ],
        "verification_criteria": [
            "Target module compiles and executes without syntax or runtime errors",
            "All existing and newly generated unit tests pass",
        ],
    }


async def plan(state: AgentState) -> dict[str, Any]:
    """
    Generates a structured, validated step-by-step execution plan from the
    retrieved code context and task description.
    """
    task_desc = state.get("task_description", "")
    rag_context = state.get("rag_context_formatted", "")
    repo_summary = state.get("repository_summary", "")
    workspace_path = state.get("workspace_path", "")
    primary_language = state.get("primary_language", "Python")
    task_id = state.get("task_id", "unknown")

    logger.info("planning_started", task_id=task_id)

    workspace_files = discover_workspace_files(workspace_path)
    files_context = "\n".join(f"- {f}" for f in workspace_files[:60]) if workspace_files else "No files listed."

    llm = get_llm_provider()
    user_prompt = f"""Repository Overview:
{repo_summary}

Repository Files in Workspace:
{files_context}

User Task Description:
{task_desc}

Relevant Code Chunks from Codebase RAG:
{rag_context}

Produce the structured Execution Plan JSON according to the schema. Ensure target_files use real paths from the workspace."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=PLANNER_SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.warning("planning_llm_fallback", error=str(exc))
        data = {}

    if not data or not data.get("steps"):
        fallback_plan = build_fallback_execution_plan(
            workspace_path=workspace_path,
            task_description=task_desc,
            primary_language=primary_language,
            task_intent=state.get("task_intent") or "feature",
        )
        return {
            "execution_plan": fallback_plan,
            "identified_root_cause": fallback_plan["root_cause_analysis"],
            "affected_files": fallback_plan["target_files"],
            "file_tree_paths": workspace_files,
        }

    # Extract or build structured plan
    task_type = data.get("task_type") or state.get("task_intent") or "feature"
    root_cause = data.get("root_cause_analysis") or "Root cause determined during execution."
    target_files = data.get("target_files") or []
    steps_raw = data.get("steps") or []

    best_default_file = select_best_target_file(workspace_path, task_desc, primary_language)
    if not target_files:
        target_files = [best_default_file]

    steps: list[PlanStep] = []
    for i, s in enumerate(steps_raw, start=1):
        tf = s.get("target_file") or best_default_file
        if tf == "unknown":
            tf = best_default_file
        steps.append({
            "step_number": s.get("step_number", i),
            "action": s.get("action", "modify_code"),
            "target_file": tf,
            "description": s.get("description", "Execute planned modification"),
            "rationale": s.get("rationale", "Fulfill task requirements"),
            "status": "pending",
        })

    plan_obj: ExecutionPlan = {
        "task_type": task_type,
        "root_cause_analysis": root_cause,
        "architecture_overview": data.get("architecture_overview") or "Modular software architecture.",
        "target_files": target_files,
        "steps": steps,
        "test_strategy": data.get("test_strategy") or ["Execute automated test suite in sandbox."],
        "verification_criteria": data.get("verification_criteria") or ["All unit tests pass."],
    }

    logger.info(
        "planning_completed",
        target_files=target_files,
        total_steps=len(steps),
    )

    return {
        "execution_plan": plan_obj,
        "identified_root_cause": root_cause,
        "affected_files": target_files,
        "file_tree_paths": workspace_files,
    }
