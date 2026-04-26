"""Thread-scoped session memory (CH4) — delegates to ``session_backend``."""

from __future__ import annotations

import json
from typing import Any

from science_graphrag.agent.context.session_backend import get_session_memory_backend


def get_session_for_thread(thread_id: str) -> dict[str, Any]:
    """Return a copy of session payload for a thread (digests, session_summary)."""
    return get_session_memory_backend().get_session_copy(thread_id)


def update_session_after_turn(
    thread_id: str,
    *,
    turn_digest: dict[str, Any],
    workspace_id: str | None = None,
) -> str:
    """Append digest and recompute session_summary. Returns the new summary text."""
    return get_session_memory_backend().update_after_turn(
        thread_id, turn_digest=turn_digest, workspace_id=workspace_id
    )


def clear_session_store_for_tests() -> None:
    """Test helper: clear all stored sessions."""
    get_session_memory_backend().clear_all()


def format_user_with_memory(
    *,
    question: str,
    session_summary: str,
    history_digest: list[dict[str, Any]],
    workspace_capsule: dict[str, Any] | None = None,
) -> str:
    """Build the first user message, optionally prefixing server/client memory (CH4+CH5)."""
    parts: list[str] = []
    ss = (session_summary or "").strip()
    if ss:
        parts.append(f"<session_memory>\n{ss}\n</session_memory>")
    wc = workspace_capsule if isinstance(workspace_capsule, dict) else None
    wid = str(wc.get("workspace_id") or "").strip() if wc else ""
    if wid:
        lines = [f"workspace_id={wid}"]
        for it in (wc.get("recent_intents") or [])[-3:]:
            s = str(it).strip()
            if s:
                lines.append(f"- {s}")
        parts.append("<workspace_capsule>\n" + "\n".join(lines) + "\n</workspace_capsule>")
    if history_digest:
        try:
            blob = json.dumps(history_digest, ensure_ascii=False)[:8000]
        except Exception:  # noqa: BLE001
            blob = str(history_digest)[:8000]
        parts.append(f"<client_history_digest>\n{blob}\n</client_history_digest>")
    if parts:
        parts.append("")
    parts.append(question)
    return "\n".join(parts)
