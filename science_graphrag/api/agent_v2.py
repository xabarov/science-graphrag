"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import asyncio
import json
import logging
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.graph.supervisor import build_retrieval_graph
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


class AgentQueryResponseV2(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    phoenix_trace_id: str | None = None
    run_metadata: dict[str, Any]


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
            )
        )

    started = perf_counter()
    agent = build_agent(settings=settings, stores=stores)
    out = agent.run(
        question=body.question,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    return AgentQueryResponseV2(
        answer=out.answer,
        citations=out.citations,
        tool_trace=list(out.tool_trace),
        duration_ms=duration_ms,
        phoenix_trace_id=None,
        run_metadata={
            "agent_runtime": settings.agent_runtime,
            "agent_enabled": settings.agent_enabled,
            "agent_max_tool_calls": max_tool_calls,
            "extraction_llm_model": settings.extraction_llm_model,
            "extraction_llm_base_url": settings.extraction_llm_base_url,
        },
    )


async def _iter_graph_chunks(
    graph: Any,
    initial_state: dict[str, Any],
    config: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """Yield graph chunks, preferring async stream with a sync fallback."""
    if hasattr(graph, "astream") and callable(graph.astream):
        async for chunk in graph.astream(initial_state, config=config):
            if isinstance(chunk, dict):
                yield chunk
        return

    def _collect_sync_chunks() -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for chunk in graph.stream(initial_state, config=config):
            if isinstance(chunk, dict):
                out.append(chunk)
        return out

    chunks = await asyncio.to_thread(_collect_sync_chunks)
    for chunk in chunks:
        yield chunk


async def _stream_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
) -> AsyncIterator[dict[str, str]]:
    """Emit SSE events from LangGraph chunks."""
    started = perf_counter()
    step = 0
    final_answer = ""
    citations: list[dict[str, Any]] = []
    tool_trace: list[dict[str, Any]] = []
    seen_messages: set[int] = set()

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
            }
            config = {"recursion_limit": settings.agent_supervisor_recursion_limit}

            async for chunk in _iter_graph_chunks(graph, initial_state, config):
                for node_state in chunk.values():
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
                                tool_trace.append(event_data)
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
            final_event = {
                "type": "final_answer",
                "answer": final_answer,
                "citations": citations,
                "tool_trace": tool_trace,
                "duration_ms": duration_ms,
                "phoenix_trace_id": None,
                "run_metadata": {
                    "agent_runtime": settings.agent_runtime,
                    "agent_max_tool_calls": max_tool_calls,
                },
            }
            yield {"data": json.dumps(final_event)}
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        yield {"data": json.dumps({"type": "error", "detail": str(exc)})}
