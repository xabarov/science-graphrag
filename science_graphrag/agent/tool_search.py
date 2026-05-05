"""Rule-based tool shortlist (Wave A — CH3)."""

from __future__ import annotations

import re
from typing import Any

from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import ToolManifestEntry, compact_catalog_lines, manifest_by_name
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

# Low-signal gate: below this top score, use full tool catalog (unchanged across Habr Jun 2026 ablation).
_RULE_TOOL_SEARCH_LOW_SIGNAL_FLOOR = 1.5


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
    "workspace_inspect",
    "paper_profile",
    "find_works",
)


def _ensure_final_answer_in_picked(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    names = {getattr(t, "name", "") for t in picked}
    if "final_answer" in names:
        return
    final_tool = next((t for t in tools if getattr(t, "name", "") == "final_answer"), None)
    if final_tool is not None:
        picked.append(final_tool)


def _merge_retrieval_catalog_baseline(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    have = {getattr(t, "name", "") for t in picked}
    for extra in ("idea_search", "paper_quote_search") + _RETRIEVAL_CORE_CATALOG:
        if extra not in have:
            hit = next((t for t in tools if getattr(t, "name", "") == extra), None)
            if hit is not None:
                picked.append(hit)
                have.add(extra)


def _sort_picked_like_registry_order(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    index_by_name = {getattr(t, "name", ""): i for i, t in enumerate(tools)}
    picked.sort(key=lambda t: index_by_name.get(getattr(t, "name", ""), 10**9))


def _build_scored_tools_for_shortlist(
    tools: list[BaseTool],
    *,
    specialist: str,
    for_single_agent: bool,
    q: str,
    has_workspace: bool,
    answer_class: str | None,
) -> list[tuple[float, BaseTool]]:
    by_meta = manifest_by_name()
    scored: list[tuple[float, BaseTool]] = []
    for t in tools:
        name = getattr(t, "name", "") or ""
        meta = by_meta.get(name)
        if meta is None:
            continue
        if not for_single_agent and meta.specialist not in (None, specialist):
            continue
        s = _score_tool(meta, q, has_workspace=has_workspace, answer_class=answer_class)
        if s < 0:
            continue
        scored.append((s, t))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored


def _answer_class_tool_boost(meta: ToolManifestEntry, answer_class: str | None) -> float:
    """Bias shortlist toward tools that match coordinator / envelope answer class."""
    if not answer_class:
        return 0.0
    ac = answer_class
    name = meta.name
    boost = 0.0
    if ac == "fact_lookup" and name in ("paper_profile", "find_works"):
        boost += 3.5
    if ac == "bibliography_export" and name == "format_bibliography_gost":
        boost += 5.0
    if ac == "quote_extraction" and name == "paper_quote_search":
        boost += 5.0
    if ac == "relation_tracing" and meta.family == "graph":
        boost += 3.5
    if ac == "inventory" and name == "workspace_inspect":
        boost += 3.5
    if ac == "ideation" and name in ("idea_search", "workspace_inspect"):
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
    _wi_hints = (
        "сколько",
        "how many",
        "count",
        "список",
        "област",
        "стат",
        "корпус",
        "работ",
        "summar",
    )
    if meta.name == "workspace_inspect" and any(x in q for x in _wi_hints):
        score += 4.0
    if meta.name == "paper_quote_search":
        if any(x in q for x in ("quote", "цитат", "passage", "snippet", "where")):
            score += 4.0
        if any(x in q for x in ("trade-off", "tradeoff", "trade-offs")):
            score += 3.5
        if "evidence" in q:
            score += 2.5
        if "verbatim" in q:
            score += 2.5
    if meta.name == "idea_search" and any(
        x in q for x in ("idea", "similar", "related", "semantic", "chunk")
    ):
        score += 3.0
    if meta.name == "find_works" and any(
        x in q for x in ("find", "search", "title", "which paper", "кто написал")
    ):
        score += 2.0
    if meta.family == "graph" and any(
        x in q for x in ("cites", "cypher", "graph", "path", "relation", "edge")
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
    for_single_agent: bool = False,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Return possibly narrowed tool list and debug meta for SSE / run_metadata."""
    if not settings.agent_rule_tool_search_enabled:
        return tools, {"skipped": True, "reason": "disabled", "catalog_size": len(tools)}
    if specialist == "writer_agent":
        return tools, {"skipped": True, "reason": "writer_minimal_set", "catalog_size": len(tools)}

    q = _norm_question(strip_tool_search_context_wrappers(question))
    scored = _build_scored_tools_for_shortlist(
        tools,
        specialist=specialist,
        for_single_agent=for_single_agent,
        q=q,
        has_workspace=has_workspace,
        answer_class=answer_class,
    )
    if not scored:
        return tools, {"reason": "fallback_full", "matched": [], "catalog_size": len(tools)}

    top_score = scored[0][0]
    if top_score < _RULE_TOOL_SEARCH_LOW_SIGNAL_FLOOR:
        return tools, {"reason": "low_signal", "top_score": top_score, "catalog_size": len(tools)}

    score_band = float(settings.agent_tool_search_score_band)
    threshold = max(0.0, top_score - score_band)
    picked = [t for s, t in scored if s >= threshold and s > 0]
    if for_single_agent:
        _ensure_final_answer_in_picked(picked, tools)
    if specialist == "retrieval_agent" or for_single_agent:
        _merge_retrieval_catalog_baseline(picked, tools)
    # Retrieval catalog is large — avoid over-narrow shortlists
    # Keep shortlists only when they still cover a reasonable slice of the catalog.
    if specialist == "retrieval_agent" and len(picked) < 3:
        return tools, {
            "reason": "fallback_full",
            "matched": [getattr(x, "name", "") for x in picked],
            "catalog_size": len(tools),
        }
    if for_single_agent and len(picked) < 5:
        return tools, {
            "reason": "fallback_full_single_agent",
            "matched": [getattr(x, "name", "") for x in picked],
            "catalog_size": len(tools),
        }
    if specialist == "graph_agent" and len(picked) < 2:
        return tools, {
            "reason": "fallback_full",
            "matched": [getattr(x, "name", "") for x in picked],
            "catalog_size": len(tools),
        }

    _sort_picked_like_registry_order(picked, tools)
    names = [getattr(t, "name", "") for t in picked]
    meta_out: dict[str, Any] = {
        "reason": "rules",
        "matched": names,
        "top_score": top_score,
        "score_band": score_band,
    }
    if for_single_agent:
        meta_out["single_agent"] = True
    meta_out["catalog_size"] = len(tools)
    meta_out["shortlist_size"] = len(names)
    meta_out["shortlist_ratio"] = round((len(names) / len(tools)), 4) if tools else 1.0
    meta_out["catalog_preview"] = compact_catalog_lines(specialist=None if for_single_agent else specialist)[
        :8
    ]
    if settings.agent_tool_search_deferred_schema_refs_enabled:
        by_meta = manifest_by_name()
        refs = []
        for name in names:
            meta = by_meta.get(name)
            if meta is None:
                continue
            refs.append({"tool": name, "schema_ref": meta.deferred_schema_ref})
        meta_out["deferred_schema_refs"] = refs
        meta_out["deferred_schema_mode"] = "shortlist_only"
    return picked, meta_out


def shortlist_tools_for_single_agent(
    tools: list[BaseTool],
    *,
    question: str,
    settings: Settings,
    has_workspace: bool,
    answer_class: str | None = None,
) -> tuple[list[BaseTool], dict[str, Any]]:
    """Rule-based shortlist for single-agent ReAct (full registry in one bind_tools surface)."""

    return shortlist_tools_for_specialist(
        tools,
        question=question,
        specialist="retrieval_agent",
        settings=settings,
        has_workspace=has_workspace,
        answer_class=answer_class,
        for_single_agent=True,
    )
