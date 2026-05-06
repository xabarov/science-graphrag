"""Optional compaction of older ToolMessage payloads before LLM calls (single-agent ReAct)."""

from __future__ import annotations

import json
from typing import Any, Sequence

from langchain_core.messages import BaseMessage, ToolMessage

from science_graphrag.agent.context.message_sanitizers import (
    sanitize_messages_for_react_pre_compact,
)
from science_graphrag.config import Settings

_MICRO_PLACEHOLDER: str = json.dumps(
    {
        "_microcompact": "cleared",
        "note": "Older tool result cleared after long client idle gap; recent tool rows retained.",
    },
    ensure_ascii=False,
)


def maybe_compact_agent_messages_for_react(
    messages: Sequence[BaseMessage],
    *,
    settings: Settings,
    client_idle_ms: int | None = None,
) -> tuple[list[BaseMessage], dict[str, Any]]:
    """Truncate string bodies of older ``ToolMessage`` rows to cap context growth.

    Keeps the most recent ``keep`` tool results intact; earlier tool JSON may be large
    (Cypher rows, chunk lists). Disabled unless ``agent_tool_history_compact_enabled``.

    When ``agent_tool_message_microcompact_time_trigger_enabled`` and client idle gap exceeds
    ``agent_tool_message_microcompact_time_gap_minutes``, clears **all** but the last K
    tool payloads (placeholder JSON), then applies the usual char truncation on remaining
    older rows when still over budget.

    Returns ``(messages, audit)``; ``audit`` may include telemetry keys for run_metadata.
    """

    audit: dict[str, Any] = {}
    if not settings.agent_tool_history_compact_enabled:
        return list(messages), audit

    pre_ok = bool(getattr(settings, "agent_pre_compact_sanitizers_enabled", True))
    out = sanitize_messages_for_react_pre_compact(messages, enabled=pre_ok)

    micro_on = bool(
        getattr(settings, "agent_tool_message_microcompact_time_trigger_enabled", False)
    )
    gap_min = max(1, int(getattr(settings, "agent_tool_message_microcompact_time_gap_minutes", 10)))
    keep_micro = max(
        1, int(getattr(settings, "agent_tool_message_microcompact_keep_last_k_tool_results", 3))
    )
    gap_ms = int(client_idle_ms) if client_idle_ms is not None else 0
    threshold_ms = gap_min * 60_000

    tool_indices = [i for i, m in enumerate(out) if isinstance(m, ToolMessage)]
    if micro_on and gap_ms >= threshold_ms and len(tool_indices) > keep_micro:
        keep_set = set(tool_indices[-keep_micro:])
        for i in tool_indices:
            if i in keep_set:
                continue
            msg = out[i]
            if not isinstance(msg, ToolMessage):
                continue
            out[i] = ToolMessage(
                content=_MICRO_PLACEHOLDER,
                tool_call_id=msg.tool_call_id,
                name=getattr(msg, "name", "") or "",
            )
        audit["tool_message_microcompact_triggered_count"] = 1

    keep = max(1, int(settings.agent_tool_history_compact_keep_latest_tool_messages))
    max_ch = max(400, int(settings.agent_tool_history_compact_max_tool_chars))
    tool_indices2 = [i for i, m in enumerate(out) if isinstance(m, ToolMessage)]
    if len(tool_indices2) <= keep:
        return out, audit
    for i in tool_indices2[:-keep]:
        msg = out[i]
        if not isinstance(msg, ToolMessage):
            continue
        content = msg.content
        if not isinstance(content, str) or len(content) <= max_ch:
            continue
        out[i] = ToolMessage(
            content=content[:max_ch] + "\n...[tool_payload_truncated]",
            tool_call_id=msg.tool_call_id,
            name=getattr(msg, "name", "") or "",
        )
    return out, audit
