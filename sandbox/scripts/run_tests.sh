#!/bin/sh
# run_tests.sh — Entry point for test execution in the sandbox container.
# Phase 6: This script is invoked by the backend's docker_runner.py.
#
# Usage:
#   run_tests.sh <test_framework> <test_args...>
#
# Environment variables:
#   TEST_FRAMEWORK: pytest | jest | vitest | mocha
#   TIMEOUT_SECONDS: Maximum execution time (enforced by Docker --stop-timeout)

set -e

FRAMEWORK="${TEST_FRAMEWORK:-pytest}"
echo "[sandbox] Starting test run: framework=${FRAMEWORK}"
echo "[sandbox] Working directory: $(pwd)"
echo "[sandbox] Python: $(python3 --version 2>/dev/null || echo 'not available')"

case "$FRAMEWORK" in
    pytest)
        echo "[sandbox] Running: python3 -m pytest $@"
        python3 -m pytest "$@" --tb=short --no-header
        ;;
    jest|vitest|mocha)
        echo "[sandbox] Running: npx $FRAMEWORK $@"
        npx "$FRAMEWORK" "$@"
        ;;
    *)
        echo "[sandbox] ERROR: Unknown test framework: $FRAMEWORK" >&2
        exit 2
        ;;
esac
