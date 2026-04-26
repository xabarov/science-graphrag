"""Deterministic per-turn digests (no extra LLM) for session memory (CH4)."""

from __future__ import annotations

import json
from typing import Any


def _tool_name(entry: Any) -> str | None:
    if isinstance(entry, dict):
        name = entry.get("tool")
        return str(name) if name else None
    return None


def build_turn_digest(
    *,
    question: str,
    answer: str,
    answer_class: str,
    tool_trace: list[Any] | None,
) -> dict[str, Any]:
    """Build a JSON-serializable compact digest of one completed turn."""
    names: list[str] = []
    for t in tool_trace or []:
        name = _tool_name(t)
        if not name or name in ("session_init", "route_to_specialist"):
            continue
        names.append(name)
    unique = list(dict.fromkeys(names))[:20]
    return {
        "user_intent": (question or "")[:500],
        "answer_class": (answer_class or "grounded_explanation")[:80],
        "tools_used": unique,
        "answer_excerpt": (answer or "")[:400],
    }


def turn_digest_to_json(digest: dict[str, Any]) -> str:
    return json.dumps(digest, ensure_ascii=True)
