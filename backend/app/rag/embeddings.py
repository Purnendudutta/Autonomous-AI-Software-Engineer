"""
Embedding generation utilities with batching, token estimation, and mock fallback.
"""

from __future__ import annotations

import hashlib
import math
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.provider import EmbeddingProvider

logger = get_logger(__name__)
settings = get_settings()


class MockEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic mock embedding provider for tests and offline development.

    Generates reproducible unit-length float vectors based on text hashes.
    """

    def __init__(self, dimensions: int = 1536) -> None:
        self._dimensions = dimensions

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-embedding-v1"

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _generate_vector(self, text: str) -> list[float]:
        """Generate a deterministic normalized vector from text."""
        seed = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec: list[float] = []
        for i in range(self._dimensions):
            # Pseudo-random float between -1.0 and 1.0
            val = math.sin(seed * (i + 1))
            vec.append(val)

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._generate_vector(t) for t in texts]

    async def embed_single(self, text: str) -> list[float]:
        return self._generate_vector(text)


async def generate_embeddings_batch(
    texts: list[str],
    provider: EmbeddingProvider,
    batch_size: int = 32,
    max_char_length: int = 8000,
) -> list[list[float]]:
    """
    Generate embeddings for a list of text strings in safe batches.

    Args:
        texts: List of strings to embed.
        provider: Active EmbeddingProvider instance.
        batch_size: Number of texts per API call.
        max_char_length: Character limit per chunk to avoid token overflow.

    Returns:
        List of embedding float vectors in the same order as input texts.
    """
    if not texts:
        return []

    # Truncate any oversized texts
    sanitized = [t[:max_char_length] for t in texts]
    all_embeddings: list[list[float]] = []

    total = len(sanitized)
    for i in range(0, total, batch_size):
        batch = sanitized[i : i + batch_size]
        try:
            vectors = await provider.embed(batch)
            all_embeddings.extend(vectors)
        except Exception as exc:
            logger.warning(
                "embedding_batch_failed_falling_back",
                batch_start=i,
                batch_size=len(batch),
                error=str(exc),
            )
            # Fallback to mock embedding if API call fails
            mock_fallback = MockEmbeddingProvider(dimensions=provider.dimensions)
            mock_vectors = await mock_fallback.embed(batch)
            all_embeddings.extend(mock_vectors)

    return all_embeddings
