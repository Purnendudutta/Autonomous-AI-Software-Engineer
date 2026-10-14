"""
Task routes — CRUD + status, live logs (SSE), diff, tests, review, report, cancel.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from app.api.dependencies import SessionDep
from app.core.logging import get_logger
from app.database.repositories import AgentRunRepo, RepositoryRepo, TaskRepo
from app.schemas.agent import AgentLogEvent, AgentStepResponse, CodeChangeResponse, DiffResponse
from app.schemas.report import CodeReviewResponse, ReportResponse, ReviewFindingResponse, TestRunResponse
from app.schemas.task import (
    TaskCancelResponse,
    TaskCreateRequest,
    TaskGitPushRequest,
    TaskGitPushResponse,
    TaskResponse,
    TaskStatusResponse,
)
from app.services.tasks import execute_agent_task, get_cached_plan, register_subscriber, unregister_subscriber

logger = get_logger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ─── Create ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create and launch a new engineering task",
)
async def create_task(
    body: TaskCreateRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> TaskResponse:
    """
    Create a new task for the AI Software Engineer.
    Enqueues the LangGraph state machine execution in the background.
    """
    task_repo = TaskRepo(session)
    repo_db = RepositoryRepo(session)

    repo = await repo_db.get_by_id(body.repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{body.repository_id}' not found. Analyze it first.",
        )

    task = await task_repo.create(
        repository_id=body.repository_id,
        description=body.description,
        branch=body.branch,
        target_commit=body.target_commit,
        status="pending",
    )
    await session.commit()
    logger.info("task_created_and_queued", task_id=task.id, repository_id=body.repository_id)

    # Launch agent workflow in background
    background_tasks.add_task(execute_agent_task, task_id=task.id)

    return TaskResponse.model_validate(task)


# ─── Read / List ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[TaskResponse], summary="List tasks")
async def list_tasks(
    session: SessionDep,
    repository_id: Optional[str] = None,
    limit: int = 50,
) -> list[TaskResponse]:
    """Return all tasks, optionally filtered by repository."""
    task_repo = TaskRepo(session)
    if repository_id:
        tasks = await task_repo.list_by_repository(repository_id, limit=limit)
    else:
        tasks = await task_repo.list_all(limit=limit)
    return [TaskResponse.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskResponse, summary="Get task details")
async def get_task(task_id: str, session: SessionDep) -> TaskResponse:
    """Return full task details including execution_plan."""
    task = await _get_task_or_404(task_id, session)
    resp = TaskResponse.model_validate(task)

    plan_data = get_cached_plan(task_id)
    if not plan_data:
        agent_repo = AgentRunRepo(session)
        steps = await agent_repo.get_steps_for_task(task_id)
        for s in reversed(steps):
            if s.step_metadata and isinstance(s.step_metadata, dict) and s.step_metadata.get("execution_plan"):
                plan_data = s.step_metadata["execution_plan"]
                break

    resp.execution_plan = plan_data
    return resp


@router.post(
    "/{task_id}/retry",
    response_model=TaskResponse,
    summary="Re-run an existing task",
)
async def retry_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    session: SessionDep,
) -> TaskResponse:
    """Reset task status and re-run the autonomous agent pipeline."""
    task = await _get_task_or_404(task_id, session)
    task_repo = TaskRepo(session)
    await task_repo.update_status(task_id, status="pending", error_message=None, retry_count=0)
    await session.commit()
    await session.refresh(task)
    background_tasks.add_task(execute_agent_task, task_id=task.id)
    return TaskResponse.model_validate(task)


@router.get(
    "/{task_id}/status",
    response_model=TaskStatusResponse,
    summary="Get lightweight task status",
)
async def get_task_status(task_id: str, session: SessionDep) -> TaskStatusResponse:
    """Return task status for polling."""
    task = await _get_task_or_404(task_id, session)
    return TaskStatusResponse(
        task_id=task.id,
        status=task.status,
        retry_count=task.retry_count,
        error_message=task.error_message,
    )


# ─── Agent Logs (SSE) ─────────────────────────────────────────────────────────

@router.get("/{task_id}/logs", summary="Stream real-time agent execution logs via SSE")
async def stream_task_logs(task_id: str, request: Request, session: SessionDep) -> StreamingResponse:
    """
    Stream real-time agent execution events using Server-Sent Events (SSE).
    """
    await _get_task_or_404(task_id, session)
    queue = register_subscriber(task_id)

    async def event_generator():
        try:
            while not await request.is_disconnected():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=12.0)
                    yield f"data: {event.model_dump_json()}\n\n"
                except asyncio.TimeoutError:
                    # Keep-alive heartbeat ping
                    ping = json.dumps({"event_type": "ping", "task_id": task_id})
                    yield f"data: {ping}\n\n"
        finally:
            unregister_subscriber(task_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Diff ────────────────────────────────────────────────────────────────────

@router.get("/{task_id}/diff", response_model=DiffResponse, summary="Get git diff")
async def get_task_diff(task_id: str, session: SessionDep) -> DiffResponse:
    """Return the git diff of all changes made by the agent."""
    from app.agents.patcher import get_workspace_git_diff
    task = await _get_task_or_404(task_id, session)

    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(task.repository_id)

    if snapshot and snapshot.workspace_path:
        diff_data = get_workspace_git_diff(snapshot.workspace_path)
        return DiffResponse(
            task_id=task_id,
            diff=diff_data["diff"],
            files_changed=diff_data["files_changed"],
            lines_added=diff_data["lines_added"],
            lines_removed=diff_data["lines_removed"],
            generated_at=datetime.now(timezone.utc),
        )

    return DiffResponse(
        task_id=task_id,
        diff="",
        files_changed=[],
        lines_added=0,
        lines_removed=0,
        generated_at=datetime.now(timezone.utc),
    )


@router.get(
    "/{task_id}/tests",
    response_model=list[TestRunResponse],
    summary="Get all test runs for a task",
)
async def get_task_tests(task_id: str, session: SessionDep) -> list[TestRunResponse]:
    """Return all test run records, ordered by attempt number."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.database.models import TestRun
    await _get_task_or_404(task_id, session)

    result = await session.execute(
        select(TestRun)
        .options(selectinload(TestRun.results))
        .where(TestRun.task_id == task_id)
        .order_by(TestRun.attempt_number.asc())
    )
    test_runs = result.scalars().all()
    return [TestRunResponse.model_validate(tr) for tr in test_runs]


