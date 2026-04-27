"""Coordinator TurnPolicy: rules_v0, hybrid_v1 (rules + LLM), or llm_v1 classifier."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from science_graphrag.agent.coordination.deterministic import (
    FUZZY_RULES_V0_REASONS,
    narrow_deterministic_classify,
    rules_v0_classify,
)
from science_graphrag.agent.coordination.llm_turn_classifier import llm_classify_turn_policy
from science_graphrag.config import Settings, get_settings

ConversationIntent = Literal["research_task", "small_talk", "meta", "ambiguous"]
ToolPolicy = Literal["no_tools", "clarify", "allow_tools"]
RouteHint = Literal["writer_agent", "retrieval_agent", "graph_agent", "finish"]
ClassifierSource = Literal["deterministic", "llm", "fallback"]


@dataclass(frozen=True)
class TurnPolicy:
    """Per-turn coordinator output: intent, whether tools may run, and trace metadata."""

    conversation_intent: ConversationIntent
    tool_policy: ToolPolicy
    route_hint: RouteHint
    reason: str
    suggested_answer_class: str
    confidence: float = 1.0
    classifier: ClassifierSource = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_intent": self.conversation_intent,
            "tool_policy": self.tool_policy,
            "route_hint": self.route_hint,
            "reason": self.reason,
            "suggested_answer_class": self.suggested_answer_class,
            "confidence": self.confidence,
            "classifier": self.classifier,
        }

    def sse_payload(self) -> dict[str, Any]:
        """Payload for SSE / debug_events type intent_classified."""
        d = self.to_dict()
        d["type"] = "intent_classified"
        if self.classifier == "deterministic":
            d["source"] = "coordinator_gate_v0"
        else:
            d["source"] = f"coordinator_gate_{self.classifier}"
        d["answer_class"] = self.suggested_answer_class
        return d


def _normalize_classifier_mode(raw: str) -> str:
    m = str(raw or "").strip().lower()
    if m in {"rules_v0", "hybrid_v1", "llm_v1"}:
        return m
    return "rules_v0"


def _from_rules_tuple(
    tup: tuple[ConversationIntent, ToolPolicy, RouteHint, str, str],
) -> TurnPolicy:
    ci, tp, rh, reason, sac = tup
    return TurnPolicy(
        conversation_intent=ci,
        tool_policy=tp,
        route_hint=rh,
        reason=reason,
        suggested_answer_class=sac,
        confidence=1.0,
        classifier="deterministic",
    )


def _fallback_clarify(reason: str, *, confidence: float = 0.25) -> TurnPolicy:
    return TurnPolicy(
        conversation_intent="ambiguous",
        tool_policy="clarify",
        route_hint="writer_agent",
        reason=reason,
        suggested_answer_class="clarification",
        confidence=confidence,
        classifier="fallback",
    )


def classify_turn_policy(
    *,
    question: str,
    workspace_id: str | None,
    session_summary: str = "",
    history_digest: list[dict[str, Any]] | None = None,
    answer_class_hint: str | None = None,
    settings: Settings | None = None,
) -> TurnPolicy:
    """Classify user turn: rules_v0 (default), hybrid_v1, or llm_v1 per Settings."""
    s = settings or get_settings()
    mode = _normalize_classifier_mode(s.agent_turn_policy_classifier)
    hist = list(history_digest or [])
    llm_ok = bool(s.agent_turn_policy_llm_enabled) and bool(
        str(s.extraction_llm_api_key or "").strip()
    )

    if mode == "rules_v0":
        return _from_rules_tuple(
            rules_v0_classify(
                question=question,
                workspace_id=workspace_id,
                session_summary=session_summary,
                history_digest=hist,
                answer_class_hint=answer_class_hint,
            )
        )

    if mode == "hybrid_v1":
        tup = rules_v0_classify(
            question=question,
            workspace_id=workspace_id,
            session_summary=session_summary,
            history_digest=hist,
            answer_class_hint=answer_class_hint,
        )
        if tup[3] in FUZZY_RULES_V0_REASONS and llm_ok:
            alt = llm_classify_turn_policy(
                settings=s,
                question=question,
                workspace_id=workspace_id,
                session_summary=session_summary,
                history_digest=hist,
                answer_class_hint=answer_class_hint,
            )
            if (
                alt is not None
                and alt[5] >= s.agent_turn_policy_confidence_threshold
            ):
                ci, tp, rh, reason, sac, conf = alt
                return TurnPolicy(
                    conversation_intent=ci,
                    tool_policy=tp,
                    route_hint=rh,
                    reason=reason,
                    suggested_answer_class=sac,
                    confidence=conf,
                    classifier="llm",
                )
        return _from_rules_tuple(tup)

    # llm_v1
    narrow = narrow_deterministic_classify(
        question=question,
        workspace_id=workspace_id,
        answer_class_hint=answer_class_hint,
    )
    if narrow is not None:
        return TurnPolicy(
            conversation_intent=narrow[0],
            tool_policy=narrow[1],
            route_hint=narrow[2],
            reason=narrow[3],
            suggested_answer_class=narrow[4],
            confidence=1.0,
            classifier="deterministic",
        )
    if not llm_ok:
        return _fallback_clarify("llm_disabled_or_missing_api_key")
    alt = llm_classify_turn_policy(
        settings=s,
        question=question,
        workspace_id=workspace_id,
        session_summary=session_summary,
        history_digest=hist,
        answer_class_hint=answer_class_hint,
    )
    if alt is None:
        return _fallback_clarify("classifier_llm_parse_failure")
    if alt[5] < s.agent_turn_policy_confidence_threshold:
        return _fallback_clarify(
            "low_confidence_clarify",
            confidence=alt[5],
        )
    ci, tp, rh, reason, sac, conf = alt
    return TurnPolicy(
        conversation_intent=ci,
        tool_policy=tp,
        route_hint=rh,
        reason=reason,
        suggested_answer_class=sac,
        confidence=conf,
        classifier="llm",
    )
