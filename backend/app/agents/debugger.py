"""
Failure Analysis, Root Cause Diagnosis, and Self-Correction Agent Node.
"""

from __future__ import annotations

from typing import Any

from app.agents.prompts import FAILURE_ANALYSIS_SYSTEM_PROMPT, extract_json_from_response
from app.agents.state import AgentState, ExecutionPlan, PlanStep
from app.api.dependencies import get_llm_provider
from app.core.logging import get_logger
from app.llm.provider import Message

logger = get_logger(__name__)


def categorize_failure(log_text: str) -> str:
    """
    Categorize error log into standard failure categories.
    """
    text_lower = (log_text or "").lower()

    if "syntaxerror" in text_lower or "indentationerror" in text_lower or "invalid syntax" in text_lower:
        return "syntax_error"
    elif "modulenotfounderror" in text_lower or "importerror" in text_lower or "cannot find module" in text_lower:
        return "import_error"
    elif "assertionerror" in text_lower or "assert " in text_lower or "failed assert" in text_lower or "expect(" in text_lower:
        return "assertion_failure"
    elif "no module named" in text_lower or "package not installed" in text_lower or "command not found" in text_lower:
        return "missing_dependency"
    elif any(err in text_lower for err in ("typeerror", "attributeerror", "nameerror", "keyerror", "valueerror", "indexerror")):
        return "runtime_exception"

    return "runtime_exception"


async def failure_analysis_node(state: AgentState) -> dict[str, Any]:
    """
    Analyzes test failures, extracts failing lines and error messages,
    prompts the LLM to diagnose root causes, and formulates a revised fix plan.
    """
    task_id = state.get("task_id", "unknown")
    test_passed = state.get("test_passed", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    # If tests passed, no failure analysis or retries needed
    if test_passed:
        logger.info("tests_passed_skipping_failure_analysis", task_id=task_id)
        return {
            "should_retry": False,
            "failure_analysis": None,
            "failure_category": None,
        }

    # Increment retry counter
    new_retry_count = retry_count + 1
    should_retry = new_retry_count < max_retries

    test_results = state.get("test_results", {})
    error_log = state.get("last_error_log") or test_results.get("failures_summary") or "Tests failed with exit code 1"
    category = categorize_failure(error_log)

    logger.info(
        "failure_analysis_started",
        task_id=task_id,
        attempt=new_retry_count,
        max_retries=max_retries,
        category=category,
        should_retry=should_retry,
    )

    llm = get_llm_provider()
    applied_changes = state.get("applied_changes", [])
    changes_desc = "\n".join(f"- {c.get('file_path')}: {c.get('diff')}" for c in applied_changes)

    user_prompt = f"""Task Description:
{state.get('task_description', '')}

Applied Changes:
{changes_desc}

Test Failure Logs & Trace:
{error_log}

Diagnose the root cause and generate revised corrective modification steps."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=FAILURE_ANALYSIS_SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.error("failure_analysis_llm_failed", error=str(exc))
        data = {}

    diagnosed_root_cause = data.get("diagnosed_root_cause") or f"Failure categorized as {category} from test output."
    fix_strategy = data.get("fix_strategy") or "Apply targeted fixes to resolve failing test assertions."
    revised_steps_raw = data.get("revised_steps") or []

    # Update execution plan with revised steps for the next implementation pass
    existing_plan = state.get("execution_plan") or {}
    new_steps: list[PlanStep] = []

    for i, s in enumerate(revised_steps_raw, start=1):
        new_steps.append({
            "step_number": s.get("step_number", i),
            "action": s.get("action", "modify_code"),
            "target_file": s.get("target_file", data.get("failing_file") or "main.py"),
            "description": s.get("description", "Correct failing logic"),
            "rationale": s.get("rationale", fix_strategy),
            "status": "pending",
        })

    if not new_steps:
        new_steps = [{
            "step_number": 1,
            "action": "modify_code",
            "target_file": data.get("failing_file") or "main.py",
            "description": f"Fix {category} in {data.get('failing_file', 'code')}",
            "rationale": fix_strategy,
            "status": "pending",
        }]

    updated_plan: ExecutionPlan = {
        **existing_plan,
        "root_cause_analysis": diagnosed_root_cause,
        "steps": new_steps,
    }

    return {
        "retry_count": new_retry_count,
        "should_retry": should_retry,
        "failure_category": category,
        "failure_analysis": f"Root Cause: {diagnosed_root_cause}\nFix Strategy: {fix_strategy}",
        "execution_plan": updated_plan,
    }


# Prevent pytest from treating LangGraph node as unit test
failure_analysis_node.__test__ = False  # type: ignore[attr-defined]
