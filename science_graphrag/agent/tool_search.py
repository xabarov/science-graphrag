"""Rule-based tool shortlist (Wave A — CH3)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import (
    ToolManifestEntry,
    compact_catalog_lines,
    manifest_by_name,
)
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

# Low-signal gate: below this top score, use full catalog (Habr Jun 2026 ablation baseline).
_RULE_TOOL_SEARCH_LOW_SIGNAL_FLOOR = 1.5

# Meta / routing tools: never treat as catalog discoveries from message history (Epic C0).
_MESSAGE_DISCOVERY_EXCLUDE = frozenset(
    {
        "route_to_specialist",
        "session_init",
        "coordinator_gate",
        "coordinator_gate_v0",
    }
)


def _tool_call_entry_name(tc: Any) -> str:
    """Resolve tool name from ``AIMessage.tool_calls`` entry (dict or LangChain object)."""
    if isinstance(tc, dict):
        return str(tc.get("name") or "").strip()
    return str(getattr(tc, "name", "") or "").strip()


def discovered_tool_names_from_lc_messages(
    messages: Sequence[Any] | None,
    *,
    cap: int,
) -> list[str]:
    """Collect tool names from LangGraph history in message order (deduped, capped).

    Reads ``AIMessage.tool_calls`` and ``ToolMessage.name``. Deterministic: first
    occurrence wins; caps at ``cap`` names.
    """
    if not messages or cap <= 0:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in getattr(msg, "tool_calls", None) or []:
                name = _tool_call_entry_name(tc)
                if not name or name in _MESSAGE_DISCOVERY_EXCLUDE:
                    continue
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
                if len(ordered) >= cap:
                    return ordered
        elif isinstance(msg, ToolMessage):
            name = str(getattr(msg, "name", "") or "").strip()
            if not name or name in _MESSAGE_DISCOVERY_EXCLUDE:
                continue
            if name not in seen:
                seen.add(name)
                ordered.append(name)
            if len(ordered) >= cap:
                return ordered
    return ordered


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


def _carryover_tool_names_from_session(session: dict[str, Any] | None, *, cap: int) -> list[str]:
    if not isinstance(session, dict):
        return []
    caps = session.get("capsules") or {}
    if not isinstance(caps, dict):
        return []
    dt = caps.get("discovered_tools")
    if not isinstance(dt, dict):
        return []
    raw = [str(x).strip() for x in (dt.get("recent_tools") or []) if str(x).strip()]
    cap_n = max(0, int(cap))
    if cap_n <= 0:
        return []
    return raw[-cap_n:]


def _merge_carryover_into_picked(
    picked: list[BaseTool],
    tools: list[BaseTool],
    carryover: list[str],
) -> list[str]:
    """Return list of carryover tool names that were merged into ``picked``."""
    if not carryover:
        return []
    have = {getattr(t, "name", "") for t in picked}
    merged: list[str] = []
    by_name = {getattr(t, "name", ""): t for t in tools}
    for nm in carryover:
        if nm in have:
            continue
        hit = by_name.get(nm)
        if hit is None:
            continue
        picked.append(hit)
        have.add(nm)
        merged.append(nm)
    return merged


def _sort_picked_like_registry_order(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    index_by_name = {getattr(t, "name", ""): i for i, t in enumerate(tools)}
    picked.sort(key=lambda t: index_by_name.get(getattr(t, "name", ""), 10**9))


def _shortlist_try_message_discovery_merge(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    lc_messages: Sequence[Any] | None,
    settings: Settings,
) -> tuple[list[str], list[str]]:
    """Merge tools discovered in LangGraph history into ``picked`` (Epic C0)."""
    if (
        lc_messages is None
        or not settings.agent_tool_search_message_discovery_enabled
        or int(settings.agent_tool_search_message_discovery_cap) <= 0
    ):
        return [], []
    names = discovered_tool_names_from_lc_messages(
        lc_messages,
        cap=int(settings.agent_tool_search_message_discovery_cap),
    )
    if not names:
        return [], []
    merged = _merge_carryover_into_picked(picked, tools, names)
    return names, merged


def _shortlist_needs_full_catalog_fallback(
    picked: list[BaseTool],
    *,
    specialist: str,
    for_single_agent: bool,
) -> tuple[bool, str]:
    """Return (use_full_catalog, reason_code) when shortlist is too narrow."""
    if specialist == "retrieval_agent" and len(picked) < 3:
        return True, "fallback_full"
    if for_single_agent and len(picked) < 5:
        return True, "fallback_full_single_agent"
    if specialist == "graph_agent" and len(picked) < 2:
        return True, "fallback_full"
    return False, ""


@dataclass(frozen=True, slots=True)
class _RulesShortlistMetaCtx:
    """Bundled knobs for ``tool_search_result`` metadata (rules path)."""

    settings: Settings
    top_score: float
    score_band: float
    specialist: str
    for_single_agent: bool
    carryover_merged: list[str]
    carryover_names: list[str]
    message_discovery_tools: list[str]
    message_discovery_merged: list[str]


def _shortlist_build_rules_meta(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    ctx: _RulesShortlistMetaCtx,
) -> dict[str, Any]:
    """Assemble ``tool_search_result`` metadata for the rules path."""
    _sort_picked_like_registry_order(picked, tools)
    names = [getattr(t, "name", "") for t in picked]
    meta_out: dict[str, Any] = {
        "reason": "rules",
        "matched": names,
        "top_score": ctx.top_score,
        "score_band": ctx.score_band,
    }
    if ctx.for_single_agent:
        meta_out["single_agent"] = True
    meta_out["catalog_size"] = len(tools)
    meta_out["shortlist_size"] = len(names)
    meta_out["shortlist_ratio"] = round((len(names) / len(tools)), 4) if tools else 1.0
    specialist_arg = None if ctx.for_single_agent else ctx.specialist
    meta_out["catalog_preview"] = compact_catalog_lines(specialist=specialist_arg)[:8]
    if ctx.settings.agent_tool_search_deferred_schema_refs_enabled:
        by_meta = manifest_by_name()
        refs: list[dict[str, Any]] = []
        for name in names:
            meta = by_meta.get(name)
            if meta is None:
                continue
            refs.append({"tool": name, "schema_ref": meta.deferred_schema_ref})
        meta_out["deferred_schema_refs"] = refs
        meta_out["deferred_schema_mode"] = "shortlist_only"
    if ctx.carryover_merged:
        meta_out["carryover_tools"] = ctx.carryover_merged
    elif ctx.carryover_names:
        meta_out["carryover_tools"] = []
    if ctx.message_discovery_tools:
        meta_out["message_discovery_tools"] = list(ctx.message_discovery_tools)
    if ctx.message_discovery_merged:
        meta_out["message_discovery_merged"] = list(ctx.message_discovery_merged)
    return meta_out


def _shortlist_apply_discovery_and_session_carryover(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    lc_messages: Sequence[Any] | None,
    session: dict[str, Any] | None,
    settings: Settings,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Message-history merge then session carry-over; returns discovery + carryover lists."""
    msg_tools, msg_merged = _shortlist_try_message_discovery_merge(
        picked,
        tools,
        lc_messages=lc_messages,
        settings=settings,
    )
    carryover_names = _carryover_tool_names_from_session(
        session,
        cap=int(settings.agent_discovered_tools_carryover_max),
    )
    carry_merged: list[str] = []
    if settings.agent_discovered_tools_carryover_enabled and carryover_names:
        carry_merged = _merge_carryover_into_picked(picked, tools, carryover_names)
    return msg_tools, msg_merged, carryover_names, carry_merged


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


