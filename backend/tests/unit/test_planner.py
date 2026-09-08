"""
Unit tests for Task Understanding, JSON extraction, and Execution Planner nodes.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.planner import code_retrieval, plan, task_understanding
from app.agents.prompts import extract_json_from_response
from app.agents.state import AgentState
from app.llm.provider import LLMResponse


def test_extract_json_from_markdown():
    raw = """
Here is your plan:
```json
{
  "task_type": "bug_fix",
  "root_cause_analysis": "Missing token expiration check",
  "target_files": ["app/auth.py"],
  "steps": [
    {
      "step_number": 1,
      "action": "modify_code",
      "target_file": "app/auth.py",
      "description": "Add expiration validation",
      "rationale": "Prevents replay attack"
    }
  ],
  "test_strategy": ["pytest tests/test_auth.py"],
  "verification_criteria": ["All tests pass"]
}
```
"""
    data = extract_json_from_response(raw)
    assert data["task_type"] == "bug_fix"
    assert "app/auth.py" in data["target_files"]
    assert len(data["steps"]) == 1


@pytest.mark.asyncio
async def test_task_understanding_node():
    mock_llm_json = json.dumps({
        "task_intent": "bug_fix",
        "target_symbols": ["verify_token", "AuthMiddleware"],
        "rag_search_queries": ["verify_token expiration", "jwt decode"],
    })

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(content=f"```json\n{mock_llm_json}\n```", model="mock"))

    state: AgentState = {
        "task_id": "test-task-1",
        "task_description": "Fix token expiration in verify_token function",
        "repository_summary": "FastAPI Authentication Service",
    }

    with patch("app.agents.planner.get_llm_provider", return_value=mock_llm):
        result = await task_understanding(state)

        assert result["task_intent"] == "bug_fix"
        assert "verify_token" in result["identified_symbols"]
        assert len(result["suggested_search_queries"]) >= 1


@pytest.mark.asyncio
async def test_planning_node():
    mock_plan_json = json.dumps({
        "task_type": "bug_fix",
        "root_cause_analysis": "The decode method did not check 'exp' claim.",
        "target_files": ["app/auth/jwt.py", "tests/unit/test_jwt.py"],
        "steps": [
            {
                "step_number": 1,
                "action": "modify_code",
                "target_file": "app/auth/jwt.py",
                "description": "Add exp timestamp check",
                "rationale": "Ensure token freshness",
            }
        ],
        "test_strategy": ["Run pytest tests/unit/test_jwt.py"],
        "verification_criteria": ["All tests pass"],
    })

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(return_value=LLMResponse(content=f"```json\n{mock_plan_json}\n```", model="mock"))

    state: AgentState = {
        "task_id": "test-task-2",
        "task_description": "Fix expired tokens being accepted",
        "rag_context_formatted": "def verify_token(): pass",
        "repository_summary": "Python FastAPI Auth",
    }

    with patch("app.agents.planner.get_llm_provider", return_value=mock_llm):
        result = await plan(state)

        plan_obj = result["execution_plan"]
        assert plan_obj["task_type"] == "bug_fix"
        assert "app/auth/jwt.py" in plan_obj["target_files"]
        assert len(plan_obj["steps"]) == 1
        assert "The decode method did not check" in result["identified_root_cause"]
