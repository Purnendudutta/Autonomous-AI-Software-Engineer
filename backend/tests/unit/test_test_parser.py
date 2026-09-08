"""
Unit tests for test runner output parsers.
"""

from __future__ import annotations

from app.sandbox.parser import parse_jest_output, parse_pytest_output, parse_test_output


def test_parse_pytest_output_all_passed():
    stdout = """
============================= test session starts =============================
collecting ... collected 5 items

tests/unit/test_auth.py::test_login PASSED                               [ 20%]
tests/unit/test_auth.py::test_logout PASSED                              [ 40%]
tests/unit/test_auth.py::test_refresh PASSED                             [ 60%]
tests/unit/test_auth.py::test_expired_token PASSED                       [ 80%]
tests/unit/test_auth.py::test_invalid_signature PASSED                   [100%]

============================== 5 passed in 0.42s ===============================
"""
    result = parse_pytest_output(stdout, stderr="", exit_code=0)

    assert result["is_success"] is True
    assert result["total"] == 5
    assert result["passed"] == 5
    assert result["failed"] == 0
    assert result["duration_seconds"] == 0.42
    assert len(result["items"]) == 5
    assert result["items"][0]["test_name"] == "test_login"
    assert result["items"][0]["status"] == "passed"


def test_parse_pytest_output_with_failures():
    stdout = """
============================= test session starts =============================
tests/unit/test_api.py::test_ok PASSED                                   [ 50%]
tests/unit/test_api.py::test_fail FAILED                                 [100%]

=================================== FAILURES ===================================
__________________________________ test_fail ___________________________________
    def test_fail():
>       assert 1 == 2
E       assert 1 == 2
tests/unit/test_api.py:10: AssertionError
=========================== short test summary info ===========================
FAILED tests/unit/test_api.py::test_fail - assert 1 == 2
========================= 1 failed, 1 passed in 0.15s ==========================
"""
    result = parse_pytest_output(stdout, stderr="", exit_code=1)

    assert result["is_success"] is False
    assert result["total"] == 2
    assert result["passed"] == 1
    assert result["failed"] == 1
    assert result["duration_seconds"] == 0.15
    assert "AssertionError" in result["failures_summary"]


def test_parse_jest_output():
    stdout = """
PASS src/auth.test.ts
FAIL src/user.test.ts
  ● User Service › should validate email format
    expect(received).toBe(expected)

Tests:       1 failed, 4 passed, 5 total
Snapshots:   0 total
Time:        1.852 s
"""
    result = parse_jest_output(stdout, stderr="Error in user test", exit_code=1)

    assert result["is_success"] is False
    assert result["total"] == 5
    assert result["passed"] == 4
    assert result["failed"] == 1
    assert result["duration_seconds"] == 1.852


def test_parse_test_output_router():
    pytest_out = "=== 3 passed in 0.10s ==="
    res = parse_test_output("Python", pytest_out, "", 0)
    assert res["passed"] == 3
