"""Shared rules for when the ReAct graph must nudge toward ``final_answer`` (P0 contract)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name

# Tools excluded when determining the "last meaningful catalog step" (routing / session noise).
TRACE_META_TOOLS_LAST = frozenset(
    {
        "session_init",
        "route_to_specialist",
        "coordinator_gate",
    },
)


def last_executed_catalog_tool_name(tool_trace: list[Any]) -> str | None:
    """Last tool in trace that represents an actual catalog call (not routing meta)."""
    last: str | None = None
    for entry in tool_trace:
        name = getattr(entry, "tool", None) if not isinstance(entry, dict) else entry.get("tool")
        if not name or not str(name).strip():
            continue
        s = str(name).strip()
        if s in TRACE_META_TOOLS_LAST:
            continue
        last = s
    return last


def has_completed_final_answer_tool(messages: list[Any]) -> bool:
    """True if some ``final_answer`` tool call has a ToolMessage JSON body with non-empty answer."""
    for i, msg in enumerate(messages):
        if not isinstance(msg, AIMessage):
            continue
        for tc in getattr(msg, "tool_calls", None) or []:
            if normalize_tool_call_name(str(tc.get("name") or "")) != "final_answer":
                continue
            call_id = tc.get("id")
            for follow in messages[i + 1 :]:
                if not isinstance(follow, ToolMessage):
                    continue
                if getattr(follow, "tool_call_id", None) != call_id:
                    continue
                raw = follow.content
                if not isinstance(raw, str):
                    continue
                try:
                    data = json.loads(raw)
                except Exception:  # noqa: BLE001
                    continue
                if not isinstance(data, dict):
                    continue
                ans = data.get("answer")
                if isinstance(ans, str) and ans.strip():
                    return True
            args = tc.get("args")
            args_dict = args if isinstance(args, dict) else {}
            ans_from_args = args_dict.get("answer")
            if isinstance(ans_from_args, str) and ans_from_args.strip():
                return True
    return False


def _tool_policy_is_allow_tools(meta: dict[str, Any]) -> bool:
    tp = meta.get("turn_policy")
    if isinstance(tp, dict):
        pol = str(tp.get("tool_policy") or "allow_tools").strip()
    else:
        pol = "allow_tools"
    return pol == "allow_tools"


def needs_final_answer_nudge(state: dict[str, Any]) -> bool:
    """Whether to insert a one-shot reminder before ending the single-agent ReAct turn.

    When the last model message has no ``tool_calls`` but ``collect_tool_trace`` shows a catalog
    tool whose last non-meta step is not ``final_answer``, route to ``final_answer_nudge`` instead
    of ``END`` (once per turn via ``metadata.final_answer_nudge_used``).
    """
    meta = state.get("metadata") or {}
    if not isinstance(meta, dict) or meta.get("final_answer_nudge_used"):
        return False
    if not _tool_policy_is_allow_tools(meta):
        return False
    messages = list(state.get("messages") or [])
    last = messages[-1] if messages else None
    if not isinstance(last, AIMessage) or getattr(last, "tool_calls", None):
        return False
    trace = collect_tool_trace(state)  # type: ignore[arg-type]
    last_tool = last_executed_catalog_tool_name(trace)
    return bool(last_tool and last_tool != "final_answer")


__all__ = [
    "TRACE_META_TOOLS_LAST",
    "has_completed_final_answer_tool",
    "last_executed_catalog_tool_name",
    "needs_final_answer_nudge",
]
