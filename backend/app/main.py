"""
FastAPI application factory.

This is the entry point for uvicorn:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

Architecture:
  - Lifespan: DB tables, logging, startup/shutdown hooks
  - CORS: Configured from settings
  - Routers: health, repositories, tasks
  - Exception handlers: validation errors, HTTP exceptions, uncaught exceptions
"""

from __future__ import annotations

import traceback
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import health, rag, repositories, tasks
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database.session import create_all_tables, dispose_engine

settings = get_settings()
logger = get_logger(__name__)


# ─── Lifespan ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup:
      1. Configure structured logging
      2. Create database tables (idempotent)
      3. Verify DB connectivity

    Shutdown:
      1. Dispose DB engine (drain connection pool)
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    configure_logging(
        environment=settings.environment,
        debug=settings.debug,
    )

    logger.info(
        "application_starting",
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )

    try:
        await create_all_tables()
        logger.info("database_ready")
    except Exception as exc:
        logger.error("database_startup_failed", error=str(exc))
        raise

    logger.info("application_ready", port=settings.backend_port)

    yield  # Application is running

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("application_shutting_down")
    await dispose_engine()
    logger.info("application_stopped")


# ─── App Factory ─────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Autonomous AI Software Engineer — agentic code analysis, bug fixing, "
            "test generation, and pull-request report generation."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Task-ID", "X-Request-ID"],
    )

    # ── Routers ──────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(repositories.router)
    app.include_router(rag.router)
    app.include_router(tasks.router)

    # ── Exception Handlers ────────────────────────────────────────────────────
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=str(request.url),
            method=request.method,
            error=str(exc),
            traceback=traceback.format_exc(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred.",
                "error_type": type(exc).__name__,
            },
        )

    return app


# Module-level app instance for uvicorn
app = create_app()
