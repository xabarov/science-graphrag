"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, Header
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.llm_history_compact import (
    maybe_llm_compact_session_after_turn,
    patch_compaction_audit_llm,
)
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.runtime import build_agent, current_otel_trace_id_hex
from science_graphrag.api.agent_v2_modules.deadline_otel import (
    record_agent_turn_deadline_exceeded,
)
from science_graphrag.api.agent_v2_modules.errors import (
    classify_agent_stream_error,
    is_retryable_provider_error_class,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    AgentQueryRequestV2,
    AgentQueryResponseV2,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    build_run_metadata as build_run_metadata_payload,
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
from science_graphrag.api.agent_v2_modules.payloads import (
    response_from_run as response_from_run_payload,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    shortcut_response as shortcut_response_payload,
)
from science_graphrag.api.agent_v2_modules.payloads import (
    thread_insight_audit_fragment,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle import (
    stream_agent_events,
    stream_shortcut_answer_events,
)
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings

logger = logging.getLogger(__name__)

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

    started = perf_counter()
    if deferred_topic_answer:
        duration_ms = int((perf_counter() - started) * 1000)
        return shortcut_response_payload(
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
            client_idle_ms=client_idle_ms,
            user_structured_answer=body.user_structured_answer,
        )
    except AgentGraphDeadlineExceeded as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        record_agent_turn_deadline_exceeded(exc, log_message="agent v2 sync deadline exceeded")
        meta = build_run_metadata_payload(
            settings=settings,
            max_tool_calls=max_tool_calls,
            thread_id=thread_id,
            extra={
                "agent_turn_deadline_exceeded": True,
                "agent_step_timeout_seconds": settings.agent_step_timeout_seconds,
                "agent_response_deadline_seconds": float(settings.agent_step_timeout_seconds),
                "agent_response_deadline_enforces_upstream_cancel": False,
                "agent_worker_may_continue_after_deadline": True,
            },
        )
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
    except AgentGraphRecursionLimitExceeded as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        logger.warning(
            "agent v2 sync recursion_limit exceeded limit=%s",
            getattr(exc, "recursion_limit", None),
        )
        meta = build_run_metadata_payload(
            settings=settings,
            max_tool_calls=max_tool_calls,
            thread_id=thread_id,
            extra={
                "agent_graph_recursion_limit_exceeded": True,
                "recursion_limit": int(getattr(exc, "recursion_limit", 0) or 0),
            },
        )
        return AgentQueryResponseV2(
            answer=(
                "The assistant stopped because the reasoning graph hit its hard step limit "
                "before producing a final answer. Try narrowing the question or asking it more "
                "specifically."
            ),
            citations=[],
            tool_trace=[],
            duration_ms=duration_ms,
            phoenix_trace_id=current_otel_trace_id_hex(),
            run_metadata=meta,
            thread_id=thread_id,
            answer_class="synthesis",
            evidence_summary="agent recursion limit exceeded",
            warnings=["agent_graph_recursion_limit_exceeded"],
            product_markers=["agent_graph_recursion_limit_exceeded"],
        )
    except Exception as exc:  # noqa: BLE001
        duration_ms = int((perf_counter() - started) * 1000)
        error_class, short_msg = classify_agent_stream_error(exc)
        markers = [error_class]
        extra_warnings: list[str] = [error_class]
        if is_retryable_provider_error_class(error_class):
            markers.append("retryable_provider_flake")
            extra_warnings.append("retryable_provider_flake")
        meta_err = build_run_metadata_payload(
            settings=settings,
            max_tool_calls=max_tool_calls,
            thread_id=thread_id,
            extra={
                "agent_sync_error": True,
                "error_class": error_class,
                "error_detail": str(exc)[:500],
            },
        )
        logger.warning(
            "agent v2 sync run failed error_class=%s type=%s",
            error_class,
            type(exc).__name__,
            exc_info=error_class == "internal_error",
        )
        return AgentQueryResponseV2(
            answer=short_msg,
            citations=[],
            tool_trace=[],
            duration_ms=duration_ms,
            phoenix_trace_id=current_otel_trace_id_hex(),
            run_metadata=meta_err,
            thread_id=thread_id,
            answer_class="synthesis",
            evidence_summary="agent run failed",
            warnings=extra_warnings,
            product_markers=markers,
        )
    duration_ms = int((perf_counter() - started) * 1000)
    excerpt: str | None = None
    extra_meta: dict[str, Any] | None = None
    if thread_id:
        ent_sync = get_session_for_thread(thread_id)
        dcount = len(ent_sync.get("digests") or [])
        llm_audit_sync = maybe_llm_compact_session_after_turn(
            settings,
            thread_id,
            digest_count=dcount,
            digest_cap=int(settings.agent_compaction_digest_cap),
        )
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
        if llm_audit_sync:
            cp_sync = patch_compaction_audit_llm(cp_sync, llm_audit=llm_audit_sync)
        comp_sync = cp_sync.get("compaction")
        if isinstance(comp_sync, dict):
            extra_meta = {"compaction": comp_sync, "session_digest_count": dcount}
            aud_sync = cp_sync.get("audit")
            if isinstance(aud_sync, dict):
                extra_meta["compaction_audit"] = aud_sync
        ti_frag = thread_insight_audit_fragment(thread_id=thread_id, settings=settings)
        if ti_frag:
            extra_meta = {**(extra_meta or {}), **ti_frag}
    extra_warnings = ["history_digest_invalid"] if history_digest_invalid else None
    return response_from_run_payload(
        out,
        duration_ms=duration_ms,
        settings=settings,
        max_tool_calls=max_tool_calls,
        session_summary_excerpt=excerpt,
        extra_warnings=extra_warnings,
        extra_run_metadata=extra_meta,
    )
