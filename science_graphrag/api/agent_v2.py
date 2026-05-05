"""Agent query API v2: SSE streaming and sync JSON response."""

from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field, field_validator
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.agent.graph.errors import (
    AgentGraphDeadlineExceeded,
    AgentGraphRecursionLimitExceeded,
)
from science_graphrag.agent.runtime import build_agent, current_otel_trace_id_hex
from science_graphrag.api.agent_v2_modules.deadline_otel import (
    record_agent_turn_deadline_exceeded,
)
from science_graphrag.api.agent_v2_modules.stream_lifecycle import (
    agent_chat_llm_run_metadata,
    stream_agent_events,
    stream_shortcut_answer_events,
)
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings

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
        **agent_chat_llm_run_metadata(settings),
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
    client_idle_ms: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Optional client-reported milliseconds since last user activity in this UI session. "
            "Used for deterministic away-recap framing (CH4/CH5)."
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
        **agent_chat_llm_run_metadata(settings),
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
            client_idle_ms=client_idle_ms,
        )
    except AgentGraphDeadlineExceeded as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        record_agent_turn_deadline_exceeded(exc, log_message="agent v2 sync deadline exceeded")
        meta = {
            "agent_runtime": settings.agent_runtime,
            "agent_max_tool_calls": max_tool_calls,
            **agent_chat_llm_run_metadata(settings),
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
    except AgentGraphRecursionLimitExceeded as exc:
        duration_ms = int((perf_counter() - started) * 1000)
        logger.warning(
            "agent v2 sync recursion_limit exceeded limit=%s",
            getattr(exc, "recursion_limit", None),
        )
        meta = {
            "agent_runtime": settings.agent_runtime,
            "agent_max_tool_calls": max_tool_calls,
            **agent_chat_llm_run_metadata(settings),
            "agent_graph_recursion_limit_exceeded": True,
            "recursion_limit": int(getattr(exc, "recursion_limit", 0) or 0),
        }
        if thread_id:
            meta["thread_id"] = thread_id
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
