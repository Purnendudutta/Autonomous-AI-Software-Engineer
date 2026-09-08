"""
Unit tests for safe filesystem, code search, and git tools.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from app.tools.filesystem import (
    list_directory_tool,
    read_file_tool,
    replace_in_file_tool,
    write_file_tool,
)
from app.tools.search import find_files_tool, search_code_regex_tool


def test_filesystem_read_and_write(tmp_path):
    res_write = write_file_tool(tmp_path, "src/hello.py", "print('hello world')\n")
    assert res_write["success"] is True

    res_read = read_file_tool(tmp_path, "src/hello.py")
    assert res_read["success"] is True
    assert "hello world" in res_read["content"]


def test_filesystem_path_traversal_blocked(tmp_path):
    res = read_file_tool(tmp_path, "../../etc/passwd")
    assert res["success"] is False
    assert "Security violation" in res["error"]


def test_filesystem_replace_in_file(tmp_path):
    write_file_tool(tmp_path, "app.py", "def add(a, b):\n    return a - b\n")

    res = replace_in_file_tool(tmp_path, "app.py", "return a - b", "return a + b")
    assert res["success"] is True

    res_read = read_file_tool(tmp_path, "app.py")
    assert "return a + b" in res_read["content"]


def test_list_directory_tool(tmp_path):
    write_file_tool(tmp_path, "pkg/a.py", "a = 1")
    write_file_tool(tmp_path, "pkg/b.py", "b = 2")

    res = list_directory_tool(tmp_path, "pkg")
    assert res["success"] is True
    assert len(res["entries"]) == 2


def test_search_code_regex_tool(tmp_path):
    write_file_tool(tmp_path, "auth.py", "def authenticate_user(token):\n    pass\n")
    write_file_tool(tmp_path, "models.py", "class User:\n    pass\n")

    res = search_code_regex_tool(tmp_path, r"def authenticate")
    assert res["success"] is True
    assert len(res["matches"]) == 1
    assert res["matches"][0]["file_path"] == "auth.py"
