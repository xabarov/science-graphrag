"""Structured LLM classifier for TurnPolicy (hybrid / llm_v1 modes)."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Literal

from langchain_core.messages import HumanMessage

from science_graphrag.agent.chat_envelope import ANSWER_CLASSES
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.config import Settings
from science_graphrag.observability.spans import (
    SpanAttributes,
    add_span_event,
    chain_span,
    llm_span,
)

logger = logging.getLogger(__name__)

ConversationIntent = Literal["research_task", "small_talk", "meta", "ambiguous"]
ToolPolicy = Literal["no_tools", "clarify", "allow_tools"]
RouteHint = Literal["writer_agent", "retrieval_agent", "graph_agent", "finish"]

_ALLOWED_INTENTS: frozenset[str] = frozenset({"research_task", "small_talk", "meta", "ambiguous"})
_ALLOWED_TOOL: frozenset[str] = frozenset({"no_tools", "clarify", "allow_tools"})
_ALLOWED_ROUTE: frozenset[str] = frozenset(
    {"writer_agent", "retrieval_agent", "graph_agent", "finish"}
)

_CLASSIFIER_PROMPT = (
    "You classify a single user message for a scholarly research assistant in a workspace UI.\n"
    "Return ONLY a compact JSON object with keys:\n"
    "- conversation_intent: one of research_task | small_talk | meta | ambiguous\n"
    "- answer_class: one of inventory | fact_lookup | grounded_explanation | "
    "relation_tracing | quote_extraction | ideation | bibliography_export | "
    "synthesis | chat | clarification\n"
    "- tool_policy: one of no_tools | clarify | allow_tools\n"
    "- route_hint: one of writer_agent | retrieval_agent | graph_agent | finish\n"
    "- confidence: number between 0 and 1\n"
    "- reason: short English phrase for logs (max 120 chars)\n"
    "\n"
    "Rules:\n"
    "- small_talk: greetings, thanks, bye, chit-chat without a research question.\n"
    "- meta: asks what you can do, who you are, how to use the assistant.\n"
    "- ambiguous: too vague to pick tools safely (ask user to clarify).\n"
    "- research_task: user wants corpus/workspace facts, search, graph, quotes, "
    "bibliography, ideas grounded in papers.\n"
    "- tool_policy no_tools for small_talk and meta; clarify for ambiguous; "
    "allow_tools for research_task.\n"
    "- route_hint: writer_agent for no_tools/clarify; retrieval_agent for allow_tools "
    "unless graph-only (cypher/path/cites) then graph_agent.\n"
    "- Never invent paper titles; if unsure use ambiguous + clarify + low confidence.\n"
)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.IGNORECASE)
    if fence:
        raw = fence.group(1)
    try:
        obj = json.loads(raw)
    except Exception:  # noqa: BLE001
        start = raw.find("{")
        end = raw.rfind("}")
        if 0 <= start < end:
            try:
                obj = json.loads(raw[start : end + 1])
            except Exception:  # noqa: BLE001
                return None
        else:
            return None
    return obj if isinstance(obj, dict) else None


def normalize_llm_classifier_dict(obj: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize LLM JSON; return None if schema rejects output."""
    return _normalize_policy_dict(obj)


def _normalize_policy_dict(obj: dict[str, Any]) -> dict[str, Any] | None:
    intent = str(obj.get("conversation_intent") or "").strip()
    tool_pol = str(obj.get("tool_policy") or "").strip()
    route = str(obj.get("route_hint") or "").strip()
    ans = str(obj.get("answer_class") or obj.get("suggested_answer_class") or "").strip()
    conf_raw = obj.get("confidence")
    try:
        conf = float(conf_raw)
    except (TypeError, ValueError):
        conf = 0.0
    conf = max(0.0, min(1.0, conf))
    reason = str(obj.get("reason") or "llm_classifier").strip()[:200]

    if intent not in _ALLOWED_INTENTS:
        return None
    if tool_pol not in _ALLOWED_TOOL:
        return None
    if route not in _ALLOWED_ROUTE:
        return None
    if ans not in ANSWER_CLASSES:
        return None

    # Enforce safe route/tool alignment
    if tool_pol in {"no_tools", "clarify"} and route not in {"writer_agent", "finish"}:
        route = "writer_agent"
    if tool_pol == "allow_tools" and route == "finish":
        route = "retrieval_agent"

    return {
        "conversation_intent": intent,
        "tool_policy": tool_pol,
        "route_hint": route,
        "suggested_answer_class": ans,
        "confidence": conf,
        "reason": reason,
    }


