"""
Unit tests for automated test generation and sandbox execution nodes.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.state import AgentState
from app.agents.tester import test_execution_node, test_generation_node
from app.llm.provider import LLMResponse
from app.sandbox.runner import TestRunResult


@pytest.mark.asyncio
async def test_test_generation_node(tmp_path):
    mock_test_json = json.dumps({
        "test_file_path": "tests/unit/test_calculator.py",
        "framework": "pytest",
        "test_code": "import pytest\n\ndef test_add():\n    assert 1 + 1 == 2\n",
        "test_cases": [
            {"name": "test_add", "description": "verifies addition logic"}
        ],
    })

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=LLMResponse(content=f"```json\n{mock_test_json}\n```", model="mock")
    )

    state: AgentState = {
        "task_id": "test-gen-1",
        "workspace_path": str(tmp_path),
        "primary_language": "Python",
        "applied_changes": [
            {"file_path": "calc.py", "change_type": "modify", "lines_added": 5, "lines_removed": 1, "diff": "..."}
        ],
    }

    with patch("app.agents.tester.get_llm_provider", return_value=mock_llm):
        result = await test_generation_node(state)

        assert len(result["generated_tests"]) == 1
        assert result["generated_tests"][0]["test_file"] == "tests/unit/test_calculator.py"

        # Verify test file on disk
        target_file = tmp_path / "tests/unit/test_calculator.py"
        assert target_file.exists()
        assert "def test_add():" in target_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_test_execution_node(tmp_path):
    mock_run_result = TestRunResult(
        command="python -m pytest tests/ -v",
        exit_code=0,
        stdout="== 3 passed in 0.20s ==",
        stderr="",
        duration_seconds=0.20,
        timed_out=False,
        parsed_results={"passed": 3, "failed": 0, "total": 3, "skipped": 0, "items": []},
    )

    state: AgentState = {
        "task_id": "test-exec-1",
        "workspace_path": str(tmp_path),
        "primary_language": "Python",
        "retry_count": 0,
    }

    with patch("app.agents.tester.execute_sandbox_tests", new_callable=AsyncMock) as mock_runner:
        mock_runner.return_value = mock_run_result

        result = await test_execution_node(state)

        assert result["test_passed"] is True
        assert result["tests_total"] == 3
        assert result["tests_passed_count"] == 3
        assert result["tests_failed_count"] == 0
