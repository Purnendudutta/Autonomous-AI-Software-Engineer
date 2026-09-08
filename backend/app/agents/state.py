"""
Comprehensive AgentState TypedDict for the LangGraph agentic workflow.

Serializable, inspectable, and tracks the full lifecycle of an autonomous
software engineering task across all 12 pipeline nodes.
"""

from __future__ import annotations

from typing import Annotated, Any, Optional, TypedDict
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class PlanStep(TypedDict, total=False):
    """An individual step within the agent's execution plan."""
    step_number: int
    action: str  # read_file | modify_code | create_file | run_tests | verify
    target_file: str
    description: str
    rationale: str
    status: str  # pending | in_progress | completed | failed


class ExecutionPlan(TypedDict, total=False):
    """Structured execution plan produced by the planning agent node."""
    task_type: str  # bug_fix | feature | refactor | performance | docs
    root_cause_analysis: Optional[str]
    architecture_overview: Optional[str]
    target_files: list[str]
    steps: list[PlanStep]
    test_strategy: list[str]
    verification_criteria: list[str]


class ProposedChange(TypedDict, total=False):
    """A proposed code modification before being applied."""
    file_path: str
    change_type: str  # create | modify | delete
    original_snippet: Optional[str]
    new_snippet: str
    explanation: str


class AppliedChange(TypedDict, total=False):
    """A code modification applied to disk."""
    file_path: str
    change_type: str
    lines_added: int
    lines_removed: int
    diff: str


class AgentState(TypedDict, total=False):
    """
    The full state of the autonomous engineering agent across all graph nodes.
    """
    # ── Task Context ──────────────────────────────────────────────────────────
    task_id: str
    repository_id: str
    snapshot_id: str
    workspace_path: str
    task_description: str
    branch: Optional[str]
    target_commit: Optional[str]

    # ── Repository Intelligence ───────────────────────────────────────────────
    repository_summary: Optional[str]
    primary_language: Optional[str]
    detected_frameworks: list[str]
    detected_test_frameworks: list[str]
    file_tree_paths: list[str]

    # ── Task Understanding & Scoping ──────────────────────────────────────────
    task_intent: Optional[str]  # bug_fix | feature | refactor | docs
    identified_symbols: list[str]
    suggested_search_queries: list[str]

    # ── RAG / Codebase Retrieval ──────────────────────────────────────────────
    retrieved_chunks: list[dict[str, Any]]
    rag_context_formatted: Optional[str]

    # ── Planning ──────────────────────────────────────────────────────────────
    execution_plan: Optional[ExecutionPlan]
    identified_root_cause: Optional[str]
    affected_files: list[str]

    # ── Implementation & Tools ────────────────────────────────────────────────
    proposed_changes: list[ProposedChange]
    applied_changes: list[AppliedChange]
    git_diff: Optional[str]
    tool_call_history: list[dict[str, Any]]

    # ── Testing & Verification ────────────────────────────────────────────────
    generated_tests: list[dict[str, Any]]
    test_results: dict[str, Any]
    test_run_id: Optional[str]
    test_passed: bool
    tests_total: int
    tests_passed_count: int
    tests_failed_count: int
    verification_status: Optional[str]

    # ── Debugging & Retry Loop ────────────────────────────────────────────────
    retry_count: int
    max_retries: int
    should_retry: bool
    failure_category: Optional[str]  # syntax_error | test_failure | import_error | runtime_exception
    failure_analysis: Optional[str]
    last_error_log: Optional[str]

    # ── Review & Documentation ────────────────────────────────────────────────
    review_findings: list[dict[str, Any]]
    documentation_changes: list[dict[str, Any]]
    final_report_markdown: Optional[str]

    # ── Final Outcome ─────────────────────────────────────────────────────────
    final_status: str  # pending | running | succeeded | partial_success | failed | blocked
    error_message: Optional[str]

    # ── Chat & Model History ──────────────────────────────────────────────────
    messages: Annotated[list[AnyMessage], add_messages]
