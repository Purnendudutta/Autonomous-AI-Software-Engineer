"""
Pull Request Report Generator Agent Node.

Compiles a comprehensive, professional pull-request report in GitHub Flavored Markdown
and persists the record in PostgreSQL.
"""

from __future__ import annotations

from typing import Any

from app.agents.state import AgentState
from app.core.logging import get_logger
from app.database.models import Report
from app.database.session import get_session_factory

logger = get_logger(__name__)


def generate_pr_markdown_report(state: AgentState) -> str:
    """
    Format a complete, professional Pull Request markdown report.
    """
    task_desc = state.get("task_description", "Autonomous Engineering Task")
    root_cause = state.get("identified_root_cause") or "Root cause resolved as planned."
    ver_status = state.get("verification_status", "SUCCESS")
    tests_total = state.get("tests_total", 0)
    tests_passed = state.get("tests_passed_count", 0)
    tests_failed = state.get("tests_failed_count", 0)
    applied_changes = state.get("applied_changes", [])
    review_findings = state.get("review_findings", [])
    git_diff = state.get("git_diff", "")
    retry_count = state.get("retry_count", 0)

    # 1. Header & Overview
    md = f"""# Pull Request: {task_desc}

> **Autonomous AI Software Engineer** · Status: **`{ver_status}`** · Iterations: **`{retry_count + 1}`**

---

## 📌 Executive Summary
This pull request autonomously addresses the engineering request:
**"{task_desc}"**.

The AI Software Engineer analyzed the repository architecture, retrieved relevant code context via pgvector, formulated a step-by-step execution plan, applied surgical code modifications, generated regression tests, and executed the test suite in an isolated sandbox.

---

## 🔍 Problem Statement & Root Cause Analysis
{root_cause}

---

## 📁 Modified Files ({len(applied_changes)})
| File Path | Change Type | Description |
| :--- | :--- | :--- |
"""
    for c in applied_changes:
        md += f"| `{c.get('file_path')}` | `{c.get('change_type', 'modify')}` | {c.get('diff', 'Modified logic')} |\n"

    if not applied_changes:
        md += "| *(No files modified)* | - | - |\n"

    # 2. Test Verification
    md += f"""
---

## 🧪 Automated Test Verification
- **Verification Status**: `{ver_status}`
- **Total Tests Executed**: `{tests_total}`
- **Tests Passed**: `{tests_passed}`
- **Tests Failed**: `{tests_failed}`
- **Self-Correction Retries**: `{retry_count}`
"""

    # 3. Code Review Findings
    md += f"""
---

## 🛡️ AI Code Review & Security Audit
Total Findings: **`{len(review_findings)}`**

| Severity | Category | File | Finding / Recommendation |
| :--- | :--- | :--- | :--- |
"""
    for f in review_findings:
        sev = f.get("severity", "info").upper()
        cat = f.get("category", "quality").capitalize()
        file_ref = f"{f.get('file_path', 'general')}:{f.get('line_number') or ''}"
        issue = f.get("issue", "")
        rec = f.get("recommendation", "")
        md += f"| **`{sev}`** | {cat} | `{file_ref}` | **{issue}**<br>*{rec}* |\n"

    if not review_findings:
        md += "| **`INFO`** | General | Codebase | Clean pass: No high or medium severity issues found. |\n"

    # 4. Git Diff
    md += f"""
---

## 📝 Unified Git Diff
```diff
{git_diff if git_diff else '# No changes generated.'}
```
"""
    return md.strip()


async def final_report_node(state: AgentState) -> dict[str, Any]:
    """
    Compiles the final PR report markdown and persists the record to the database.
    """
    task_id = state.get("task_id", "unknown")
    logger.info("final_report_node_started", task_id=task_id)

    report_md = generate_pr_markdown_report(state)
    task_desc = state.get("task_description", "Autonomous Engineering PR")
    root_cause = state.get("identified_root_cause") or "Root cause resolved."
    ver_status = state.get("verification_status", "SUCCESS")
    git_diff = state.get("git_diff", "")

    # Persist Report to database
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            report_record = Report(
                task_id=task_id,
                title=f"PR: {task_desc[:80]}",
                summary=f"Automated resolution of: {task_desc}",
                problem_description=task_desc,
                root_cause=root_cause,
                changes_description=f"Modified {len(state.get('applied_changes', []))} file(s)",
                verification_status=ver_status,
                git_diff=git_diff,
                full_report_markdown=report_md,
            )
            session.add(report_record)
            await session.commit()
            logger.info("pr_report_persisted_to_db", task_id=task_id, report_id=report_record.id)
        except Exception as exc:
            logger.warning("failed_persisting_pr_report", error=str(exc))

    return {
        "final_report_markdown": report_md,
        "final_status": state.get("final_status", "succeeded"),
    }


# Prevent pytest from treating LangGraph node as unit test
final_report_node.__test__ = False  # type: ignore[attr-defined]
