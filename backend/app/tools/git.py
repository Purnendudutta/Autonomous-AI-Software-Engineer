"""
Git inspection and diff tools.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import git
from git.exc import InvalidGitRepositoryError

from app.core.logging import get_logger

logger = get_logger(__name__)


def get_git_diff_tool(workspace_path: Path | str) -> dict[str, Any]:
    """
    Generate unified git diff for all unstaged and staged changes in workspace.
    """
    root = Path(workspace_path).resolve()
    try:
        repo = git.Repo(root, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return {"success": False, "error": "Not a valid git repository", "diff": ""}

    try:
        diff_text = repo.git.diff("HEAD")
        untracked = repo.untracked_files
        modified = [item.a_path for item in repo.index.diff(None)]

        return {
            "success": True,
            "diff": diff_text,
            "modified_files": modified,
            "untracked_files": untracked,
            "has_changes": bool(diff_text or untracked or modified),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to get git diff: {exc}", "diff": ""}


def get_git_status_tool(workspace_path: Path | str) -> dict[str, Any]:
    """
    Get active branch name and list of modified/untracked files.
    """
    root = Path(workspace_path).resolve()
    try:
        repo = git.Repo(root, search_parent_directories=True)
        return {
            "success": True,
            "branch": repo.active_branch.name if not repo.head.is_detached else "HEAD",
            "commit_sha": repo.head.commit.hexsha,
            "is_dirty": repo.is_dirty(),
            "untracked_files": repo.untracked_files,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to inspect git status: {exc}"}
