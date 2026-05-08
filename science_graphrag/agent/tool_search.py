"""Rule-based tool shortlist (Wave A — CH3)."""

from __future__ import annotations

import functools
import json
import re
from typing import Any, Sequence

from langchain_core.tools import BaseTool

from science_graphrag.agent.tool_manifest import (
    ToolManifestEntry,
    compact_catalog_lines,
    manifest_by_name,
)
from science_graphrag.agent.tool_search_discovery_carryover import (
    discovered_tool_names_from_lc_messages as _discovered_tool_names_from_lc_messages,
)
from science_graphrag.agent.tool_search_discovery_carryover import (
    shortlist_apply_discovery_and_session_carryover,
)
from science_graphrag.agent.tool_search_discovery_carryover import (
    tool_call_entry_name as _tool_call_entry_name,
)
from science_graphrag.agent.tool_search_strict_deferred import (
    RulesShortlistMetaCtx,
    apply_strict_deferred_activation_filter,
    extend_rules_meta_strict_telemetry,
)
from science_graphrag.agent.tool_selector_hybrid import maybe_llm_rerank_shortlist
from science_graphrag.config import Settings


@functools.lru_cache(maxsize=1)
def _manifest_map() -> dict[str, ToolManifestEntry]:
    """Frozen tool manifest keyed by name (cached for shortlist hot paths)."""
    return manifest_by_name()


def _json_wire_bytes(obj: Any) -> int:
    """UTF-8 byte length of a compact JSON serialization (telemetry / transport sizing)."""
    try:
        return len(
            json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
        )
    except (TypeError, ValueError):
        return 0


def _tool_args_json_schema(tool: BaseTool) -> dict[str, Any] | None:
    """Best-effort Pydantic JSON Schema for a LangChain tool (for deferred transport)."""
    asc = getattr(tool, "args_schema", None)
    if asc is None:
        return None
    try:
        if hasattr(asc, "model_json_schema"):
            return asc.model_json_schema()  # type: ignore[no-any-return]
        schema_fn = getattr(asc, "schema", None)
        if callable(schema_fn):
            legacy = schema_fn()
            if isinstance(legacy, dict):
                return legacy
    except (TypeError, ValueError, AttributeError):
        return None
    return None


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
_LAST_TURN_DIGEST_RE = re.compile(
    r"<last_turn_digest>.*?</last_turn_digest>\s*",
    re.DOTALL | re.IGNORECASE,
)
_THREAD_INSIGHT_RE = re.compile(
    r"<thread_insight\b[^>]*>.*?</thread_insight>\s*",
    re.DOTALL | re.IGNORECASE,
)
_RESEARCH_PLAN_RE = re.compile(
    r"<research_plan>.*?</research_plan>\s*",
    re.DOTALL | re.IGNORECASE,
)
_USER_STRUCTURED_ANSWER_RE = re.compile(
    r"<user_structured_answer>.*?</user_structured_answer>\s*",
    re.DOTALL | re.IGNORECASE,
)

# Low-signal gate: below this top score, use full catalog (Habr Jun 2026 ablation baseline).
_RULE_TOOL_SEARCH_LOW_SIGNAL_FLOOR = 1.5


def strip_tool_search_context_wrappers(text: str) -> str:
    """Strip CH4 memory/digest XML blocks so scoring uses the user's question only."""
    s = text or ""
    s = _SESSION_MEMORY_RE.sub("", s)
    s = _CLIENT_DIGEST_RE.sub("", s)
    s = _ACTIVE_WS_ID_RE.sub("", s)
    s = _LAST_TURN_DIGEST_RE.sub("", s)
    s = _THREAD_INSIGHT_RE.sub("", s)
    s = _RESEARCH_PLAN_RE.sub("", s)
    s = _USER_STRUCTURED_ANSWER_RE.sub("", s)
    return s.strip()


def _norm_question(q: str) -> str:
    return (q or "").strip().lower()


