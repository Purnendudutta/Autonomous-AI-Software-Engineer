"""
Repository cloning and workspace isolation management.

Responsibilities:
- Validate repository URLs and GitHub credentials.
- Clone repositories into isolated temporary workspaces.
- Check out specific branches or commit SHAs.
- Extract commit metadata (SHA, author, message, timestamp).
- Enforce workspace storage limits (MAX_REPO_SIZE_MB).
- Securely sanitize Git URLs so tokens never appear in logs or exceptions.
- Provide cleanup routines for temporary working directories.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import git
from git.exc import GitCommandError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import safe_path, validate_github_url

logger = get_logger(__name__)
settings = get_settings()


class WorkspaceManager:
    """Manages isolated file workspaces for repository checkouts and agent tasks."""

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.workspace_base_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def create_workspace(self, workspace_id: str) -> Path:
        """
        Create a clean, isolated workspace directory.

        Args:
            workspace_id: Unique identifier (e.g. task_id or snapshot_id).

        Returns:
            Path to the newly created workspace.
        """
        target = safe_path(self.base_dir, workspace_id)
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        logger.info("workspace_created", workspace_id=workspace_id, path=str(target))
        return target

    def get_workspace(self, workspace_id: str) -> Path:
        """Resolve workspace path and verify it stays within base_dir."""
        return safe_path(self.base_dir, workspace_id)

    def calculate_size_bytes(self, path: Path) -> int:
        """Calculate total disk usage of a directory in bytes."""
        total = 0
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    total += entry.stat().st_size
                elif entry.is_dir(follow_symlinks=False):
                    total += self.calculate_size_bytes(Path(entry.path))
        except (PermissionError, FileNotFoundError):
            pass
        return total

    def cleanup_workspace(self, workspace_id: str) -> None:
        """Remove a workspace and all its contents safely."""
        target = safe_path(self.base_dir, workspace_id)
        if target.exists():
            # Handle read-only files (e.g. .git on Windows)
            def on_rm_error(func, path, exc_info):
                try:
                    os.chmod(path, 0o777)
                    func(path)
                except Exception:
                    pass

            shutil.rmtree(target, onerror=on_rm_error)
            logger.info("workspace_cleaned", workspace_id=workspace_id)


def sanitize_git_url(url: str) -> str:
    """Strip authentication tokens from git URLs for safe logging."""
    if "@" in url:
        # e.g. https://token@github.com/... -> https://github.com/...
        parts = url.split("@", 1)
        protocol = parts[0].split("://", 1)[0]
        return f"{protocol}://{parts[1]}"
    return url


def build_authenticated_url(url: str, token: Optional[str] = None) -> str:
    """Inject GitHub token into clone URL securely if provided."""
    token_to_use = token or settings.github_token
    if not token_to_use:
        return url

    # Remove existing protocol
    clean_url = url.strip()
    if clean_url.startswith("https://"):
        clean_url = clean_url[len("https://"):]
    elif clean_url.startswith("http://"):
        clean_url = clean_url[len("http://"):]

    return f"https://x-access-token:{token_to_use}@{clean_url}"


class CloneResult:
    """Structured result from cloning a repository."""

    def __init__(
        self,
        workspace_path: Path,
        repo_path: Path,
        owner: str,
        repo_name: str,
        commit_sha: str,
        branch: str,
        default_branch: str,
        author: str,
        commit_message: str,
        committed_at: datetime,
        total_size_bytes: int,
    ) -> None:
        self.workspace_path = workspace_path
        self.repo_path = repo_path
        self.owner = owner
        self.repo_name = repo_name
        self.commit_sha = commit_sha
        self.branch = branch
        self.default_branch = default_branch
        self.author = author
        self.commit_message = commit_message
        self.committed_at = committed_at
        self.total_size_bytes = total_size_bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_path": str(self.workspace_path),
            "repo_path": str(self.repo_path),
            "owner": self.owner,
            "repo_name": self.repo_name,
            "commit_sha": self.commit_sha,
            "branch": self.branch,
            "default_branch": self.default_branch,
            "author": self.author,
            "commit_message": self.commit_message,
            "committed_at": self.committed_at.isoformat(),
            "total_size_bytes": self.total_size_bytes,
        }


async def clone_repository(
    url: str,
    workspace: Path,
    branch: Optional[str] = None,
    commit_sha: Optional[str] = None,
    github_token: Optional[str] = None,
    depth: int = 50,
) -> CloneResult:
    """
    Clone a GitHub repository into the designated workspace and extract metadata.

    Args:
        url: GitHub repository URL.
        workspace: Base directory where repository should be cloned.
        branch: Optional specific branch to clone or check out.
        commit_sha: Optional specific commit SHA to checkout.
        github_token: Optional GitHub Personal Access Token.
        depth: Clone history depth (default 50 for shallow clone efficiency).

    Returns:
        CloneResult with commit metadata and paths.

    Raises:
        ValueError: On invalid URL or repository size exceeding limits.
        RuntimeError: On Git clone or checkout failures.
    """
    owner, repo_name = validate_github_url(url)
    target_dir = workspace / repo_name
    auth_url = build_authenticated_url(url, github_token)

    safe_log_url = sanitize_git_url(auth_url)
    logger.info(
        "repository_clone_started",
        owner=owner,
        repo=repo_name,
        branch=branch,
        commit_sha=commit_sha,
        url=safe_log_url,
    )

    clone_kwargs: dict[str, Any] = {
        "depth": depth if not commit_sha else None,  # Full clone needed if specific historical SHA requested
    }
    if branch and not commit_sha:
        clone_kwargs["branch"] = branch

    try:
        # Clone using GitPython
        repo = git.Repo.clone_from(auth_url, target_dir, **{k: v for k, v in clone_kwargs.items() if v is not None})
    except GitCommandError as exc:
        clean_msg = sanitize_git_url(str(exc))
        logger.error("git_clone_failed", error=clean_msg)
        raise RuntimeError(f"Git clone failed: {clean_msg}") from exc
    except Exception as exc:
        clean_msg = sanitize_git_url(str(exc))
        logger.error("git_clone_unexpected_error", error=clean_msg)
        raise RuntimeError(f"Unexpected error cloning repository: {clean_msg}") from exc

    # If a specific commit SHA was requested, check it out
    if commit_sha:
        try:
            repo.git.checkout(commit_sha)
            logger.info("checked_out_commit", commit_sha=commit_sha)
        except GitCommandError as exc:
            clean_msg = sanitize_git_url(str(exc))
            raise RuntimeError(f"Failed to checkout commit {commit_sha}: {clean_msg}") from exc

    # Extract active branch & commit details
    head_commit = repo.head.commit
    current_sha = head_commit.hexsha

    try:
        active_branch = repo.active_branch.name
    except TypeError:
        # Detached HEAD state
        active_branch = branch or "HEAD"

    default_branch = active_branch
    try:
        # Detect remote default branch if available
        remote_refs = repo.remotes.origin.refs
        for ref in remote_refs:
            if ref.name.endswith("/HEAD"):
                default_branch = ref.ref.name.split("/")[-1]
                break
    except Exception:
        pass

    author_name = head_commit.author.name or "Unknown"
    author_email = head_commit.author.email or ""
    author_display = f"{author_name} <{author_email}>" if author_email else author_name
    commit_msg = head_commit.message.strip()
    committed_at = datetime.fromtimestamp(head_commit.committed_date, tz=timezone.utc)

    # Check total size
    ws_mgr = WorkspaceManager()
    total_size_bytes = ws_mgr.calculate_size_bytes(target_dir)
    max_bytes = settings.max_repo_size_mb * 1024 * 1024

    if total_size_bytes > max_bytes:
        ws_mgr.cleanup_workspace(workspace.name)
        raise ValueError(
            f"Repository size ({total_size_bytes / (1024*1024):.1f} MB) exceeds "
            f"maximum allowed limit ({settings.max_repo_size_mb} MB)."
        )

    logger.info(
        "repository_clone_completed",
        commit_sha=current_sha[:8],
        branch=active_branch,
        size_mb=round(total_size_bytes / (1024 * 1024), 2),
    )

    return CloneResult(
        workspace_path=workspace,
        repo_path=target_dir,
        owner=owner,
        repo_name=repo_name,
        commit_sha=current_sha,
        branch=active_branch,
        default_branch=default_branch,
        author=author_display,
        commit_message=commit_msg,
        committed_at=committed_at,
        total_size_bytes=total_size_bytes,
    )
