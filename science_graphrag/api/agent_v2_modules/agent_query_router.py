"""FastAPI router for POST /v2/agent/query (SSE + sync JSON).

Extracted from :mod:`science_graphrag.api.agent_v2` so the package root stays a thin compatibility
facade (W4 structural split; R2 contract unchanged).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from science_graphrag.api.agent_v2_modules.agent_run_buffer import (
    get_agent_run_buffer,
    iter_buffered_run_sse,
    wrap_stream_with_run_buffer,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    AgentQueryRequestV2,
    AgentQueryResponseV2,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    deferred_topic_answer as deferred_topic_answer_payload,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    looks_like_deferred_topic as looks_like_deferred_topic_payload,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    normalize_history_digest_input as normalize_history_digest_input_payload,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle import (
    stream_agent_events,
    stream_shortcut_answer_events,
)
from science_graphrag.api.agent_v2_modules.sync_agent_query import (
    execute_agent_query_v2_json_response,
)
from science_graphrag.api.deps import get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.stores.registry import StoreRegistry

router = APIRouter()


async def _tee_agent_sse(
    *,
    settings: Settings,
    thread_id: str | None,
    workspace_id: str | None,
    inner: AsyncIterator[dict[str, str]],
) -> AsyncIterator[dict[str, str]]:
    """Wrap SSE iterator with optional run buffer + run_started event."""
    if not bool(getattr(settings, "agent_stream_resume_enabled", True)):
        async for ev in inner:
            yield ev
        return
    buf = get_agent_run_buffer(
        ttl_seconds=float(getattr(settings, "agent_stream_resume_ttl_seconds", 3600)),
    )
    run_id = await buf.create_run(
        thread_id=thread_id,
        workspace_id=workspace_id,
    )
    started = {
        "type": "run_started",
        "run_id": run_id,
        "thread_id": thread_id,
        "workspace_id": workspace_id,
    }

    async def _with_start() -> Any:
        yield {"data": json.dumps(started)}
        async for ev in inner:
            yield ev

    async for ev in wrap_stream_with_run_buffer(run_id, _with_start()):
        yield ev


def normalize_history_digest_input(raw: object) -> tuple[list[dict[str, Any]], bool]:
    """Compatibility wrapper around canonical payload helper."""
    return normalize_history_digest_input_payload(raw)


def _looks_like_deferred_topic(question: str) -> bool:
    """Compatibility wrapper around canonical payload helper."""
    return looks_like_deferred_topic_payload(question)


def _deferred_topic_answer(question: str) -> str:
    return deferred_topic_answer_payload(question)


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
    client_idle_ms = body.client_idle_ms
    history_digest, history_digest_invalid = normalize_history_digest_input(body.history_digest)
    deferred_topic_answer = (
        _deferred_topic_answer(body.question) if _looks_like_deferred_topic(body.question) else None
    )

    pdf_rr = body.pdf_read_request.model_dump() if body.pdf_read_request is not None else None
    if wants_sse:
        if deferred_topic_answer:
            shortcut = stream_shortcut_answer_events(
                settings=settings,
                question=body.question,
                answer=deferred_topic_answer,
                max_tool_calls=max_tool_calls,
                workspace_id=workspace_id,
                thread_id=thread_id,
                reason="deferred_topic_clarification",
            )
            return EventSourceResponse(
                _tee_agent_sse(
                    settings=settings,
                    thread_id=thread_id,
                    workspace_id=workspace_id,
                    inner=shortcut,
                )
            )
        graph_stream = stream_agent_events(
            settings=settings,
            stores=stores,
            question=body.question,
            workspace_id=workspace_id,
            max_tool_calls=max_tool_calls,
            answer_class_hint=body.answer_class_hint,
            thread_id=thread_id,
            history_digest=history_digest,
            history_digest_invalid=history_digest_invalid,
            client_idle_ms=client_idle_ms,
            user_structured_answer=body.user_structured_answer,
            web_research_enabled=body.web_research_enabled,
            agent_mode=body.agent_mode,
            pdf_read_request=pdf_rr,
        )
        return EventSourceResponse(
            _tee_agent_sse(
                settings=settings,
                thread_id=thread_id,
                workspace_id=workspace_id,
                inner=graph_stream,
            )
        )

    return await execute_agent_query_v2_json_response(
        body=body,
        settings=settings,
        stores=stores,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
        thread_id=thread_id,
        history_digest=history_digest,
        history_digest_invalid=history_digest_invalid,
        deferred_topic_answer=deferred_topic_answer,
    )


@router.get("/agent/query/runs/{run_id}/stream")
async def get_agent_query_run_stream(
    run_id: str,
    after_seq: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
):
    """Resume SSE for an in-flight or recently completed agent run (replay + live tail)."""
    if not bool(getattr(settings, "agent_stream_resume_enabled", True)):
        raise HTTPException(status_code=404, detail="agent_stream_resume_disabled")
    rec = await get_agent_run_buffer().get_run(run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="agent_run_not_found")
    return EventSourceResponse(iter_buffered_run_sse(run_id, after_seq=after_seq))


__all__ = [
    "get_agent_query_run_stream",
    "normalize_history_digest_input",
    "post_agent_query_v2",
    "router",
]
