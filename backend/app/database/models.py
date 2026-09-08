"""
SQLAlchemy ORM models for the Autonomous AI Software Engineer.

All tables use UUID primary keys and UTC timestamps.
The FileChunk model carries a pgvector embedding column for RAG.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ─── Base ─────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


# ─── Repository ───────────────────────────────────────────────────────────────

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[Optional[str]] = mapped_column(String(255))
    is_private: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("owner", "name", name="uq_repo_owner_name"),)

    snapshots: Mapped[list["RepositorySnapshot"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )


class RepositorySnapshot(Base):
    """A point-in-time snapshot of a repository at a specific commit."""

    __tablename__ = "repository_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    branch: Mapped[Optional[str]] = mapped_column(String(255))
    workspace_path: Mapped[Optional[str]] = mapped_column(String(1024))
    languages: Mapped[Optional[dict]] = mapped_column(JSONB)
    frameworks: Mapped[Optional[list]] = mapped_column(JSONB)
    file_count: Mapped[Optional[int]] = mapped_column(Integer)
    total_size_bytes: Mapped[Optional[int]] = mapped_column(BigInteger)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    repository: Mapped["Repository"] = relationship(back_populates="snapshots")
    file_chunks: Mapped[list["FileChunk"]] = relationship(
        back_populates="snapshot", cascade="all, delete-orphan"
    )


# ─── Task ────────────────────────────────────────────────────────────────────

class TaskStatus(str):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial_success"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class Task(Base):
    """A user-initiated engineering task for a repository."""

    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    snapshot_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("repository_snapshots.id", ondelete="SET NULL")
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default=TaskStatus.PENDING, nullable=False
    )
    branch: Mapped[Optional[str]] = mapped_column(String(255))
    target_commit: Mapped[Optional[str]] = mapped_column(String(40))
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    repository: Mapped["Repository"] = relationship(back_populates="tasks")
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    code_changes: Mapped[list["CodeChange"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    test_runs: Mapped[list["TestRun"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )
    report: Mapped[Optional["Report"]] = relationship(
        back_populates="task", uselist=False, cascade="all, delete-orphan"
    )


# ─── Agent Run / Steps ────────────────────────────────────────────────────────

class AgentRun(Base):
    """A single execution of the LangGraph agent for a task."""

    __tablename__ = "agent_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), default="running")
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    total_tool_calls: Mapped[int] = mapped_column(Integer, default=0)
    llm_tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    task: Mapped["Task"] = relationship(back_populates="agent_runs")
    steps: Mapped[list["AgentStep"]] = relationship(
        back_populates="agent_run", cascade="all, delete-orphan", order_by="AgentStep.sequence"
    )


class AgentStep(Base):
    """One observable step (node execution) within an AgentRun."""

    __tablename__ = "agent_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node_name: Mapped[str] = mapped_column(String(128), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(128))
    input_summary: Mapped[Optional[str]] = mapped_column(Text)
    output_summary: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="running")
    error: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    step_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    agent_run: Mapped["AgentRun"] = relationship(back_populates="steps")


# ─── RAG: File Chunks + Embeddings ────────────────────────────────────────────

class FileChunk(Base):
    """
    A semantic chunk of source code, stored with its embedding for RAG retrieval.

    The `embedding` column uses pgvector for similarity search.
    """

    __tablename__ = "file_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    snapshot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repository_snapshots.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(64))
    symbol_type: Mapped[Optional[str]] = mapped_column(String(64))  # function, class, module
    symbol_name: Mapped[Optional[str]] = mapped_column(String(255))
    start_line: Mapped[Optional[int]] = mapped_column(Integer)
    end_line: Mapped[Optional[int]] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    # pgvector embedding — dimension configured via settings
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536))
    chunk_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    snapshot: Mapped["RepositorySnapshot"] = relationship(back_populates="file_chunks")


# ─── Code Changes ─────────────────────────────────────────────────────────────

class CodeChange(Base):
    """A file modification produced by the coding agent."""

    __tablename__ = "code_changes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    change_type: Mapped[str] = mapped_column(String(32))  # created | modified | deleted
    original_content: Mapped[Optional[str]] = mapped_column(Text)
    new_content: Mapped[Optional[str]] = mapped_column(Text)
    diff: Mapped[Optional[str]] = mapped_column(Text)
    explanation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="code_changes")


# ─── Test Runs ────────────────────────────────────────────────────────────────

class TestRun(Base):
    """One execution of the test suite inside the Docker sandbox."""

    __tablename__ = "test_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    command: Mapped[Optional[str]] = mapped_column(Text)
    exit_code: Mapped[Optional[int]] = mapped_column(Integer)
    stdout: Mapped[Optional[str]] = mapped_column(Text)
    stderr: Mapped[Optional[str]] = mapped_column(Text)
    duration_seconds: Mapped[Optional[float]] = mapped_column()
    timed_out: Mapped[bool] = mapped_column(Boolean, default=False)
    tests_total: Mapped[Optional[int]] = mapped_column(Integer)
    tests_passed: Mapped[Optional[int]] = mapped_column(Integer)
    tests_failed: Mapped[Optional[int]] = mapped_column(Integer)
    tests_skipped: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="test_runs")
    results: Mapped[list["TestResult"]] = relationship(
        back_populates="test_run", cascade="all, delete-orphan"
    )


class TestResult(Base):
    """Result of an individual test case within a TestRun."""

    __tablename__ = "test_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    test_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False
    )
    test_name: Mapped[str] = mapped_column(String(512), nullable=False)
    test_file: Mapped[Optional[str]] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32))  # passed | failed | skipped | error
    duration_seconds: Mapped[Optional[float]] = mapped_column()
    failure_message: Mapped[Optional[str]] = mapped_column(Text)
    failure_traceback: Mapped[Optional[str]] = mapped_column(Text)

    test_run: Mapped["TestRun"] = relationship(back_populates="results")


# ─── Review Findings ─────────────────────────────────────────────────────────

class ReviewFinding(Base):
    """A single finding from the AI code-review agent."""

    __tablename__ = "review_findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    severity: Mapped[str] = mapped_column(String(16))  # high | medium | low | info
    category: Mapped[str] = mapped_column(String(64))  # security | correctness | etc.
    file_path: Mapped[Optional[str]] = mapped_column(String(1024))
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    issue: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ─── Report ───────────────────────────────────────────────────────────────────

class Report(Base):
    """The final pull-request-style report generated for a task."""

    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    task_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    problem_description: Mapped[Optional[str]] = mapped_column(Text)
    root_cause: Mapped[Optional[str]] = mapped_column(Text)
    changes_description: Mapped[Optional[str]] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(32), default="pending"
    )  # SUCCESS | PARTIAL_SUCCESS | FAILED | BLOCKED
    git_diff: Mapped[Optional[str]] = mapped_column(Text)
    full_report_markdown: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    task: Mapped["Task"] = relationship(back_populates="report")
