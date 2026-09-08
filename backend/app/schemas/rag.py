"""
Pydantic schemas for Code Search and RAG endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class CodeSearchRequest(BaseModel):
    """Request payload for semantic and hybrid code search."""

    query: str = Field(
        ...,
        min_length=2,
        max_length=2048,
        description="Natural language query or code symbol to search for",
        examples=["authentication token verification middleware", "def login_user"],
    )
    limit: int = Field(default=8, ge=1, le=50, description="Max chunks to return")
    similarity_threshold: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Minimum relevance similarity threshold (0.0 - 1.0)"
    )
    language: Optional[str] = Field(default=None, description="Filter by programming language (e.g. 'Python', 'TypeScript')")
    symbol_type: Optional[str] = Field(default=None, description="Filter by symbol type (e.g. 'function', 'class', 'route', 'model')")
    file_path_prefix: Optional[str] = Field(default=None, description="Filter by file path prefix (e.g. 'app/api/')")


class RetrievedChunk(BaseModel):
    """A single retrieved code chunk with relevance score and metadata."""

    id: str
    file_path: str
    language: Optional[str] = None
    symbol_type: Optional[str] = None
    symbol_name: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    content: str
    score: float = Field(description="Normalized similarity score (0.0 to 1.0, higher is better)")
    match_type: str = Field(default="semantic", description="semantic | exact_symbol | keyword")
    metadata: Optional[dict[str, Any]] = None


class CodeSearchResponse(BaseModel):
    """Response returned by the code search endpoint."""

    query: str
    repository_id: str
    snapshot_id: str
    total_matches: int
    chunks: list[RetrievedChunk]
    searched_at: datetime


class IndexStatusResponse(BaseModel):
    """Status of repository indexing."""

    repository_id: str
    snapshot_id: str
    status: str  # pending | indexing | completed | failed
    total_files_indexed: int = 0
    total_chunks_created: int = 0
    error_message: Optional[str] = None
    indexed_at: Optional[datetime] = None
