"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Header
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.chat_envelope import build_chat_envelope, heuristic_answer_class
from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.runtime import (
    build_agent,
    current_otel_trace_id_hex,
    extract_langgraph_answer,
)
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.spans import OpenInferenceAttributes, chain_span

logger = logging.getLogger(__name__)

router = APIRouter()


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
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
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
        default=None, description="CH4: stable id for server-side session memory."
    )
    history_digest: str | list[dict[str, Any]] | None = Field(
        default=None,
        description="CH4: JSON string or list of compact turn dicts from the client.",
    )
    answer_class_hint: str | None = Field(
        default=None,
        description="Optional hint for answer_class / UI (does not force tool routing).",
    )

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
        description="CH4: excerpt of server session_summary after this turn; JSON parity with SSE context_compacted.",
    )
    answer_class: str | None = None
    evidence_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    inventory: dict[str, Any] | None = None
    relation_trace: dict[str, Any] | None = None
    quote_candidates: list[dict[str, Any]] | None = None
    idea_suggestions: list[dict[str, Any]] | None = None
    bibliography: dict[str, Any] | None = None


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
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
    }
    if extra_run_metadata:
        run_metadata.update(extra_run_metadata)
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
    out = agent.run(
        question=body.question,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        answer_class_hint=body.answer_class_hint,
        thread_id=thread_id,
        history_digest=history_digest,
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
) -> AsyncIterator[Any]:
    """Yield graph stream chunks (updates dict, or (mode, payload) tuples when supported)."""
    if hasattr(graph, "astream") and callable(graph.astream):
        sig = inspect.signature(graph.astream)
        kwargs: dict[str, Any] = {}
        if "stream_mode" in sig.parameters:
            kwargs["stream_mode"] = ["updates", "values"]
        async for chunk in graph.astream(initial_state, config=config, **kwargs):
            yield chunk
        return

    def _collect_sync_chunks() -> list[Any]:
        out: list[Any] = []
        for chunk in graph.stream(initial_state, config=config):
            out.append(chunk)
        return out

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
                    "extraction_llm_model": settings.extraction_llm_model,
                    "extraction_llm_base_url": settings.extraction_llm_base_url,
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
    prev_route_len = 0
    prev_debug_len = 0
    dig = list(history_digest or [])
    active_subagent_id: str | None = None

    attrs: dict[str, Any] = {
        "agent.runtime": settings.agent_runtime,
        "agent.max_tool_calls": max_tool_calls,
        "user.id": workspace_id or "",
        "input.value": question[:500],
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

            hint_class = heuristic_answer_class(question, answer_class_hint)
            yield {
                "data": json.dumps(
                    {
                        "type": "intent_classified",
                        "answer_class": hint_class,
                        "source": "hint" if answer_class_hint else "heuristic",
                    }
                )
            }

            if history_digest_invalid:
                yield {
                    "data": json.dumps(
                        {
                            "type": "warning",
                            "code": "history_digest_invalid",
                            "message": "history_digest was not a JSON array of objects; it was ignored",
                        }
                    )
                }

            async for chunk in _iter_graph_chunks(graph, initial_state, config):
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
                                if isinstance(ev, dict) and ev.get("type") == "tool_search_result":
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
                                event_data = {
                                    "type": "tool_call",
                                    "step": step,
                                    "tool": str(tc.get("name") or ""),
                                    "args_summary": {k: str(v)[:200] for k, v in args_dict.items()},
                                }
                                yield {"data": json.dumps(event_data)}
                                if active_subagent_id:
                                    yield {
                                        "data": json.dumps(
                                            {
                                                "type": "subagent_progress",
                                                "subagent_id": active_subagent_id,
                                                "step": step,
                                                "tool": str(tc.get("name") or ""),
                                                "summary": str(tc.get("name") or ""),
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
                        elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                            final_answer = str(msg.content or "")
                    citations_chunk = node_state.get("citations")
                    if citations_chunk:
                        citations = list(citations_chunk)

            duration_ms = int((perf_counter() - started) * 1000)

            trace_for_run: list[Any] = []
            if latest_full_state is not None:
                trace_for_run = collect_tool_trace(latest_full_state)  # type: ignore[arg-type]
                state_answer, fa_citations = extract_langgraph_answer(
                    list(latest_full_state.get("messages") or [])
                )
                if state_answer:
                    final_answer = state_answer
                if fa_citations is not None:
                    citations = fa_citations
            trace_list: list[dict[str, Any]] = [dict(t) for t in trace_for_run]

            envelope: dict[str, Any] = {}
            if latest_full_state is not None:
                envelope = build_chat_envelope(
                    state=latest_full_state,  # type: ignore[arg-type]
                    answer=final_answer,
                    citations=citations,
                    tool_trace=trace_for_run,  # type: ignore[arg-type]
                    answer_class_hint=answer_class_hint,
                )
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
            run_meta: dict[str, Any] = {
                "agent_runtime": settings.agent_runtime,
                "agent_max_tool_calls": max_tool_calls,
                "extraction_llm_model": settings.extraction_llm_model,
                "extraction_llm_base_url": settings.extraction_llm_base_url,
                "debug_events": (
                    (latest_full_state or {}).get("debug_events", [])[-50:]
                    if isinstance(latest_full_state, dict)
                    else []
                ),
            }
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
                "inventory": envelope.get("inventory"),
                "relation_trace": envelope.get("relation_trace"),
                "quote_candidates": envelope.get("quote_candidates"),
                "idea_suggestions": envelope.get("idea_suggestions"),
                "bibliography": envelope.get("bibliography"),
            }
            yield {"data": json.dumps({"type": "answer_synthesis_finished"})}
            yield {"data": json.dumps(final_event)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        yield {"data": json.dumps({"type": "error", "detail": str(exc)})}
