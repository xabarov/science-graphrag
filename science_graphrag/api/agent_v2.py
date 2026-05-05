"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, Header
from langchain_core.messages import AIMessage, ToolMessage
from opentelemetry import context as otel_context
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.chat_envelope import build_chat_envelope, heuristic_answer_class
from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.runtime import (
    aggregate_agent_llm_usage,
    build_agent,
    current_otel_trace_id_hex,
    resolve_langgraph_answer_with_salvage,
)
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    add_span_event,
    chain_span,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_META_TOOL_NAMES = frozenset(
    {"session_init", "route_to_specialist", "coordinator_gate", "final_answer"}
)


def _extract_runtime_telemetry_from_debug_events(
    debug_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate shortlist/budget telemetry from debug events for run_metadata."""
    shortlist_ratios: list[float] = []
    deferred_schema_hits = 0
    budget_stop_reasons: list[str] = []
    for ev in debug_events:
        if not isinstance(ev, dict):
            continue
        if str(ev.get("type") or "") == "tool_search_result":
            raw_ratio = ev.get("shortlist_ratio")
            try:
                shortlist_ratios.append(float(raw_ratio))
            except (TypeError, ValueError):
                pass
            refs = ev.get("deferred_schema_refs")
            if isinstance(refs, list) and refs:
                deferred_schema_hits += 1
        if str(ev.get("type") or "") == "budget_stop_decision":
            reason = str(ev.get("code") or "").strip()
            if reason:
                budget_stop_reasons.append(reason)
    telemetry: dict[str, Any] = {}
    if shortlist_ratios:
        telemetry["tool_search_shortlist_ratio_avg"] = round(
            sum(shortlist_ratios) / len(shortlist_ratios), 4
        )
    if deferred_schema_hits:
        telemetry["tool_search_deferred_schema_events"] = deferred_schema_hits
    if budget_stop_reasons:
        telemetry["budget_stop_reasons"] = budget_stop_reasons
    return telemetry


def _agent_chat_llm_run_metadata(settings: Settings) -> dict[str, Any]:
    """LLM fields attached to agent run_metadata (extraction vs chat model split)."""
    return {
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
        "chat_llm_model": settings.chat_llm_model,
        "resolved_chat_llm_model": effective_chat_llm_model(settings),
    }


def _product_step_code_for_tool(tool_name: str) -> str | None:
    """Map normalized tool name to a short product_step code for SSE/UI."""
    mapping: dict[str, str] = {
        "idea_search": "searching_literature",
        "workspace_inspect": "summarizing_workspace",
        "cypher_query": "exploring_graph",
        "edge_search": "exploring_graph",
        "find_works": "paper_lookup",
        "paper_profile": "paper_metadata",
        "paper_quote_search": "finding_quotes",
        "format_bibliography_gost": "formatting_bibliography",
        "final_answer": "composing_answer",
    }
    return mapping.get(tool_name)


def _format_agent_stream_error(exc: BaseException) -> str:
    """Map common LangChain/OpenRouter failures to a short SSE/UI-facing message."""
    if isinstance(exc, ValueError) and exc.args:
        arg0 = exc.args[0]
        if isinstance(arg0, dict):
            msg = str(arg0.get("message") or "provider error").strip()
            code = arg0.get("code")
            meta = arg0.get("metadata")
            raw_hint = ""
            if isinstance(meta, dict):
                raw = meta.get("raw")
                if isinstance(raw, str) and raw.strip():
                    raw_hint = f" — {raw.strip()[:280]}"
            if code is not None:
                return f"Upstream LLM rejected the request (code {code}): {msg}{raw_hint}"
            return f"Upstream LLM error: {msg}{raw_hint}"
        if isinstance(arg0, str) and arg0.strip():
            return arg0.strip()
    return str(exc)


def normalize_history_digest_input(raw: object) -> tuple[list[dict[str, Any]], bool]:
    """Parse client history digest; return (normalized_turn_dicts, invalid).

    ``invalid`` is True when the client clearly sent a non-empty JSON string that
    is not a JSON array of objects (parse failure, or JSON object/scalar). This
    surfaces as top-level ``warnings`` / SSE ``warning`` instead of failing silently.
    """
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


def _looks_like_deferred_topic(question: str) -> bool:
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


def _deferred_topic_answer(question: str) -> str:
    if _has_cyrillic(question):
        return (
            "Хорошо. Пришлите тему следующим сообщением, и я сравню статьи в рабочей области "
            "по этой теме: выделю совпадения, противоречия и укажу, какие статьи их поддерживают."
        )
    return (
        "Sure. Send the topic in your next message, and I will compare the workspace papers "
        "around it: agreements, contradictions, and which papers support each point."
    )


def _shortcut_response(
    *,
    answer: str,
    settings: Settings,
    max_tool_calls: int,
    duration_ms: int,
    thread_id: str | None = None,
    run_metadata: dict[str, Any] | None = None,
) -> AgentQueryResponseV2:
    meta = {
        "agent_runtime": settings.agent_runtime,
        "agent_max_tool_calls": max_tool_calls,
        **_agent_chat_llm_run_metadata(settings),
    }
    if run_metadata:
        meta.update(run_metadata)
    if thread_id:
        meta["thread_id"] = thread_id
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


def _response_from_run(
    out: Any,
    *,
    duration_ms: int,
    settings: Settings,
    max_tool_calls: int,
    extra_run_metadata: dict[str, Any] | None = None,
    session_summary_excerpt: str | None = None,
    extra_warnings: list[str] | None = None,
) -> AgentQueryResponseV2:
    trace_dicts = [dict(t) for t in (out.tool_trace or [])]
    run_metadata = {
        "agent_runtime": settings.agent_runtime,
        "agent_max_tool_calls": max_tool_calls,
        **_agent_chat_llm_run_metadata(settings),
    }
    if extra_run_metadata:
        run_metadata.update(extra_run_metadata)
    llm_usage = getattr(out, "llm_usage", None)
    if isinstance(llm_usage, dict) and llm_usage:
        run_metadata["usage"] = dict(llm_usage)
    if getattr(out, "debug_events", None):
        run_metadata["debug_events"] = list(out.debug_events)[-50:]
    tid = getattr(out, "thread_id", None)
    if tid:
        run_metadata["thread_id"] = tid
    warnings = list(getattr(out, "warnings", None) or [])
    for w in extra_warnings or []:
        ws = str(w).strip()
        if ws and ws not in warnings:
            warnings.append(ws)
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


@router.post("/agent/query", response_model=AgentQueryResponseV2)
async def post_agent_query_v2(
    body: AgentQueryRequestV2,
    accept: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
):
    """POST /v2/agent/query with JSON or SSE output based on Accept."""
    workspace_id = (body.workspace_id or "").strip() or None
    max_tool_calls = body.max_tool_calls or settings.agent_max_tool_calls
    wants_sse = "text/event-stream" in (accept or "")
    thread_id = (body.thread_id or "").strip() or None
    history_digest, history_digest_invalid = normalize_history_digest_input(body.history_digest)
    deferred_topic_answer = (
        _deferred_topic_answer(body.question) if _looks_like_deferred_topic(body.question) else None
    )

    if wants_sse:
        if deferred_topic_answer:
            return EventSourceResponse(
                _stream_shortcut_answer(
                    settings=settings,
                    question=body.question,
                    answer=deferred_topic_answer,
                    max_tool_calls=max_tool_calls,
                    workspace_id=workspace_id,
                    thread_id=thread_id,
                    reason="deferred_topic_clarification",
                )
            )
        return EventSourceResponse(
            _stream_agent(
                settings=settings,
                stores=stores,
                question=body.question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                answer_class_hint=body.answer_class_hint,
                thread_id=thread_id,
                history_digest=history_digest,
                history_digest_invalid=history_digest_invalid,
            )
        )

    started = perf_counter()
    if deferred_topic_answer:
        duration_ms = int((perf_counter() - started) * 1000)
        return _shortcut_response(
            answer=deferred_topic_answer,
            settings=settings,
            max_tool_calls=max_tool_calls,
            duration_ms=duration_ms,
            thread_id=thread_id,
            run_metadata={"shortcut": "deferred_topic_clarification"},
        )
    agent = build_agent(settings=settings, stores=stores)
    try:
        out = agent.run(
            question=body.question,
            workspace_id=workspace_id,
            max_tool_calls=max_tool_calls,
            answer_class_hint=body.answer_class_hint,
            thread_id=thread_id,
            history_digest=history_digest,
        )
    except AgentGraphDeadlineExceeded as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        logger.warning(
            "agent v2 sync deadline exceeded timeout=%s",
            getattr(exc, "timeout_seconds", None),
        )
        add_span_event(
            "agent.response_deadline_exceeded",
            {
                "timeout_seconds": float(getattr(exc, "timeout_seconds", 0) or 0),
                "worker_may_continue": True,
                "deadline_kind": "response_only",
            },
        )
        meta = {
            "agent_runtime": settings.agent_runtime,
            "agent_max_tool_calls": max_tool_calls,
            **_agent_chat_llm_run_metadata(settings),
            "agent_turn_deadline_exceeded": True,
            "agent_step_timeout_seconds": settings.agent_step_timeout_seconds,
            "agent_response_deadline_seconds": float(settings.agent_step_timeout_seconds),
            "agent_response_deadline_enforces_upstream_cancel": False,
            "agent_worker_may_continue_after_deadline": True,
        }
        if thread_id:
            meta["thread_id"] = thread_id
        return AgentQueryResponseV2(
            answer=(
                "The assistant run exceeded the server time limit for one turn. "
                "Try a shorter question or increase SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS."
            ),
            citations=[],
            tool_trace=[],
            duration_ms=duration_ms,
            phoenix_trace_id=current_otel_trace_id_hex(),
            run_metadata=meta,
            thread_id=thread_id,
            answer_class="synthesis",
            evidence_summary="deadline exceeded",
            warnings=["agent_turn_deadline_exceeded"],
            product_markers=["agent_turn_deadline_exceeded"],
        )
    duration_ms = int((perf_counter() - started) * 1000)
    excerpt: str | None = None
    extra_meta: dict[str, Any] | None = None
    if thread_id:
        raw_sum = str(get_session_for_thread(thread_id).get("session_summary") or "")
        excerpt = raw_sum[:500] if raw_sum.strip() else None
        ent_sync = get_session_for_thread(thread_id)
        dcount = len(ent_sync.get("digests") or [])
        wc_sync = (ent_sync.get("capsules") or {}).get("workspace")
        cp_sync = build_context_compacted_payload(
            thread_id=thread_id,
            session_summary_excerpt=excerpt or "",
            latest_full_state={"source": "sync_json"},
            digest_count=dcount,
            rolling_threshold=settings.agent_compaction_rolling_memory_min_digests,
            digest_cap=settings.agent_compaction_digest_cap,
            workspace_id=workspace_id,
            workspace_capsule_present=isinstance(wc_sync, dict)
            and bool(str(wc_sync.get("workspace_id") or "").strip()),
        )
        comp_sync = cp_sync.get("compaction")
        if isinstance(comp_sync, dict):
            extra_meta = {"compaction": comp_sync, "session_digest_count": dcount}
    extra_warnings = ["history_digest_invalid"] if history_digest_invalid else None
    return _response_from_run(
        out,
        duration_ms=duration_ms,
        settings=settings,
        max_tool_calls=max_tool_calls,
        session_summary_excerpt=excerpt,
        extra_warnings=extra_warnings,
        extra_run_metadata=extra_meta,
    )


async def _iter_graph_chunks(
    graph: Any,
    initial_state: dict[str, Any],
    config: dict[str, Any],
    *,
    deadline_seconds: float | None = None,
) -> AsyncIterator[Any]:
    """Yield graph stream chunks (updates dict, or (mode, payload) tuples when supported)."""
    if hasattr(graph, "astream") and callable(graph.astream):
        sig = inspect.signature(graph.astream)
        kwargs: dict[str, Any] = {}
        if "stream_mode" in sig.parameters:
            kwargs["stream_mode"] = ["updates", "values"]

        async def _astream_body() -> AsyncIterator[Any]:
            async for chunk in graph.astream(initial_state, config=config, **kwargs):
                yield chunk

        if deadline_seconds and deadline_seconds > 0:
            try:
                async with asyncio.timeout(float(deadline_seconds)):
                    async for item in _astream_body():
                        yield item
            except TimeoutError as exc:
                raise AgentGraphDeadlineExceeded(
                    timeout_seconds=float(deadline_seconds),
                ) from exc
            return

        async for chunk in _astream_body():
            yield chunk
        return

    parent_ctx = otel_context.get_current()

    def _collect_sync_chunks() -> list[Any]:
        token = otel_context.attach(parent_ctx)
        try:
            out: list[Any] = []
            for chunk in graph.stream(initial_state, config=config):
                out.append(chunk)
            return out
        finally:
            otel_context.detach(token)

    if deadline_seconds and deadline_seconds > 0:
        try:
            chunks = await asyncio.wait_for(
                asyncio.to_thread(_collect_sync_chunks),
                timeout=float(deadline_seconds),
            )
        except TimeoutError as exc:
            raise AgentGraphDeadlineExceeded(
                timeout_seconds=float(deadline_seconds),
            ) from exc
    else:
        chunks = await asyncio.to_thread(_collect_sync_chunks)
    for chunk in chunks:
        yield chunk


def _iter_update_node_states(chunk: Any) -> list[Any]:
    """Normalize stream chunk to a list of per-node state dicts."""
    if isinstance(chunk, tuple) and len(chunk) == 2:
        _mode, payload = chunk
        if isinstance(payload, dict):
            return list(payload.values())
        return []
    if isinstance(chunk, dict):
        return list(chunk.values())
    return []


async def _stream_shortcut_answer(
    *,
    settings: Settings,
    question: str,
    answer: str,
    max_tool_calls: int,
    workspace_id: str | None,
    thread_id: str | None = None,
    reason: str,
) -> AsyncIterator[dict[str, str]]:
    """Emit a small SSE response for pre-agent clarifications."""
    started = perf_counter()
    yield {
        "data": json.dumps(
            {
                "type": "intent_classified",
                "answer_class": "synthesis",
                "source": reason,
            }
        )
    }
    summary_excerpt: str | None = None
    if thread_id:
        new_sum = apply_turn_digest_to_thread(
            thread_id=thread_id,
            raw_user_question=question,
            answer=answer,
            answer_class="synthesis",
            tool_trace=[],
            workspace_id=workspace_id,
        )
        summary_excerpt = (new_sum or "")[:500] if str(new_sum or "").strip() else None
    duration_ms = int((perf_counter() - started) * 1000)
    yield {"data": json.dumps({"type": "answer_synthesis_started"})}
    yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
    yield {
        "data": json.dumps(
            {
                "type": "final_answer",
                "answer": answer,
                "citations": [],
                "tool_trace": [],
                "duration_ms": duration_ms,
                "phoenix_trace_id": current_otel_trace_id_hex(),
                "thread_id": thread_id,
                "session_summary_excerpt": summary_excerpt,
                "run_metadata": {
                    "agent_runtime": settings.agent_runtime,
                    "agent_max_tool_calls": max_tool_calls,
                    **_agent_chat_llm_run_metadata(settings),
                    "shortcut": reason,
                },
                "answer_class": "synthesis",
                "evidence_summary": "clarification requested before retrieval",
                "warnings": [],
                "inventory": None,
                "relation_trace": None,
                "quote_candidates": None,
                "idea_suggestions": None,
                "bibliography": None,
            }
        )
    }


async def _stream_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    answer_class_hint: str | None,
    thread_id: str | None = None,
    history_digest: list[dict[str, Any]] | None = None,
    history_digest_invalid: bool = False,
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events from LangGraph chunks."""
    started = perf_counter()
    step = 0
    final_answer = ""
    citations: list[dict[str, Any]] = []
    seen_messages: set[int] = set()
    latest_full_state: dict[str, Any] | None = None
    salvaged_after_deadline = False
    prev_route_len = 0
    prev_debug_len = 0
    dig = list(history_digest or [])
    active_subagent_id: str | None = None

    deadline_s = float(settings.agent_step_timeout_seconds)
    attrs: dict[str, Any] = {
        "agent.runtime": settings.agent_runtime,
        "agent.max_tool_calls": max_tool_calls,
        "user.id": workspace_id or "",
        "input.value": question[:500],
        "agent.response_deadline_seconds": deadline_s,
        "agent.response_deadline_enforces_upstream_cancel": False,
    }
    if thread_id:
        attrs[OpenInferenceAttributes.SESSION_ID] = thread_id

    try:
        with chain_span("agent.query", attrs):
            graph = build_retrieval_graph(stores, settings)
            session_summary = ""
            if thread_id:
                session_summary = str(
                    get_session_for_thread(thread_id).get("session_summary") or ""
                )
            initial_state = build_initial_agent_state(
                question=question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                agent_runtime=settings.agent_runtime,
                thread_id=thread_id,
                history_digest=dig,
                session_summary=session_summary,
                answer_class_hint=answer_class_hint,
            )
            config = {"recursion_limit": settings.agent_supervisor_recursion_limit}

            initial_debug = list(initial_state.get("debug_events") or [])
            for ev in initial_debug:
                if isinstance(ev, dict):
                    yield {"data": json.dumps(ev)}
            prev_debug_len = len(initial_debug)

            if history_digest_invalid:
                yield {
                    "data": json.dumps(
                        {
                            "type": "warning",
                            "code": "history_digest_invalid",
                            "message": (
                                "history_digest was not a JSON array of objects; it was ignored"
                            ),
                        }
                    )
                }

            try:
                async for chunk in _iter_graph_chunks(
                    graph,
                    initial_state,
                    config,
                    deadline_seconds=float(settings.agent_step_timeout_seconds),
                ):
                    if isinstance(chunk, tuple) and len(chunk) == 2:
                        mode, payload = chunk
                        if mode == "values" and isinstance(payload, dict):
                            latest_full_state = payload
                            routes = list(payload.get("routing_log") or [])
                            if len(routes) > prev_route_len:
                                for entry in routes[prev_route_len:]:
                                    if active_subagent_id:
                                        yield {
                                            "data": json.dumps(
                                                {
                                                    "type": "subagent_finished",
                                                    "subagent_id": active_subagent_id,
                                                }
                                            )
                                        }
                                        active_subagent_id = None
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "specialist_selected",
                                                "from": entry.get("from"),
                                                "to": entry.get("to"),
                                                "budget_left": entry.get("budget_left"),
                                                "reason": entry.get("reason"),
                                            }
                                        )
                                    }
                                    to_raw = entry.get("to")
                                    to_id = str(to_raw).strip() if to_raw is not None else ""
                                    if not to_id:
                                        to_id = "specialist"
                                    reason_txt = entry.get("reason")
                                    summary = (
                                        str(reason_txt)[:200]
                                        if reason_txt is not None and str(reason_txt).strip()
                                        else None
                                    )
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "subagent_started",
                                                "subagent_id": to_id,
                                                "from": entry.get("from"),
                                                "summary": summary,
                                            }
                                        )
                                    }
                                    active_subagent_id = to_id
                                prev_route_len = len(routes)
                            dev = list(payload.get("debug_events") or [])
                            if len(dev) > prev_debug_len:
                                for ev in dev[prev_debug_len:]:
                                    if not isinstance(ev, dict):
                                        continue
                                    et = ev.get("type")
                                    if et in ("tool_search_result", "intent_classified"):
                                        yield {"data": json.dumps(dict(ev))}
                                    elif et == "budget_stop_decision":
                                        yield {"data": json.dumps(dict(ev))}
                                    elif et == "warning" and str(ev.get("code") or "").strip():
                                        yield {"data": json.dumps(dict(ev))}
                                prev_debug_len = len(dev)
                        if mode != "updates":
                            continue
                        chunk = payload

                    for node_state in _iter_update_node_states(chunk):
                        if not isinstance(node_state, dict):
                            continue
                        for msg in node_state.get("messages") or []:
                            marker = id(msg)
                            if marker in seen_messages:
                                continue
                            seen_messages.add(marker)
                            if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
                                for tc in msg.tool_calls:
                                    step += 1
                                    args = tc.get("args") if isinstance(tc, dict) else {}
                                    args_dict = args if isinstance(args, dict) else {}
                                    tool_name = normalize_tool_call_name(str(tc.get("name") or ""))
                                    event_data = {
                                        "type": "tool_call",
                                        "step": step,
                                        "tool": tool_name,
                                        "args_summary": {
                                            k: str(v)[:200] for k, v in args_dict.items()
                                        },
                                    }
                                    yield {"data": json.dumps(event_data)}
                                    psc = _product_step_code_for_tool(tool_name)
                                    if tool_name not in _META_TOOL_NAMES:
                                        if psc:
                                            yield {
                                                "data": json.dumps(
                                                    {
                                                        "type": "product_step",
                                                        "code": psc,
                                                        "tool": tool_name,
                                                    }
                                                )
                                            }
                                        else:
                                            yield {
                                                "data": json.dumps(
                                                    {
                                                        "type": "product_step",
                                                        "code": "using_tool",
                                                        "tool": tool_name,
                                                    }
                                                )
                                            }
                                    if active_subagent_id:
                                        yield {
                                            "data": json.dumps(
                                                {
                                                    "type": "subagent_progress",
                                                    "subagent_id": active_subagent_id,
                                                    "step": step,
                                                    "tool": tool_name,
                                                    "summary": tool_name,
                                                }
                                            )
                                        }
                            elif isinstance(msg, ToolMessage):
                                result_payload: dict[str, Any] = {}
                                error: str | None = None
                                try:
                                    parsed = json.loads(str(msg.content or ""))
                                    if isinstance(parsed, dict):
                                        result_payload = parsed
                                except Exception:  # noqa: BLE001
                                    error = str(msg.content or "")[:200]
                                result_event = {
                                    "type": "tool_result",
                                    "step": step,
                                    "tool": str(getattr(msg, "name", "") or ""),
                                    "row_count": result_payload.get("row_count"),
                                    "error": error,
                                }
                                yield {"data": json.dumps(result_event)}
                            elif isinstance(msg, AIMessage) and not getattr(
                                msg, "tool_calls", None
                            ):
                                final_answer = str(msg.content or "")
                        citations_chunk = node_state.get("citations")
                        if citations_chunk:
                            citations = list(citations_chunk)

            except AgentGraphDeadlineExceeded as exc:
                logger.warning(
                    "agent v2 stream deadline exceeded timeout=%s",
                    getattr(exc, "timeout_seconds", None),
                )
                add_span_event(
                    "agent.response_deadline_exceeded",
                    {
                        "timeout_seconds": float(getattr(exc, "timeout_seconds", 0) or 0),
                        "worker_may_continue": True,
                        "deadline_kind": "response_only",
                    },
                )
                salvaged = False
                if latest_full_state is not None:
                    state_answer, resolved_cites, _g, _q, _d = (
                        resolve_langgraph_answer_with_salvage(latest_full_state)
                    )
                    if (state_answer or "").strip():
                        salvaged = True
                        final_answer = str(state_answer).strip()
                        citations = list(resolved_cites)
                if not salvaged:
                    yield {
                        "data": json.dumps(
                            {
                                "type": "error",
                                "detail": str(exc),
                                "code": "agent_turn_deadline_exceeded",
                            }
                        )
                    }
                    return
                salvaged_after_deadline = True
                yield {
                    "data": json.dumps(
                        {
                            "type": "warning",
                            "code": "agent_turn_deadline_exceeded",
                            "message": (
                                "The assistant hit the per-turn time limit after producing "
                                "an answer; treat this turn as partially finalized."
                            ),
                        }
                    )
                }

            duration_ms = int((perf_counter() - started) * 1000)

            trace_for_run: list[Any] = []
            graph_salvage_stream = False
            quote_salvage_stream = False
            draft_salvage_stream = False
            if latest_full_state is not None:
                trace_for_run = collect_tool_trace(latest_full_state)  # type: ignore[arg-type]
                (
                    final_answer,
                    citations,
                    graph_salvage_stream,
                    quote_salvage_stream,
                    draft_salvage_stream,
                ) = resolve_langgraph_answer_with_salvage(latest_full_state)
            trace_list: list[dict[str, Any]] = [dict(t) for t in trace_for_run]

            envelope: dict[str, Any] = {}
            if latest_full_state is not None:
                env_kw: dict[str, Any] = {
                    "state": latest_full_state,
                    "answer": final_answer,
                    "citations": citations,
                    "tool_trace": trace_for_run,
                    "answer_class_hint": answer_class_hint,
                }
                extra_stream_warnings: list[str] = []
                if graph_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_graph_tool")
                if quote_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_quote_candidates")
                if draft_salvage_stream:
                    extra_stream_warnings.append("answer_salvaged_from_assistant_draft")
                if salvaged_after_deadline:
                    extra_stream_warnings.extend(
                        [
                            "agent_turn_deadline_exceeded",
                            "partial_after_deadline",
                        ]
                    )
                    env_kw["extra_product_markers"] = ["partial_after_deadline"]
                if extra_stream_warnings:
                    env_kw["extra_warnings"] = extra_stream_warnings
                envelope = build_chat_envelope(**env_kw)  # type: ignore[arg-type]
            else:
                envelope = {
                    "answer_class": heuristic_answer_class(question, answer_class_hint),
                    "evidence_summary": None,
                    "warnings": ([] if workspace_id else ["no_workspace"]),
                }

            if active_subagent_id:
                yield {
                    "data": json.dumps(
                        {"type": "subagent_finished", "subagent_id": active_subagent_id}
                    )
                }
                active_subagent_id = None
            yield {"data": json.dumps({"type": "answer_synthesis_started"})}

            if citations:
                yield {
                    "data": json.dumps({"type": "evidence_ready", "citation_count": len(citations)})
                }

            compact_payload: dict[str, Any] | None = None
            if thread_id:
                raw_q = question
                if latest_full_state is not None:
                    rq = (latest_full_state.get("metadata") or {}).get("raw_user_question")
                    if isinstance(rq, str) and rq.strip():
                        raw_q = rq
                new_sum = apply_turn_digest_to_thread(
                    thread_id=thread_id,
                    raw_user_question=raw_q,
                    answer=final_answer,
                    answer_class=str(envelope.get("answer_class") or "grounded_explanation"),
                    tool_trace=trace_for_run,
                    workspace_id=workspace_id,
                )
                ent_post = get_session_for_thread(thread_id)
                dcount = len(ent_post.get("digests") or [])
                wc_post = (ent_post.get("capsules") or {}).get("workspace")
                compact_payload = build_context_compacted_payload(
                    thread_id=thread_id,
                    session_summary_excerpt=(new_sum or "")[:500],
                    latest_full_state=latest_full_state,
                    digest_count=dcount,
                    rolling_threshold=settings.agent_compaction_rolling_memory_min_digests,
                    digest_cap=settings.agent_compaction_digest_cap,
                    workspace_id=workspace_id,
                    workspace_capsule_present=isinstance(wc_post, dict)
                    and bool(str(wc_post.get("workspace_id") or "").strip()),
                )
                yield {"data": json.dumps(compact_payload)}

            phx = current_otel_trace_id_hex()
            stream_usage: dict[str, int] | None = None
            if latest_full_state is not None:
                msgs_for_usage = list(latest_full_state.get("messages") or [])
                stream_usage = aggregate_agent_llm_usage(msgs_for_usage)
            run_meta: dict[str, Any] = {
                "agent_runtime": settings.agent_runtime,
                "agent_max_tool_calls": max_tool_calls,
                **_agent_chat_llm_run_metadata(settings),
                "product_path": envelope.get("product_path"),
                "product_markers": envelope.get("product_markers"),
                "debug_events": (
                    (latest_full_state or {}).get("debug_events", [])[-50:]
                    if isinstance(latest_full_state, dict)
                    else []
                ),
            }
            debug_events_tail = (
                (latest_full_state or {}).get("debug_events", [])[-50:]
                if isinstance(latest_full_state, dict)
                else []
            )
            if isinstance(debug_events_tail, list):
                run_meta.update(
                    _extract_runtime_telemetry_from_debug_events(
                        [x for x in debug_events_tail if isinstance(x, dict)]
                    )
                )
            if stream_usage:
                run_meta["usage"] = stream_usage
            if salvaged_after_deadline:
                run_meta["salvaged_after_deadline"] = True
            if thread_id:
                run_meta["thread_id"] = thread_id
                if compact_payload is not None:
                    comp = compact_payload.get("compaction")
                    if isinstance(comp, dict):
                        run_meta["compaction"] = comp
                        if isinstance(comp.get("digest_count"), int):
                            run_meta["session_digest_count"] = comp["digest_count"]

            final_warnings = list(envelope.get("warnings") or [])
            if history_digest_invalid and "history_digest_invalid" not in final_warnings:
                final_warnings.append("history_digest_invalid")

            summary_excerpt: str | None = None
            if thread_id:
                raw_sum = str(get_session_for_thread(thread_id).get("session_summary") or "")
                summary_excerpt = raw_sum[:500] if raw_sum.strip() else None

            final_event = {
                "type": "final_answer",
                "answer": final_answer,
                "citations": citations,
                "tool_trace": trace_list,
                "duration_ms": duration_ms,
                "phoenix_trace_id": phx,
                "thread_id": thread_id,
                "session_summary_excerpt": summary_excerpt,
                "run_metadata": run_meta,
                "answer_class": envelope.get("answer_class"),
                "evidence_summary": envelope.get("evidence_summary"),
                "warnings": final_warnings,
                "product_path": envelope.get("product_path"),
                "product_markers": envelope.get("product_markers"),
                "inventory": envelope.get("inventory"),
                "relation_trace": envelope.get("relation_trace"),
                "quote_candidates": envelope.get("quote_candidates"),
                "idea_suggestions": envelope.get("idea_suggestions"),
                "bibliography": envelope.get("bibliography"),
            }
            yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
            yield {"data": json.dumps(final_event)}
            tp0 = (initial_state.get("metadata") or {}).get("turn_policy") or {}
            logger.info(
                "agent_query_completed",
                extra={
                    "agent_metrics": {
                        "duration_ms": duration_ms,
                        "classifier": tp0.get("classifier"),
                        "tool_policy": tp0.get("tool_policy"),
                        "conversation_intent": tp0.get("conversation_intent"),
                        "workspace_id_set": bool(workspace_id),
                        "thread_id_set": bool(thread_id),
                    }
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        detail = _format_agent_stream_error(exc)
        err_payload: dict[str, Any] = {
            "type": "error",
            "detail": detail,
            "code": "agent_runtime_error",
        }
        if isinstance(exc, ValueError) and exc.args and isinstance(exc.args[0], dict):
            prov_code = exc.args[0].get("code")
            if prov_code is not None:
                err_payload["provider_code"] = prov_code
        yield {"data": json.dumps(err_payload)}
