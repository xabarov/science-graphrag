"""Rule-based tool shortlist (Wave A — CH3)."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import ToolManifestEntry, manifest_by_name
from science_graphrag.config import Settings

_SESSION_MEMORY_RE = re.compile(
    r"<session_memory>.*?</session_memory>\s*",
    re.DOTALL | re.IGNORECASE,
)
_CLIENT_DIGEST_RE = re.compile(
    r"<client_history_digest>.*?</client_history_digest>\s*",
    re.DOTALL | re.IGNORECASE,
)
_ACTIVE_WS_ID_RE = re.compile(
    r"<active_workspace_id>.*?</active_workspace_id>\s*",
    re.DOTALL | re.IGNORECASE,
)


def strip_tool_search_context_wrappers(text: str) -> str:
    """Strip CH4 memory/digest XML blocks so scoring uses the user's question only."""
    s = text or ""
    s = _SESSION_MEMORY_RE.sub("", s)
    s = _CLIENT_DIGEST_RE.sub("", s)
    s = _ACTIVE_WS_ID_RE.sub("", s)
    return s.strip()


def _norm_question(q: str) -> str:
    return (q or "").strip().lower()


_RETRIEVAL_CORE_CATALOG = (
    "workspace_overview",
    "workspace_list_papers",
    "paper_lookup",
    "paper_metadata",
    "paper_authors",
    "paper_counts",
)


def _answer_class_tool_boost(meta: ToolManifestEntry, answer_class: str | None) -> float:
    """Bias shortlist toward tools that match coordinator / envelope answer class."""
    if not answer_class:
        return 0.0
    ac = answer_class
    name = meta.name
    boost = 0.0
    if ac == "fact_lookup" and name in ("paper_authors", "paper_metadata", "paper_lookup"):
        boost += 3.5
    if ac == "bibliography_export" and name == "format_bibliography_gost":
        boost += 5.0
    if ac == "quote_extraction" and name == "paper_quote_search":
        boost += 5.0
    if ac == "relation_tracing" and meta.family == "graph":
        boost += 3.5
    if ac == "inventory" and name in ("workspace_overview", "workspace_list_papers", "paper_counts"):
        boost += 3.5
    if ac == "ideation" and name in ("idea_search", "summarize_workspace"):
        boost += 2.5
    return boost


def _score_tool(
    meta: ToolManifestEntry,
    q: str,
    *,
    has_workspace: bool,
    answer_class: str | None = None,
) -> float:
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
        x in q
        for x in (
            "paper",
            "work",
            "стат",
            "workspace",
            "how many",
            "list",
            "сколько",
            "список",
            "работ",
            "област",
            "корпус",
            "стать",
        )
    ):
        score += 1.5
    if meta.name in ("workspace_overview", "workspace_list_papers", "paper_counts") and any(
        x in q
        for x in ("сколько", "how many", "count", "список", "област", "стат", "корпус", "работ")
    ):
        score += 4.0
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
    score += _answer_class_tool_boost(meta, answer_class)
    return score


def shortlist_tools_for_specialist(
    tools: list[BaseTool],
    *,
    question: str,
    specialist: str,
    settings: Settings,
    has_workspace: bool,
    answer_class: str | None = None,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Return possibly narrowed tool list and debug meta for SSE / run_metadata."""
    if not settings.agent_rule_tool_search_enabled:
        return tools, {"skipped": True, "reason": "disabled"}
    if specialist == "writer_agent":
        return tools, {"skipped": True, "reason": "writer_minimal_set"}

    by_meta = manifest_by_name()
    q = _norm_question(strip_tool_search_context_wrappers(question))
    scored: list[tuple[float, BaseTool]] = []
    for t in tools:
        name = getattr(t, "name", "") or ""
        meta = by_meta.get(name)
        if meta is None or meta.specialist not in (None, specialist):
            continue
        s = _score_tool(meta, q, has_workspace=has_workspace, answer_class=answer_class)
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
        for extra in _RETRIEVAL_CORE_CATALOG:
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
