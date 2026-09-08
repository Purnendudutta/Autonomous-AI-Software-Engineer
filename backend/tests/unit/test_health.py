"""
Unit tests for the health endpoint.

These tests do NOT require a live PostgreSQL database.
The DB session dependency is overridden with a mock.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.api.dependencies import get_llm_provider
from app.database.session import get_session


@pytest.fixture
def mock_session():
    """Mock async DB session that returns a passing SELECT 1."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    return session


@pytest.fixture
def mock_llm():
    """Mock LLM provider."""
    provider = MagicMock()
    provider.provider_name = "openai"
    provider.model_name = "gpt-4o"
    return provider


@pytest.mark.asyncio
async def test_health_returns_200(mock_session, mock_llm):
    """Health endpoint should return HTTP 200 with status 'ok'."""

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert data["llm_provider"] == "openai"
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_degraded_when_db_fails(mock_llm):
    """Health endpoint should return 'degraded' status when DB is unreachable."""

    async def failing_session():
        session = AsyncMock()
        session.execute = AsyncMock(side_effect=Exception("connection refused"))
        yield session

    app.dependency_overrides[get_session] = failing_session
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert "error" in data["db"]


@pytest.mark.asyncio
async def test_health_response_schema(mock_session, mock_llm):
    """Health response must include all required fields."""

    async def override_session():
        yield mock_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_llm_provider] = lambda: mock_llm

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    app.dependency_overrides.clear()

    data = response.json()
    required_fields = {"status", "version", "environment", "db", "llm_provider", "llm_model", "timestamp"}
    assert required_fields.issubset(data.keys())
