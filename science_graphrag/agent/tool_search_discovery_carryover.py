"""Message-history tool discovery and session carry-over for rule-based shortlist (Wave A seam)."""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool

from science_graphrag.config import Settings

# Meta / routing tools: never treat as catalog discoveries from message history (Epic C0).
_MESSAGE_DISCOVERY_EXCLUDE = frozenset(
    {
        "route_to_specialist",
        "session_init",
        "coordinator_gate",
        "coordinator_gate_v0",
    }
)


def tool_call_entry_name(tc: Any) -> str:
    """Resolve tool name from ``AIMessage.tool_calls`` entry (dict or LangChain object)."""
    if isinstance(tc, dict):
        return str(tc.get("name") or "").strip()
    return str(getattr(tc, "name", "") or "").strip()


def discovered_tool_names_from_lc_messages(
    messages: Sequence[Any] | None,
    *,
    cap: int,
) -> list[str]:
    """Collect tool names from LangGraph history in message order (deduped, capped).

    Reads ``AIMessage.tool_calls`` and ``ToolMessage.name``. Deterministic: first
    occurrence wins; caps at ``cap`` names.
    """
    if not messages or cap <= 0:
        return []
    seen: set[str] = set()
    ordered: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage):
            for tc in getattr(msg, "tool_calls", None) or []:
                name = tool_call_entry_name(tc)
                if not name or name in _MESSAGE_DISCOVERY_EXCLUDE:
                    continue
                if name not in seen:
                    seen.add(name)
                    ordered.append(name)
                if len(ordered) >= cap:
                    return ordered
        elif isinstance(msg, ToolMessage):
            name = str(getattr(msg, "name", "") or "").strip()
            if not name or name in _MESSAGE_DISCOVERY_EXCLUDE:
                continue
            if name not in seen:
                seen.add(name)
                ordered.append(name)
            if len(ordered) >= cap:
                return ordered
    return ordered


def _carryover_tool_names_from_session(session: dict[str, Any] | None, *, cap: int) -> list[str]:
    if not isinstance(session, dict):
        return []
    caps = session.get("capsules") or {}
    if not isinstance(caps, dict):
        return []
    dt = caps.get("discovered_tools")
    if not isinstance(dt, dict):
        return []
    raw = [str(x).strip() for x in (dt.get("recent_tools") or []) if str(x).strip()]
    cap_n = max(0, int(cap))
    if cap_n <= 0:
        return []
    return raw[-cap_n:]


def _merge_carryover_into_picked(
    picked: list[BaseTool],
    tools: list[BaseTool],
    carryover: list[str],
) -> list[str]:
    """Return list of carryover tool names that were merged into ``picked``."""
    if not carryover:
        return []
    have = {getattr(t, "name", "") for t in picked}
    merged: list[str] = []
    by_name = {getattr(t, "name", ""): t for t in tools}
    for nm in carryover:
        if nm in have:
            continue
        hit = by_name.get(nm)
        if hit is None:
            continue
        picked.append(hit)
        have.add(nm)
        merged.append(nm)
    return merged


def _shortlist_try_message_discovery_merge(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    lc_messages: Sequence[Any] | None,
    settings: Settings,
) -> tuple[list[str], list[str]]:
    """Merge tools discovered in LangGraph history into ``picked`` (Epic C0)."""
    if (
        lc_messages is None
        or not settings.agent_tool_search_message_discovery_enabled
        or int(settings.agent_tool_search_message_discovery_cap) <= 0
    ):
        return [], []
    names = discovered_tool_names_from_lc_messages(
        lc_messages,
        cap=int(settings.agent_tool_search_message_discovery_cap),
    )
    if not names:
        return [], []
    merged = _merge_carryover_into_picked(picked, tools, names)
    return names, merged


def shortlist_apply_discovery_and_session_carryover(
    picked: list[BaseTool],
    tools: list[BaseTool],
    *,
    lc_messages: Sequence[Any] | None,
    session: dict[str, Any] | None,
    settings: Settings,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Message-history merge then session carry-over; returns discovery + carryover lists."""
    msg_tools, msg_merged = _shortlist_try_message_discovery_merge(
        picked,
        tools,
        lc_messages=lc_messages,
        settings=settings,
    )
    carryover_names = _carryover_tool_names_from_session(
        session,
        cap=int(settings.agent_discovered_tools_carryover_max),
    )
    carry_merged: list[str] = []
    if settings.agent_discovered_tools_carryover_enabled and carryover_names:
        carry_merged = _merge_carryover_into_picked(picked, tools, carryover_names)
    return msg_tools, msg_merged, carryover_names, carry_merged


__all__ = [
    "discovered_tool_names_from_lc_messages",
    "shortlist_apply_discovery_and_session_carryover",
    "tool_call_entry_name",
]
