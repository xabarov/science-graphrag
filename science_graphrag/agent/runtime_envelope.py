"""Subagent fork warning codes for chat envelope assembly (Wave A runtime seam)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.runtime_subagent_collectors import (
    collect_claim_verification_results,
    collect_corpus_explore_results,
    collect_research_plan_results,
)


def collect_subagent_fork_warning_codes(messages: list[Any]) -> list[str]:
    """Return ordered warning codes for non-success or issue-bearing fork children."""
    out: list[str] = []
    for row in collect_claim_verification_results(messages):
        if not isinstance(row, dict):
            continue
        if str(row.get("terminal_state") or "") != "succeeded":
            out.append("claim_verification_child_non_success")
            break
        issues = row.get("issues")
        if isinstance(issues, list) and any(str(x).strip() for x in issues):
            out.append("claim_verification_child_issues")
            break

    for row in collect_corpus_explore_results(messages):
        if not isinstance(row, dict):
            continue
        if str(row.get("terminal_state") or "") != "succeeded":
            out.append("corpus_explore_child_non_success")
            break
        issues = row.get("issues")
        if isinstance(issues, list) and any(str(x).strip() for x in issues):
            out.append("corpus_explore_child_issues")
            break

    for row in collect_research_plan_results(messages):
        if not isinstance(row, dict):
            continue
        if str(row.get("terminal_state") or "") != "succeeded":
            out.append("research_plan_child_non_success")
            break
        issues = row.get("issues")
        if isinstance(issues, list) and any(str(x).strip() for x in issues):
            out.append("research_plan_child_issues")
            break

    return out


__all__ = ["collect_subagent_fork_warning_codes"]
