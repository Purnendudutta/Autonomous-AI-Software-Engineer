"""
Repository codebase indexing pipeline for pgvector RAG.

Scans workspace files, chunks them semantically, generates vector embeddings,
and stores records into the PostgreSQL file_chunks table.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.models import FileChunk, RepositorySnapshot
from app.llm.provider import EmbeddingProvider
from app.rag.chunker import CodeChunk, chunk_source_file
from app.rag.embeddings import generate_embeddings_batch
from app.repository.analyzer import detect_file_language, is_ignored_file

logger = get_logger(__name__)


class IndexingResult:
    """Statistics from an indexing run."""

    def __init__(self, snapshot_id: str, files_indexed: int, chunks_created: int, duration_seconds: float) -> None:
        self.snapshot_id = snapshot_id
        self.files_indexed = files_indexed
        self.chunks_created = chunks_created
        self.duration_seconds = duration_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "files_indexed": self.files_indexed,
            "chunks_created": self.chunks_created,
            "duration_seconds": round(self.duration_seconds, 2),
        }


async def index_repository_snapshot(
    snapshot_id: str,
    workspace_path: Path | str,
    session: AsyncSession,
    embedding_provider: EmbeddingProvider,
) -> IndexingResult:
    """
    Parse, chunk, embed, and index all codebase files of a repository snapshot.

    Args:
        snapshot_id: Target snapshot UUID.
        workspace_path: Local path to the cloned repository directory.
        session: Active SQLAlchemy AsyncSession.
        embedding_provider: Provider instance used to generate embeddings.

    Returns:
        IndexingResult summary with chunk and file counts.
    """
    root_path = Path(workspace_path).resolve()
    start_time = datetime.now(timezone.utc)
    logger.info("indexing_started", snapshot_id=snapshot_id, root=str(root_path))

    if not root_path.exists():
        raise FileNotFoundError(f"Repository workspace directory does not exist: {root_path}")

    # 1. Collect and chunk all eligible source files
    all_chunks: list[CodeChunk] = []
    files_indexed = 0

    for root, dirs, files in os.walk(root_path):
        current_dir = Path(root)

        # Filter directories in-place
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".") or d == ".github"
        ]

        for file_name in files:
            file_path = current_dir / file_name
            if is_ignored_file(file_path, root_path):
                continue

            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if not content.strip():
                continue

            lang = detect_file_language(file_path)
            try:
                rel_path = str(file_path.relative_to(root_path)).replace("\\", "/")
            except ValueError:
                rel_path = file_name

            file_chunks = chunk_source_file(
                file_path=rel_path,
                content=content,
                language=lang,
            )

            all_chunks.extend(file_chunks)
            files_indexed += 1

    logger.info(
        "chunking_completed",
        snapshot_id=snapshot_id,
        files=files_indexed,
        total_chunks=len(all_chunks),
    )

    if not all_chunks:
        return IndexingResult(snapshot_id, files_indexed=0, chunks_created=0, duration_seconds=0.0)

    # 2. Generate vector embeddings in batches
    chunk_texts = [c.content for c in all_chunks]
    embeddings = await generate_embeddings_batch(chunk_texts, embedding_provider, batch_size=32)

    # 3. Clean up existing chunks for this snapshot
    await session.execute(
        delete(FileChunk).where(FileChunk.snapshot_id == snapshot_id)
    )

    # 4. Insert chunks into PostgreSQL with vector embeddings
    db_records: list[FileChunk] = []
    for chunk, emb in zip(all_chunks, embeddings):
        record = FileChunk(
            snapshot_id=snapshot_id,
            file_path=chunk.file_path,
            language=chunk.language,
            symbol_type=chunk.symbol_type,
            symbol_name=chunk.symbol_name,
            start_line=chunk.start_line,
            end_line=chunk.end_line,
            content=chunk.content,
            content_hash=chunk.content_hash,
            embedding=emb,
            chunk_metadata=chunk.chunk_metadata,
        )
        db_records.append(record)

    session.add_all(db_records)

    # 5. Mark snapshot as indexed
    await session.execute(
        update(RepositorySnapshot)
        .where(RepositorySnapshot.id == snapshot_id)
        .values(indexed_at=datetime.now(timezone.utc))
    )

    await session.commit()

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(
        "indexing_completed",
        snapshot_id=snapshot_id,
        chunks_stored=len(db_records),
        duration_s=round(duration, 2),
    )

    return IndexingResult(
        snapshot_id=snapshot_id,
        files_indexed=files_indexed,
        chunks_created=len(db_records),
        duration_seconds=duration,
    )
