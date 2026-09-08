"""
End-to-end integration test for the Autonomous AI Software Engineer.

Validates the complete 12-node LangGraph autonomous agent workflow from
task ingestion through planning, surgical code modification, test execution,
solution verification, code review, and pull-request report compilation.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.graph import agent_graph
from app.agents.state import AgentState
from app.llm.provider import LLMResponse
from app.sandbox.runner import TestRunResult


@pytest.mark.asyncio
async def test_complete_autonomous_agent_workflow(tmp_path: Path):
    # 1. Initialize sample repository workspace with git
    import git
    repo = git.Repo.init(tmp_path)

    # Initial buggy file
    auth_code = """
def validate_token(token: str) -> bool:
    # Bug: Always returns False
    return False
"""
    auth_file = tmp_path / "auth.py"
    auth_file.write_text(auth_code.strip(), encoding="utf-8")

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / "test_auth.py"
    test_file.write_text(
        "from auth import validate_token\n\ndef test_validate_token():\n    assert validate_token('valid_jwt') is True\n",
        encoding="utf-8",
    )

    repo.index.add(["auth.py", "tests/test_auth.py"])
    repo.index.commit("Initial commit")

    # 2. Mock LLM responses for each phase
    def mock_llm_dispatch(messages, **kwargs):
        prompt_text = " ".join(m.content for m in messages)

        # Task Understanding
        if "expert AI Software Architect" in prompt_text:
            return LLMResponse(
                content=json.dumps({
                    "task_intent": "bug_fix",
                    "problem_summary": "Fix token validation returning False",
                    "target_symbols": ["validate_token"],
                    "rag_search_queries": ["validate_token auth"],
                    "potential_files": ["auth.py"],
                }),
                model="mock",
            )

        # Planning
        elif "Principal Software Engineer and Architect" in prompt_text:
            return LLMResponse(
                content=json.dumps({
                    "task_type": "bug_fix",
                    "root_cause_analysis": "validate_token hardcoded to return False",
                    "architecture_overview": "Auth service module",
                    "target_files": ["auth.py"],
                    "steps": [
                        {
                            "step_number": 1,
                            "action": "modify_code",
                            "target_file": "auth.py",
                            "description": "Change return False to return bool(token)",
                            "rationale": "Fixes validate_token assertion",
                        }
                    ],
                    "test_strategy": ["Run pytest tests/test_auth.py"],
                    "verification_criteria": ["test_validate_token passes"],
                }),
                model="mock",
            )

        # Implementation (Search / Replace)
        elif "applying targeted, surgical code modifications" in prompt_text:
            return LLMResponse(
                content="""<<<<<<< SEARCH
def validate_token(token: str) -> bool:
    # Bug: Always returns False
    return False
=======
def validate_token(token: str) -> bool:
    return bool(token and token.startswith('valid'))
>>>>>>> REPLACE""",
                model="mock",
            )

        # Test Generation
        elif "expert QA and Software Testing Engineer" in prompt_text:
            return LLMResponse(
                content=json.dumps({
                    "test_file_path": "tests/test_regression_auth.py",
                    "framework": "pytest",
                    "test_code": "from auth import validate_token\n\ndef test_empty_token():\n    assert validate_token('') is False\n",
                    "test_cases": [{"name": "test_empty_token", "description": "verifies empty token rejected"}],
                }),
                model="mock",
            )

        # Code Review
        elif "Staff Software Engineer and Security Auditor" in prompt_text:
            return LLMResponse(
                content=json.dumps({
                    "findings": [
                        {
                            "severity": "low",
                            "category": "quality",
                            "file_path": "auth.py",
                            "line_number": 2,
                            "issue": "Add docstring for token format requirements",
                            "recommendation": "Document valid token prefix criteria",
                        }
                    ],
                    "high_count": 0,
                    "medium_count": 0,
                    "low_count": 1,
                    "info_count": 0,
                }),
                model="mock",
            )

        return LLMResponse(content="{}", model="mock")

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(side_effect=mock_llm_dispatch)

    mock_sandbox_result = TestRunResult(
        command="python -m pytest tests/ -v",
        exit_code=0,
        stdout="=== 2 passed in 0.12s ===",
        stderr="",
        duration_seconds=0.12,
        timed_out=False,
        parsed_results={"passed": 2, "failed": 0, "total": 2, "skipped": 0, "items": []},
    )

    # 3. Initial Agent State
    initial_state: AgentState = {
        "task_id": "e2e-task-100",
        "task_description": "Fix validate_token bug where valid tokens return False",
        "workspace_path": str(tmp_path),
        "primary_language": "Python",
        "retry_count": 0,
        "max_retries": 3,
    }

    # 4. Execute the complete StateGraph
    with patch("app.agents.planner.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.editor.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.tester.get_llm_provider", return_value=mock_llm), \
         patch("app.agents.tester.execute_sandbox_tests", new_callable=AsyncMock, return_value=mock_sandbox_result), \
         patch("app.agents.reviewer.get_llm_provider", return_value=mock_llm):

        final_state = await agent_graph.ainvoke(initial_state)

    # 5. Assert End-to-End Success Outcomes
    assert final_state["task_intent"] == "bug_fix"
    assert "validate_token" in final_state["identified_symbols"]
    assert len(final_state["execution_plan"]["steps"]) >= 1
    assert len(final_state["applied_changes"]) >= 1
    assert final_state["test_passed"] is True
    assert final_state["verification_status"] == "SUCCESS"
    assert final_state["final_status"] == "succeeded"
    assert len(final_state["review_findings"]) == 1
    assert "final_report_markdown" in final_state
    assert "# Pull Request:" in final_state["final_report_markdown"]

    # 6. Verify Workspace Changes on Disk
    modified_content = auth_file.read_text(encoding="utf-8")
    assert "return bool(token and token.startswith('valid'))" in modified_content
