"""
FastAPI dependency injection providers.

Centralises all shared dependencies so routes don't construct objects directly.
Add new shared dependencies here (e.g. current_user, rate_limiter).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.database.session import get_session
from app.llm.openai_provider import create_embedding_provider, create_llm_provider
from app.llm.provider import EmbeddingProvider, LLMProvider


# ── Settings ─────────────────────────────────────────────────────────────────

def get_app_settings() -> Settings:
    """Dependency that returns the application settings singleton."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


# ── Database ──────────────────────────────────────────────────────────────────

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# ── LLM / Embedding ───────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_llm_provider() -> LLMProvider:
    """Singleton LLM provider (constructed once per process)."""
    return create_llm_provider()


@lru_cache(maxsize=1)
def _get_embedding_provider() -> EmbeddingProvider:
    """Singleton embedding provider (constructed once per process)."""
    return create_embedding_provider()


def get_llm_provider() -> LLMProvider:
    return _get_llm_provider()


def get_embedding_provider() -> EmbeddingProvider:
    return _get_embedding_provider()


LLMDep = Annotated[LLMProvider, Depends(get_llm_provider)]
EmbeddingDep = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
