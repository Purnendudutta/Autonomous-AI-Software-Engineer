"""
LangGraph agent state machine definition.

Wires all 12 pipeline nodes with state tracking, error handling,
and conditional retry loops.
"""

from __future__ import annotations

from typing import Any
from langgraph.graph import END, START, StateGraph

from app.agents.debugger import failure_analysis_node
from app.agents.documenter import documentation_node
from app.agents.editor import implementation_node
from app.agents.planner import code_retrieval, plan, task_understanding
from app.agents.reporter import final_report_node
from app.agents.reviewer import code_review_node
from app.agents.state import AgentState
from app.agents.tester import test_execution_node, test_generation_node
from app.agents.verifier import verification_node
from app.core.logging import get_logger

logger = get_logger(__name__)


# ─── Node Handlers ───────────────────────────────────────────────────────────

async def repository_analysis_node(state: AgentState) -> dict[str, Any]:
    """Inspects workspace state and summary before agent reasoning."""
    logger.info("node_repository_analysis", task_id=state.get("task_id"))
    return {
        "workspace_path": state.get("workspace_path", ""),
        "primary_language": state.get("primary_language", "Python"),
    }


async def task_understanding_node(state: AgentState) -> dict[str, Any]:
    """Analyzes task intent and formulates RAG queries."""
    return await task_understanding(state)


async def code_retrieval_node(state: AgentState) -> dict[str, Any]:
    """Performs hybrid code retrieval from pgvector."""
    return await code_retrieval(state)


async def planning_node(state: AgentState) -> dict[str, Any]:
    """Generates structured execution plan using LLM."""
    return await plan(state)


# ─── Conditional Routing ─────────────────────────────────────────────────────

def should_retry_router(state: AgentState) -> str:
    """
    Route after failure_analysis:
      - 'retry'  → back to implementation if retry count < max_retries
      - 'verify' → proceed to verification
    """
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    should_retry = state.get("should_retry", False)

    if should_retry and retry_count < max_retries:
        return "retry"
    return "verify"


# ─── Graph Builder ───────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    """Construct and compile the LangGraph state machine."""
    builder = StateGraph(AgentState)

    # Register all 12 nodes
    builder.add_node("repository_analysis", repository_analysis_node)
    builder.add_node("task_understanding", task_understanding_node)
    builder.add_node("code_retrieval", code_retrieval_node)
    builder.add_node("planning", planning_node)
    builder.add_node("implementation", implementation_node)
    builder.add_node("test_generation", test_generation_node)
    builder.add_node("test_execution", test_execution_node)
    builder.add_node("failure_analysis", failure_analysis_node)
    builder.add_node("verification", verification_node)
    builder.add_node("code_review", code_review_node)
    builder.add_node("documentation", documentation_node)
    builder.add_node("final_report", final_report_node)

    # Linear workflow sequence
    builder.add_edge(START, "repository_analysis")
    builder.add_edge("repository_analysis", "task_understanding")
    builder.add_edge("task_understanding", "code_retrieval")
    builder.add_edge("code_retrieval", "planning")
    builder.add_edge("planning", "implementation")
    builder.add_edge("implementation", "test_generation")
    builder.add_edge("test_generation", "test_execution")
    builder.add_edge("test_execution", "failure_analysis")

    # Conditional retry loop
    builder.add_conditional_edges(
        "failure_analysis",
        should_retry_router,
        {
            "retry": "implementation",
            "verify": "verification",
        },
    )

    builder.add_edge("verification", "code_review")
    builder.add_edge("code_review", "documentation")
    builder.add_edge("documentation", "final_report")
    builder.add_edge("final_report", END)

    return builder


# Compiled agent graph instance
agent_graph = build_agent_graph().compile()
