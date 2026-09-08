"""
Autonomous AI Code Review Agent Node.

Audits final Git diffs for security vulnerabilities, performance regressions,
and architecture quality, persisting findings in PostgreSQL.
"""

from __future__ import annotations

from typing import Any

from app.agents.prompts import CODE_REVIEW_SYSTEM_PROMPT, extract_json_from_response
from app.agents.state import AgentState
from app.api.dependencies import get_llm_provider
from app.core.logging import get_logger
from app.database.models import ReviewFinding
from app.database.session import get_session_factory
from app.llm.provider import Message

logger = get_logger(__name__)


async def code_review_node(state: AgentState) -> dict[str, Any]:
    """
    Performs automated security, quality, and performance code review pass.
    """
    task_id = state.get("task_id", "unknown")
    git_diff = state.get("git_diff", "")

    logger.info("code_review_node_started", task_id=task_id, diff_length=len(git_diff))

    if not git_diff:
        return {"review_findings": []}

    llm = get_llm_provider()
    prompt = f"""Task Description:
{state.get('task_description', '')}

Unified Git Diff to Review:
```diff
{git_diff[:8000]}
```

Perform thorough security, performance, quality, and maintainability review according to schema."""

    try:
        response = await llm.complete(
            messages=[
                Message(role="system", content=CODE_REVIEW_SYSTEM_PROMPT),
                Message(role="user", content=prompt),
            ],
            temperature=0.1,
            max_tokens=2048,
        )
        data = extract_json_from_response(response.content)
    except Exception as exc:
        logger.error("code_review_llm_failed", error=str(exc))
        data = {}

    findings_raw = data.get("findings", [])
    findings: list[dict[str, Any]] = []

    for f in findings_raw:
        findings.append({
            "severity": f.get("severity", "info"),
            "category": f.get("category", "quality"),
            "file_path": f.get("file_path"),
            "line_number": f.get("line_number"),
            "issue": f.get("issue", "Code quality observation"),
            "recommendation": f.get("recommendation", "Follow project standards"),
        })

    # Persist ReviewFinding records to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            for f in findings:
                finding_record = ReviewFinding(
                    task_id=task_id,
                    severity=f["severity"],
                    category=f["category"],
                    file_path=f["file_path"],
                    line_number=f["line_number"],
                    issue=f["issue"],
                    recommendation=f["recommendation"],
                )
                session.add(finding_record)

            await session.commit()
            logger.info("review_findings_persisted_to_db", task_id=task_id, count=len(findings))
        except Exception as exc:
            logger.warning("failed_persisting_review_findings", error=str(exc))

    return {"review_findings": findings}


# Prevent pytest from treating LangGraph node as unit test
code_review_node.__test__ = False  # type: ignore[attr-defined]
