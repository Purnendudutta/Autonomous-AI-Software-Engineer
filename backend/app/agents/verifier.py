"""
Solution Verification Agent Node.

Validates the final outcome of tests and code modifications, assigns verification
status, and cleans up temporary backup files.
"""

from __future__ import annotations

from typing import Any

from app.agents.patcher import cleanup_file_backups
from app.agents.state import AgentState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def verification_node(state: AgentState) -> dict[str, Any]:
    """
    Evaluates final tests, git diff cleanliness, and determines final status.
    """
    task_id = state.get("task_id", "unknown")
    workspace_path = state.get("workspace_path")
    test_passed = state.get("test_passed", False)
    failed_count = state.get("tests_failed_count", 0)
    passed_count = state.get("tests_passed_count", 0)
    git_diff = state.get("git_diff", "")
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    logger.info("verification_node_started", task_id=task_id, test_passed=test_passed)

    # 1. Determine Verification Status
    if test_passed and failed_count == 0:
        verification_status = "SUCCESS"
        final_status = "succeeded"
    elif not git_diff and not test_passed:
        verification_status = "BLOCKED"
        final_status = "blocked"
    elif failed_count > 0 and retry_count >= max_retries:
        verification_status = "FAILED"
        final_status = "failed"
    elif passed_count > 0 and failed_count > 0:
        verification_status = "PARTIAL_SUCCESS"
        final_status = "partial_success"
    else:
        verification_status = "SUCCESS" if test_passed else "FAILED"
        final_status = "succeeded" if test_passed else "failed"

    # 2. Cleanup workspace temporary backup files
    if workspace_path:
        cleaned = cleanup_file_backups(workspace_path)
        logger.debug("verification_cleaned_backups", count=cleaned)

    logger.info(
        "verification_completed",
        task_id=task_id,
        verification_status=verification_status,
        final_status=final_status,
    )

    return {
        "verification_status": verification_status,
        "final_status": final_status,
    }


# Prevent pytest from treating LangGraph node as unit test
verification_node.__test__ = False  # type: ignore[attr-defined]