def _score_tool_tags_and_catalog_families(meta: ToolManifestEntry, q: str) -> float:
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


def _score_tool_name_family_patterns(meta: ToolManifestEntry, q: str) -> float:
    """Per-tool-name and graph-family heuristics."""
    score = 0.0
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
    return score


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
    score = _score_tool_tags_and_catalog_families(meta, q)
    score += _score_tool_name_family_patterns(meta, q)
    score += _answer_class_tool_boost(meta, answer_class)
    return score


def shortlist_tools_for_specialist(  # pylint: disable=too-many-arguments,too-many-locals
    tools: list[BaseTool],
    *,
    question: str,
    specialist: str,
    settings: Settings,
    has_workspace: bool,
    answer_class: str | None = None,
    for_single_agent: bool = False,
    session: dict[str, Any] | None = None,
    lc_messages: Sequence[Any] | None = None,
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
    (
        message_discovery_tools,
        message_discovery_merged,
        carryover_names,
        carryover_merged,
    ) = _shortlist_apply_discovery_and_session_carryover(
        picked,
        tools,
        lc_messages=lc_messages,
        session=session,
        settings=settings,
    )
    if for_single_agent:
        _ensure_final_answer_in_picked(picked, tools)
    if specialist == "retrieval_agent" or for_single_agent:
        _merge_retrieval_catalog_baseline(picked, tools)
    # Retrieval catalog is large — avoid over-narrow shortlists
    # Keep shortlists only when they still cover a reasonable slice of the catalog.
    need_full, fb_reason = _shortlist_needs_full_catalog_fallback(
        picked,
        specialist=specialist,
        for_single_agent=for_single_agent,
    )
    if need_full:
        return tools, {
            "reason": fb_reason,
            "matched": [getattr(x, "name", "") for x in picked],
            "catalog_size": len(tools),
        }

    meta_out = _shortlist_build_rules_meta(
        picked,
        tools,
        ctx=_RulesShortlistMetaCtx(
            settings=settings,
            top_score=top_score,
            score_band=score_band,
            specialist=specialist,
            for_single_agent=for_single_agent,
            carryover_merged=carryover_merged,
            carryover_names=carryover_names,
            message_discovery_tools=message_discovery_tools,
            message_discovery_merged=message_discovery_merged,
        ),
    )
    return picked, meta_out


def shortlist_tools_for_single_agent(
    tools: list[BaseTool],
    *,
    question: str,
    settings: Settings,
    has_workspace: bool,
    answer_class: str | None = None,
    session: dict[str, Any] | None = None,
    lc_messages: Sequence[Any] | None = None,
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
        session=session,
        lc_messages=lc_messages,
    )