# ─── Review ──────────────────────────────────────────────────────────────────

@router.get(
    "/{task_id}/review",
    response_model=CodeReviewResponse,
    summary="Get AI code review findings",
)
async def get_task_review(task_id: str, session: SessionDep) -> CodeReviewResponse:
    """Return AI code review findings for the task."""
    from sqlalchemy import select
    from app.database.models import ReviewFinding
    await _get_task_or_404(task_id, session)

    result = await session.execute(
        select(ReviewFinding)
        .where(ReviewFinding.task_id == task_id)
        .order_by(ReviewFinding.created_at.asc())
    )
    findings = result.scalars().all()

    return CodeReviewResponse(
        task_id=task_id,
        findings=[ReviewFindingResponse.model_validate(f) for f in findings],
        high_count=sum(1 for f in findings if f.severity == "high"),
        medium_count=sum(1 for f in findings if f.severity == "medium"),
        low_count=sum(1 for f in findings if f.severity == "low"),
        info_count=sum(1 for f in findings if f.severity == "info"),
        generated_at=datetime.now(timezone.utc),
    )


# ─── Report ──────────────────────────────────────────────────────────────────

@router.get(
    "/{task_id}/report",
    response_model=ReportResponse,
    summary="Get the final PR-style report",
)
async def get_task_report(task_id: str, session: SessionDep) -> ReportResponse:
    """Return the final pull-request-style report for a task."""
    from sqlalchemy import select
    from app.database.models import Report
    await _get_task_or_404(task_id, session)

    result = await session.execute(
        select(Report).where(Report.task_id == task_id).order_by(Report.created_at.desc())
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not yet generated for this task.",
        )

    return ReportResponse.model_validate(report)


