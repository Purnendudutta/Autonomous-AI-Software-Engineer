"""
Code and file search tools for the agent.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Optional

from app.core.security import PathTraversalError, safe_path
from app.repository.analyzer import IGNORED_DIRECTORIES, is_ignored_file


def find_files_tool(
    workspace_path: Path | str,
    pattern: str = "*",
    max_results: int = 50,
) -> dict[str, Any]:
    """
    Find files in the workspace matching a glob pattern (e.g. '*.py', '*auth*').
    """
    root = Path(workspace_path).resolve()
    matches: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRECTORIES and not d.startswith(".")]

        for filename in filenames:
            file_path = Path(dirpath) / filename
            if is_ignored_file(file_path, root):
                continue

            try:
                rel = str(file_path.relative_to(root)).replace("\\", "/")
            except ValueError:
                rel = filename

            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(rel, pattern):
                matches.append(rel)
                if len(matches) >= max_results:
                    break
        if len(matches) >= max_results:
            break

    return {"success": True, "pattern": pattern, "matches": matches, "total": len(matches)}


def search_code_regex_tool(
    workspace_path: Path | str,
    regex_pattern: str,
    file_extension: Optional[str] = None,
    max_results: int = 30,
) -> dict[str, Any]:
    """
    Search for regular expression patterns across workspace files.
    """
    root = Path(workspace_path).resolve()
    try:
        compiled_re = re.compile(regex_pattern, re.IGNORECASE)
    except re.error as exc:
        return {"success": False, "error": f"Invalid regex pattern: {exc}", "matches": []}

    matches: list[dict[str, Any]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRECTORIES and not d.startswith(".")]

        for filename in filenames:
            if file_extension and not filename.endswith(file_extension):
                continue

            file_path = Path(dirpath) / filename
            if is_ignored_file(file_path, root):
                continue

            try:
                rel = str(file_path.relative_to(root)).replace("\\", "/")
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, start=1):
                        if compiled_re.search(line):
                            matches.append({
                                "file_path": rel,
                                "line_number": line_no,
                                "line_content": line.strip(),
                            })
                            if len(matches) >= max_results:
                                break
            except Exception:
                pass
        if len(matches) >= max_results:
            break

    return {"success": True, "pattern": regex_pattern, "matches": matches, "total": len(matches)}
