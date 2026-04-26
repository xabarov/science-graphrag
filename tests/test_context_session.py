"""Session store + turn digests (CH4)."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.post_turn import apply_turn_digest_to_thread
from science_graphrag.agent.context.session_backend import set_session_memory_backend
from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    format_user_with_memory,
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


class _RecordingBackend:
    """Minimal ``SessionMemoryBackend`` for wiring tests."""

    def __init__(self) -> None:
        self.turns: list[tuple[str, dict[str, Any], str | None]] = []

    def get_session_copy(self, _thread_id: str) -> dict[str, Any]:
        return {"digests": [], "session_summary": "", "capsules": {}}

    def update_after_turn(
        self, thread_id: str, *, turn_digest: dict[str, Any], workspace_id: str | None = None
    ) -> str:
        self.turns.append((thread_id, dict(turn_digest), workspace_id))
        return "ok"

    def clear_all(self) -> None:
        self.turns.clear()


def test_format_user_with_memory_includes_workspace_capsule() -> None:
    s = format_user_with_memory(
        question="List papers",
        session_summary="",
        history_digest=[],
        workspace_capsule={"workspace_id": "w1", "recent_intents": ["prior q"]},
    )
    assert "<workspace_capsule>" in s
    assert "workspace_id=w1" in s
    assert "prior q" in s
    assert "List papers" in s


def test_workspace_capsule_roundtrip() -> None:
    try:
        tid = "t_capsule_ws"
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": "q about papers",
                "answer_excerpt": "a",
                "answer_class": "x",
                "tools_used": [],
            },
            workspace_id="ws-uuid-1",
        )
        ent = get_session_for_thread(tid)
        wc = (ent.get("capsules") or {}).get("workspace")
        assert isinstance(wc, dict)
        assert wc.get("workspace_id") == "ws-uuid-1"
        assert "q about papers" in (wc.get("recent_intents") or [])
    finally:
        clear_session_store_for_tests()


def test_set_session_memory_backend_custom_protocol() -> None:
    rec = _RecordingBackend()
    set_session_memory_backend(rec)  # type: ignore[arg-type]
    try:
        update_session_after_turn(
            "tid_custom",
            turn_digest={"user_intent": "u", "answer_excerpt": "a"},
        )
        assert len(rec.turns) == 1
        assert rec.turns[0][0] == "tid_custom"
        assert rec.turns[0][2] is None
    finally:
        set_session_memory_backend(None)
        clear_session_store_for_tests()
