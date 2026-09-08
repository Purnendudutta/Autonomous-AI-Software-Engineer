"""
Unit tests for the AI Code Review agent node.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.reviewer import code_review_node
from app.agents.state import AgentState
from app.llm.provider import LLMResponse


@pytest.mark.asyncio
async def test_code_review_node_empty_diff():
    state: AgentState = {
        "task_id": "test-rev-1",
        "git_diff": "",
    }
    result = await code_review_node(state)
    assert result["review_findings"] == []


@pytest.mark.asyncio
async def test_code_review_node_with_findings():
    mock_review_json = json.dumps({
        "findings": [
            {
                "severity": "medium",
                "category": "security",
                "file_path": "app/auth.py",
                "line_number": 25,
                "issue": "Missing expiration check on refresh token",
                "recommendation": "Add exp claim validation during token refresh",
            },
            {
                "severity": "low",
                "category": "quality",
                "file_path": "app/auth.py",
                "line_number": 40,
                "issue": "Type hint missing on return parameter",
                "recommendation": "Add -> TokenResponse type annotation",
            },
        ],
        "high_count": 0,
        "medium_count": 1,
        "low_count": 1,
        "info_count": 0,
    })

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=LLMResponse(content=f"```json\n{mock_review_json}\n```", model="mock")
    )

    state: AgentState = {
        "task_id": "test-rev-2",
        "task_description": "Enhance JWT auth security",
        "git_diff": "diff --git a/app/auth.py b/app/auth.py\n+def refresh_token(): pass",
    }

    with patch("app.agents.reviewer.get_llm_provider", return_value=mock_llm):
        result = await code_review_node(state)

        assert len(result["review_findings"]) == 2
        assert result["review_findings"][0]["severity"] == "medium"
        assert result["review_findings"][0]["category"] == "security"
        assert result["review_findings"][1]["severity"] == "low"
