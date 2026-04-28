"""Optional compaction of older ToolMessage payloads before LLM calls (single-agent ReAct)."""

from __future__ import annotations

from typing import Sequence

from langchain_core.messages import BaseMessage, ToolMessage

from science_graphrag.config import Settings


def maybe_compact_agent_messages_for_react(
    messages: Sequence[BaseMessage],
    *,
    settings: Settings,
) -> list[BaseMessage]:
    """Truncate string bodies of older ``ToolMessage`` rows to cap context growth.

    Keeps the most recent ``keep`` tool results intact; earlier tool JSON may be large
    (Cypher rows, chunk lists). Disabled unless ``agent_tool_history_compact_enabled``.
    """

    if not settings.agent_tool_history_compact_enabled:
        return list(messages)
    out = list(messages)
    keep = max(1, int(settings.agent_tool_history_compact_keep_latest_tool_messages))
    max_ch = max(400, int(settings.agent_tool_history_compact_max_tool_chars))
    tool_indices = [i for i, m in enumerate(out) if isinstance(m, ToolMessage)]
    if len(tool_indices) <= keep:
        return out
    for i in tool_indices[:-keep]:
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
    return out
