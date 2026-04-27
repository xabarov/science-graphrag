from __future__ import annotations

import pytest

from science_graphrag.agent.coordination.turn_policy import classify_turn_policy
from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.config import Settings


def test_greeting_russian_no_tools() -> None:
    p = classify_turn_policy(question="привет", workspace_id="ws-1", session_summary="")
    assert p.tool_policy == "no_tools"
    assert p.conversation_intent == "small_talk"
    assert p.suggested_answer_class == "chat"


def test_greeting_english_no_tools() -> None:
    p = classify_turn_policy(question="Hello!", workspace_id=None)
    assert p.tool_policy == "no_tools"
    assert p.conversation_intent == "small_talk"


def test_meta_no_tools() -> None:
    p = classify_turn_policy(question="Что ты умеешь?", workspace_id="ws-1")
    assert p.tool_policy == "no_tools"
    assert p.conversation_intent == "meta"


def test_explicit_inventory_allow_tools() -> None:
    p = classify_turn_policy(
        question="Какие статьи есть в моём workspace?",
        workspace_id="ws-1",
    )
    assert p.tool_policy == "allow_tools"
    assert p.conversation_intent == "research_task"
    assert p.reason == "explicit_research_signal"


def test_research_question_allow_tools() -> None:
    p = classify_turn_policy(
        question="How does BERT attention relate to efficiency in long documents?",
        workspace_id="ws-1",
    )
    assert p.tool_policy == "allow_tools"
    assert p.conversation_intent == "research_task"


def test_vague_scope_with_workspace_clarify() -> None:
    p = classify_turn_policy(question="Что тут есть?", workspace_id="ws-1")
    assert p.tool_policy == "clarify"
    assert p.conversation_intent == "ambiguous"


def test_answer_class_hint_inventory() -> None:
    p = classify_turn_policy(
        question="anything",
        workspace_id="ws-1",
        answer_class_hint="inventory",
    )
    assert p.tool_policy == "allow_tools"


def test_to_dict_roundtrip_keys() -> None:
    p = classify_turn_policy(question="привет", workspace_id=None)
    d = p.to_dict()
    assert set(d.keys()) >= {
        "conversation_intent",
        "tool_policy",
        "route_hint",
        "reason",
        "suggested_answer_class",
        "confidence",
        "classifier",
    }
    sse = p.sse_payload()
    assert sse["type"] == "intent_classified"
    assert sse["source"] == "coordinator_gate_v0"
    assert sse.get("answer_class") == p.suggested_answer_class
    assert sse.get("classifier") == "deterministic"
    assert sse.get("confidence") == 1.0


def test_llm_v1_fallback_without_api_key() -> None:
    settings = Settings().model_copy(
        update={
            "agent_turn_policy_classifier": "llm_v1",
            "agent_turn_policy_llm_enabled": True,
            "extraction_llm_api_key": "",
        }
    )
    p = classify_turn_policy(
        question="qqqq vvv bbbb",
        workspace_id="ws-1",
        settings=settings,
    )
    assert p.classifier == "fallback"
    assert p.tool_policy == "clarify"
    assert p.reason == "llm_disabled_or_missing_api_key"


def test_llm_v1_classifier_parse_failure_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from science_graphrag.agent.coordination import turn_policy as tp_mod

    monkeypatch.setattr(tp_mod, "llm_classify_turn_policy", lambda **_kw: None)
    settings = Settings().model_copy(
        update={
            "agent_turn_policy_classifier": "llm_v1",
            "agent_turn_policy_llm_enabled": True,
            "extraction_llm_api_key": "dummy",
        }
    )
    p = classify_turn_policy(
        question="opaque blob zzz yyy www",
        workspace_id="ws-1",
        settings=settings,
    )
    assert p.classifier == "fallback"
    assert p.reason == "classifier_llm_parse_failure"