def discovered_tool_names_from_lc_messages(
    messages: Sequence[Any] | None,
    *,
    cap: int,
) -> list[str]:
    """Backward-compatible re-export for tests and external callers."""
    return _discovered_tool_names_from_lc_messages(messages, cap=cap)


_RETRIEVAL_CORE_CATALOG = (
    "workspace_inspect",
    "paper_profile",
    "find_works",
)
_RETRIEVAL_OPTIONAL_BASELINE = ("idea_search", "paper_quote_search")
_RETRIEVAL_CORE_EXEMPT: frozenset[str] = frozenset(_RETRIEVAL_CORE_CATALOG)


def _ensure_final_answer_in_picked(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    names = {getattr(t, "name", "") for t in picked}
    if "final_answer" in names:
        return
    final_tool = next((t for t in tools if getattr(t, "name", "") == "final_answer"), None)
    if final_tool is not None:
        picked.append(final_tool)


def _merge_retrieval_catalog_baseline(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    strict_deferred: bool,
) -> list[str]:
    """Merge retrieval baseline; optional tools may be skipped under strict policy.

    Returns names of strict-deferred optional baseline tools (idea_search, paper_quote_search)
    that were **not** merged because ``strict_deferred`` withheld auto-injection.
    """
    skipped: list[str] = []
    have = {getattr(t, "name", "") for t in picked}
    for extra in _RETRIEVAL_OPTIONAL_BASELINE + _RETRIEVAL_CORE_CATALOG:
        if extra in have:
            continue
        if strict_deferred and extra in _RETRIEVAL_OPTIONAL_BASELINE:
            skipped.append(extra)
            continue
        hit = next((t for t in tools if getattr(t, "name", "") == extra), None)
        if hit is not None:
            picked.append(hit)
            have.add(extra)
    return skipped


def _sort_picked_like_registry_order(picked: list[BaseTool], tools: list[BaseTool]) -> None:
    index_by_name = {getattr(t, "name", ""): i for i, t in enumerate(tools)}
    picked.sort(key=lambda t: index_by_name.get(getattr(t, "name", ""), 10**9))


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


def _shortlist_build_rules_meta(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    ctx: RulesShortlistMetaCtx,
    selector_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble ``tool_search_result`` metadata for the rules path."""
    _sort_picked_like_registry_order(picked, tools)
    names = [getattr(t, "name", "") for t in picked]
    reason = (
        "hybrid_llm" if (selector_extra or {}).get("selector_stage") == "hybrid_llm" else "rules"
    )
    meta_out: dict[str, Any] = {
        "reason": reason,
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
        by_meta = _manifest_map()
        discovery = set(ctx.message_discovery_merged) | set(ctx.carryover_merged)
        name_to_tool = {getattr(t, "name", ""): t for t in picked if getattr(t, "name", "")}
        refs: list[dict[str, Any]] = []
        full_rows: list[dict[str, Any]] = []
        hypothetical_wire = 0
        actual_wire = 0
        do_full = bool(
            getattr(
                ctx.settings, "agent_tool_search_deferred_schema_full_on_discovery_enabled", True
            )
        )
        max_schema = int(
            getattr(
                ctx.settings, "agent_tool_search_deferred_schema_full_max_bytes_per_tool", 24_000
            )
        )
        for name in names:
            meta_ent = by_meta.get(name)
            if meta_ent is None or not meta_ent.strict_deferred_requires_discovery:
                continue
            ref_entry = {"tool": name, "schema_ref": meta_ent.deferred_schema_ref}
            refs.append(ref_entry)
            tool_obj = name_to_tool.get(name)
            schema_dict = _tool_args_json_schema(tool_obj) if tool_obj is not None else None
            raw_full = _json_wire_bytes(schema_dict) if isinstance(schema_dict, dict) else 0
            hypothetical_wire += raw_full if raw_full else _json_wire_bytes(ref_entry)
            if (
                name in discovery
                and do_full
                and isinstance(schema_dict, dict)
                and 0 < raw_full <= max_schema
            ):
                full_rows.append({"tool": name, "json_schema": schema_dict})
                actual_wire += _json_wire_bytes({"tool": name, "json_schema": schema_dict})
            else:
                actual_wire += _json_wire_bytes(ref_entry)
        if refs:
            meta_out["deferred_schema_refs"] = refs
            meta_out["deferred_schema_mode"] = (
                "compact_default_full_on_discovery"
                if full_rows
                else "compact_only_deferred_shortlist"
            )
            if full_rows:
                meta_out["deferred_schema_full_tools"] = full_rows
            saved = max(0, int(hypothetical_wire - actual_wire))
            meta_out["tool_schema_bytes_saved"] = saved
    if ctx.carryover_merged:
        meta_out["carryover_tools"] = ctx.carryover_merged
    elif ctx.carryover_names:
        meta_out["carryover_tools"] = []
    if ctx.message_discovery_tools:
        meta_out["message_discovery_tools"] = list(ctx.message_discovery_tools)
    if ctx.message_discovery_merged:
        meta_out["message_discovery_merged"] = list(ctx.message_discovery_merged)
    if ctx.rules_matched_tools:
        meta_out["rules_matched_tools"] = list(ctx.rules_matched_tools)
    if ctx.skipped_optional_baseline:
        meta_out["deferred_strict_skipped_optional_baseline"] = list(ctx.skipped_optional_baseline)
    if ctx.strict_removed_tools:
        meta_out["deferred_strict_removed_from_picked"] = list(ctx.strict_removed_tools)
    extend_rules_meta_strict_telemetry(meta_out, ctx, names)
    if selector_extra:
        for k, v in selector_extra.items():
            if v is None:
                continue
            meta_out[k] = v
    return meta_out


def _build_scored_tools_for_shortlist(
    tools: list[BaseTool],
    *,
    specialist: str,
    for_single_agent: bool,
    q: str,
    has_workspace: bool,
    answer_class: str | None,
) -> list[tuple[float, BaseTool]]:
    by_meta = _manifest_map()
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


# Scoring helpers live in ``tool_search_scoring.py`` (Phase 7.3 split). The
# legacy ``_score_tool*`` private names remain available below as re-exports
# for any external callers; new code should import from the scoring module
# directly.
from science_graphrag.agent.tool_search_scoring import (
    answer_class_tool_boost as _answer_class_tool_boost,
)
from science_graphrag.agent.tool_search_scoring import score_tool as _score_tool
from science_graphrag.agent.tool_search_scoring import (
    score_tool_name_family_patterns as _score_tool_name_family_patterns,
)
from science_graphrag.agent.tool_search_scoring import (
    score_tool_tags_and_catalog_families as _score_tool_tags_and_catalog_families,
)


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
        return tools, {
            "reason": "fallback_full",
            "matched": [],
            "catalog_size": len(tools),
            "activation_policy": "relaxed_fallback_full",
        }

    top_score = scored[0][0]
    if top_score < _RULE_TOOL_SEARCH_LOW_SIGNAL_FLOOR:
        return tools, {
            "reason": "low_signal",
            "top_score": top_score,
            "catalog_size": len(tools),
            "activation_policy": "relaxed_low_signal",
        }

    score_band = float(settings.agent_tool_search_score_band)
    threshold = max(0.0, top_score - score_band)
    picked = [t for s, t in scored if s >= threshold and s > 0]
    rules_matched_tools = [getattr(t, "name", "") for t in picked]
    rules_names = {n for n in rules_matched_tools if n}
    strict_on = bool(
        getattr(settings, "agent_tool_search_strict_deferred_activation_enabled", False)
    )
    activation_policy = "strict_only_on_discovery" if strict_on else "default"
    skipped_optional_baseline: list[str] = []
    strict_removed_tools: list[str] = []
    (
        message_discovery_tools,
        message_discovery_merged,
        carryover_names,
        carryover_merged,
    ) = shortlist_apply_discovery_and_session_carryover(
        picked,
        tools,
        lc_messages=lc_messages,
        session=session,
        settings=settings,
    )
    if for_single_agent:
        _ensure_final_answer_in_picked(picked, tools)
    if specialist == "retrieval_agent" or for_single_agent:
        skipped_optional_baseline = _merge_retrieval_catalog_baseline(
            picked,
            tools,
            strict_deferred=strict_on,
        )
    core_exempt = (
        _RETRIEVAL_CORE_EXEMPT
        if (specialist == "retrieval_agent" or for_single_agent)
        else frozenset()
    )
    if strict_on:
        picked, strict_removed_tools = apply_strict_deferred_activation_filter(
            picked,
            rules_names=rules_names,
            message_merged=set(message_discovery_merged),
            carry_merged=set(carryover_merged),
            retrieval_core_exempt=core_exempt,
        )
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
            "activation_policy": "relaxed_fallback_full",
        }

    selector_extra: dict[str, Any] | None = None
    picked, selector_extra = maybe_llm_rerank_shortlist(
        picked,
        question=question,
        specialist=specialist,
        settings=settings,
        rules_matched_tools=rules_matched_tools,
        message_discovery_merged=message_discovery_merged,
        carryover_merged=carryover_merged,
    )

    meta_out = _shortlist_build_rules_meta(
        picked,
        tools,
        ctx=RulesShortlistMetaCtx(
            settings=settings,
            top_score=top_score,
            score_band=score_band,
            specialist=specialist,
            for_single_agent=for_single_agent,
            carryover_merged=carryover_merged,
            carryover_names=carryover_names,
            message_discovery_tools=message_discovery_tools,
            message_discovery_merged=message_discovery_merged,
            rules_matched_tools=rules_matched_tools,
            skipped_optional_baseline=skipped_optional_baseline,
            strict_removed_tools=strict_removed_tools,
            activation_policy=activation_policy,
        ),
        selector_extra=selector_extra,
    )
    return picked, meta_out


def build_tool_search_result_debug_event(
    *,
    specialist: str,
    meta: dict[str, Any],
    writer_mode: str | None = None,
) -> dict[str, Any]:
    """Canonical ``tool_search_result`` debug payload for SSE / run_metadata aggregation."""
    ev: dict[str, Any] = {
        "type": "tool_search_result",
        "specialist": specialist,
        "tools": meta.get("matched"),
        "reason": meta.get("reason"),
        "top_score": meta.get("top_score"),
        "score_band": meta.get("score_band"),
        "catalog_size": meta.get("catalog_size"),
        "shortlist_size": meta.get("shortlist_size"),
        "shortlist_ratio": meta.get("shortlist_ratio"),
        "deferred_schema_mode": meta.get("deferred_schema_mode"),
        "deferred_schema_refs": meta.get("deferred_schema_refs"),
        "skipped": bool(meta.get("skipped")),
        "carryover_tools": meta.get("carryover_tools"),
        "message_discovery_tools": meta.get("message_discovery_tools"),
        "message_discovery_merged": meta.get("message_discovery_merged"),
    }
    if writer_mode is not None:
        ev["writer_mode"] = writer_mode
    optional_keys = (
        "activation_policy",
        "rules_matched_tools",
        "deferred_strict_skipped_optional_baseline",
        "deferred_strict_removed_from_picked",
        "deferred_strict_candidates",
        "deferred_strict_in_shortlist_count",
        "deferred_activated_via_message_or_carryover_count",
        "tool_search_miss_due_to_no_discovery",
        "deferred_tool_activation_rate",
        "selector_stage",
        "selector_confidence",
        "selector_reason_codes",
        "rules_candidate_tools",
        "llm_ranked_tools",
        "pre_llm_denied_tools",
        "deferred_schema_full_tools",
        "tool_schema_bytes_saved",
    )
    for k in optional_keys:
        if k not in meta:
            continue
        val = meta[k]
        if val is None:
            continue
        ev[k] = val
    return ev


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
