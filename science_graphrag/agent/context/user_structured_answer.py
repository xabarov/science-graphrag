"""Structured user answers for ``ask_user_question`` roundtrip (CH4 session_meta)."""

from __future__ import annotations

import json
import time
from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import get_session_for_thread
from science_graphrag.config import Settings


def _mismatch_events(expected_request_id: str, got_request_id: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "warning",
            "code": "user_structured_answer_mismatch",
            "expected_request_id": expected_request_id,
            "got_request_id": got_request_id or None,
        }
    ]


def _answered_debug_events(request_id: str, answer_count: int) -> list[dict[str, Any]]:
    return [
        {
            "type": "user_answered",
            "request_id": request_id,
            "answer_count": answer_count,
        }
    ]


def _structured_answer_suffix(request_id: str, answers: list[Any]) -> str:
    blob = json.dumps({"request_id": request_id, "answers": answers}, ensure_ascii=False)
    return (
        "<user_structured_answer>\n"
        f"{blob}\n"
        "</user_structured_answer>\n"
        "The user submitted structured answers to your previous multi-choice question. "
        "Continue the research task using these selections."
    )


def consume_user_structured_answer_for_thread(
    thread_id: str,
    payload: dict[str, Any] | None,
    *,
    settings: Settings,
) -> tuple[list[dict[str, Any]], str | None]:
    """If payload matches pending ask, emit debug events + user-message suffix; clear pending."""
    empty: tuple[list[dict[str, Any]], str | None] = ([], None)
    if not payload or not settings.agent_ask_user_question_tool_enabled:
        return empty
    tid = (thread_id or "").strip()
    if not tid:
        return empty
    ent = get_session_for_thread(tid)
    meta_raw = ent.get("session_meta")
    meta = meta_raw if isinstance(meta_raw, dict) else {}
    pending = meta.get("pending_user_question")
    if not isinstance(pending, dict):
        return empty
    prid = str(pending.get("request_id") or "").strip()
    if not prid:
        return empty
    rid = str(payload.get("request_id") or "").strip()
    if rid != prid:
        return (_mismatch_events(prid, rid), None)

    raw_answers = payload.get("answers")
    answers: list[Any] = raw_answers if isinstance(raw_answers, list) else []
    audit = {"ts": time.time(), "request_id": prid, "answers": answers}
    backend = get_session_memory_backend()
    prev_audit = meta.get("user_question_audit") or []
    audit_tail = [dict(x) for x in prev_audit if isinstance(x, dict)][-19:] + [audit]
    backend.patch_session_meta(
        tid,
        patch={"pending_user_question": None, "user_question_audit": audit_tail},
    )
    return (
        _answered_debug_events(prid, len(answers)),
        _structured_answer_suffix(prid, answers),
    )
