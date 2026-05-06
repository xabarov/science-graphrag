"""Contract tests for CH4 prompt memory precedence (Epic A2)."""

from __future__ import annotations

from science_graphrag.agent.context.prompt_memory_policy import resolve_prompt_memory_policy
from science_graphrag.agent.context.session_store import format_user_with_memory
from science_graphrag.config import Settings


def test_resolve_injects_digest_and_fresh_insight() -> None:
    ent = {
        "digests": [
            {
                "user_intent": "alpha topic",
                "answer_excerpt": "a1",
                "answer_class": "x",
                "tools_used": [],
            },
            {
                "user_intent": "beta follow",
                "answer_excerpt": "a2",
                "answer_class": "x",
                "tools_used": [],
            },
        ],
        "session_summary": "rolling",
        "session_meta": {
            "turn_counter": 2,
            "thread_insight": {
                "current": "## thread_insight\nalpha topic and beta follow recap.",
                "version": 1,
                "audit": {"schema_version": "thread_insight_audit_v1", "built_at_turn_counter": 2},
            },
            "insight_circuit": {"open_until_turn": 0, "consecutive_failures": 0},
        },
    }
    st = Settings(agent_thread_insights_enabled=True, agent_thread_insights_min_digests=1)
    pm = resolve_prompt_memory_policy(session_ent=ent, settings=st)
    assert pm.last_turn_digest_text and "beta follow" in pm.last_turn_digest_text
    assert pm.thread_insight_text and "alpha topic" in pm.thread_insight_text
    assert pm.insight_fallback_reason is None
    text = format_user_with_memory(
        question="Next?",
        session_summary=pm.session_memory_text,
        history_digest=[],
        last_turn_digest_text=pm.last_turn_digest_text,
        thread_insight_text=pm.thread_insight_text,
        thread_insight_status=pm.thread_insight_status,
    )
    assert text.index("<last_turn_digest>") < text.index("<thread_insight")
    assert text.index("<thread_insight") < text.index("<session_memory>")


def test_resolve_circuit_open_skips_insight() -> None:
    ent = {
        "digests": [
            {"user_intent": "q", "answer_excerpt": "a", "answer_class": "x", "tools_used": []},
        ],
        "session_summary": "mem",
        "session_meta": {
            "turn_counter": 1,
            "insight_circuit": {"open_until_turn": 99, "consecutive_failures": 3},
            "thread_insight": {
                "current": "should not inject",
                "version": 1,
                "audit": {"built_at_turn_counter": 1},
            },
        },
    }
    st = Settings(agent_thread_insights_enabled=True)
    pm = resolve_prompt_memory_policy(session_ent=ent, settings=st)
    assert pm.thread_insight_text is None
    assert pm.insight_fallback_reason == "insight_circuit_open"


def test_resolve_stale_lag_no_insight() -> None:
    ent = {
        "digests": [
            {"user_intent": "old", "answer_excerpt": "a", "answer_class": "x", "tools_used": []},
            {
                "user_intent": "newintent",
                "answer_excerpt": "b",
                "answer_class": "x",
                "tools_used": [],
            },
        ],
        "session_summary": "rolling",
        "session_meta": {
            "turn_counter": 2,
            "thread_insight": {
                "current": "stale body",
                "version": 1,
                "audit": {"built_at_turn_counter": 1},
            },
            "insight_circuit": {"open_until_turn": 0},
        },
    }
    st = Settings(agent_thread_insights_enabled=True)
    pm = resolve_prompt_memory_policy(session_ent=ent, settings=st)
    assert pm.thread_insight_text is None
    assert pm.insight_fallback_reason == "insight_stale_lag"
