"""
Patch and Git diff utilities with backup and atomic rollback capabilities.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

import git
from git.exc import InvalidGitRepositoryError

from app.core.logging import get_logger

logger = get_logger(__name__)


def create_file_backup(file_path: Path) -> Path:
    """
    Create a backup snapshot of a file prior to modification.
    """
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    if file_path.exists():
        shutil.copy2(file_path, backup_path)
        logger.debug("backup_created", file=str(file_path), backup=str(backup_path))
    return backup_path


def restore_file_backups(workspace_path: Path | str) -> list[str]:
    """
    Restore all modified files from their .bak backups and clean up backups.
    """
    root = Path(workspace_path).resolve()
    restored: list[str] = []

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".bak"):
                bak_file = Path(dirpath) / fname
                orig_file = bak_file.with_suffix("")  # strip .bak

                shutil.copy2(bak_file, orig_file)
                bak_file.unlink()

                try:
                    rel = str(orig_file.relative_to(root)).replace("\\", "/")
                except ValueError:
                    rel = orig_file.name
                restored.append(rel)

    logger.info("backups_restored", count=len(restored), files=restored)
    return restored


def cleanup_file_backups(workspace_path: Path | str) -> int:
    """
    Remove all .bak files across workspace.
    """
    root = Path(workspace_path).resolve()
    cleaned = 0

    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            if fname.endswith(".bak"):
                (Path(dirpath) / fname).unlink(missing_ok=True)
                cleaned += 1

    return cleaned


def calculate_diff_stats(diff_text: str) -> tuple[int, int, list[str]]:
    """
    Calculate lines added, lines removed, and changed file paths from unified diff.

    Returns:
        (lines_added, lines_removed, files_changed)
    """
    lines_added = 0
    lines_removed = 0
    files_changed: set[str] = set()

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            files_changed.add(line[6:].strip())
        elif line.startswith("+") and not line.startswith("+++"):
            lines_added += 1
        elif line.startswith("-") and not line.startswith("---"):
            lines_removed += 1

    return lines_added, lines_removed, sorted(list(files_changed))


def get_workspace_git_diff(workspace_path: Path | str) -> dict[str, Any]:
    """
    Generate unified git diff for all modifications in the workspace.
    """
    root = Path(workspace_path).resolve()
    if not root.exists():
        return {"diff": "", "lines_added": 0, "lines_removed": 0, "files_changed": []}

    try:
        repo = git.Repo(root, search_parent_directories=True)
    except InvalidGitRepositoryError:
        return {"diff": "", "lines_added": 0, "lines_removed": 0, "files_changed": []}

    try:
        diff_text = repo.git.diff("HEAD")

        # Also capture untracked newly created files
        untracked = repo.untracked_files
        for uf in untracked:
            if uf.endswith(".bak"):
                continue
            uf_path = root / uf
            if uf_path.is_file():
                try:
                    content = uf_path.read_text(encoding="utf-8", errors="ignore")
                    diff_text += f"\n--- /dev/null\n+++ b/{uf}\n@@ -0,0 +1,{len(content.splitlines())} @@\n"
                    diff_text += "\n".join("+" + l for l in content.splitlines()) + "\n"
                except Exception:
                    pass

        lines_added, lines_removed, files_changed = calculate_diff_stats(diff_text)

        return {
            "diff": diff_text.strip(),
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "files_changed": files_changed or [u for u in untracked if not u.endswith(".bak")],
        }
    except Exception as exc:
        logger.warning("git_diff_failed", error=str(exc))
        return {"diff": "", "lines_added": 0, "lines_removed": 0, "files_changed": []}
