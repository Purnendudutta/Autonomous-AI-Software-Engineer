"""
Unit tests for security utilities.
"""

from __future__ import annotations

import pytest

from app.core.security import (
    PathTraversalError,
    safe_path,
    validate_github_url,
    validate_sandbox_command,
    validate_workspace_path,
)


class TestSafePath:
    def test_valid_path(self, tmp_path):
        result = safe_path(tmp_path, "src/main.py")
        assert result == tmp_path / "src" / "main.py"

    def test_traversal_raises(self, tmp_path):
        with pytest.raises(PathTraversalError):
            safe_path(tmp_path, "../../etc/passwd")

    def test_nested_valid_path(self, tmp_path):
        result = safe_path(tmp_path, "a/b/c/d.txt")
        assert result.is_relative_to(tmp_path)


class TestValidateGithubUrl:
    def test_valid_https_url(self):
        owner, repo = validate_github_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_valid_url_with_git_suffix(self):
        owner, repo = validate_github_url("https://github.com/owner/repo.git")
        assert repo == "repo"

    def test_invalid_domain_raises(self):
        with pytest.raises(ValueError):
            validate_github_url("https://gitlab.com/owner/repo")

    def test_missing_repo_raises(self):
        with pytest.raises(ValueError):
            validate_github_url("https://github.com/owner")

    def test_empty_url_raises(self):
        with pytest.raises(ValueError):
            validate_github_url("")


class TestValidateSandboxCommand:
    def test_allowed_command(self):
        validate_sandbox_command(["pytest", "tests/"])

    def test_disallowed_command_raises(self):
        with pytest.raises(ValueError):
            validate_sandbox_command(["rm", "-rf", "/"])

    def test_empty_command_raises(self):
        with pytest.raises(ValueError):
            validate_sandbox_command([])

    def test_python_with_args(self):
        validate_sandbox_command(["python3", "-m", "pytest", "tests/"])
