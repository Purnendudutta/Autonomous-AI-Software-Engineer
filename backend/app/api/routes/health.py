"""
Health check endpoint.

GET /health  — public, no auth required.
Returns DB connectivity, LLM provider name, and app version.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.dependencies import LLMDep, SessionDep, SettingsDep

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    db: str
    llm_provider: str
    llm_model: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Health check")
@router.get("/api/health", response_model=HealthResponse, include_in_schema=False)
async def health_check(
    settings: SettingsDep,
    session: SessionDep,
    llm: LLMDep,
) -> HealthResponse:
    """
    Returns application health.

    - **status**: 'ok' if all systems are reachable, 'degraded' otherwise.
    - **db**: 'connected' or error message.
    - **llm_provider**: The configured LLM provider name.
    """
    # Check database connectivity
    db_status = "connected"
    overall_status = "ok"
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_status = f"error: {type(exc).__name__}"
        overall_status = "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        environment=settings.environment,
        db=db_status,
        llm_provider=llm.provider_name,
        llm_model=llm.model_name,
        timestamp=datetime.now(timezone.utc),
    )
