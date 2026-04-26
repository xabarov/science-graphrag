"""In-process session store by thread_id (CH4 in-memory; replace with Redis later if needed)."""

from __future__ import annotations

import json
import threading
from typing import Any

_lock = threading.Lock()
_store: dict[str, dict[str, Any]] = {}


def get_session_for_thread(thread_id: str) -> dict[str, Any]:
    """Return a copy of session payload for a thread (digests, session_summary)."""
    with _lock:
        ent = _store.get(thread_id.strip())
        if not ent:
            return {"digests": [], "session_summary": ""}
        return {
            "digests": list(ent.get("digests") or []),
            "session_summary": str(ent.get("session_summary") or ""),
        }


def _rolling_summary(digests: list[dict[str, Any]]) -> str:
    window = digests[-3:]
    parts: list[str] = []
    for d in window:
        u = str(d.get("user_intent") or "")[:200]
        a = str(d.get("answer_excerpt") or "")[:300]
        if u or a:
            parts.append(f"Q: {u}\nA: {a}")
    return "\n---\n".join(parts)


def update_session_after_turn(
    thread_id: str,
    *,
    turn_digest: dict[str, Any],
) -> str:
    """Append digest and recompute session_summary. Returns the new summary text."""
    tid = (thread_id or "").strip()
    if not tid:
        return ""
    with _lock:
        ent = _store.setdefault(tid, {"digests": [], "session_summary": ""})
        digests: list[dict[str, Any]] = list(ent.get("digests") or [])
        digests.append(dict(turn_digest))
        digests = digests[-10:]
        ent["digests"] = digests
        summary = _rolling_summary(digests)
        ent["session_summary"] = summary
        return summary


def clear_session_store_for_tests() -> None:
    """Test helper: clear all stored sessions."""
    with _lock:
        _store.clear()


def format_user_with_memory(
    *,
    question: str,
    session_summary: str,
    history_digest: list[dict[str, Any]],
) -> str:
    """Build the first user message, optionally prefixing server/client memory (CH4)."""
    parts: list[str] = []
    ss = (session_summary or "").strip()
    if ss:
        parts.append(f"<session_memory>\n{ss}\n</session_memory>")
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
