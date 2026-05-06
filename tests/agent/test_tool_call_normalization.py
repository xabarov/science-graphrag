"""Regression: padded tool-call names are trimmed before ToolNode and in traces."""

from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.tracing import collect_tool_execution_steps, collect_tool_trace
from science_graphrag.agent.tool_call_normalization import (
    build_normalized_tool_node_executor,
    normalize_ai_message_tool_calls,
    normalize_tool_call_name,
    state_with_normalized_last_ai_tool_calls,
)


def test_russian_user_message_padded_tool_names_still_normalize() -> None:
    """Regression: Cyrillic user text must not block trimming tool-call names."""
    msg = AIMessage(
        content="Дай обзор воркспейса и что по бенчмаркам",
        tool_calls=[
            {"name": "  workspace_inspect  ", "id": "a", "args": {}},
            {"name": " idea_search ", "id": "b", "args": {"query": "тест"}},
        ],
    )
    out = normalize_ai_message_tool_calls(msg)
    assert out.tool_calls[0]["name"] == "workspace_inspect"
    assert out.tool_calls[1]["name"] == "idea_search"


def test_normalize_tool_call_name_strips_padding() -> None:
    assert normalize_tool_call_name("  workspace_inspect  ") == "workspace_inspect"
    assert normalize_tool_call_name(" find_works ") == "find_works"
    assert normalize_tool_call_name(" idea_search ") == "idea_search"


def test_normalize_ai_message_tool_calls() -> None:
    msg = AIMessage(
        content="",
        tool_calls=[
            {"name": "  workspace_inspect  ", "id": "1", "args": {}},
            {"name": " idea_search ", "id": "2", "args": {"q": "x"}},
        ],
    )
    out = normalize_ai_message_tool_calls(msg)
    assert out.tool_calls[0]["name"] == "workspace_inspect"
    assert out.tool_calls[1]["name"] == "idea_search"


def test_collect_tool_trace_uses_normalized_names() -> None:
    """Trace collector should not persist padded tool ids."""
    msg = AIMessage(
        content="",
        tool_calls=[{"name": " workspace_inspect ", "id": "tc1", "args": {}}],
    )
    follow = ToolMessage(content="{}", tool_call_id="tc1", name="workspace_inspect")
    state: AgentState = {"messages": [msg, follow]}
    traces = collect_tool_trace(state)
    assert any(t.get("tool") == "workspace_inspect" for t in traces)


def test_collect_tool_execution_steps_matches_tool_trace_rows() -> None:
    ai = AIMessage(
        content="",
        tool_calls=[{"name": " idea_search ", "id": "tc2", "args": {"query": "x"}}],
    )
    tool_message = ToolMessage(
        content='{"row_count": 2, "truncated": true}',
        tool_call_id="tc2",
        name="idea_search",
    )
    state: AgentState = {"messages": [ai, tool_message]}
    steps = collect_tool_execution_steps(state["messages"])
    trace = collect_tool_trace(state)
    assert len(steps) == 1
    assert steps[0]["tool"] == "idea_search"
    assert steps[0]["row_count"] == 2
    assert steps[0]["truncated"] is True
    assert len(trace) == 1
    assert trace[0]["tool"] == steps[0]["tool"]
    assert trace[0]["row_count"] == steps[0]["row_count"]


def test_build_normalized_tool_node_executor_invokes_with_trimmed_names() -> None:
    @tool
    def workspace_inspect(workspace_id: str = "") -> str:
        """Stub workspace inspect for ToolNode lookup."""
        _ = workspace_id
        return '{"ok": true}'

    tools = [workspace_inspect]
    executor = build_normalized_tool_node_executor(tools)
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "  workspace_inspect  ", "id": "call-1", "args": {}}],
    )
    state: AgentState = {"messages": [ai], "budget_remaining": 5}
    result = executor(state)
    messages = list(result.get("messages") or [])
    assert any(getattr(m, "name", None) == "workspace_inspect" for m in messages)


def test_state_with_normalized_last_ai_tool_calls() -> None:
    ai = AIMessage(content="", tool_calls=[{"name": "  foo  ", "id": "1", "args": {}}])
    state: AgentState = {"messages": [ai]}
    st = state_with_normalized_last_ai_tool_calls(state)
    last = st["messages"][-1]
    assert isinstance(last, AIMessage)
    assert last.tool_calls[0]["name"] == "foo"
