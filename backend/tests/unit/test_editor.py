"""
Unit tests for the Code Modification Engine and SEARCH/REPLACE block parser.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.agents.editor import apply_search_replace_edit, implementation_node
from app.agents.prompts import SearchReplaceBlock, extract_search_replace_blocks
from app.agents.state import AgentState
from app.llm.provider import LLMResponse


def test_extract_search_replace_blocks():
    text = """
Here are the changes:
<<<<<<< SEARCH
def old_fn():
    return 1
=======
def old_fn():
    return 2
>>>>>>> REPLACE

And one more:
<<<<<<< SEARCH
def other():
    pass
=======
def other():
    return True
>>>>>>> REPLACE
"""
    blocks = extract_search_replace_blocks(text)
    assert len(blocks) == 2
    assert "def old_fn():" in blocks[0].search
    assert "return 2" in blocks[0].replace
    assert "def other():" in blocks[1].search
    assert "return True" in blocks[1].replace


def test_apply_search_replace_edit_exact():
    original = """
import os

def calculate_discount(price: float) -> float:
    return price * 0.10

def format_price(p: float) -> str:
    return f"${p:.2f}"
"""
    blocks = [
        SearchReplaceBlock(
            search="def calculate_discount(price: float) -> float:\n    return price * 0.10",
            replace="def calculate_discount(price: float, is_vip: bool = False) -> float:\n    discount = 0.20 if is_vip else 0.10\n    return price * discount",
        )
    ]

    success, updated, err = apply_search_replace_edit(original, blocks)
    assert success is True
    assert "is_vip: bool = False" in updated
    assert "def format_price" in updated


def test_apply_search_replace_edit_crlf_normalization():
    original = "line1\r\nline2\r\nline3\r\n"
    blocks = [
        SearchReplaceBlock(
            search="line2\n",
            replace="line2_modified\n",
        )
    ]
    success, updated, _ = apply_search_replace_edit(original, blocks)
    assert success is True
    assert "line2_modified" in updated


@pytest.mark.asyncio
async def test_implementation_node_full_write(tmp_path):
    # Setup mock workspace file
    app_file = tmp_path / "app.py"
    app_file.write_text("def ping():\n    return 'pong'\n", encoding="utf-8")

    mock_llm = MagicMock()
    mock_llm.complete = AsyncMock(
        return_value=LLMResponse(
            content="""<<<<<<< SEARCH
def ping():
    return 'pong'
=======
def ping():
    return {'status': 'ok'}
>>>>>>> REPLACE""",
            model="mock",
        )
    )

    state: AgentState = {
        "task_id": "task-edit-1",
        "workspace_path": str(tmp_path),
        "execution_plan": {
            "task_type": "bug_fix",
            "target_files": ["app.py"],
            "steps": [
                {
                    "step_number": 1,
                    "action": "modify_code",
                    "target_file": "app.py",
                    "description": "Return JSON from ping endpoint",
                    "rationale": "API standardization",
                    "status": "pending",
                }
            ],
            "test_strategy": [],
            "verification_criteria": [],
        },
    }

    with patch("app.agents.editor.get_llm_provider", return_value=mock_llm):
        result = await implementation_node(state)

        assert len(result["applied_changes"]) == 1
        assert result["applied_changes"][0]["file_path"] == "app.py"
        assert result["applied_changes"][0]["change_type"] == "modify"

        # Verify disk content changed
        updated_content = app_file.read_text(encoding="utf-8")
        assert "{'status': 'ok'}" in updated_content
