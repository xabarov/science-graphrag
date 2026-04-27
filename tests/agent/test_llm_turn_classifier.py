from __future__ import annotations

import pytest

from science_graphrag.agent.coordination.llm_turn_classifier import (
    normalize_llm_classifier_dict,
)


@pytest.mark.parametrize(
    ("payload", "expected_intent"),
    [
        (
            {
                "conversation_intent": "small_talk",
                "tool_policy": "no_tools",
                "route_hint": "writer_agent",
                "answer_class": "chat",
                "confidence": 0.9,
                "reason": "greeting",
            },
            "small_talk",
        ),
        (
            {
                "conversation_intent": "research_task",
                "tool_policy": "allow_tools",
                "route_hint": "retrieval_agent",
                "answer_class": "inventory",
                "confidence": 0.8,
                "reason": "list papers",
            },
            "research_task",
        ),
    ],
)
def test_normalize_llm_classifier_dict_ok(
    payload: dict,
    expected_intent: str,
) -> None:
    out = normalize_llm_classifier_dict(payload)
    assert out is not None
    assert out["conversation_intent"] == expected_intent
    assert 0.0 <= float(out["confidence"]) <= 1.0


@pytest.mark.parametrize(
    "bad",
    [
        {
            "conversation_intent": "unknown",
            "tool_policy": "no_tools",
            "route_hint": "writer_agent",
            "answer_class": "chat",
            "confidence": 1,
        },
        {
            "conversation_intent": "meta",
            "tool_policy": "ban_tools",
            "route_hint": "writer_agent",
            "answer_class": "chat",
            "confidence": 1,
        },
        {
            "conversation_intent": "meta",
            "tool_policy": "no_tools",
            "route_hint": "writer_agent",
            "answer_class": "not_a_class",
            "confidence": 1,
        },
    ],
)
def test_normalize_llm_classifier_dict_rejects(bad: dict) -> None:
    assert normalize_llm_classifier_dict(bad) is None


def test_normalize_clamps_confidence_and_aligns_route() -> None:
    out = normalize_llm_classifier_dict(
        {
            "conversation_intent": "ambiguous",
            "tool_policy": "clarify",
            "route_hint": "retrieval_agent",
            "answer_class": "clarification",
            "confidence": 2.5,
            "reason": "x",
        }
    )
    assert out is not None
    assert out["confidence"] == 1.0
    assert out["route_hint"] == "writer_agent"
