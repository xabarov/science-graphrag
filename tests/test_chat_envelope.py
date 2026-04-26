"""Tests for agent chat envelope builder (Wave A CH1)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from science_graphrag.agent.chat_envelope import build_chat_envelope
from science_graphrag.agent.graph.state import AgentState


def test_build_chat_envelope_merges_inventory_from_specialist_results() -> None:
    state: AgentState = {
        "messages": [HumanMessage(content="list papers")],
        "workspace_id": "ws1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {},
        "specialist_results": {
            "retrieval_agent": [
                {"inventory": {"papers": [{"work_id": "w1", "title": "T"}]}, "row_count": 1},
            ],
        },
        "current_specialist": None,
        "routing_log": [],
        "debug_events": [],
    }
    trace = [{"step": 1, "tool": "workspace_list_papers", "args_summary": {}, "row_count": 1}]
    env = build_chat_envelope(
        state=state,
        answer="ok",
        citations=[],
        tool_trace=trace,  # type: ignore[arg-type]
        answer_class_hint=None,
    )
    assert env.get("answer_class") == "inventory"
    assert env.get("inventory", {}).get("papers")
