"""Shared micro-helpers for ReAct-style subagent runtimes."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage


def permission_denied_in_messages(messages: list[Any]) -> bool:
    """Return True when any ToolMessage payload signals permission_denied."""
    for msg in messages:
        if not isinstance(msg, ToolMessage):
            continue
        raw = getattr(msg, "content", None)
        if not isinstance(raw, str):
            continue
        try:
            data = json.loads(raw)
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("error") == "permission_denied":
            return True
    return False


def last_assistant_text(messages: list[Any]) -> str:
    """Return latest non-empty AI assistant text from message history."""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage):
            text = str(msg.content or "").strip()
            if text:
                return text
    return ""


def fanout_suffixes(
    *,
    max_fan: int,
    variant_prompt_suffixes: list[str] | None,
    defaults: list[str],
) -> list[str]:
    """Resolve fanout suffixes from explicit variants or deterministic defaults."""
    if variant_prompt_suffixes:
        return list(variant_prompt_suffixes)[:max_fan]
    if max_fan > 1:
        return list(defaults)[:max_fan]
    return [""]


__all__ = ["fanout_suffixes", "last_assistant_text", "permission_denied_in_messages"]
