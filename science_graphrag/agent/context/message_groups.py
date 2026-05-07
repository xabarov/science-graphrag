"""LangChain message grouping for compaction / PTL-style truncation (Epic A1).

API-round grouping follows the roadmap contract: preamble (group 0) + each assistant
message block until the next assistant message. Dropping whole tail groups preserves
``AIMessage.tool_calls`` ↔ ``ToolMessage`` adjacency when truncating from the head.

CH4 turn digests map to the same grouping contract for L4 PTL retries: a fixed preamble
``HumanMessage`` plus one ``AIMessage`` JSON blob per digest round (see
``digest_window_as_messages_for_api_rounds``).
"""

from __future__ import annotations

import json
import logging
from typing import Any, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage

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


_DIGEST_PREAMBLE_TEXT = "CH4_turn_digest_window_v1"


def digest_window_as_messages_for_api_rounds(
    digests: Sequence[dict[str, Any]],
) -> list[BaseMessage]:
    """Map CH4 digests to LC messages: fixed preamble + one AIMessage JSON blob per digest.

    This aligns ``drop_oldest_api_round_groups`` with "drop oldest digest rounds" for L4
    compaction PTL retries without fabricating tool adjacency.
    """
    out: list[BaseMessage] = [HumanMessage(content=_DIGEST_PREAMBLE_TEXT)]
    for d in digests:
        if not isinstance(d, dict):
            continue
        try:
            blob = json.dumps(d, ensure_ascii=False, sort_keys=True, default=str)
        except (TypeError, ValueError):
            blob = str(d)
        cap = 6000
        if len(blob) > cap:
            blob = blob[: max(cap - 12, 0)] + "\n…[truncated]"
        out.append(AIMessage(content=blob))
    return out


def drop_oldest_digest_rounds_for_ptl(
    digests: list[dict[str, Any]],
    *,
    groups_to_drop: int,
) -> list[dict[str, Any]]:
    """Drop the oldest digest rounds using API-round grouping (preamble + per-digest AI).

    Each digest is one assistant-led round after the fixed preamble (see
    ``digest_window_as_messages_for_api_rounds``). When grouping degenerates (e.g. empty
    digest list filtered to preamble-only), fall back to dropping whole digests from the
    head while keeping at least two rows so L4 can still retry.
    """
    if groups_to_drop <= 0 or not digests:
        return list(digests)
    msgs = digest_window_as_messages_for_api_rounds(digests)
    groups = group_messages_by_api_round(msgs)
    if len(groups) <= 1:
        k = min(max(0, groups_to_drop), max(0, len(digests) - 2))
        return digests[k:] if k else list(digests)
    rest = groups[1:]
    drop_n = min(max(0, groups_to_drop), len(rest))
    if drop_n <= 0:
        return list(digests)
    return digests[drop_n:]
