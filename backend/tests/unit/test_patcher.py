"""
Unit tests for patch, git diff, and backup management.
"""

from __future__ import annotations

from pathlib import Path
from app.agents.patcher import (
    calculate_diff_stats,
    cleanup_file_backups,
    create_file_backup,
    restore_file_backups,
)


def test_calculate_diff_stats():
    sample_diff = """--- a/app/main.py
+++ b/app/main.py
@@ -10,3 +10,4 @@
 def health():
-    return "ok"
+    return {"status": "ok"}
+    # extra line
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,2 +1,1 @@
-import deprecated
"""
    lines_added, lines_removed, files = calculate_diff_stats(sample_diff)

    assert lines_added == 2
    assert lines_removed == 2
    assert "app/main.py" in files
    assert "app/auth.py" in files


def test_backup_and_restore_cycle(tmp_path):
    target = tmp_path / "service.py"
    target.write_text("original content\n", encoding="utf-8")

    # 1. Create backup
    bak = create_file_backup(target)
    assert bak.exists()

    # 2. Modify target
    target.write_text("corrupted / broken modification\n", encoding="utf-8")

    # 3. Restore
    restored = restore_file_backups(tmp_path)
    assert len(restored) == 1
    assert target.read_text(encoding="utf-8") == "original content\n"
    assert not bak.exists()


def test_cleanup_file_backups(tmp_path):
    f1 = tmp_path / "a.py.bak"
    f2 = tmp_path / "b.py.bak"
    f1.write_text("bak1")
    f2.write_text("bak2")

    cleaned = cleanup_file_backups(tmp_path)
    assert cleaned == 2
    assert not f1.exists()
    assert not f2.exists()
