"""
Test output parsers for Pytest, Jest, and unittest test runners.
"""

from __future__ import annotations

import re
from typing import Any, Optional


def parse_pytest_output(stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    """
    Parse standard pytest console output into structured test summary and items.
    """
    combined = (stdout or "") + "\n" + (stderr or "")

    # Extract summary line (e.g. "== 2 failed, 39 passed, 1 skipped in 1.37s ==")
    passed = 0
    failed = 0
    skipped = 0
    duration_s = 0.0

    passed_match = re.search(r"(\d+)\s+passed", combined)
    if passed_match:
        passed = int(passed_match.group(1))

    failed_match = re.search(r"(\d+)\s+failed", combined)
    if failed_match:
        failed = int(failed_match.group(1))

    error_match = re.search(r"(\d+)\s+error", combined)
    if error_match:
        failed += int(error_match.group(1))

    skipped_match = re.search(r"(\d+)\s+skipped", combined)
    if skipped_match:
        skipped = int(skipped_match.group(1))

    duration_match = re.search(r"in\s+([\d\.]+)\s*s", combined)
    if duration_match:
        try:
            duration_s = float(duration_match.group(1))
        except ValueError:
            duration_s = 0.0

    total = passed + failed + skipped
    if total == 0 and exit_code == 0 and "passed" in combined:
        passed = 1
        total = 1

    # Extract individual test line results (e.g. "tests/unit/test_auth.py::test_login PASSED")
    items: list[dict[str, Any]] = []
    item_pattern = re.compile(
        r"^(.*?::[^\s]+)\s+(PASSED|FAILED|SKIPPED|ERROR)",
        re.MULTILINE,
    )
    for match in item_pattern.finditer(combined):
        full_test_id = match.group(1)
        test_status = match.group(2).lower()
        if test_status == "passed":
            status_norm = "passed"
        elif test_status in ("failed", "error"):
            status_norm = "failed"
        else:
            status_norm = "skipped"

        parts = full_test_id.split("::")
        test_file = parts[0]
        test_name = parts[-1]

        items.append({
            "test_name": test_name,
            "test_file": test_file,
            "status": status_norm,
            "duration_seconds": None,
            "failure_message": None,
        })

    # Extract failure section if any
    failures_section = ""
    if "=== FAILURES ===" in combined:
        parts = combined.split("=== FAILURES ===")
        if len(parts) > 1:
            failures_section = parts[1].split("=== short test summary info ===")[0].strip()

    return {
        "framework": "pytest",
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": duration_s,
        "items": items,
        "failures_summary": failures_section,
        "exit_code": exit_code,
        "is_success": exit_code == 0 and failed == 0,
    }


def parse_jest_output(stdout: str, stderr: str, exit_code: int) -> dict[str, Any]:
    """
    Parse Jest / Vitest console output into structured test summary.
    """
    combined = (stdout or "") + "\n" + (stderr or "")

    passed = 0
    failed = 0
    skipped = 0
    total = 0

    # Match: Tests: 2 failed, 8 passed, 10 total
    tests_match = re.search(r"Tests:\s+(.*)", combined)
    if tests_match:
        line = tests_match.group(1)
        pm = re.search(r"(\d+)\s+passed", line)
        if pm:
            passed = int(pm.group(1))
        fm = re.search(r"(\d+)\s+failed", line)
        if fm:
            failed = int(fm.group(1))
        sm = re.search(r"(\d+)\s+skipped", line)
        if sm:
            skipped = int(sm.group(1))
        tm = re.search(r"(\d+)\s+total", line)
        if tm:
            total = int(tm.group(1))

    if total == 0:
        total = passed + failed + skipped

    duration_match = re.search(r"Time:\s+([\d\.]+)\s*s", combined)
    duration_s = float(duration_match.group(1)) if duration_match else 0.0

    return {
        "framework": "jest",
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "duration_seconds": duration_s,
        "items": [],
        "failures_summary": stderr if failed > 0 else "",
        "exit_code": exit_code,
        "is_success": exit_code == 0 and failed == 0,
    }


def parse_test_output(
    framework: str,
    stdout: str,
    stderr: str,
    exit_code: int,
) -> dict[str, Any]:
    """
    Route test output to appropriate framework parser.
    """
    fw_lower = (framework or "pytest").lower()
    if "jest" in fw_lower or "vitest" in fw_lower or "npm" in fw_lower:
        return parse_jest_output(stdout, stderr, exit_code)
    return parse_pytest_output(stdout, stderr, exit_code)
