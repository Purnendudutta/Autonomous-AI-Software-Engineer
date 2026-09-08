"""
Task Understanding, Code Retrieval, and Structured Planning agent nodes.
"""

from __future__ import annotations

import json
from typing import Any

from app.agents.prompts import (
    PLANNER_SYSTEM_PROMPT,
    TASK_UNDERSTANDING_SYSTEM_PROMPT,
    extract_json_from_response,
)
from app.agents.state import AgentState, ExecutionPlan, PlanStep
from app.api.dependencies import get_embedding_provider, get_llm_provider
from app.core.logging import get_logger
from app.database.session import get_session_factory
from app.llm.provider import Message
from app.rag.retriever import CodebaseRetriever

logger = get_logger(__name__)


async def task_understanding(state: AgentState) -> dict[str, Any]:
    """
    Analyzes the user's task description to classify intent, extract target
    symbols, and generate targeted search queries for Codebase RAG.
    """
    task_desc = state.get("task_description", "")
    repo_summary = state.get("repository_summary", "")
    task_id = state.get("task_id", "unknown")

    logger.info("task_understanding_started", task_id=task_id, task_desc=task_desc[:60])

    llm = get_llm_provider()
    user_prompt = f"""Repository Summary:
{repo_summary}

User Task Request:
{task_desc}

Analyze this task and return the required JSON schema."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=TASK_UNDERSTANDING_SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.1,
            max_tokens=1024,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.warning("task_understanding_llm_failed_using_heuristic", error=str(exc))
        data = {}

    task_intent = data.get("task_intent") or ("bug_fix" if any(w in task_desc.lower() for w in ("fix", "bug", "error", "fail")) else "feature")
    identified_symbols = data.get("target_symbols") or []
    suggested_queries = data.get("rag_search_queries") or [task_desc]

    logger.info(
        "task_understanding_completed",
        task_intent=task_intent,
        symbols_count=len(identified_symbols),
        queries_count=len(suggested_queries),
    )

    return {
        "task_intent": task_intent,
        "identified_symbols": identified_symbols,
        "suggested_search_queries": suggested_queries,
    }


async def code_retrieval(state: AgentState) -> dict[str, Any]:
    """
    Retrieves the most relevant code chunks from pgvector using the queries
    generated in task_understanding.
    """
    snapshot_id = state.get("snapshot_id")
    task_id = state.get("task_id", "unknown")
    queries = state.get("suggested_search_queries") or [state.get("task_description", "")]
    embedding_provider = get_embedding_provider()

    logger.info("code_retrieval_started", task_id=task_id, snapshot_id=snapshot_id)

    if not snapshot_id:
        return {"retrieved_chunks": [], "rag_context_formatted": "No repository snapshot available."}

    all_chunks: list[dict[str, Any]] = []
    seen_chunk_ids: set[str] = set()

    session_factory = get_session_factory()
    async with session_factory() as session:
        retriever = CodebaseRetriever(session=session, embedding_provider=embedding_provider)

        for q in queries[:3]:
            try:
                results = await retriever.search(
                    snapshot_id=snapshot_id,
                    query=q,
                    limit=4,
                    similarity_threshold=0.25,
                )
                for r in results:
                    if r.id not in seen_chunk_ids:
                        seen_chunk_ids.add(r.id)
                        all_chunks.append(r.model_dump())
            except Exception as exc:
                logger.warning("retrieval_query_failed", query=q, error=str(exc))

    # Format code context for LLM prompt
    formatted_chunks: list[str] = []
    for idx, c in enumerate(all_chunks, start=1):
        formatted_chunks.append(
            f"--- [Chunk {idx}] File: {c['file_path']} (L{c['start_line']}-L{c['end_line']}) | Symbol: {c.get('symbol_name') or 'N/A'} ---\n{c['content']}"
        )

    rag_context = "\n\n".join(formatted_chunks) if formatted_chunks else "No relevant code chunks found."

    logger.info("code_retrieval_completed", total_chunks=len(all_chunks))

    return {
        "retrieved_chunks": all_chunks,
        "rag_context_formatted": rag_context,
    }


async def plan(state: AgentState) -> dict[str, Any]:
    """
    Generates a structured, validated step-by-step execution plan from the
    retrieved code context and task description.
    """
    task_desc = state.get("task_description", "")
    rag_context = state.get("rag_context_formatted", "")
    repo_summary = state.get("repository_summary", "")
    task_id = state.get("task_id", "unknown")

    logger.info("planning_started", task_id=task_id)

    llm = get_llm_provider()
    user_prompt = f"""Repository Overview:
{repo_summary}

User Task Description:
{task_desc}

Relevant Code Chunks from Codebase RAG:
{rag_context}

Produce the structured Execution Plan JSON according to the schema."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=PLANNER_SYSTEM_PROMPT),
                Message(role="user", content=user_prompt),
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.error("planning_llm_failed", error=str(exc))
        data = {}

    # Extract or build structured plan
    task_type = data.get("task_type") or state.get("task_intent") or "bug_fix"
    root_cause = data.get("root_cause_analysis") or "Root cause determined during execution."
    target_files = data.get("target_files") or []
    steps_raw = data.get("steps") or []

    steps: list[PlanStep] = []
    for i, s in enumerate(steps_raw, start=1):
        steps.append({
            "step_number": s.get("step_number", i),
            "action": s.get("action", "modify_code"),
            "target_file": s.get("target_file", target_files[0] if target_files else "unknown"),
            "description": s.get("description", "Execute planned modification"),
            "rationale": s.get("rationale", "Fulfill task requirements"),
            "status": "pending",
        })

    if not steps:
        steps = [{
            "step_number": 1,
            "action": "modify_code",
            "target_file": target_files[0] if target_files else "main.py",
            "description": f"Implement changes for: {task_desc}",
            "rationale": "Direct implementation",
            "status": "pending",
        }]

    plan_obj: ExecutionPlan = {
        "task_type": task_type,
        "root_cause_analysis": root_cause,
        "architecture_overview": data.get("architecture_overview") or "Modular software architecture.",
        "target_files": target_files,
        "steps": steps,
        "test_strategy": data.get("test_strategy") or ["Execute automated test suite in Docker sandbox."],
        "verification_criteria": data.get("verification_criteria") or ["All unit tests pass."],
    }

    logger.info(
        "planning_completed",
        target_files=target_files,
        total_steps=len(steps),
    )

    return {
        "execution_plan": plan_obj,
        "identified_root_cause": root_cause,
        "affected_files": target_files,
    }
