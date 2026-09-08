"""
Automated Test Generation and Sandbox Execution Agent Nodes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.agents.prompts import TEST_GENERATION_SYSTEM_PROMPT, extract_json_from_response
from app.agents.state import AgentState
from app.api.dependencies import get_llm_provider
from app.core.logging import get_logger
from app.core.security import safe_path
from app.database.models import TestRun
from app.database.session import get_session_factory
from app.llm.provider import Message
from app.sandbox.runner import execute_sandbox_tests

logger = get_logger(__name__)


async def test_generation_node(state: AgentState) -> dict[str, Any]:
    """
    Generates targeted unit and regression test cases for the applied changes.
    """
    task_id = state.get("task_id", "unknown")
    workspace_path = state.get("workspace_path")
    applied_changes = state.get("applied_changes", [])
    framework = state.get("primary_language", "Python")

    logger.info("test_generation_node_started", task_id=task_id, changes_count=len(applied_changes))

    if not workspace_path:
        return {"generated_tests": []}

    root = Path(workspace_path).resolve()
    llm = get_llm_provider()

    # Summarize changes
    changes_desc = "\n".join(
        f"- File: {c.get('file_path')} ({c.get('change_type')}): {c.get('diff', '')}"
        for c in applied_changes
    ) or "Code modified to satisfy task requirements."

    prompt = f"""Task Description:
{state.get('task_description', '')}

Applied Code Modifications:
{changes_desc}

Target Framework: {framework} (pytest for Python, jest for Node/TS)

Generate comprehensive, non-trivial test cases for these modifications."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=TEST_GENERATION_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.warning("test_generation_llm_failed", error=str(exc))
        data = {}

    test_file_path = data.get("test_file_path") or ("tests/unit/test_generated_auto.py" if "python" in framework.lower() else "tests/generated.test.ts")
    test_code = data.get("test_code") or ""
    test_cases = data.get("test_cases") or []

    generated_tests: list[dict[str, Any]] = []

    if test_code:
        try:
            target_path = safe_path(root, test_file_path)
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(test_code, encoding="utf-8")

            generated_tests.append({
                "test_file": test_file_path,
                "cases_count": len(test_cases),
                "cases": test_cases,
            })
            logger.info("generated_test_file_written", file=test_file_path, cases=len(test_cases))
        except Exception as exc:
            logger.error("failed_writing_generated_test", error=str(exc))

    return {"generated_tests": generated_tests}


async def test_execution_node(state: AgentState) -> dict[str, Any]:
    """
    Executes the test suite in the isolated sandbox, logs test runs to DB,
    and updates AgentState with parsed pass/fail metrics.
    """
    task_id = state.get("task_id", "unknown")
    workspace_path = state.get("workspace_path")
    framework = state.get("primary_language", "Python")

    logger.info("test_execution_node_started", task_id=task_id)

    if not workspace_path:
        return {
            "test_passed": True,
            "test_results": {},
            "tests_total": 0,
            "tests_passed_count": 0,
            "tests_failed_count": 0,
        }

    run_result = await execute_sandbox_tests(
        workspace_path=workspace_path,
        framework="pytest" if "python" in framework.lower() else "jest",
        timeout_seconds=120,
    )

    parsed = run_result.parsed_results
    passed_count = parsed.get("passed", 0)
    failed_count = parsed.get("failed", 0)
    total_count = parsed.get("total", passed_count + failed_count)
    is_success = run_result.is_success

    # Persist TestRun record to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            test_run_record = TestRun(
                task_id=task_id,
                attempt_number=state.get("retry_count", 0) + 1,
                command=run_result.command,
                exit_code=run_result.exit_code,
                stdout=run_result.stdout,
                stderr=run_result.stderr,
                duration_seconds=run_result.duration_seconds,
                timed_out=run_result.timed_out,
                tests_total=total_count,
                tests_passed=passed_count,
                tests_failed=failed_count,
                tests_skipped=parsed.get("skipped", 0),
                results=parsed.get("items", []),
            )
            session.add(test_run_record)
            await session.commit()
            logger.info("test_run_persisted_to_db", task_id=task_id, test_run_id=test_run_record.id)
        except Exception as exc:
            logger.warning("failed_to_persist_test_run", error=str(exc))

    return {
        "test_passed": is_success,
        "test_results": parsed,
        "tests_total": total_count,
        "tests_passed_count": passed_count,
        "tests_failed_count": failed_count,
        "last_error_log": run_result.stderr if not is_success else None,
    }


# Prevent pytest from treating LangGraph nodes as unit tests
test_generation_node.__test__ = False  # type: ignore[attr-defined]
test_execution_node.__test__ = False  # type: ignore[attr-defined]

