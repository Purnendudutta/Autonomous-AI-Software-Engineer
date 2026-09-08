"""
Unit tests for the Failure Analysis and Self-Correction Debugger node.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.debugger import categorize_failure, failure_analysis_node
from app.agents.state import AgentState
from app.llm.provider import LLMResponse


def test_categorize_failure_patterns():
    assert categorize_failure("SyntaxError: invalid syntax (auth.py, line 12)") == "syntax_error"
    assert categorize_failure("ModuleNotFoundError: No module named 'jwt'") == "import_error"
    assert categorize_failure("AssertionError: assert 401 == 200") == "assertion_failure"
    assert categorize_failure("TypeError: 'NoneType' object is not subscriptable") == "runtime_exception"
    assert categorize_failure("pytest: command not found") == "missing_dependency"


@pytest.mark.asyncio
async def test_failure_analysis_node_when_tests_pass():
    state: AgentState = {
        "task_id": "test-pass-1",
        "test_passed": True,
        "retry_count": 0,
    }

    result = await failure_analysis_node(state)
    assert result["should_retry"] is False
    assert result["failure_analysis"] is None


@pytest.mark.asyncio
async def test_failure_analysis_node_generates_retry_plan():
    mock_llm_json = json.dumps({
        "failure_category": "assertion_failure",
        "diagnosed_root_cause": "The token validator returned 403 instead of 401 on expired token",
        "failing_file": "app/auth.py",
        "failing_line_number": 35,
        "fix_strategy": "Change HTTPException status_code from 403 to 401",
        "revised_steps": [
            {
                "step_number": 1,
                "action": "modify_code",
                "target_file": "app/auth.py",
                "description": "Return 401 for expired token",
                "rationale": "Fixes test_expired_token assertion",
            }
        ],
    })

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=LLMResponse(content=f"```json\n{mock_llm_json}\n```", model="mock")
    )

    state: AgentState = {
        "task_id": "test-retry-1",
        "task_description": "Handle token expiration with 401 status",
        "test_passed": False,
        "retry_count": 0,
        "max_retries": 3,
        "last_error_log": "AssertionError: assert 403 == 401",
        "applied_changes": [{"file_path": "app/auth.py", "diff": "..."}],
    }

    with patch("app.agents.debugger.get_llm_provider", return_value=mock_llm):
        result = await failure_analysis_node(state)

        assert result["retry_count"] == 1
        assert result["should_retry"] is True
        assert result["failure_category"] == "assertion_failure"
        assert "The token validator returned 403" in result["failure_analysis"]

        # Check updated execution plan
        updated_plan = result["execution_plan"]
        assert len(updated_plan["steps"]) == 1
        assert updated_plan["steps"][0]["target_file"] == "app/auth.py"
