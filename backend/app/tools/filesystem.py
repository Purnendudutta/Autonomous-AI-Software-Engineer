"""
Safe filesystem tools with strict workspace path boundary enforcement.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from app.core.logging import get_logger
from app.core.security import PathTraversalError, safe_path

logger = get_logger(__name__)


def read_file_tool(
    workspace_path: Path | str,
    relative_path: str,
    start_line: Optional[int] = None,
    end_line: Optional[int] = None,
) -> dict[str, Any]:
    """
    Safely read the content of a file within the workspace.

    Args:
        workspace_path: Root workspace directory path.
        relative_path: Target file path relative to workspace.
        start_line: Optional 1-indexed start line.
        end_line: Optional 1-indexed end line.

    Returns:
        Dict with keys: success, content, file_path, total_lines, error.
    """
    root = Path(workspace_path).resolve()
    try:
        target = safe_path(root, relative_path)
    except PathTraversalError as exc:
        return {"success": False, "error": f"Security violation: {exc}", "content": ""}

    if not target.is_file():
        return {"success": False, "error": f"File '{relative_path}' does not exist.", "content": ""}

    try:
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if start_line is not None or end_line is not None:
            s_idx = max(0, (start_line or 1) - 1)
            e_idx = min(total_lines, end_line or total_lines)
            content = "".join(lines[s_idx:e_idx])
        else:
            content = "".join(lines)

        return {
            "success": True,
            "file_path": relative_path,
            "content": content,
            "total_lines": total_lines,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to read file: {exc}", "content": ""}


def write_file_tool(
    workspace_path: Path | str,
    relative_path: str,
    content: str,
    overwrite: bool = True,
) -> dict[str, Any]:
    """
    Safely write or create a file within the workspace.

    Args:
        workspace_path: Root workspace directory path.
        relative_path: Target file path relative to workspace.
        content: Text content to write.
        overwrite: If False, raises error if file already exists.
    """
    root = Path(workspace_path).resolve()
    try:
        target = safe_path(root, relative_path)
    except PathTraversalError as exc:
        return {"success": False, "error": f"Security violation: {exc}"}

    if target.exists() and not overwrite:
        return {"success": False, "error": f"File '{relative_path}' already exists and overwrite is False."}

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("file_written", file=relative_path, bytes=len(content))
        return {
            "success": True,
            "file_path": relative_path,
            "bytes_written": len(content),
            "created": not target.exists(),
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to write file: {exc}"}


def replace_in_file_tool(
    workspace_path: Path | str,
    relative_path: str,
    target_content: str,
    replacement_content: str,
) -> dict[str, Any]:
    """
    Safely replace a specific unique text block in a file.
    """
    root = Path(workspace_path).resolve()
    try:
        target = safe_path(root, relative_path)
    except PathTraversalError as exc:
        return {"success": False, "error": f"Security violation: {exc}"}

    if not target.is_file():
        return {"success": False, "error": f"File '{relative_path}' does not exist."}

    try:
        content = target.read_text(encoding="utf-8")
        if target_content not in content:
            return {
                "success": False,
                "error": "Target content to replace was not found in the file.",
            }

        occurrences = content.count(target_content)
        if occurrences > 1:
            return {
                "success": False,
                "error": f"Target content occurs {occurrences} times. Must be unique.",
            }

        new_content = content.replace(target_content, replacement_content, 1)
        target.write_text(new_content, encoding="utf-8")
        logger.info("file_content_replaced", file=relative_path)
        return {
            "success": True,
            "file_path": relative_path,
            "replacements_made": 1,
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to replace content: {exc}"}


def list_directory_tool(
    workspace_path: Path | str,
    relative_path: str = "",
    max_depth: int = 3,
) -> dict[str, Any]:
    """
    Safely list directory contents within the workspace.
    """
    root = Path(workspace_path).resolve()
    try:
        target = safe_path(root, relative_path)
    except PathTraversalError as exc:
        return {"success": False, "error": f"Security violation: {exc}", "entries": []}

    if not target.is_dir():
        return {"success": False, "error": f"Directory '{relative_path}' does not exist.", "entries": []}

    entries: list[dict[str, Any]] = []
    try:
        for entry in target.iterdir():
            if entry.name.startswith(".") and entry.name != ".github":
                continue
            if entry.name in ("node_modules", "__pycache__", ".venv", "venv"):
                continue

            rel = str(entry.relative_to(root)).replace("\\", "/")
            entries.append({
                "name": entry.name,
                "path": rel,
                "is_dir": entry.is_dir(),
                "size_bytes": entry.stat().st_size if entry.is_file() else 0,
            })

        return {"success": True, "directory": relative_path, "entries": sorted(entries, key=lambda e: (not e["is_dir"], e["name"]))}
    except Exception as exc:
        return {"success": False, "error": f"Failed to list directory: {exc}", "entries": []}
