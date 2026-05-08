"""Scoring helpers for ``tool_search`` shortlist (Phase 7.3 split).

Pure functions only — no side effects, no I/O. Operates on
:class:`ToolManifestEntry` and the normalized question string. The host
module (``tool_search.py``) provides the orchestration and merges the score
output with discovery / carryover / strict-deferred policy.
"""

from __future__ import annotations

from science_graphrag.agent.tool_manifest import ToolManifestEntry


def score_tool_tags_and_catalog_families(meta: ToolManifestEntry, q: str) -> float:
    """Bibliography / catalog / tag hints (shared rule table fragment)."""
    score = 0.0
    if meta.name == "format_bibliography_gost" and any(
        x in q for x in ("gost", "гост", "bibliograph", "литератур", "references")
    ):
        score += 6.0
    for tag in meta.tags:
        if tag and tag in q:
            score += 2.0
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
    return score


def score_tool_name_family_patterns(meta: ToolManifestEntry, q: str) -> float:
    """Per-tool-name and graph-family heuristics."""
    score = 0.0
    wi_hints = (
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
    if meta.name == "workspace_inspect" and any(x in q for x in wi_hints):
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
    return score


def answer_class_tool_boost(meta: ToolManifestEntry, answer_class: str | None) -> float:
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


def score_tool(
    meta: ToolManifestEntry,
    q: str,
    *,
    has_workspace: bool,
    answer_class: str | None = None,
) -> float:
    """Aggregate base score for one tool against the normalized question."""
    if meta.requires_workspace and not has_workspace:
        return -1.0
    score = score_tool_tags_and_catalog_families(meta, q)
    score += score_tool_name_family_patterns(meta, q)
    score += answer_class_tool_boost(meta, answer_class)
    return score


__all__ = [
    "answer_class_tool_boost",
    "score_tool",
    "score_tool_name_family_patterns",
    "score_tool_tags_and_catalog_families",
]
