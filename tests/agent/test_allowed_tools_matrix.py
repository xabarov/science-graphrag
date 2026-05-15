"""Tests for optional allowed-tools matrix + tool execution wrapper."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from langchain_core.tools import tool

from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.tool_execution_pipeline import (
    apply_allowed_tools_matrix,
    build_tool_execution_node,
)
from science_graphrag.config import Settings


def _named_tool(name: str):
    @tool(name)
    def _t(x: str = "") -> dict:
        """Test stub tool."""
        return {"row_count": 0}

    return _t


def test_apply_allowed_tools_matrix_filters_by_always_denylist() -> None:
    tools = [_named_tool("idea_search"), _named_tool("final_answer")]
    st = Settings(
        agent_allowed_tools_matrix_enabled=True,
        agent_tool_denylist_always=["idea_search"],
    )
    state = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=st,
    )
    out, meta = apply_allowed_tools_matrix(tools, settings=st, state=state)
    names = {getattr(t, "name", "") for t in out}
    assert "idea_search" not in names
    assert "final_answer" in names
    assert meta.get("removed")


def test_react_bound_tool_names_denies_calls_outside_shortlist() -> None:
    """Single-agent ReAct: ToolNode must respect ``metadata.react_bound_tool_names``."""

    @tool("idea_search")
    def idea_search(x: str = "") -> dict:
        """Stub."""
        return {"row_count": 0}

    @tool("final_answer")
    def final_answer(x: str = "") -> dict:
        """Stub."""
        return {"row_count": 0}

    st = Settings.model_construct()
    state = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=st,
    )
    meta = dict(state.get("metadata") or {})
    meta["react_bound_tool_names"] = ["final_answer"]
    state2 = {**state, "metadata": meta}
    tools_node = build_tool_execution_node(tools=[idea_search, final_answer], settings=st)
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "idea_search", "id": "t1", "args": {}}],
    )
    out = tools_node({**state2, "messages": [ai]}, None)
    msgs = out.get("messages") or []
    assert msgs

    body = json.loads(str(getattr(msgs[0], "content", "") or ""))
    assert body.get("error") == "permission_denied"
    assert "not_in_bound_tool_surface" in str(body.get("reason") or "")


def test_turn_tool_denylist_denies_named_tools() -> None:
    @tool("web_search")
    def web_search(x: str = "") -> dict:
        """Stub web search."""
        return {"ok": True}

    st = Settings.model_construct()
    state = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=st,
        turn_tool_denylist=["web_search"],
    )
    tools_node = build_tool_execution_node(tools=[web_search], settings=st)
    ai = AIMessage(
        content="",
        tool_calls=[{"name": "web_search", "id": "t1", "args": {}}],
    )
    out = tools_node({**state, "messages": [ai]}, None)
    msgs = out.get("messages") or []
    assert msgs
    body = json.loads(str(getattr(msgs[0], "content", "") or ""))
    assert body.get("error") == "permission_denied"
    assert "turn_tool_denylist" in str(body.get("reason") or "")


def test_apply_allowed_tools_matrix_filters_turn_tool_denylist() -> None:
    tools = [_named_tool("arxiv_fetch"), _named_tool("read_external_pdf")]
    st = Settings(
        agent_allowed_tools_matrix_enabled=True,
    )
    state = build_initial_agent_state(
        question="hi",
        workspace_id=None,
        max_tool_calls=4,
        agent_runtime="langgraph_research_v1",
        settings=st,
        turn_tool_denylist=["arxiv_fetch"],
    )
    out, meta = apply_allowed_tools_matrix(tools, settings=st, state=state)
    names = {getattr(t, "name", "") for t in out}
    assert "arxiv_fetch" not in names
    assert "read_external_pdf" in names
    removed = list(meta.get("removed") or [])
    assert any(
        isinstance(row, dict)
        and row.get("tool") == "arxiv_fetch"
        and row.get("reason") == "turn_tool_denylist"
        for row in removed
    )
