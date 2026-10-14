"""
Pydantic schemas for Task API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    """Request body for POST /api/tasks"""

    repository_id: str = Field(..., description="Repository to operate on")
    description: str = Field(
        ...,
        min_length=3,
        max_length=4096,
        description="Natural language description of the engineering task",
        examples=["Add a factorial function in calculator.py and unit tests"],
    )
    branch: Optional[str] = Field(
        default=None,
        description="Branch to work on (defaults to repository default branch)",
    )
    target_commit: Optional[str] = Field(
        default=None,
        description="Specific commit SHA to base the task on",
    )


class TaskResponse(BaseModel):
    """Response schema for a task."""

    id: str
    repository_id: str
    snapshot_id: Optional[str]
    description: str
    status: str
    branch: Optional[str]
    target_commit: Optional[str]
    retry_count: int
    error_message: Optional[str]
    execution_plan: Optional[dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TaskStatusResponse(BaseModel):
    """Lightweight status check response."""

    task_id: str
    status: str
    retry_count: int
    current_step: Optional[str] = None
    progress_percent: Optional[float] = None
    error_message: Optional[str] = None


class TaskCancelResponse(BaseModel):
    """Response after cancelling a task."""

    task_id: str
    status: str
    message: str


class TaskGitPushRequest(BaseModel):
    """Request body for POST /api/tasks/{task_id}/push"""

    commit_message: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Custom commit message (defaults to AI task summary)",
    )
    branch: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Target branch to push to (defaults to repository default branch)",
    )
    github_token: Optional[str] = Field(
        default=None,
        description="GitHub Personal Access Token (optional if GITHUB_TOKEN is set in .env)",
    )


class TaskGitPushResponse(BaseModel):
    """Response after committing and pushing task changes to GitHub."""

    task_id: str
    commit_sha: str
    branch: str
    commit_url: str
    message: str