def test_llm_v1_low_confidence_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from science_graphrag.agent.coordination import turn_policy as tp_mod

    def _fake_llm(**_kwargs):  # type: ignore[no-untyped-def]
        return (
            "research_task",
            "allow_tools",
            "retrieval_agent",
            "ok",
            "grounded_explanation",
            0.2,
        )

    monkeypatch.setattr(tp_mod, "llm_classify_turn_policy", _fake_llm)
    settings = Settings().model_copy(
        update={
            "agent_turn_policy_classifier": "llm_v1",
            "agent_turn_policy_llm_enabled": True,
            "extraction_llm_api_key": "dummy",
            "agent_turn_policy_confidence_threshold": 0.65,
        }
    )
    p = classify_turn_policy(
        question="Tell me about opaque topic xyz",
        workspace_id="ws-1",
        settings=settings,
    )
    assert p.classifier == "fallback"
    assert p.tool_policy == "clarify"
    assert p.reason == "low_confidence_clarify"
    assert p.confidence == 0.2


def test_hybrid_v1_calls_llm_on_fuzzy_rules_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    from science_graphrag.agent.coordination import turn_policy as tp_mod

    def _fake_llm(**_kwargs):  # type: ignore[no-untyped-def]
        return ("small_talk", "no_tools", "writer_agent", "llm_override", "chat", 0.92)

    monkeypatch.setattr(tp_mod, "llm_classify_turn_policy", _fake_llm)
    settings = Settings().model_copy(
        update={
            "agent_turn_policy_classifier": "hybrid_v1",
            "agent_turn_policy_llm_enabled": True,
            "extraction_llm_api_key": "dummy",
            "agent_turn_policy_confidence_threshold": 0.65,
        }
    )
    p = classify_turn_policy(
        question="Solve this clearly: 2+2?",
        workspace_id="ws-1",
        settings=settings,
    )
    assert p.classifier == "llm"
    assert p.conversation_intent == "small_talk"
    assert p.tool_policy == "no_tools"
    assert p.confidence == 0.92


def test_hybrid_v1_skips_llm_for_obvious_greeting(monkeypatch: pytest.MonkeyPatch) -> None:
    from science_graphrag.agent.coordination import turn_policy as tp_mod

    called: list[int] = []

    def _fake_llm(**_kwargs):  # type: ignore[no-untyped-def]
        called.append(1)
        return (
            "research_task",
            "allow_tools",
            "retrieval_agent",
            "should_not_use",
            "grounded_explanation",
            0.99,
        )

    monkeypatch.setattr(tp_mod, "llm_classify_turn_policy", _fake_llm)
    settings = Settings().model_copy(
        update={
            "agent_turn_policy_classifier": "hybrid_v1",
            "agent_turn_policy_llm_enabled": True,
            "extraction_llm_api_key": "dummy",
        }
    )
    p = classify_turn_policy(question="привет", workspace_id="ws-1", settings=settings)
    assert p.classifier == "deterministic"
    assert not called


@pytest.mark.parametrize(
    ("question", "workspace_id", "expect_tools"),
    [
        ("приведи цитату из статьи про BERT", "ws-1", "allow_tools"),
        ("GOST bibliography export for these works", "ws-1", "allow_tools"),
        ("Who cited paper A after 2020 in this workspace?", "ws-1", "allow_tools"),
        ("Suggest a new research idea based on gaps in the corpus", "ws-1", "allow_tools"),
    ],
)
def test_rules_v0_researchish_routes_allow_tools(
    question: str,
    workspace_id: str,
    expect_tools: str,
) -> None:
    p = classify_turn_policy(question=question, workspace_id=workspace_id)
    assert p.tool_policy == expect_tools
    assert p.conversation_intent == "research_task"


def test_initial_debug_emits_classifier_fallback_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "science_graphrag.config.get_settings",
        lambda: Settings().model_copy(
            update={
                "agent_turn_policy_classifier": "llm_v1",
                "agent_turn_policy_llm_enabled": True,
                "extraction_llm_api_key": "",
            }
        ),
    )
    st = build_initial_agent_state(
        question="opaque blob zzz yyy www",
        workspace_id="ws-1",
        max_tool_calls=3,
        agent_runtime="langgraph_v2",
    )
    dev = list(st.get("debug_events") or [])
    types = [e.get("type") for e in dev if isinstance(e, dict)]
    assert "intent_classified" in types
    assert "warning" in types
    warn = next(e for e in dev if isinstance(e, dict) and e.get("type") == "warning")
    assert warn.get("code") == "coordinator_classifier_fallback"
