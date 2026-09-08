"""
Pydantic schemas for Repository, Snapshot, FileTree, and Code Intelligence endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class RepositoryAnalyzeRequest(BaseModel):
    """Request body for POST /api/repositories/analyze"""

    url: str = Field(
        ...,
        description="GitHub repository URL",
        examples=["https://github.com/fastapi/fastapi"],
    )
    branch: Optional[str] = Field(
        default=None,
        description="Target branch (defaults to repository default branch)",
    )
    commit_sha: Optional[str] = Field(
        default=None,
        description="Specific commit SHA to analyze (overrides branch tip)",
        min_length=7,
        max_length=40,
    )
    task_description: Optional[str] = Field(
        default=None,
        description="Optional initial task description",
        max_length=4096,
    )

    @field_validator("url")
    @classmethod
    def validate_github_url(cls, v: str) -> str:
        from app.core.security import validate_github_url
        validate_github_url(v)
        return v.strip().rstrip("/")


class LanguageStat(BaseModel):
    """Language breakdown details."""
    name: str
    file_count: int
    lines_of_code: int
    percentage: float


class FrameworkInfo(BaseModel):
    """Detected framework and its category."""
    name: str
    category: str  # web_framework | orm | testing | build | ml | ui
    version: Optional[str] = None
    config_file: Optional[str] = None


class FileTreeNode(BaseModel):
    """Hierarchical file tree node."""
    name: str
    path: str
    is_dir: bool
    size_bytes: int = 0
    extension: Optional[str] = None
    language: Optional[str] = None
    children: Optional[list[FileTreeNode]] = None


class RepositorySnapshotResponse(BaseModel):
    """Response schema for a repository snapshot."""

    id: str
    repository_id: str
    commit_sha: str
    branch: Optional[str] = None
    workspace_path: Optional[str] = None
    languages: Optional[dict[str, Any]] = None
    frameworks: Optional[list[Any]] = None
    file_count: Optional[int] = 0
    total_size_bytes: Optional[int] = 0
    summary: Optional[str] = None
    indexed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RepositoryResponse(BaseModel):
    """Response schema for a repository record."""

    id: str
    url: str
    owner: str
    name: str
    default_branch: Optional[str] = None
    is_private: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryWithSnapshotResponse(RepositoryResponse):
    """Repository with its latest snapshot details."""

    latest_snapshot: Optional[RepositorySnapshotResponse] = None


class FileContentResponse(BaseModel):
    """File content response for browsing repo files safely."""
    path: str
    filename: str
    size_bytes: int
    language: Optional[str]
    content: str
    is_truncated: bool = False
