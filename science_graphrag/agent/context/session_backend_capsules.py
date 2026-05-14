"""Capsule merge helpers for session memory (CH4/CH5)."""

from __future__ import annotations

from typing import Any


def rolling_summary_from_digests(digests: list[dict[str, Any]]) -> str:
    window = digests[-3:]
    parts: list[str] = []
    for d in window:
        u = str(d.get("user_intent") or "")[:200]
        a = str(d.get("answer_excerpt") or "")[:300]
        if u or a:
            parts.append(f"Q: {u}\nA: {a}")
    return "\n---\n".join(parts)


def merge_workspace_capsule(
    prev: dict[str, Any] | None,
    workspace_id: str,
    turn_digest: dict[str, Any],
    digest_count: int,
) -> dict[str, Any]:
    """Compact reusable workspace capsule (CH5 v1): recent intents + id (no extra LLM)."""
    intents: list[str] = []
    if isinstance(prev, dict):
        intents = [str(x) for x in (prev.get("recent_intents") or []) if str(x).strip()]
    ui = str(turn_digest.get("user_intent") or "")[:200].strip()
    if ui:
        intents.append(ui)
    intents = intents[-5:]
    return {
        "workspace_id": workspace_id,
        "recent_intents": intents,
        "digest_count": digest_count,
    }


def merge_discovered_tools_capsule(
    prev: dict[str, Any] | None,
    turn_digest: dict[str, Any],
    *,
    cap: int,
) -> dict[str, Any]:
    """Rolling union of tool names from CH4 turn digests (Wave 3 carry-over)."""
    names: list[str] = []
    if isinstance(prev, dict):
        names = [str(x) for x in (prev.get("recent_tools") or []) if str(x).strip()]
    for nm in turn_digest.get("tools_used") or []:
        s = str(nm).strip()
        if s and s not in names:
            names.append(s)
    cap_n = max(4, int(cap))
    names = names[-cap_n:]
    return {"recent_tools": names, "source": "turn_digest_tools_used"}


def empty_session() -> dict[str, Any]:
    return {"digests": [], "session_summary": "", "capsules": {}, "session_meta": {}}


# Historical private names (tests / parity)
_rolling_summary = rolling_summary_from_digests
_merge_workspace_capsule = merge_workspace_capsule
_merge_discovered_tools_capsule = merge_discovered_tools_capsule
_empty_session = empty_session

__all__ = [
    "empty_session",
    "merge_discovered_tools_capsule",
    "merge_workspace_capsule",
    "rolling_summary_from_digests",
]
