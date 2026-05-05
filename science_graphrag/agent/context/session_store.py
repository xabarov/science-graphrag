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
    discovered_tools_carryover_enabled: bool = True,
    discovered_tools_carryover_cap: int = 24,
) -> str:
    """Append digest and recompute session_summary. Returns the new summary text."""
    return get_session_memory_backend().update_after_turn(
        thread_id,
        turn_digest=turn_digest,
        workspace_id=workspace_id,
        discovered_tools_carryover_enabled=discovered_tools_carryover_enabled,
        discovered_tools_carryover_cap=discovered_tools_carryover_cap,
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
    discovered_tools_capsule: dict[str, Any] | None = None,
    away_recap_lines: list[str] | None = None,
    active_workspace_id: str | None = None,
) -> str:
    """Build the first user message, optionally prefixing server/client memory (CH4+CH5).

    ``active_workspace_id`` is the API request workspace scope (always inject when set) so
    tool-calling models see the UUID even before a thread workspace capsule exists.
    """
    parts: list[str] = []
    away_lines = [str(x).strip() for x in (away_recap_lines or []) if str(x).strip()]
    if away_lines:
        parts.append("<away_recap>\n" + "\n".join(f"- {x}" for x in away_lines) + "\n</away_recap>")
    ss = (session_summary or "").strip()
    if ss:
        parts.append(f"<session_memory>\n{ss}\n</session_memory>")
    aw = str(active_workspace_id or "").strip()
    if aw:
        parts.append(f"<active_workspace_id>\n{aw}\n</active_workspace_id>")
    wc = workspace_capsule if isinstance(workspace_capsule, dict) else None
    wid = str(wc.get("workspace_id") or "").strip() if wc else ""
    if wid:
        lines = [f"workspace_id={wid}"]
        for it in (wc.get("recent_intents") or [])[-3:]:
            s = str(it).strip()
            if s:
                lines.append(f"- {s}")
        parts.append("<workspace_capsule>\n" + "\n".join(lines) + "\n</workspace_capsule>")
    dc = discovered_tools_capsule if isinstance(discovered_tools_capsule, dict) else None
    rt = (
        [str(x).strip() for x in (dc.get("recent_tools") or []) if str(x).strip()]
        if dc
        else []
    )
    if rt:
        lines = ["Tools recently used in this thread (carry-over):"]
        for name in rt[-16:]:
            lines.append(f"- {name}")
        parts.append("<discovered_tools>\n" + "\n".join(lines) + "\n</discovered_tools>")
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
