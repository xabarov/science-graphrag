"""Normalize LLM tool-call names before ToolNode execution (strip padded names)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState


def normalize_tool_call_name(name: str | None) -> str:
    """Strip whitespace from tool names so registry lookup succeeds."""
    return str(name or "").strip()


def normalize_tool_call_dict(tool_call: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of a tool_call dict with trimmed ``name`` when present."""
    if not isinstance(tool_call, dict):
        return tool_call
    out = dict(tool_call)
    raw = out.get("name")
    if isinstance(raw, str):
        out["name"] = normalize_tool_call_name(raw)
    return out


def normalize_ai_message_tool_calls(msg: AIMessage) -> AIMessage:
    """Return a copy of ``msg`` with every dict ``tool_calls[i].name`` trimmed."""
    tool_calls = getattr(msg, "tool_calls", None) or []
    if not tool_calls:
        return msg
    normalized: list[Any] = []
    for tc in tool_calls:
        if isinstance(tc, dict):
            normalized.append(normalize_tool_call_dict(tc))
        else:
            normalized.append(tc)
    return msg.model_copy(update={"tool_calls": normalized})


def state_with_normalized_last_ai_tool_calls(state: AgentState) -> AgentState:
    """Copy state with last AIMessage tool_calls trimmed (ToolNode reads the tail)."""
    messages = list(state.get("messages") or [])
    if not messages:
        return state
    last = messages[-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        fixed = normalize_ai_message_tool_calls(last)
        return {**state, "messages": [*messages[:-1], fixed]}
    return state


def build_normalized_tool_node_executor(
    tools: list[BaseTool],
) -> Callable[[AgentState, Any | None], Any]:
    """Return a LangGraph node callable that trims tool names before ``ToolNode`` runs."""
    inner = ToolNode(tools)

    def tools_node(state: AgentState, config: Any | None = None) -> Any:
        st = state_with_normalized_last_ai_tool_calls(state)
        if config is None:
            return inner.invoke(st)
        return inner.invoke(st, config)

    return tools_node
