"""
Unit tests for the Solution Verification node.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from app.agents.state import AgentState
from app.agents.verifier import verification_node


@pytest.mark.asyncio
async def test_verification_node_success(tmp_path):
    # Setup temporary .bak file
    bak_file = tmp_path / "app.py.bak"
    bak_file.write_text("backup")

    state: AgentState = {
        "task_id": "test-v-1",
        "workspace_path": str(tmp_path),
        "test_passed": True,
        "tests_failed_count": 0,
        "tests_passed_count": 5,
        "git_diff": "diff --git a/app.py b/app.py",
        "retry_count": 0,
    }

    result = await verification_node(state)

    assert result["verification_status"] == "SUCCESS"
    assert result["final_status"] == "succeeded"

    # Verify .bak was cleaned up
    assert not bak_file.exists()


@pytest.mark.asyncio
async def test_verification_node_failed_after_max_retries():
    state: AgentState = {
        "task_id": "test-v-2",
        "test_passed": False,
        "tests_failed_count": 2,
        "tests_passed_count": 3,
        "retry_count": 3,
        "max_retries": 3,
        "git_diff": "diff ...",
    }

    result = await verification_node(state)

    assert result["verification_status"] == "FAILED"
    assert result["final_status"] == "failed"
