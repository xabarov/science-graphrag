"""Tests for ReAct specialist debug_events merge helper."""

from __future__ import annotations

from science_graphrag.agent.graph.nodes.retrieval_subgraph import merge_react_subgraph_debug_events


def test_merge_react_subgraph_debug_events_includes_subgraph_tail() -> None:
    meta = {"matched": ["call_mcp_tool"], "reason": "test", "skipped": False}
    mtx = {"skipped": True}
    subgraph = {
        "debug_events": [
            {"type": "tool_execution", "phase": "post_hooks", "ok": True},
            {"type": "mcp_audit", "phase": "call", "server": "smoke", "ok": True},
        ],
    }
    events = merge_react_subgraph_debug_events(
        specialist="retrieval_agent",
        tool_search_meta=meta,
        permissions_matrix=mtx,
        subgraph_state=subgraph,
        extra_events=[{"type": "fork", "ok": True}],
    )
    types = [e.get("type") for e in events]
    assert types[0] == "tool_search_result"
    assert "tool_permissions" not in types
    assert "tool_execution" in types
    assert "mcp_audit" in types
    assert types[-1] == "fork"