# ─── Cancel ──────────────────────────────────────────────────────────────────

@router.post(
    "/{task_id}/cancel",
    response_model=TaskCancelResponse,
    summary="Cancel a running task",
)
async def cancel_task(task_id: str, session: SessionDep) -> TaskCancelResponse:
    """Request cancellation of a running task."""
    task = await _get_task_or_404(task_id, session)

    if task.status in ("succeeded", "failed", "cancelled", "blocked"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Task is already in terminal state: '{task.status}'",
        )

    task_repo = TaskRepo(session)
    await task_repo.update_status(task_id, "cancelled")
    logger.info("task_cancelled", task_id=task_id)

    return TaskCancelResponse(
        task_id=task_id,
        status="cancelled",
        message="Task cancellation requested.",
    )


# ─── Delete ──────────────────────────────────────────────────────────────────

@router.delete(
    "/failed/clear",
    summary="Clear all failed tasks",
)
async def clear_failed_tasks(session: SessionDep):
    """Delete all tasks with status 'failed'."""
    from sqlalchemy import delete
    from app.database.models import Task
    result = await session.execute(
        delete(Task).where(Task.status == "failed")
    )
    await session.commit()
    logger.info("failed_tasks_cleared", count=result.rowcount)
    return {"deleted_count": result.rowcount, "message": f"Cleared {result.rowcount} failed task(s)."}


@router.delete(
    "/{task_id}",
    summary="Delete a single task",
)
async def delete_task(task_id: str, session: SessionDep):
    """Delete a task and cascade to its runs, steps, tests, and reports."""
    task = await _get_task_or_404(task_id, session)
    await session.delete(task)
    await session.commit()
    logger.info("task_deleted", task_id=task_id)
    return {"task_id": task_id, "deleted": True, "message": f"Task '{task_id}' deleted."}


# ─── Commit & Push to GitHub ─────────────────────────────────────────────────

@router.post(
    "/{task_id}/push",
    response_model=TaskGitPushResponse,
    summary="Commit and push workspace changes to the remote GitHub repository",
)
async def push_task_to_github(
    task_id: str,
    body: TaskGitPushRequest,
    session: SessionDep,
) -> TaskGitPushResponse:
    """
    Stage all modified/created files in the task's repository workspace,
    create a Git commit, and push to the remote GitHub repository.
    """
    from pathlib import Path
    from app.repository.clone import commit_and_push_workspace

    task = await _get_task_or_404(task_id, session)
    repo_db = RepositoryRepo(session)
    repo = await repo_db.get_by_id(task.repository_id)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated repository not found.",
        )

    snapshot = await repo_db.get_latest_snapshot(task.repository_id)
    if not snapshot or not snapshot.workspace_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No local workspace found for this repository.",
        )

    commit_msg = (body.commit_message or "").strip() or f"AI Task: {task.description[:120]}"
    target_branch = (body.branch or "").strip() or task.branch or snapshot.branch or repo.default_branch or "main"

    try:
        result = await asyncio.to_thread(
            commit_and_push_workspace,
            workspace_path=Path(snapshot.workspace_path),
            repo_url=repo.url,
            commit_message=commit_msg,
            branch=target_branch,
            github_token=body.github_token,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    return TaskGitPushResponse(
        task_id=task_id,
        commit_sha=result["commit_sha"],
        branch=result["branch"],
        commit_url=result["commit_url"],
        message=result["message"],
    )


# ─── Helpers ─────────────────────────────────────────────────────────────────

async def _get_task_or_404(task_id: str, session):
    """Retrieve a task by ID or raise HTTP 404."""
    task_repo = TaskRepo(session)
    task = await task_repo.get_by_id(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task '{task_id}' not found.",
        )
    return task

