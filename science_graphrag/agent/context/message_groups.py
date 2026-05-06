"""LangChain message grouping for compaction / PTL-style truncation (Epic A1).

API-round grouping follows the roadmap contract: preamble (group 0) + each assistant
message block until the next assistant message. Dropping whole tail groups preserves
``AIMessage.tool_calls`` ↔ ``ToolMessage`` adjacency when truncating from the head.
"""

from __future__ import annotations

import logging
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage

logger = logging.getLogger(__name__)


def tool_call_entry_id(entry: Any) -> str:
    """Normalize tool call id from dict-shaped or object-shaped LangChain entries."""
    if isinstance(entry, dict):
        return str(entry.get("id") or "")
    return str(getattr(entry, "id", "") or "")


def group_messages_by_api_round(messages: Sequence[BaseMessage]) -> list[list[BaseMessage]]:
    """Split messages into API-round groups (preamble + assistant-led segments)."""
    msgs = list(messages)
    if not msgs:
        return []
    first_ai = None
    for i, m in enumerate(msgs):
        if isinstance(m, AIMessage):
            first_ai = i
            break
    if first_ai is None:
        return [msgs]
    groups: list[list[BaseMessage]] = []
    if first_ai > 0:
        groups.append(msgs[:first_ai])
    start = first_ai
    while start < len(msgs):
        if not isinstance(msgs[start], AIMessage):
            start += 1
            continue
        end = start + 1
        while end < len(msgs) and not isinstance(msgs[end], AIMessage):
            end += 1
        groups.append(msgs[start:end])
        start = end
    return groups


def _integrity_ai_tool_calls(msgs: list[BaseMessage]) -> list[str]:
    issues: list[str] = []
    for i, msg in enumerate(msgs):
        if not isinstance(msg, AIMessage):
            continue
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            continue
        expected_ids = {tool_call_entry_id(c) for c in calls}
        expected_ids.discard("")
        if not expected_ids:
            continue
        j = i + 1
        seen: set[str] = set()
        while j < len(msgs) and isinstance(msgs[j], ToolMessage):
            tid = str(getattr(msgs[j], "tool_call_id", "") or "")
            if tid:
                seen.add(tid)
            j += 1
        missing = expected_ids - seen
        if missing:
            issues.append(
                f"AIMessage@{i}: tool_calls without matching ToolMessage ids {sorted(missing)}"
            )
    return issues


def _integrity_tool_messages(msgs: list[BaseMessage]) -> list[str]:
    issues: list[str] = []
    for i, msg in enumerate(msgs):
        if not isinstance(msg, ToolMessage):
            continue
        tid = str(getattr(msg, "tool_call_id", "") or "")
        if not tid:
            issues.append(f"ToolMessage@{i}: empty tool_call_id")
            continue
        prev_ai: AIMessage | None = None
        for k in range(i - 1, -1, -1):
            if isinstance(msgs[k], AIMessage):
                prev_ai = msgs[k]
                break
        if prev_ai is None:
            issues.append(f"ToolMessage@{i}: no preceding AIMessage for tool_call_id={tid!r}")
            continue
        ids = {tool_call_entry_id(c) for c in (getattr(prev_ai, "tool_calls", None) or [])}
        ids.discard("")
        if tid not in ids:
            issues.append(
                f"ToolMessage@{i}: tool_call_id={tid!r} not in nearest AIMessage.tool_calls"
            )
    return issues


def validate_tool_message_integrity(messages: Sequence[BaseMessage]) -> list[str]:
    """Return human-readable integrity violations (empty list = OK)."""
    msgs = list(messages)
    return _integrity_ai_tool_calls(msgs) + _integrity_tool_messages(msgs)


def drop_oldest_api_round_groups(
    messages: Sequence[BaseMessage],
    *,
    groups_to_drop: int,
) -> list[BaseMessage]:
    """Remove the first ``groups_to_drop`` non-preamble API-round groups, then flatten."""
    groups = group_messages_by_api_round(messages)
    if groups_to_drop <= 0 or len(groups) <= 1:
        return list(messages)
    preamble, rest = groups[0], groups[1:]
    if groups_to_drop >= len(rest):
        merged = [preamble]
    else:
        merged = [preamble, *rest[groups_to_drop:]]
    out: list[BaseMessage] = []
    for g in merged:
        out.extend(g)
    viol = validate_tool_message_integrity(out)
    if viol:
        logger.debug("tool integrity after PTL drop: %s", viol)
    return out


def messages_fit_token_budget(
    messages: Sequence[BaseMessage],
    *,
    max_tokens: int,
    approx_chars_per_token: int = 4,
) -> bool:
    """Cheap char-length proxy for whether the message list fits a token budget."""
    total = 0
    for m in messages:
        c = getattr(m, "content", "") or ""
        if isinstance(c, str):
            total += max(1, len(c) // max(1, approx_chars_per_token))
        elif isinstance(c, list):
            total += max(1, len(str(c)) // max(1, approx_chars_per_token))
        else:
            total += max(1, len(str(c)) // max(1, approx_chars_per_token))
    return total <= max_tokens
