"""
Pydantic schemas for agent steps, logs, and diff endpoint responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AgentStepResponse(BaseModel):
    """One observable step in the agent timeline."""

    id: str
    sequence: int
    node_name: str
    tool_name: Optional[str]
    input_summary: Optional[str]
    output_summary: Optional[str]
    status: str
    error: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentLogEvent(BaseModel):
    """
    Server-Sent Event payload for real-time agent progress streaming.

    Streamed to the frontend via GET /api/tasks/{task_id}/logs (SSE).
    """

    event_type: str  # step_started | step_completed | step_failed | task_done
    task_id: str
    sequence: int
    node_name: str
    tool_name: Optional[str] = None
    message: str
    status: str
    timestamp: datetime


class DiffResponse(BaseModel):
    """Git diff for all changes made by the agent."""

    task_id: str
    diff: str
    files_changed: list[str]
    lines_added: int
    lines_removed: int
    generated_at: datetime


class CodeChangeResponse(BaseModel):
    """A single file change made by the agent."""

    id: str
    file_path: str
    change_type: str  # created | modified | deleted
    explanation: Optional[str]
    diff: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
