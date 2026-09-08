"""
Documentation and Changelog Generator Agent Node.
"""

from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.core.logging import get_logger

logger = get_logger(__name__)


async def documentation_node(state: AgentState) -> dict[str, Any]:
    """
    Generates changelog entries and documentation notes for applied code modifications.
    """
    task_id = state.get("task_id", "unknown")
    applied_changes = state.get("applied_changes", [])
    task_desc = state.get("task_description", "")

    logger.info("documentation_node_started", task_id=task_id)

    doc_entries: list[dict[str, Any]] = []

    for change in applied_changes:
        file_path = change.get("file_path", "unknown")
        change_type = change.get("change_type", "modify")
        doc_entries.append({
            "file_path": file_path,
            "type": change_type,
            "note": f"Updated {file_path} to support: {task_desc}",
        })

    return {"documentation_changes": doc_entries}


# Prevent pytest from treating LangGraph node as unit test
documentation_node.__test__ = False  # type: ignore[attr-defined]
