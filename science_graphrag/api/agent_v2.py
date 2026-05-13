"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header
from sse_starlette.sse import EventSourceResponse

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
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings

router = APIRouter()


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

    if wants_sse:
        if deferred_topic_answer:
            return EventSourceResponse(
                stream_shortcut_answer_events(
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
            stream_agent_events(
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
