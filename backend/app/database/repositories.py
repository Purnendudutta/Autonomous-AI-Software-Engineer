"""
Data access layer (Repository pattern).

All database queries live here — never in route handlers or agent nodes.
Each class corresponds to one ORM model and provides typed CRUD methods.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    AgentRun,
    AgentStep,
    CodeChange,
    FileChunk,
    Report,
    Repository,
    RepositorySnapshot,
    ReviewFinding,
    Task,
    TaskStatus,
    TestResult,
    TestRun,
)


class RepositoryRepo:
    """CRUD for Repository and RepositorySnapshot models."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, repo_id: str, load_snapshots: bool = False) -> Optional[Repository]:
        query = select(Repository).where(Repository.id == repo_id)
        if load_snapshots:
            query = query.options(selectinload(Repository.snapshots))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_owner_name(self, owner: str, name: str) -> Optional[Repository]:
        result = await self.session.execute(
            select(Repository).where(
                Repository.owner == owner, Repository.name == name
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Repository:
        repo = Repository(**kwargs)
        self.session.add(repo)
        await self.session.flush()
        return repo

    async def update_default_branch(self, repo_id: str, default_branch: str) -> None:
        await self.session.execute(
            update(Repository)
            .where(Repository.id == repo_id)
            .values(default_branch=default_branch)
        )

    async def list_all(self, limit: int = 50, offset: int = 0) -> list[Repository]:
        result = await self.session.execute(
            select(Repository)
            .options(selectinload(Repository.snapshots))
            .order_by(Repository.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    # Snapshot CRUD
    async def create_snapshot(self, **kwargs) -> RepositorySnapshot:
        snapshot = RepositorySnapshot(**kwargs)
        self.session.add(snapshot)
        await self.session.flush()
        return snapshot

    async def get_latest_snapshot(self, repository_id: str) -> Optional[RepositorySnapshot]:
        result = await self.session.execute(
            select(RepositorySnapshot)
            .where(RepositorySnapshot.repository_id == repository_id)
            .order_by(RepositorySnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_snapshot_by_id(self, snapshot_id: str) -> Optional[RepositorySnapshot]:
        result = await self.session.execute(
            select(RepositorySnapshot).where(RepositorySnapshot.id == snapshot_id)
        )
        return result.scalar_one_or_none()


class TaskRepo:
    """CRUD for Task model."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, task_id: str) -> Optional[Task]:
        result = await self.session.execute(
            select(Task).where(Task.id == task_id)
        )
        return result.scalar_one_or_none()

    async def create(self, **kwargs) -> Task:
        task = Task(**kwargs)
        self.session.add(task)
        await self.session.flush()
        return task

    async def update_status(self, task_id: str, status: str, **kwargs) -> None:
        await self.session.execute(
            update(Task)
            .where(Task.id == task_id)
            .values(status=status, **kwargs)
        )

    async def list_by_repository(
        self, repository_id: str, limit: int = 20, offset: int = 0
    ) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.repository_id == repository_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_all(
        self, limit: int = 50, offset: int = 0
    ) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .order_by(Task.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class AgentRunRepo:
    """CRUD for AgentRun and AgentStep models."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, **kwargs) -> AgentRun:
        run = AgentRun(**kwargs)
        self.session.add(run)
        await self.session.flush()
        return run

    async def add_step(self, **kwargs) -> AgentStep:
        step = AgentStep(**kwargs)
        self.session.add(step)
        await self.session.flush()
        return step

    async def get_steps_for_task(self, task_id: str) -> list[AgentStep]:
        result = await self.session.execute(
            select(AgentStep)
            .join(AgentRun, AgentStep.agent_run_id == AgentRun.id)
            .where(AgentRun.task_id == task_id)
            .order_by(AgentStep.created_at.asc())
        )
        return list(result.scalars().all())
