"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.chat_envelope import build_chat_envelope, heuristic_answer_class
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.runtime import build_agent
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.spans import chain_span

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentQueryRequestV2(BaseModel):
    question: str = Field(..., min_length=1)
    workspace_id: str | None = None
    max_tool_calls: int | None = Field(default=None, ge=1, le=30)
    thread_id: str | None = Field(default=None, description="Reserved for CH4 multi-turn.")
    history_digest: str | None = Field(default=None, description="Reserved for CH4.")
    answer_class_hint: str | None = Field(
        default=None,
        description="Optional hint for answer_class / UI (does not force tool routing).",
    )


class AgentQueryResponseV2(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    phoenix_trace_id: str | None = None
    run_metadata: dict[str, Any]
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
) -> AgentQueryResponseV2:
    trace_dicts = [dict(t) for t in (out.tool_trace or [])]
    run_metadata = {
        "agent_runtime": settings.agent_runtime,
        "agent_enabled": settings.agent_enabled,
        "agent_max_tool_calls": max_tool_calls,
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
    }
    if extra_run_metadata:
        run_metadata.update(extra_run_metadata)
    if getattr(out, "debug_events", None):
        run_metadata["debug_events"] = list(out.debug_events)[-50:]
    return AgentQueryResponseV2(
        answer=out.answer,
        citations=out.citations,
        tool_trace=trace_dicts,
        duration_ms=duration_ms,
        phoenix_trace_id=None,
        run_metadata=run_metadata,
        answer_class=getattr(out, "answer_class", None),
        evidence_summary=getattr(out, "evidence_summary", None),
        warnings=list(getattr(out, "warnings", None) or []),
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
    if not settings.agent_enabled:
        raise HTTPException(status_code=503, detail="agent_disabled")

    workspace_id = (body.workspace_id or "").strip() or None
    max_tool_calls = body.max_tool_calls or settings.agent_max_tool_calls
    wants_sse = "text/event-stream" in (accept or "")

    if wants_sse:
        return EventSourceResponse(
            _stream_agent(
                settings=settings,
                stores=stores,
                question=body.question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
                answer_class_hint=body.answer_class_hint,
            )
        )

    started = perf_counter()
    agent = build_agent(settings=settings, stores=stores)
    out = agent.run(
        question=body.question,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        answer_class_hint=body.answer_class_hint,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    return _response_from_run(
        out, duration_ms=duration_ms, settings=settings, max_tool_calls=max_tool_calls
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


async def _stream_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
    answer_class_hint: str | None,
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

    attrs = {
        "agent.runtime": settings.agent_runtime,
        "agent.max_tool_calls": max_tool_calls,
        "user.id": workspace_id or "",
        "input.value": question[:500],
    }

    try:
        with chain_span("agent.query", attrs):
            graph = build_retrieval_graph(stores, settings)
            initial_state = {
                "messages": [HumanMessage(content=question)],
                "workspace_id": workspace_id,
                "citations": [],
                "tool_trace": [],
                "budget_remaining": max_tool_calls,
                "metadata": {"agent_runtime": settings.agent_runtime},
                "specialist_results": {},
                "current_specialist": None,
                "routing_log": [],
                "debug_events": [],
            }
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

            async for chunk in _iter_graph_chunks(graph, initial_state, config):
                if isinstance(chunk, tuple) and len(chunk) == 2:
                    mode, payload = chunk
                    if mode == "values" and isinstance(payload, dict):
                        latest_full_state = payload
                        routes = list(payload.get("routing_log") or [])
                        if len(routes) > prev_route_len:
                            for entry in routes[prev_route_len:]:
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

            trace_list: list[dict[str, Any]]
            if latest_full_state is not None:
                trace_list = [dict(t) for t in collect_tool_trace(latest_full_state)]  # type: ignore[arg-type]
            else:
                trace_list = []

            envelope: dict[str, Any] = {}
            if latest_full_state is not None:
                envelope = build_chat_envelope(
                    state=latest_full_state,  # type: ignore[arg-type]
                    answer=final_answer,
                    citations=citations,
                    tool_trace=collect_tool_trace(latest_full_state),  # type: ignore[arg-type]
                    answer_class_hint=answer_class_hint,
                )
            else:
                envelope = {
                    "answer_class": heuristic_answer_class(question, answer_class_hint),
                    "evidence_summary": None,
                    "warnings": ([] if workspace_id else ["no_workspace"]),
                }

            if citations:
                yield {
                    "data": json.dumps({"type": "evidence_ready", "citation_count": len(citations)})
                }

            final_event = {
                "type": "final_answer",
                "answer": final_answer,
                "citations": citations,
                "tool_trace": trace_list,
                "duration_ms": duration_ms,
                "phoenix_trace_id": None,
                "run_metadata": {
                    "agent_runtime": settings.agent_runtime,
                    "agent_max_tool_calls": max_tool_calls,
                    "debug_events": (
                        (latest_full_state or {}).get("debug_events", [])[-50:]
                        if isinstance(latest_full_state, dict)
                        else []
                    ),
                },
                "answer_class": envelope.get("answer_class"),
                "evidence_summary": envelope.get("evidence_summary"),
                "warnings": list(envelope.get("warnings") or []),
                "inventory": envelope.get("inventory"),
                "relation_trace": envelope.get("relation_trace"),
                "quote_candidates": envelope.get("quote_candidates"),
                "idea_suggestions": envelope.get("idea_suggestions"),
                "bibliography": envelope.get("bibliography"),
            }
            yield {"data": json.dumps(final_event)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        yield {"data": json.dumps({"type": "error", "detail": str(exc)})}
