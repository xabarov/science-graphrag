"""Unit tests for partial-state checkpoint + deadline salvage in runtime."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.graph.partial_state_checkpoint import (
    clear_for_tests,
    pop_latest_partial_state,
    record_partial_state,
)


def test_record_and_pop_round_trip() -> None:
    clear_for_tests()
    state = {
        "messages": [HumanMessage(content="hello")],
        "metadata": {"parent_turn_id": "tid-123"},
    }
    record_partial_state(state)
    out = pop_latest_partial_state("tid-123")
    assert out is not None
    assert isinstance(out.get("messages"), list)
    # Pop again — must be empty (no second snapshot).
    assert pop_latest_partial_state("tid-123") is None


def test_record_without_parent_turn_id_is_noop() -> None:
    clear_for_tests()
    record_partial_state({"messages": [], "metadata": {}})
    record_partial_state({"messages": [], "metadata": {"parent_turn_id": ""}})
    record_partial_state({})
    assert pop_latest_partial_state(None) is None
    assert pop_latest_partial_state("") is None


def test_record_overwrites_with_latest_snapshot() -> None:
    clear_for_tests()
    record_partial_state(
        {
            "messages": [HumanMessage(content="first")],
            "metadata": {"parent_turn_id": "tid-X"},
        }
    )
    record_partial_state(
        {
            "messages": [HumanMessage(content="second")],
            "metadata": {"parent_turn_id": "tid-X"},
        }
    )
    out = pop_latest_partial_state("tid-X")
    assert out is not None
    assert "second" in str(out["messages"][0].content)


def test_supervisor_node_records_partial_state_for_each_hop(monkeypatch) -> None:
    """``supervisor_node`` must call ``record_partial_state`` so the runtime
    can salvage the latest accumulated state if the global deadline fires
    mid-turn. We don't run a real graph here — we assert the seam directly.
    """

    clear_for_tests()
    captured: list[str | None] = []

    def _spy(state: dict[str, Any]) -> None:
        meta = state.get("metadata") or {}
        captured.append(str(meta.get("parent_turn_id") or "") or None)

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.record_partial_state",
        _spy,
    )

    # Build a minimal state and feed it to the supervisor node directly.
    from science_graphrag.agent.graph.supervisor import build_supervisor_graph

    class _FakeRouter:
        def invoke(self, _messages):
            return AIMessage(content="writer_agent")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda _settings: _FakeRouter(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.retrieval_agent.build_chat_model",
        lambda _settings: _FakeSpecialist(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.graph_agent.build_chat_model",
        lambda _settings: _FakeSpecialist(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.writer_agent.build_chat_model",
        lambda _settings: _FakeSpecialist(),
    )

    settings = MagicMock()
    settings.agent_max_tool_calls = 4
    settings.agent_runtime = "langgraph_supervisor_v3"
    settings.agent_supervisor_recursion_limit = 8
    settings.agent_semantic_query_fast_route = False
    settings.agent_route_plan_enabled = False
    settings.agent_supervisor_replan_only_llm_enabled = False
    settings.agent_route_plan_post_retrieval_handoff_enabled = False
    settings.agent_supervisor_max_rounds = 4

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()

    graph = build_supervisor_graph(stores, settings)
    initial = {
        "messages": [HumanMessage(content="hi")],
        "workspace_id": "ws-1",
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 4,
        "metadata": {
            "parent_turn_id": "checkpoint-test-1",
            "agent_runtime": "langgraph_supervisor_v3",
            "agent_max_tool_calls": 4,
            "raw_user_question": "hi",
            "turn_policy": {"tool_policy": "allow_tools", "route_hint": ""},
        },
        "specialist_results": {},
        "specialist_results_v3": {"merge": {}, "legs": []},
        "current_specialist": None,
        "routing_log": [],
        "answer_class": "grounded_explanation",
        "history_digest": [],
        "session_summary": "",
    }
    graph.invoke(initial)
    assert "checkpoint-test-1" in captured
