"""Payload models and response builders for Agent API v2."""

from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.debug_events_telemetry import (
    extract_runtime_telemetry_from_debug_events,
)
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.runtime import current_otel_trace_id_hex
from science_graphrag.config import Settings
from science_graphrag.llm.openrouter_model_registry import (
    openrouter_reference_pricing_run_metadata,
)


def thread_insight_audit_fragment(
    *,
    thread_id: str | None,
    settings: Settings,
) -> dict[str, Any] | None:
    """Return thread insight audit (+ optional control plane) for run_metadata."""
    tid = (thread_id or "").strip()
    if not tid or not getattr(settings, "agent_thread_insights_enabled", False):
        return None

    ent = get_session_for_thread(tid)
    sm = ent.get("session_meta") or {}
    if not isinstance(sm, dict):
        return None
    out: dict[str, Any] = {}
    tip = sm.get("thread_insight")
    if isinstance(tip, dict):
        aud = tip.get("audit")
        if isinstance(aud, dict):
            out["thread_insight_audit"] = aud
    ctrl = sm.get("thread_insight_control")
    if isinstance(ctrl, dict):
        out["thread_insight_control"] = ctrl
    return out if out else None


def agent_chat_llm_run_metadata(settings: Settings) -> dict[str, Any]:
    """LLM fields attached to agent run_metadata (extraction vs chat model split)."""
    meta = {
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
        "chat_llm_model": settings.chat_llm_model,
        "resolved_chat_llm_model": effective_chat_llm_model(settings),
    }
    meta.update(
        openrouter_reference_pricing_run_metadata(
            base_url=settings.extraction_llm_base_url,
            chat_model_id=str(meta.get("resolved_chat_llm_model") or ""),
            extraction_model_id=settings.extraction_llm_model,
        )
    )
    return meta


