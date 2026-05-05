"""Tests for optional allowed-tools matrix + tool execution wrapper."""

from __future__ import annotations

from unittest.mock import MagicMock

from langchain_core.tools import tool

from science_graphrag.agent.graph.state import build_initial_agent_state
from science_graphrag.agent.tool_execution_pipeline import apply_allowed_tools_matrix


def _named_tool(name: str):
    @tool(name)
    def _t(x: str = "") -> dict:
        """Test stub tool."""
        return {"row_count": 0}

    return _t


def test_apply_allowed_tools_matrix_filters_by_always_denylist() -> None:
    from science_graphrag.config import Settings

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
