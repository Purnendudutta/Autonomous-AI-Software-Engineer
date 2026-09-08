"""
Code Search and RAG API routes.

Endpoints:
- POST /api/repositories/{id}/index  — Enqueue or execute snapshot indexing.
- POST /api/repositories/{id}/search — Search codebase using pgvector hybrid search.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.api.dependencies import EmbeddingDep, SessionDep
from app.core.logging import get_logger
from app.database.repositories import RepositoryRepo
from app.database.session import get_session_factory
from app.rag.indexer import index_repository_snapshot
from app.rag.retriever import CodebaseRetriever
from app.schemas.rag import CodeSearchRequest, CodeSearchResponse, IndexStatusResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/api/repositories", tags=["code_rag"])


async def run_snapshot_indexing_task(
    snapshot_id: str,
    workspace_path: str,
    embedding_provider,
) -> None:
    """Background worker that chunks, embeds, and indexes a snapshot into pgvector."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            res = await index_repository_snapshot(
                snapshot_id=snapshot_id,
                workspace_path=workspace_path,
                session=session,
                embedding_provider=embedding_provider,
            )
            logger.info("background_indexing_finished", snapshot_id=snapshot_id, chunks=res.chunks_created)
        except Exception as exc:
            logger.error("background_indexing_failed", snapshot_id=snapshot_id, error=str(exc))


@router.post(
    "/{repository_id}/index",
    response_model=IndexStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Index repository codebase for RAG",
)
async def trigger_repository_indexing(
    repository_id: str,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    embedding_provider: EmbeddingDep,
) -> IndexStatusResponse:
    """
    Trigger semantic AST chunking, vector embedding, and pgvector indexing
    for the latest repository snapshot.
    """
    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(repository_id)

    if not snapshot or not snapshot.workspace_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active snapshot found for repository '{repository_id}'. Please analyze it first.",
        )

    workspace_dir = Path(snapshot.workspace_path)
    if not workspace_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository workspace files not found on disk.",
        )

    # Enqueue background indexing
    background_tasks.add_task(
        run_snapshot_indexing_task,
        snapshot_id=snapshot.id,
        workspace_path=str(workspace_dir),
        embedding_provider=embedding_provider,
    )

    return IndexStatusResponse(
        repository_id=repository_id,
        snapshot_id=snapshot.id,
        status="indexing",
        total_files_indexed=snapshot.file_count or 0,
        total_chunks_created=0,
        indexed_at=snapshot.indexed_at,
    )


@router.post(
    "/{repository_id}/search",
    response_model=CodeSearchResponse,
    summary="Semantic and symbol search across repository codebase",
)
async def search_codebase_endpoint(
    repository_id: str,
    body: CodeSearchRequest,
    session: SessionDep,
    embedding_provider: EmbeddingDep,
) -> CodeSearchResponse:
    """
    Search the repository's source code chunks using vector similarity,
    symbol matching, and optional filters (by language, symbol type, file path).
    """
    repo_db = RepositoryRepo(session)
    snapshot = await repo_db.get_latest_snapshot(repository_id)

    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' has not been analyzed or indexed.",
        )

    retriever = CodebaseRetriever(session=session, embedding_provider=embedding_provider)
    chunks = await retriever.search(
        snapshot_id=snapshot.id,
        query=body.query,
        limit=body.limit,
        similarity_threshold=body.similarity_threshold,
        language=body.language,
        symbol_type=body.symbol_type,
        file_path_prefix=body.file_path_prefix,
    )

    return CodeSearchResponse(
        query=body.query,
        repository_id=repository_id,
        snapshot_id=snapshot.id,
        total_matches=len(chunks),
        chunks=chunks,
        searched_at=datetime.now(timezone.utc),
    )
