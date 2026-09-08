"""
Core application configuration using Pydantic Settings.

All configuration is loaded from environment variables (and .env file in dev).
No secrets are ever hard-coded here.
"""

from __future__ import annotations

from functools import lru_cache
import json
from typing import Any, Literal

from pydantic import AnyUrl, Field, PostgresDsn, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Precedence (highest → lowest):
      1. Actual environment variables
      2. .env file
      3. Default values defined here
    """

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "Autonomous AI Software Engineer"
    app_version: str = "0.1.0"
    environment: Literal["development", "production", "testing"] = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me", min_length=8)

    # ── API ──────────────────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    cors_origins: str | list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            if v.startswith("["):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["http://localhost:3000", "http://localhost:5173"]

    # ── Database ─────────────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "ai_engineer"
    postgres_user: str = "ai_engineer"
    postgres_password: str = Field(default="changeme", repr=False)

    # Optional: explicit DATABASE_URL overrides computed value
    database_url: str | None = None

    @computed_field  # type: ignore[misc]
    @property
    def async_database_url(self) -> str:
        """Build the asyncpg connection URL."""
        if self.database_url:
            # Ensure the scheme is asyncpg-compatible
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[misc]
    @property
    def sync_database_url(self) -> str:
        """Build the standard psycopg2-compatible URL (used by Alembic)."""
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── LLM Provider ─────────────────────────────────────────────────────────
    llm_provider: Literal["openai", "openai_compatible", "local"] = "openai"
    llm_model: str = "gpt-4o"
    llm_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=4096, gt=0)
    llm_base_url: str | None = None  # None → official OpenAI endpoint
    openai_api_key: str | None = Field(default=None, repr=False)

    # ── Embedding Model ───────────────────────────────────────────────────────
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ── GitHub ───────────────────────────────────────────────────────────────
    github_token: str | None = Field(default=None, repr=False)

    # ── Agent / Sandbox ───────────────────────────────────────────────────────
    max_retries: int = Field(default=3, ge=1, le=10)
    sandbox_cpu_quota: int = 50_000          # microseconds per 100ms period
    sandbox_memory_mb: int = 512
    sandbox_timeout_seconds: int = 120
    sandbox_network_disabled: bool = True
    max_repo_size_mb: int = 500
    max_file_size_kb: int = 512
    max_agent_iterations: int = 50
    max_tool_calls: int = 200

    # ── Workspaces ────────────────────────────────────────────────────────────
    workspace_base_dir: str = "/tmp/ai-engineer-workspaces"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the singleton Settings instance.

    Uses lru_cache so the .env file is read only once per process.
    Call ``get_settings.cache_clear()`` in tests to reload settings.
    """
    return Settings()


# Module-level convenience alias
settings: Settings = get_settings()
