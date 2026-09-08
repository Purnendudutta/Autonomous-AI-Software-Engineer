"""
Repository API routes.

Endpoints:
- POST /api/repositories/analyze  — Ingest, clone, and analyze a GitHub repository in the background.
- GET  /api/repositories           — List all repositories with their latest snapshot metadata.
- GET  /api/repositories/{id}      — Get repository metadata and latest snapshot.
- GET  /api/repositories/{id}/snapshot — Get full latest snapshot details.
- GET  /api/repositories/{id}/tree — Get hierarchical file tree for UI navigation.
- GET  /api/repositories/{id}/file — Get specific file content safely.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import SessionDep, SettingsDep
from app.core.logging import get_logger
from app.core.security import safe_path, validate_github_url, validate_workspace_path
from app.database.repositories import RepositoryRepo, TaskRepo
from app.database.session import get_session_factory
from app.repository.analyzer import analyze_repository, build_file_tree_node, detect_file_language
from app.repository.clone import WorkspaceManager, clone_repository
from app.schemas.repository import (
    FileContentResponse,
    FileTreeNode,
    RepositoryAnalyzeRequest,
    RepositoryResponse,
    RepositorySnapshotResponse,
    RepositoryWithSnapshotResponse,
)
from app.schemas.task import TaskResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/repositories", tags=["repositories"])


async def run_repository_ingestion(
    task_id: str,
    repository_id: str,
    url: str,
    branch: Optional[str] = None,
    commit_sha: Optional[str] = None,
) -> None:
    """
    Background worker that clones and analyzes a repository.
    Updates the database with snapshot metadata and task status.
    """
    session_factory = get_session_factory()
    ws_mgr = WorkspaceManager()

    async with session_factory() as session:
        task_repo = TaskRepo(session)
        repo_db = RepositoryRepo(session)

        await task_repo.update_status(
            task_id,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        await session.commit()

        workspace = ws_mgr.create_workspace(repository_id)

        try:
            # 1. Clone repository
            clone_res = await clone_repository(
                url=url,
                workspace=workspace,
                branch=branch,
                commit_sha=commit_sha,
            )

            # Update default branch on repository record
            if clone_res.default_branch:
                await repo_db.update_default_branch(repository_id, clone_res.default_branch)

            # 2. Analyze codebase
            analysis = await analyze_repository(clone_res.repo_path)

            # 3. Persist Snapshot
            snapshot = await repo_db.create_snapshot(
                repository_id=repository_id,
                commit_sha=clone_res.commit_sha,
                branch=clone_res.branch,
                workspace_path=str(clone_res.repo_path),
                languages={k: v.model_dump() for k, v in analysis.languages.items()},
                frameworks=[f.model_dump() for f in analysis.frameworks],
                file_count=analysis.file_count,
                total_size_bytes=clone_res.total_size_bytes,
                summary=analysis.summary,
                indexed_at=datetime.now(timezone.utc),
            )

            # 4. Update task as succeeded
            await task_repo.update_status(
                task_id,
                status="succeeded",
                snapshot_id=snapshot.id,
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()

            logger.info(
                "repository_ingestion_succeeded",
                repository_id=repository_id,
                snapshot_id=snapshot.id,
                files=analysis.file_count,
                primary_lang=analysis.primary_language,
            )

        except Exception as exc:
            logger.error("repository_ingestion_failed", repository_id=repository_id, error=str(exc))
            await task_repo.update_status(
                task_id,
                status="failed",
                error_message=str(exc),
                completed_at=datetime.now(timezone.utc),
            )
            await session.commit()


@router.post(
    "/analyze",
    response_model=TaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a repository for cloning and deep analysis",
)
async def analyze_repository_endpoint(
    body: RepositoryAnalyzeRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    settings: SettingsDep,
) -> TaskResponse:
    """
    Validate repository URL, register repository record, and enqueue ingestion
    in the background.

    Returns a TaskResponse to track analysis progress.
    """
    owner, repo_name = validate_github_url(body.url)

    repo_db = RepositoryRepo(session)
    task_repo = TaskRepo(session)

    repo = await repo_db.get_by_owner_name(owner, repo_name)
    if not repo:
        repo = await repo_db.create(
            url=body.url,
            owner=owner,
            name=repo_name,
            default_branch=body.branch or "main",
        )
        logger.info("repository_registered", owner=owner, repo=repo_name, id=repo.id)

    task = await task_repo.create(
        repository_id=repo.id,
        description=body.task_description or f"Repository analysis for {owner}/{repo_name}",
        branch=body.branch,
        target_commit=body.commit_sha,
        status="pending",
    )
    await session.commit()

    # Enqueue background ingestion
    background_tasks.add_task(
        run_repository_ingestion,
        task_id=task.id,
        repository_id=repo.id,
        url=body.url,
        branch=body.branch,
        commit_sha=body.commit_sha,
    )

    return TaskResponse.model_validate(task)


@router.get(
    "",
    response_model=list[RepositoryWithSnapshotResponse],
    summary="List all repositories with latest snapshot details",
)
async def list_repositories(session: SessionDep) -> list[RepositoryWithSnapshotResponse]:
    """Return all repositories along with their latest snapshot metadata."""
    repo_db = RepositoryRepo(session)
    repos = await repo_db.list_all()

    response: list[RepositoryWithSnapshotResponse] = []
    for r in repos:
        latest = r.snapshots[-1] if r.snapshots else None
        item = RepositoryWithSnapshotResponse(
            id=r.id,
            url=r.url,
            owner=r.owner,
            name=r.name,
            default_branch=r.default_branch,
            is_private=r.is_private,
            created_at=r.created_at,
            updated_at=r.updated_at,
            latest_snapshot=RepositorySnapshotResponse.model_validate(latest) if latest else None,
        )
        response.append(item)

    return response


@router.get(
    "/{repository_id}",
    response_model=RepositoryWithSnapshotResponse,
    summary="Get a repository by ID with latest snapshot",
)
async def get_repository(repository_id: str, session: SessionDep) -> RepositoryWithSnapshotResponse:
    """Return single repository record and latest snapshot."""
    repo_db = RepositoryRepo(session)
    repo = await repo_db.get_by_id(repository_id, load_snapshots=True)
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found",
        )

    latest = repo.snapshots[-1] if repo.snapshots else None
    return RepositoryWithSnapshotResponse(
        id=repo.id,
        url=repo.url,
        owner=repo.owner,
        name=repo.name,
        default_branch=repo.default_branch,
        is_private=repo.is_private,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
        latest_snapshot=RepositorySnapshotResponse.model_validate(latest) if latest else None,
    )


@router.get(
    "/{repository_id}/snapshot",
    response_model=RepositorySnapshotResponse,
    summary="Get latest snapshot details for a repository",
)
async def get_repository_snapshot(repository_id: str, session: SessionDep) -> RepositorySnapshotResponse:
    """Return full snapshot metadata (languages, frameworks, summary)."""
    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(repository_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No snapshot found for repository '{repository_id}'. Please analyze it first.",
        )
    return RepositorySnapshotResponse.model_validate(snapshot)


@router.get(
    "/{repository_id}/tree",
    response_model=FileTreeNode,
    summary="Get hierarchical file tree for a repository",
)
async def get_repository_tree(repository_id: str, session: SessionDep) -> FileTreeNode:
    """Return the nested FileTreeNode structure of the cloned repository."""
    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(repository_id)
    if not snapshot or not snapshot.workspace_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workspace found for repository '{repository_id}'. Please analyze it first.",
        )

    repo_dir = Path(snapshot.workspace_path)
    if not repo_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository workspace directory is not on disk.",
        )

    tree = build_file_tree_node(repo_dir, repo_dir)
    if not tree:
        return FileTreeNode(name=repo_dir.name, path="", is_dir=True, children=[])
    return tree


@router.get(
    "/{repository_id}/file",
    response_model=FileContentResponse,
    summary="Get contents of a specific file safely",
)
async def get_repository_file(
    repository_id: str,
    session: SessionDep,
    path: str = Query(..., description="Relative file path inside the repository"),
) -> FileContentResponse:
    """
    Read file content from the repository workspace safely with path traversal protection.
    """
    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(repository_id)
    if not snapshot or not snapshot.workspace_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workspace found for repository '{repository_id}'.",
        )

    workspace_dir = Path(snapshot.workspace_path)

    try:
        target_file = validate_workspace_path(str(workspace_dir), path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if not target_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File '{path}' not found.")

    max_read_bytes = 256 * 1024  # 256 KB preview limit
    file_size = target_file.stat().st_size
    is_truncated = file_size > max_read_bytes

    try:
        with open(target_file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_read_bytes)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {exc}",
        )

    return FileContentResponse(
        path=path,
        filename=target_file.name,
        size_bytes=file_size,
        language=detect_file_language(target_file),
        content=content,
        is_truncated=is_truncated,
    )
