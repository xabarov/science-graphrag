"""Payload models and response builders for Agent API v2."""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, field_validator

from science_graphrag.agent.llm.chat import effective_chat_llm_model
from science_graphrag.agent.runtime import current_otel_trace_id_hex
from science_graphrag.config import Settings


def agent_chat_llm_run_metadata(settings: Settings) -> dict[str, Any]:
    """LLM fields attached to agent run_metadata (extraction vs chat model split)."""
    return {
        "extraction_llm_model": settings.extraction_llm_model,
        "extraction_llm_base_url": settings.extraction_llm_base_url,
        "chat_llm_model": settings.chat_llm_model,
        "resolved_chat_llm_model": effective_chat_llm_model(settings),
    }


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


__all__ = [
    "AgentQueryRequestV2",
    "AgentQueryResponseV2",
    "agent_chat_llm_run_metadata",
    "deferred_topic_answer",
    "looks_like_deferred_topic",
    "normalize_history_digest_input",
    "response_from_run",
    "shortcut_response",
]
