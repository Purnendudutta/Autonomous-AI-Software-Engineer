"""
Unit tests for the PR Report Generator node.
"""

from __future__ import annotations

import pytest

from app.agents.reporter import final_report_node, generate_pr_markdown_report
from app.agents.state import AgentState


def test_generate_pr_markdown_report():
    state: AgentState = {
        "task_id": "test-rep-1",
        "task_description": "Fix token expiration bug in auth service",
        "identified_root_cause": "Token validator compared seconds instead of milliseconds",
        "verification_status": "SUCCESS",
        "tests_total": 4,
        "tests_passed_count": 4,
        "tests_failed_count": 0,
        "applied_changes": [
            {"file_path": "app/auth.py", "change_type": "modify", "diff": "Fixed time comparison"}
        ],
        "review_findings": [
            {
                "severity": "low",
                "category": "quality",
                "file_path": "app/auth.py",
                "line_number": 15,
                "issue": "Add docstring",
                "recommendation": "Document token format",
            }
        ],
        "git_diff": "diff --git a/app/auth.py b/app/auth.py\n+ return exp > now",
        "retry_count": 0,
    }

    report = generate_pr_markdown_report(state)

    assert "# Pull Request: Fix token expiration bug in auth service" in report
    assert "Token validator compared seconds instead of milliseconds" in report
    assert "Verification Status**: `SUCCESS`" in report
    assert "Total Tests Executed**: `4`" in report
    assert "app/auth.py" in report
    assert "diff --git a/app/auth.py b/app/auth.py" in report


@pytest.mark.asyncio
async def test_final_report_node_persists():
    state: AgentState = {
        "task_id": "test-rep-2",
        "task_description": "Add healthcheck endpoint",
        "verification_status": "SUCCESS",
        "final_status": "succeeded",
        "tests_total": 2,
        "tests_passed_count": 2,
        "git_diff": "+def health(): return 'OK'",
    }

    result = await final_report_node(state)

    assert "final_report_markdown" in result
    assert "# Pull Request: Add healthcheck endpoint" in result["final_report_markdown"]
    assert result["final_status"] == "succeeded"
