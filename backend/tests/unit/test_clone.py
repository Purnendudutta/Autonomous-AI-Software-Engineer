"""
Unit tests for WorkspaceManager and clone utilities.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.repository.clone import (
    WorkspaceManager,
    build_authenticated_url,
    clone_repository,
    sanitize_git_url,
)


class TestWorkspaceManager:
    def test_create_and_cleanup_workspace(self, tmp_path):
        mgr = WorkspaceManager(base_dir=str(tmp_path))
        ws = mgr.create_workspace("test-ws-1")

        assert ws.exists()
        assert ws.is_dir()
        assert ws.name == "test-ws-1"

        # Create dummy file inside
        dummy_file = ws / "dummy.txt"
        dummy_file.write_text("hello world")
        assert dummy_file.exists()

        # Calculate size
        size = mgr.calculate_size_bytes(ws)
        assert size > 0

        # Cleanup
        mgr.cleanup_workspace("test-ws-1")
        assert not ws.exists()

    def test_get_workspace_path_stays_inside_base(self, tmp_path):
        mgr = WorkspaceManager(base_dir=str(tmp_path))
        ws = mgr.get_workspace("valid-name")
        assert ws.is_relative_to(tmp_path)


class TestUrlSanitization:
    def test_sanitize_git_url_with_token(self):
        dirty = "https://x-access-token:ghp_1234567890abcdef@github.com/owner/repo.git"
        clean = sanitize_git_url(dirty)
        assert "ghp_" not in clean
        assert clean == "https://github.com/owner/repo.git"

    def test_sanitize_git_url_without_token(self):
        clean = "https://github.com/owner/repo.git"
        assert sanitize_git_url(clean) == clean

    def test_build_authenticated_url(self):
        url = "https://github.com/owner/repo"
        auth_url = build_authenticated_url(url, token="my-token-123")
        assert auth_url == "https://x-access-token:my-token-123@github.com/owner/repo"


@pytest.mark.asyncio
async def test_clone_repository_mocked(tmp_path):
    """Test clone_repository metadata extraction with GitPython mocked."""
    mock_commit = MagicMock()
    mock_commit.hexsha = "abcdef1234567890"
    mock_commit.author.name = "Test Author"
    mock_commit.author.email = "test@example.com"
    mock_commit.message = "Initial commit"
    mock_commit.committed_date = 1700000000

    mock_repo = MagicMock()
    mock_repo.head.commit = mock_commit
    mock_repo.active_branch.name = "main"

    with patch("git.Repo.clone_from", return_value=mock_repo):
        res = await clone_repository(
            url="https://github.com/fastapi/fastapi",
            workspace=tmp_path,
            branch="main",
        )

        assert res.owner == "fastapi"
        assert res.repo_name == "fastapi"
        assert res.commit_sha == "abcdef1234567890"
        assert res.branch == "main"
        assert "Test Author" in res.author
