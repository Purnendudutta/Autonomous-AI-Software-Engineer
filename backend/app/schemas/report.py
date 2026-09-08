"""
Pydantic schemas for test results, review findings, and the final PR report.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ─── Test Results ─────────────────────────────────────────────────────────────

class TestResultItem(BaseModel):
    """Result of a single test case."""

    test_name: str
    test_file: Optional[str]
    status: str  # passed | failed | skipped | error
    duration_seconds: Optional[float]
    failure_message: Optional[str]

    model_config = {"from_attributes": True}


class TestRunResponse(BaseModel):
    """Full test run with all individual results."""

    id: str
    task_id: str
    attempt_number: int
    command: Optional[str]
    exit_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
    duration_seconds: Optional[float]
    timed_out: bool
    tests_total: Optional[int]
    tests_passed: Optional[int]
    tests_failed: Optional[int]
    tests_skipped: Optional[int]
    results: list[TestResultItem] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Code Review ──────────────────────────────────────────────────────────────

class ReviewFindingResponse(BaseModel):
    """A single code review finding."""

    id: str
    severity: str      # high | medium | low | info
    category: str      # security | correctness | performance | maintainability
    file_path: Optional[str]
    line_number: Optional[int]
    issue: str
    recommendation: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class CodeReviewResponse(BaseModel):
    """All findings from the AI code review agent."""

    task_id: str
    findings: list[ReviewFindingResponse]
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    generated_at: datetime


# ─── Final PR Report ─────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    """Full pull-request-style report."""

    id: str
    task_id: str
    title: str
    summary: Optional[str]
    problem_description: Optional[str]
    root_cause: Optional[str]
    changes_description: Optional[str]
    verification_status: str  # SUCCESS | PARTIAL_SUCCESS | FAILED | BLOCKED
    git_diff: Optional[str]
    full_report_markdown: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
