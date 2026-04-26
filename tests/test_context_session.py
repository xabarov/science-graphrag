"""Session store + turn digests (CH4)."""

from __future__ import annotations

from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.agent.context.turn_digest import build_turn_digest
from science_graphrag.agent.trace import ToolCallTrace


def test_session_store_rolling_summary() -> None:
    try:
        tid = "t_test_thread"
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": "q1",
                "answer_excerpt": "a1",
                "answer_class": "x",
                "tools_used": [],
            },
        )
        s1 = get_session_for_thread(tid).get("session_summary") or ""
        assert "q1" in s1 and "a1" in s1
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": "q2",
                "answer_excerpt": "a2",
                "answer_class": "x",
                "tools_used": [],
            },
        )
        s2 = get_session_for_thread(tid).get("session_summary") or ""
        assert "q2" in s2
    finally:
        clear_session_store_for_tests()


def test_build_turn_digest_uses_trace() -> None:
    tr: list[ToolCallTrace] = [
        {
            "step": 1,
            "tool": "idea_search",
            "args_summary": {},
            "row_count": 1,
            "duration_ms": 0,
            "truncated": False,
            "error": None,
        }
    ]
    d = build_turn_digest(
        question="hi", answer="bye", answer_class="grounded_explanation", tool_trace=tr
    )
    assert d.get("tools_used") == ["idea_search"]


def test_apply_turn_digest_to_thread_updates_store() -> None:
    try:
        tid = "t_post_turn_apply"
        summary = apply_turn_digest_to_thread(
            thread_id=tid,
            raw_user_question="What papers?",
            answer="Two works.",
            answer_class="inventory",
            tool_trace=[],
        )
        assert isinstance(summary, str)
        assert len(summary) > 0
        ent = get_session_for_thread(tid)
        assert len(ent.get("digests") or []) >= 1
    finally:
        clear_session_store_for_tests()


def test_apply_turn_digest_no_thread_returns_empty() -> None:
    assert (
        apply_turn_digest_to_thread(
            thread_id=None,
            raw_user_question="q",
            answer="a",
            answer_class="x",
            tool_trace=[],
        )
        == ""
    )
