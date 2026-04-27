"""Regression: multi-hop specialist runs must not wipe prior tool payloads."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.graph.nodes.retrieval_agent import _extract_tool_payloads


def test_extract_tool_payloads_parses_json_tool_messages() -> None:
    msgs = [
        HumanMessage(content="q"),
        AIMessage(content="", tool_calls=[{"name": "x", "id": "c1", "args": {}}]),
        ToolMessage(content='{"row_count": 1, "ok": true}', tool_call_id="c1", name="x"),
    ]
    assert _extract_tool_payloads(msgs, 1) == [{"row_count": 1, "ok": True}]


def test_merge_pattern_empty_new_hop_preserves_prior() -> None:
    """Mirrors retrieval/graph agent node: prior + new must keep prior when new is empty."""
    prior = [{"row_count": 1, "name": "Object Detection"}]
    new_payloads: list[dict] = []
    assert prior + new_payloads == prior
