"""
Hybrid Codebase Retriever combining pgvector semantic search with symbol and keyword matching.
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.database.models import FileChunk
from app.llm.provider import EmbeddingProvider
from app.schemas.rag import RetrievedChunk

logger = get_logger(__name__)


class CodebaseRetriever:
    """Retrieves relevant code chunks using vector similarity and exact symbol matching."""

    def __init__(self, session: AsyncSession, embedding_provider: EmbeddingProvider) -> None:
        self.session = session
        self.embedding_provider = embedding_provider

    async def search(
        self,
        snapshot_id: str,
        query: str,
        limit: int = 8,
        similarity_threshold: float = 0.3,
        language: Optional[str] = None,
        symbol_type: Optional[str] = None,
        file_path_prefix: Optional[str] = None,
    ) -> list[RetrievedChunk]:
        """
        Execute hybrid search over the repository's indexed chunks.

        Args:
            snapshot_id: Repository snapshot ID to search within.
            query: Natural language or symbol query.
            limit: Maximum chunks to return.
            similarity_threshold: Minimum score filter (0.0 - 1.0).
            language: Optional language filter.
            symbol_type: Optional symbol type filter.
            file_path_prefix: Optional path prefix filter.

        Returns:
            List of scored RetrievedChunk instances.
        """
        query_clean = query.strip()
        if not query_clean:
            return []

        logger.info("retrieval_started", snapshot_id=snapshot_id, query=query_clean[:60])

        # 1. Generate query embedding
        query_vector = await self.embedding_provider.embed_single(query_clean)

        # 2. Build base query with filters
        conditions = [FileChunk.snapshot_id == snapshot_id]

        if language:
            conditions.append(FileChunk.language.ilike(f"%{language}%"))
        if symbol_type:
            conditions.append(FileChunk.symbol_type == symbol_type)
        if file_path_prefix:
            clean_prefix = file_path_prefix.replace("\\", "/").lstrip("/")
            conditions.append(FileChunk.file_path.startswith(clean_prefix))

        # 3. Vector distance expression (cosine distance)
        cosine_distance = FileChunk.embedding.cosine_distance(query_vector)

        # 4. Keyword / symbol match check
        exact_symbol_match = FileChunk.symbol_name.ilike(f"%{query_clean}%")
        keyword_match = FileChunk.content.ilike(f"%{query_clean}%")

        stmt = (
            select(
                FileChunk,
                cosine_distance.label("distance"),
                exact_symbol_match.label("is_symbol_match"),
                keyword_match.label("is_keyword_match"),
            )
            .where(*conditions)
            .order_by(cosine_distance.asc())
            .limit(limit * 2)  # Retrieve candidate pool for re-ranking
        )

        result = await self.session.execute(stmt)
        rows = result.all()

        retrieved: list[RetrievedChunk] = []

        for row in rows:
            chunk: FileChunk = row[0]
            distance: float = float(row[1]) if row[1] is not None else 1.0
            is_symbol_match: bool = bool(row[2])
            is_keyword_match: bool = bool(row[3])

            # Convert cosine distance (0.0 to 2.0) to similarity score (1.0 to 0.0)
            base_score = max(0.0, 1.0 - (distance / 2.0))

            match_type = "semantic"
            final_score = base_score

            # Boost exact symbol and keyword matches
            if is_symbol_match:
                final_score = min(1.0, base_score + 0.25)
                match_type = "exact_symbol"
            elif is_keyword_match:
                final_score = min(1.0, base_score + 0.10)
                match_type = "keyword"

            if final_score < similarity_threshold:
                continue

            retrieved.append(
                RetrievedChunk(
                    id=chunk.id,
                    file_path=chunk.file_path,
                    language=chunk.language,
                    symbol_type=chunk.symbol_type,
                    symbol_name=chunk.symbol_name,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    content=chunk.content,
                    score=round(final_score, 4),
                    match_type=match_type,
                    metadata=chunk.chunk_metadata,
                )
            )

        # Re-sort by final boosted score descending
        retrieved.sort(key=lambda c: c.score, reverse=True)
        final_results = retrieved[:limit]

        logger.info(
            "retrieval_completed",
            candidates_found=len(rows),
            filtered_results=len(final_results),
            top_score=final_results[0].score if final_results else 0.0,
        )

        return final_results
