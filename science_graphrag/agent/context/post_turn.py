"""Shared post-turn session update (CH4) for sync JSON and SSE paths."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.session_store import update_session_after_turn
from science_graphrag.agent.context.turn_digest import build_turn_digest


def apply_turn_digest_to_thread(
    *,
    thread_id: str | None,
    raw_user_question: str,
    answer: str,
    answer_class: str,
    tool_trace: list[Any],
    workspace_id: str | None = None,
) -> str:
    """Build turn digest and update session backend. Returns new session_summary text."""
    tid = (thread_id or "").strip()
    if not tid:
        return ""
    digest = build_turn_digest(
        question=raw_user_question,
        answer=answer,
        answer_class=answer_class,
        tool_trace=tool_trace,
    )
    return update_session_after_turn(tid, turn_digest=digest, workspace_id=workspace_id)