def llm_classify_turn_policy(  # pylint: disable=too-many-locals
    *,
    settings: Settings,
    question: str,
    workspace_id: str | None,
    session_summary: str = "",
    history_digest: list[dict[str, Any]] | None = None,
    answer_class_hint: str | None = None,
) -> tuple[ConversationIntent, ToolPolicy, RouteHint, str, str, float] | None:
    """Return policy tuple + confidence, or None on failure."""
    if not str(settings.extraction_llm_api_key or "").strip():
        return None

    q = str(question or "").strip()
    if not q:
        return None

    has_ws = bool(str(workspace_id or "").strip())
    digest_blob = ""
    if history_digest:
        try:
            digest_blob = json.dumps(history_digest[-3:], ensure_ascii=False)[:2000]
        except Exception:  # noqa: BLE001
            digest_blob = str(history_digest[-3:])[:2000]
    summary_excerpt = str(session_summary or "").strip()[:800]
    hint_line = (
        f"answer_class_hint={answer_class_hint!r}"
        if answer_class_hint
        else "answer_class_hint=null"
    )

    user_block = "\n".join(
        [
            f"has_workspace={has_ws}",
            hint_line,
            f"session_summary_excerpt={summary_excerpt!r}",
            f"recent_history_digest_tail={digest_blob!r}",
            f"user_message={q[:4000]!r}",
        ]
    )
    messages = [
        HumanMessage(content=_CLASSIFIER_PROMPT),
        HumanMessage(content=user_block),
    ]

    try:
        llm = build_chat_model(
            settings,
            temperature=0.0,
            max_tokens=min(384, settings.agent_chat_max_tokens),
            timeout_seconds=settings.agent_turn_policy_classifier_timeout_seconds,
        )
        with chain_span(
            "agent.turn_policy",
            {
                "agent.turn_policy.classifier": str(settings.agent_turn_policy_classifier or ""),
            },
        ):
            with llm_span(
                "llm.agent.turn_policy",
                {
                    **SpanAttributes.llm_runtime_policy_attributes(
                        pool_name="agent_classifier",
                        transport_timeout_seconds=float(
                            settings.agent_turn_policy_classifier_timeout_seconds
                        ),
                        timeout_contract="transport_only",
                        retry_extra_budget=0,
                    ),
                    "llm.invocation_name": "agent_turn_policy_classifier",
                },
            ):
                resp = llm.invoke(messages)
        content = str(getattr(resp, "content", "") or "")
        parsed = _extract_json_object(content)
        if not parsed:
            add_span_event(
                "agent.turn_policy.parse_failed",
                {"reason": "no_json_object", "content_chars": str(len(content))},
            )
            return None
        norm = _normalize_policy_dict(parsed)
        if not norm:
            add_span_event("agent.turn_policy.parse_failed", {"reason": "normalize_failed"})
            return None
        add_span_event(
            "agent.turn_policy.parsed",
            {
                "conversation_intent": str(norm["conversation_intent"]),
                "tool_policy": str(norm["tool_policy"]),
                "route_hint": str(norm["route_hint"]),
                "confidence": float(norm["confidence"]),
                "suggested_answer_class": str(norm["suggested_answer_class"]),
            },
        )
        return (
            norm["conversation_intent"],  # type: ignore[return-value]
            norm["tool_policy"],  # type: ignore[return-value]
            norm["route_hint"],  # type: ignore[return-value]
            norm["reason"],
            norm["suggested_answer_class"],
            float(norm["confidence"]),
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Turn policy LLM classifier failed: %s", exc)
        return None


def llm_classify_or_none(
    *,
    settings: Settings,
    question: str,
    workspace_id: str | None,
    session_summary: str = "",
    history_digest: list[dict[str, Any]] | None = None,
    answer_class_hint: str | None = None,
) -> tuple[ConversationIntent, ToolPolicy, RouteHint, str, str, float] | None:
    """Same as llm_classify_turn_policy; respects classifier timeout via ChatOpenAI timeout."""
    return llm_classify_turn_policy(
        settings=settings,
        question=question,
        workspace_id=workspace_id,
        session_summary=session_summary,
        history_digest=history_digest,
        answer_class_hint=answer_class_hint,
    )


__all__ = [
    "llm_classify_turn_policy",
    "llm_classify_or_none",
    "normalize_llm_classifier_dict",
]
