"""Rule-based tool shortlist (Wave A — CH3)."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import ToolManifestEntry, manifest_by_name
from science_graphrag.config import Settings


def _norm_question(q: str) -> str:
    return (q or "").strip().lower()


def _score_tool(meta: ToolManifestEntry, q: str, *, has_workspace: bool) -> float:
    if meta.requires_workspace and not has_workspace:
        return -1.0
    score = 0.0
    if meta.name == "format_bibliography_gost" and any(
        x in q for x in ("gost", "гост", "bibliograph", "литератур", "references")
    ):
        score += 6.0
    for tag in meta.tags:
        if tag and tag in q:
            score += 2.0
    # family hints
    if meta.family == "bibliography" and any(
        x in q for x in ("gost", "гост", "bibliograph", "литератур")
    ):
        score += 5.0
    if meta.family == "catalog" and any(
        x in q for x in ("paper", "work", "стат", "workspace", "how many", "list")
    ):
        score += 1.5
    if meta.name == "paper_quote_search" and any(
        x in q for x in ("quote", "цитат", "passage", "snippet", "where")
    ):
        score += 4.0
    if meta.name == "idea_search" and any(
        x in q for x in ("idea", "similar", "related", "semantic", "chunk")
    ):
        score += 3.0
    if meta.name == "summarize_workspace" and "summar" in q:
        score += 3.0
    if meta.family == "graph" and any(
        x in q for x in ("cites", "cypher", "graph", "path", "relation", "edge", "entity")
    ):
        score += 2.5
    if meta.name == "cypher_query" and ("cypher" in q or "neo4j" in q):
        score += 4.0
    if meta.name == "final_answer":
        score += 0.1
    return score


def shortlist_tools_for_specialist(
    tools: list[BaseTool],
    *,
    question: str,
    specialist: str,
    settings: Settings,
    has_workspace: bool,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Return possibly narrowed tool list and debug meta for SSE / run_metadata."""
    if not settings.agent_rule_tool_search_enabled:
        return tools, {"skipped": True, "reason": "disabled"}
    if specialist == "writer_agent":
        return tools, {"skipped": True, "reason": "writer_minimal_set"}

    by_meta = manifest_by_name()
    q = _norm_question(question)
    scored: list[tuple[float, BaseTool]] = []
    for t in tools:
        name = getattr(t, "name", "") or ""
        meta = by_meta.get(name)
        if meta is None or meta.specialist not in (None, specialist):
            continue
        s = _score_tool(meta, q, has_workspace=has_workspace)
        if s < 0:
            continue
        scored.append((s, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return tools, {"reason": "fallback_full", "matched": []}

    top_score = scored[0][0]
    if top_score < 1.5:
        return tools, {"reason": "low_signal", "top_score": top_score}

    threshold = max(0.0, top_score - 1.5)
    picked = [t for s, t in scored if s >= threshold and s > 0]
    if specialist == "retrieval_agent":
        have = {getattr(t, "name", "") for t in picked}
        for extra in ("idea_search", "summarize_workspace"):
            if extra not in have:
                hit = next((t for t in tools if getattr(t, "name", "") == extra), None)
                if hit is not None:
                    picked.append(hit)
                    have.add(extra)
    # Retrieval catalog is large — avoid over-narrow shortlists
    # Keep shortlists only when they still cover a reasonable slice of the catalog.
    if specialist == "retrieval_agent" and len(picked) < 3:
        return tools, {
            "reason": "fallback_full",
            "matched": [getattr(x, "name", "") for x in picked],
        }
    if specialist == "graph_agent" and len(picked) < 2:
        return tools, {
            "reason": "fallback_full",
            "matched": [getattr(x, "name", "") for x in picked],
        }

    names = [getattr(t, "name", "") for t in picked]
    return picked, {"reason": "rules", "matched": names, "top_score": top_score}
