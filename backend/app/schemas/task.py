"""
Pydantic schemas for Task API endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    """Request body for POST /api/tasks"""

    repository_id: str = Field(..., description="Repository to operate on")
    description: str = Field(
        ...,
        min_length=10,
        max_length=4096,
        description="Natural language description of the engineering task",
        examples=["Find and fix the authentication bug that causes token expiration errors"],
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
