"""
Isolated Docker and Subprocess Sandbox Test Execution Engine.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import SecurityViolationError, validate_sandbox_command
from app.sandbox.parser import parse_test_output

logger = get_logger(__name__)
settings = get_settings()


class TestRunResult:
    """Encapsulates the raw and structured outcome of a test suite execution."""

    __test__ = False  # Prevent pytest from collecting this as a test class

    def __init__(
        self,
        command: str,
        exit_code: int,
        stdout: str,
        stderr: str,
        duration_seconds: float,
        timed_out: bool,
        parsed_results: dict[str, Any],
    ) -> None:
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.duration_seconds = duration_seconds
        self.timed_out = timed_out
        self.parsed_results = parsed_results

    @property
    def is_success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out and self.parsed_results.get("failed", 0) == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": round(self.duration_seconds, 2),
            "timed_out": self.timed_out,
            "parsed": self.parsed_results,
            "is_success": self.is_success,
        }


def get_default_test_command(framework: str) -> str:
    """Return the standard test invocation command for a given framework."""
    fw = (framework or "pytest").lower()
    if "jest" in fw or "npm" in fw:
        return "npm test"
    elif "cargo" in fw:
        return "cargo test"
    elif "go" in fw:
        return "go test ./..."
    elif "unittest" in fw:
        return "python -m unittest discover"
    return "python -m pytest tests/ -v"


async def execute_sandbox_tests(
    workspace_path: Path | str,
    test_command: Optional[str] = None,
    timeout_seconds: int = 120,
    framework: str = "pytest",
) -> TestRunResult:
    """
    Execute tests inside the workspace sandbox with resource limits and timeout.

    Args:
        workspace_path: Path to repository workspace directory.
        test_command: Optional custom command (e.g. 'pytest tests/unit/').
        timeout_seconds: Max execution duration before SIGKILL.
        framework: Testing framework name for parsing output.

    Returns:
        TestRunResult with stdout, stderr, exit code, and parsed metrics.
    """
    root = Path(workspace_path).resolve()
    cmd = test_command or get_default_test_command(framework)

    # Security check: validate command against allowlist
    try:
        validate_sandbox_command(cmd)
    except SecurityViolationError as exc:
        logger.error("sandbox_command_rejected", command=cmd, error=str(exc))
        return TestRunResult(
            command=cmd,
            exit_code=126,
            stdout="",
            stderr=f"Security violation: {exc}",
            duration_seconds=0.0,
            timed_out=False,
            parsed_results=parse_test_output(framework, "", str(exc), 126),
        )

    logger.info("sandbox_execution_starting", command=cmd, workspace=str(root))
    start_time = time.perf_counter()
    timed_out = False
    stdout = ""
    stderr = ""
    exit_code = 1

    env = os.environ.copy()
    # Add workspace to PYTHONPATH
    env["PYTHONPATH"] = str(root) + os.pathsep + env.get("PYTHONPATH", "")

    def _run_cmd() -> tuple[str, str, int, bool]:
        try:
            completed = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                cwd=str(root),
                env=env,
                timeout=timeout_seconds,
            )
            out = completed.stdout.decode("utf-8", errors="replace") if isinstance(completed.stdout, bytes) else str(completed.stdout)
            err = completed.stderr.decode("utf-8", errors="replace") if isinstance(completed.stderr, bytes) else str(completed.stderr)
            return out, err, completed.returncode, False
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b"").decode("utf-8", errors="replace") if isinstance(exc.stdout, bytes) else str(exc.stdout or "")
            err = f"Test execution timed out after {timeout_seconds} seconds."
            return out, err, 124, True
        except Exception as exc:
            return "", f"Failed to launch sandbox execution: {exc}", 1, False

    try:
        stdout, stderr, exit_code, timed_out = await asyncio.to_thread(_run_cmd)
    except Exception as exc:
        logger.error("sandbox_execution_exception", error=str(exc))
        stderr = f"Failed to launch sandbox execution: {exc}"
        exit_code = 1

    duration = time.perf_counter() - start_time
    parsed = parse_test_output(framework, stdout, stderr, exit_code)

    logger.info(
        "sandbox_execution_finished",
        exit_code=exit_code,
        duration_s=round(duration, 2),
        passed=parsed.get("passed", 0),
        failed=parsed.get("failed", 0),
    )

    return TestRunResult(
        command=cmd,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=duration,
        timed_out=timed_out,
        parsed_results=parsed,
    )
