"""
Task execution and real-time SSE event streaming service.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import agent_graph
from app.agents.state import AgentState
from app.core.logging import get_logger
from app.database.repositories import AgentRunRepo, RepositoryRepo, TaskRepo
from app.database.session import get_session_factory
from app.schemas.agent import AgentLogEvent

logger = get_logger(__name__)

# In-memory event bus: task_id -> list of subscriber Queues
_subscribers: dict[str, list[asyncio.Queue[AgentLogEvent]]] = {}
_cached_events: dict[str, list[AgentLogEvent]] = {}


def register_subscriber(task_id: str) -> asyncio.Queue[AgentLogEvent]:
    """Register an SSE subscriber queue for real-time task events."""
    q: asyncio.Queue[AgentLogEvent] = asyncio.Queue()
    if task_id not in _subscribers:
        _subscribers[task_id] = []
    _subscribers[task_id].append(q)

    # Replay past events to new subscriber
    if task_id in _cached_events:
        for ev in _cached_events[task_id]:
            q.put_nowait(ev)

    return q


def unregister_subscriber(task_id: str, q: asyncio.Queue[AgentLogEvent]) -> None:
    """Unregister an SSE subscriber queue."""
    if task_id in _subscribers and q in _subscribers[task_id]:
        _subscribers[task_id].remove(q)
        if not _subscribers[task_id]:
            del _subscribers[task_id]


def broadcast_event(task_id: str, event: AgentLogEvent) -> None:
    """Broadcast an event to all connected subscribers for a task."""
    if task_id not in _cached_events:
        _cached_events[task_id] = []
    _cached_events[task_id].append(event)

    if task_id in _subscribers:
        for q in _subscribers[task_id]:
            q.put_nowait(event)


async def execute_agent_task(task_id: str) -> None:
    """
    Background worker that runs the LangGraph state machine on a task,
    persisting runs and steps in PostgreSQL and broadcasting live events.
    """
    session_factory = get_session_factory()
    start_time = datetime.now(timezone.utc)

    logger.info("agent_task_execution_started", task_id=task_id)

    async with session_factory() as session:
        task_repo = TaskRepo(session)
        repo_db = RepositoryRepo(session)
        agent_repo = AgentRunRepo(session)

        task = await task_repo.get_by_id(task_id)
        if not task:
            logger.error("task_not_found_for_execution", task_id=task_id)
            return

        # Update task status to running
        await task_repo.update_status(task_id, status="running", started_at=start_time)
        run_record = await agent_repo.create_run(task_id=task_id, status="running")
        await session.commit()

        snapshot = await repo_db.get_latest_snapshot(task.repository_id)

        # Broadcast task started event
        seq = 1
        broadcast_event(
            task_id,
            AgentLogEvent(
                event_type="task_started",
                task_id=task_id,
                sequence=seq,
                node_name="orchestrator",
                message=f"Starting AI Software Engineer task: {task.description}",
                status="running",
                timestamp=datetime.now(timezone.utc).isoformat(),
            ),
        )

        initial_state: AgentState = {
            "task_id": task_id,
            "repository_id": task.repository_id,
            "snapshot_id": snapshot.id if snapshot else "",
            "workspace_path": snapshot.workspace_path if snapshot else "",
            "task_description": task.description,
            "repository_summary": snapshot.summary if snapshot else "",
            "primary_language": "Python",
            "retry_count": 0,
            "max_retries": 3,
            "messages": [],
        }

        try:
            # Execute LangGraph state machine
            final_state = await agent_graph.ainvoke(initial_state)

            # Record final steps & status
            plan_obj = final_state.get("execution_plan")
            plan_summary = f"Generated {len(plan_obj.get('steps', []))} steps plan" if plan_obj else "Plan completed"

            seq += 1
            step_record = await agent_repo.add_step(
                agent_run_id=run_record.id,
                sequence=seq,
                node_name="planning",
                status="completed",
                output_summary=plan_summary,
            )

            await task_repo.update_status(
                task_id,
                status=final_state.get("final_status", "succeeded"),
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()

            broadcast_event(
                task_id,
                AgentLogEvent(
                    event_type="task_completed",
                    task_id=task_id,
                    sequence=seq + 1,
                    node_name="orchestrator",
                    message="Agent task completed successfully.",
                    status="succeeded",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
            )

            logger.info("agent_task_execution_succeeded", task_id=task_id)

        except Exception as exc:
            logger.error("agent_task_execution_failed", task_id=task_id, error=str(exc))
            await task_repo.update_status(
                task_id,
                status="failed",
                error_message=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()

            broadcast_event(
                task_id,
                AgentLogEvent(
                    event_type="task_failed",
                    task_id=task_id,
                    sequence=seq + 1,
                    node_name="orchestrator",
                    message=f"Agent encountered an error: {exc}",
                    status="failed",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
            )
