"""
Security utilities: path traversal protection, input validation, secret redaction.

No authentication logic here (that lives in api/dependencies.py).
This module is pure utility — no FastAPI dependencies.
"""

from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath


# ─── Path traversal protection ────────────────────────────────────────────────

_DANGEROUS_PATH_SEGMENTS = frozenset({
    "..",
    "~",
    "/etc",
    "/proc",
    "/sys",
    "/dev",
    "/root",
    "/var",
    "/run",
})


class PathTraversalError(ValueError):
    """Raised when a path escapes its allowed base directory."""


def safe_path(base_dir: str | Path, requested_path: str | Path) -> Path:
    """
    Resolve ``requested_path`` relative to ``base_dir`` and verify it stays
    within ``base_dir``.

    Raises:
        PathTraversalError: if the resolved path escapes the base directory.

    Example::

        safe_path("/workspaces/abc", "src/main.py")   # OK
        safe_path("/workspaces/abc", "../../etc/passwd")  # raises
    """
    base = Path(base_dir).resolve()
    target = (base / requested_path).resolve()

    try:
        target.relative_to(base)
    except ValueError:
        raise PathTraversalError(
            f"Path '{requested_path}' escapes the allowed base directory '{base}'"
        )

    return target


def validate_workspace_path(workspace_dir: str, file_path: str) -> Path:
    """
    Validate that a file path requested by the AI agent is within the workspace.

    Also rejects absolute paths and dangerous segments.
    """
    # Reject absolute paths outright
    if os.path.isabs(file_path):
        raise PathTraversalError(
            f"Absolute paths are not allowed: '{file_path}'"
        )

    # Check for dangerous segments
    parts = PurePosixPath(file_path.replace("\\", "/")).parts
    for part in parts:
        if part in _DANGEROUS_PATH_SEGMENTS:
            raise PathTraversalError(
                f"Dangerous path segment '{part}' found in '{file_path}'"
            )

    return safe_path(workspace_dir, file_path)


# ─── GitHub URL validation ─────────────────────────────────────────────────────

_GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def validate_github_url(url: str) -> tuple[str, str]:
    """
    Validate a GitHub repository URL and extract owner/repo.

    Returns:
        (owner, repo) tuple.

    Raises:
        ValueError: if the URL is not a valid GitHub repository URL.
    """
    url = url.strip().rstrip("/")
    match = _GITHUB_URL_RE.match(url)
    if not match:
        raise ValueError(
            f"Invalid GitHub repository URL: '{url}'. "
            "Expected format: https://github.com/owner/repository"
        )
    return match.group("owner"), match.group("repo")


# ─── Command validation ───────────────────────────────────────────────────────

# Commands the agent is explicitly allowed to suggest running in the sandbox.
# Shell execution must be gated through this allowlist.
ALLOWED_SANDBOX_COMMANDS: frozenset[str] = frozenset({
    "pytest",
    "python",
    "python3",
    "pip",
    "pip3",
    "node",
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "jest",
    "vitest",
    "mocha",
    "cargo",
    "go",
    "mvn",
    "gradle",
    "ruff",
    "mypy",
    "flake8",
    "eslint",
})


class SecurityViolationError(ValueError):
    """Raised when an operation violates security policy."""


def validate_sandbox_command(command: str | list[str]) -> None:
    """
    Ensure the executable of a command is in the sandbox allowlist.

    Raises:
        ValueError / SecurityViolationError: if the command is not allowed.
    """
    if not command:
        raise SecurityViolationError("Empty command")

    if isinstance(command, str):
        import shlex
        parts = shlex.split(command, posix=False) if os.name == 'nt' else shlex.split(command)
    else:
        parts = command

    if not parts:
        raise SecurityViolationError("Empty command")

    executable = Path(parts[0]).name.lower()
    if executable.endswith(".exe"):
        executable = executable[:-4]

    if executable not in ALLOWED_SANDBOX_COMMANDS:
        raise SecurityViolationError(
            f"Command '{executable}' is not in the sandbox allowlist. "
            f"Allowed: {sorted(ALLOWED_SANDBOX_COMMANDS)}"
        )
