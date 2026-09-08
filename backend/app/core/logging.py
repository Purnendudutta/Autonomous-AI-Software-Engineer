"""
Structured logging configuration using structlog.

Features:
- JSON output in production
- Pretty colored output in development
- Automatic secret redaction (API keys, passwords, tokens)
- Request ID / trace ID propagation
"""

from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


# ─── Secret redaction ─────────────────────────────────────────────────────────

# Patterns that look like secrets (API keys, tokens, passwords, etc.)
_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"sk-[A-Za-z0-9]{20,}", re.IGNORECASE),      # OpenAI keys
    re.compile(r"ghp_[A-Za-z0-9]{36}", re.IGNORECASE),       # GitHub PATs
    re.compile(r"github_pat_[A-Za-z0-9_]{82}", re.IGNORECASE),
    re.compile(r"(?i)(password|passwd|secret|token|api.?key)\s*[=:]\s*\S+"),
]

_SENSITIVE_KEYS = frozenset({
    "password",
    "passwd",
    "secret",
    "secret_key",
    "api_key",
    "openai_api_key",
    "github_token",
    "authorization",
    "token",
    "access_token",
    "refresh_token",
    "private_key",
})


def _redact_value(value: str) -> str:
    """Apply all secret-pattern redactions to a string value."""
    for pattern in _SECRET_PATTERNS:
        value = pattern.sub("[REDACTED]", value)
    return value


class SecretRedactionProcessor:
    """
    structlog processor that redacts secrets from log events.

    Walks the event dict and:
    - Replaces values of sensitive keys with '[REDACTED]'
    - Applies regex-based redaction on string values
    """

    def __call__(
        self,
        logger: WrappedLogger,
        method: str,
        event_dict: EventDict,
    ) -> EventDict:
        cleaned: dict[str, Any] = {}
        for key, value in event_dict.items():
            if key.lower() in _SENSITIVE_KEYS:
                cleaned[key] = "[REDACTED]"
            elif isinstance(value, str):
                cleaned[key] = _redact_value(value)
            elif isinstance(value, dict):
                # Shallow sanitise nested dicts (task inputs, tool args, etc.)
                cleaned[key] = {
                    k: "[REDACTED]" if k.lower() in _SENSITIVE_KEYS else v
                    for k, v in value.items()
                }
            else:
                cleaned[key] = value
        return cleaned


# ─── Configuration ────────────────────────────────────────────────────────────

def configure_logging(environment: str = "development", debug: bool = False) -> None:
    """
    Configure structlog for the application.

    Call once at application startup (in the FastAPI lifespan).
    """
    log_level = logging.DEBUG if debug else logging.INFO

    # Shared processors for all environments
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        SecretRedactionProcessor(),
    ]

    if environment == "production":
        # JSON output for log aggregation (Datadog, Loki, CloudWatch, etc.)
        renderer = structlog.processors.JSONRenderer()
    else:
        # Human-friendly colored output for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quiet noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if debug else logging.WARNING
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a named structlog logger for use in modules."""
    return structlog.get_logger(name)