def build_run_metadata(
    *,
    settings: Settings,
    max_tool_calls: int,
    run_kind: str | None = None,
    graph_id: str | None = None,
    thread_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build canonical agent run_metadata envelope used by sync and SSE."""
    meta: dict[str, Any] = {
        "agent_runtime": settings.agent_runtime,
        "agent_max_tool_calls": max_tool_calls,
        **agent_chat_llm_run_metadata(settings),
    }
    if run_kind:
        meta["run_kind"] = run_kind
    if graph_id:
        meta["graph_id"] = graph_id
    if thread_id:
        meta["thread_id"] = thread_id
    if extra:
        meta.update(extra)
    return meta


def _hook_chain_event_fingerprint(ev: dict[str, Any]) -> tuple[str, str, str, bool, str]:
    detail = ev.get("detail")
    if isinstance(detail, dict):
        detail_repr = json.dumps(detail, sort_keys=True, default=str)
    else:
        detail_repr = str(detail)
    return (
        str(ev.get("type") or ""),
        str(ev.get("hook") or ""),
        str(ev.get("phase") or ""),
        bool(ev.get("ok")),
        detail_repr,
    )


def merge_hook_chain_events_into_run_metadata(
    run_metadata: dict[str, Any],
    *,
    extra_events: list[dict[str, Any]] | None = None,
    debug_events_tail: list[dict[str, Any]] | None = None,
) -> None:
    """Attach explainable hook chain rows (Train T3 §10.6) for trace-review + clients.

    Preserves any ``hook_chain_events`` already merged into ``run_metadata`` (e.g. from
    ``extra`` in ``build_run_metadata``), then appends ``extra_events`` and ``debug_events_tail``,
    deduplicating by a stable fingerprint.
    """
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, bool, str]] = set()

    def _add(ev: dict[str, Any]) -> None:
        if str(ev.get("type") or "") != "hook_chain_event":
            return
        fp = _hook_chain_event_fingerprint(ev)
        if fp in seen:
            return
        seen.add(fp)
        merged.append(dict(ev))

    existing = run_metadata.get("hook_chain_events")
    if isinstance(existing, list):
        for ev in existing:
            if isinstance(ev, dict):
                _add(ev)
    for ev in list(extra_events or []):
        if isinstance(ev, dict):
            _add(ev)
    for ev in list(debug_events_tail or []):
        if isinstance(ev, dict):
            _add(ev)
    if merged:
        run_metadata["hook_chain_events"] = merged


def apply_runtime_metadata_from_state(
    *,
    run_metadata: dict[str, Any],
    state: dict[str, Any] | None,
) -> dict[str, Any]:
    """Patch run metadata with canonical runtime attribution from graph state."""
    if not isinstance(state, dict):
        return run_metadata
    raw_meta = state.get("metadata") or {}
    if not isinstance(raw_meta, dict):
        return run_metadata
    state_run_kind = str(raw_meta.get("run_kind") or "").strip()
    state_graph_id = str(raw_meta.get("graph_id") or "").strip()
    if state_run_kind:
        run_metadata["run_kind"] = state_run_kind
    if state_graph_id:
        run_metadata["graph_id"] = state_graph_id
    react_total_hops = raw_meta.get("react_total_hops")
    if isinstance(react_total_hops, int):
        run_metadata["react_total_hops"] = react_total_hops
    react_force_finalize = raw_meta.get("react_force_finalize")
    if isinstance(react_force_finalize, str) and react_force_finalize:
        run_metadata["react_force_finalize"] = react_force_finalize
    parent_turn_id = raw_meta.get("parent_turn_id")
    if isinstance(parent_turn_id, str) and parent_turn_id.strip():
        run_metadata["parent_turn_id"] = parent_turn_id.strip()
    max_par = raw_meta.get("max_parallel_subagents")
    if isinstance(max_par, int) and max_par >= 1:
        run_metadata["max_parallel_subagents"] = max_par
    rpc = raw_meta.get("post_compact_paper_sources_restored_count")
    if isinstance(rpc, int) and rpc >= 0:
        run_metadata["post_compact_paper_sources_restored_count"] = int(rpc)
    return run_metadata


def normalize_history_digest_input(raw: object) -> tuple[list[dict[str, Any]], bool]:
    """Parse client history digest; return (normalized_turn_dicts, invalid)."""
    if raw is None:
        return [], False
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)], False
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return [], False
        try:
            parsed = json.loads(s)
        except Exception:  # noqa: BLE001
            return [], True
        if isinstance(parsed, list):
            return [x for x in parsed if isinstance(x, dict)], False
        return [], True
    return [], False


def looks_like_deferred_topic(question: str) -> bool:
    """User is setting up the task but says the actual topic will come later."""
    q = " ".join(str(question or "").lower().split())
    if not q:
        return False
    return any(
        marker in q
        for marker in (
            "следующим сообщением",
            "следующем сообщении",
            "следующем запросе",
            "следующим запросом",
            "позже сформулирую",
            "сформулирую позже",
            "next message",
            "next prompt",
        )
    )


def _has_cyrillic(text: str) -> bool:
    return any("а" <= ch.lower() <= "я" or ch.lower() == "ё" for ch in str(text or ""))


def deferred_topic_answer(question: str) -> str:
    """Localized deferred-topic clarification answer."""
    if _has_cyrillic(question):
        return (
            "Хорошо. Пришлите тему следующим сообщением, и я сравню статьи в рабочей области "
            "по этой теме: выделю совпадения, противоречия и укажу, какие статьи их поддерживают."
        )
    return (
        "Sure. Send the topic in your next message, and I will compare the workspace papers "
        "around it: agreements, contradictions, and which papers support each point."
    )


class AgentQueryRequestV2(BaseModel):
    question: str = Field(..., min_length=1)
    workspace_id: str | None = None
    max_tool_calls: int | None = Field(default=None, ge=1, le=30)
    thread_id: str | None = Field(
        default=None,
        max_length=256,
        description="CH4: stable id for server-side session memory.",
    )
    history_digest: str | list[dict[str, Any]] | None = Field(
        default=None,
        description="CH4: JSON string or list of compact turn dicts from the client.",
    )
    answer_class_hint: str | None = Field(
        default=None,
        description="Optional hint for answer_class / UI (does not force tool routing).",
    )
    client_idle_ms: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional client-reported milliseconds since last user activity in this UI session. "
            "Used for deterministic away-recap framing (CH4/CH5)."
        ),
    )
    user_structured_answer: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Structured answers to a prior ``ask_user_question`` turn "
            "(``request_id`` + ``answers``); requires matching ``thread_id``."
        ),
    )
    agent_mode: Literal["agent", "plan"] = Field(
        default="agent",
        description='UI mode: "plan" enables read-focused plan_mode for this turn (high-risk tools blocked).',
    )
    web_research_enabled: bool | None = Field(
        default=None,
        description=(
            "When false, deny external HTTP research tools for this turn "
            "(``web_search`` / ``web_fetch`` / ``arxiv_search`` / ``arxiv_fetch`` / "
            "``unpaywall_lookup``). "
            "When true or null/omitted, keep web research tools enabled."
        ),
    )
    pdf_read_request: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional explicit PDF-read action from UI. "
            "Current schema: ``{pdf_url: https://...}``."
        ),
    )

    @field_validator("thread_id", mode="before")
    @classmethod
    def _normalize_thread_id(cls, v: object) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    @field_validator("history_digest", mode="before")
    @classmethod
    def _coerce_history_digest(cls, v: object) -> object:
        return v

    @field_validator("user_structured_answer", mode="before")
    @classmethod
    def _coerce_user_structured_answer(cls, v: object) -> dict[str, Any] | None:
        if v is None:
            return None
        if isinstance(v, dict) and v:
            return dict(v)
        return None

    @field_validator("pdf_read_request", mode="before")
    @classmethod
    def _coerce_pdf_read_request(cls, v: object) -> dict[str, Any] | None:
        if v is None or not isinstance(v, dict):
            return None
        pdf_url = str(v.get("pdf_url") or "").strip()
        if not pdf_url:
            return None
        return {"pdf_url": pdf_url[:2048]}

    @field_validator("agent_mode", mode="before")
    @classmethod
    def _normalize_agent_mode(cls, v: object) -> str:
        s = str(v or "agent").strip().lower()
        return s if s in {"agent", "plan"} else "agent"


class AgentQueryResponseV2(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    phoenix_trace_id: str | None = None
    run_metadata: dict[str, Any]
    thread_id: str | None = None
    session_summary_excerpt: str | None = Field(
        default=None,
        description=(
            "CH4: excerpt of server session_summary after this turn; "
            "JSON parity with SSE context_compacted."
        ),
    )
    answer_class: str | None = None
    evidence_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None
    product_path: str | None = None
    product_markers: list[str] = Field(default_factory=list)


def shortcut_response(
    *,
    answer: str,
    settings: Settings,
    max_tool_calls: int,
    duration_ms: int,
    thread_id: str | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> AgentQueryResponseV2:
    """Build shortcut response payload for pre-agent clarifications."""
    meta = build_run_metadata(
        settings=settings,
        max_tool_calls=max_tool_calls,
        thread_id=thread_id,
        extra=run_metadata,
    )
    return AgentQueryResponseV2(
        answer=answer,
        citations=[],
        tool_trace=[],
        duration_ms=duration_ms,
        phoenix_trace_id=current_otel_trace_id_hex(),
        run_metadata=meta,
        thread_id=thread_id,
        answer_class="synthesis",
        evidence_summary="clarification requested before retrieval",
        warnings=[],
    )


def response_from_run(
    out: Any,
    *,
    duration_ms: int,
    settings: Settings,
    max_tool_calls: int,
    extra_run_metadata: dict[str, Any] | None = None,
    session_summary_excerpt: str | None = None,
    extra_warnings: list[str] | None = None,
) -> AgentQueryResponseV2:
    """Build JSON response payload from agent run output."""
    trace_dicts = [dict(t) for t in (out.tool_trace or [])]
    run_metadata = build_run_metadata(
        settings=settings,
        max_tool_calls=max_tool_calls,
        thread_id=getattr(out, "thread_id", None),
        extra=extra_run_metadata,
    )
    llm_usage = getattr(out, "llm_usage", None)
    if isinstance(llm_usage, dict) and llm_usage:
        run_metadata["usage"] = dict(llm_usage)
    dbg_all = [x for x in list(getattr(out, "debug_events", None) or []) if isinstance(x, dict)]
    dbg_tail = dbg_all[-50:]
    if dbg_tail:
        run_metadata["debug_events"] = dbg_tail
    if dbg_all:
        # Keep payload small via tail, but aggregate telemetry from full list.
        run_metadata.update(extract_runtime_telemetry_from_debug_events(dbg_all))
    hc_list = [x for x in (getattr(out, "hook_chain_events", None) or []) if isinstance(x, dict)]
    merge_hook_chain_events_into_run_metadata(
        run_metadata,
        extra_events=hc_list or None,
        debug_events_tail=dbg_tail if dbg_tail else None,
    )
    tid = getattr(out, "thread_id", None)
    warnings = list(getattr(out, "warnings", None) or [])
    for w in extra_warnings or []:
        ws = str(w).strip()
        if ws and ws not in warnings:
            warnings.append(ws)
    pm = getattr(out, "prompt_memory_run_metadata", None)
    if isinstance(pm, dict) and pm:
        run_metadata.update(pm)
    sar = getattr(out, "subagent_runs", None)
    if isinstance(sar, list) and sar:
        run_metadata["subagent_runs"] = list(sar)
    stn = getattr(out, "subagent_task_notifications", None)
    if isinstance(stn, list) and stn:
        run_metadata["subagent_task_notifications"] = list(stn)
    slane = getattr(out, "subagent_observability_lane", None)
    if isinstance(slane, str) and slane.strip():
        run_metadata["subagent_observability_lane"] = slane.strip()
    sr3 = getattr(out, "specialist_results_v3", None)
    if isinstance(sr3, dict) and sr3:
        run_metadata["specialist_results_v3"] = dict(sr3)
    cvr = getattr(out, "claim_verification_results", None)
    if isinstance(cvr, list) and cvr:
        run_metadata["claim_verification_results"] = list(cvr)
    cer = getattr(out, "corpus_explore_results", None)
    if isinstance(cer, list) and cer:
        run_metadata["corpus_explore_results"] = list(cer)
    rpr = getattr(out, "research_plan_results", None)
    if isinstance(rpr, list) and rpr:
        run_metadata["research_plan_results"] = list(rpr)
    request_plan_mode = str(run_metadata.get("request_agent_mode") or "").strip().lower() == "plan"
    if tid and (
        request_plan_mode or bool(getattr(settings, "agent_research_plan_tool_enabled", False))
    ):
        from science_graphrag.agent.context.research_plan_session import (
            get_research_plan_snapshot_for_thread,
        )

        rp_snap = get_research_plan_snapshot_for_thread(str(tid).strip())
        if isinstance(rp_snap, dict):
            run_metadata["research_plan"] = rp_snap
    brief = getattr(out, "brief", None)
    if isinstance(brief, str) and brief.strip():
        run_metadata["brief"] = brief.strip()[:240]
    rl = getattr(out, "routing_log", None)
    if isinstance(rl, list) and rl:
        run_metadata["routing_log"] = [x for x in rl if isinstance(x, dict)]
    return AgentQueryResponseV2(
        answer=out.answer,
        citations=out.citations,
        tool_trace=trace_dicts,
        duration_ms=duration_ms,
        phoenix_trace_id=getattr(out, "phoenix_trace_id", None),
        run_metadata=run_metadata,
        thread_id=tid,
        session_summary_excerpt=session_summary_excerpt,
        answer_class=getattr(out, "answer_class", None),
        evidence_summary=getattr(out, "evidence_summary", None),
        warnings=warnings,
        inventory=getattr(out, "inventory", None),
        relation_trace=getattr(out, "relation_trace", None),
        quote_candidates=getattr(out, "quote_candidates", None),
        idea_suggestions=getattr(out, "idea_suggestions", None),
        bibliography=getattr(out, "bibliography", None),
        product_path=getattr(out, "product_path", None),
        product_markers=list(getattr(out, "product_markers", None) or []),
    )


__all__ = [
    "AgentQueryRequestV2",
    "AgentQueryResponseV2",
    "agent_chat_llm_run_metadata",
    "apply_runtime_metadata_from_state",
    "merge_hook_chain_events_into_run_metadata",
    "build_run_metadata",
    "deferred_topic_answer",
    "looks_like_deferred_topic",
    "normalize_history_digest_input",
    "response_from_run",
    "shortcut_response",
    "thread_insight_audit_fragment",
]
