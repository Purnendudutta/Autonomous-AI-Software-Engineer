"""
Unit tests for CodebaseRetriever and embedding generation.
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.database.models import FileChunk
from app.rag.embeddings import MockEmbeddingProvider, generate_embeddings_batch
from app.rag.retriever import CodebaseRetriever


@pytest.mark.asyncio
async def test_mock_embedding_provider():
    provider = MockEmbeddingProvider(dimensions=1536)
    assert provider.dimensions == 1536

    vec = await provider.embed_single("def test_function(): pass")
    assert len(vec) == 1536

    # Verify unit length normalization
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-4

    # Deterministic check
    vec2 = await provider.embed_single("def test_function(): pass")
    assert vec == vec2


@pytest.mark.asyncio
async def test_generate_embeddings_batch():
    provider = MockEmbeddingProvider(dimensions=128)
    texts = [f"sample chunk number {i}" for i in range(75)]

    results = await generate_embeddings_batch(texts, provider, batch_size=32)
    assert len(results) == 75
    assert len(results[0]) == 128


@pytest.mark.asyncio
async def test_codebase_retriever_scoring():
    """Test retrieval boosting on symbol and keyword matches."""
    provider = MockEmbeddingProvider(dimensions=128)

    mock_chunk = FileChunk(
        id="chunk-123",
        snapshot_id="snap-1",
        file_path="app/auth/jwt.py",
        language="Python",
        symbol_type="function",
        symbol_name="verify_jwt_token",
        start_line=10,
        end_line=25,
        content="def verify_jwt_token(token: str):\n    return jwt.decode(token)\n",
        content_hash="hash123",
    )

    # Mock DB row: (chunk, cosine_distance, is_symbol_match, is_keyword_match)
    mock_row = (mock_chunk, 0.2, True, True)

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    retriever = CodebaseRetriever(session=mock_session, embedding_provider=provider)
    results = await retriever.search(
        snapshot_id="snap-1",
        query="verify_jwt_token",
        limit=5,
    )

    assert len(results) == 1
    chunk_res = results[0]
    assert chunk_res.id == "chunk-123"
    assert chunk_res.match_type == "exact_symbol"
    assert chunk_res.score > 0.8
    assert chunk_res.symbol_name == "verify_jwt_token"
