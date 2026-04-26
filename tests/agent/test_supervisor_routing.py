from __future__ import annotations

import typing
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage


def test_supervisor_routes_to_retrieval_agent(monkeypatch) -> None:
    class _FakeRouter:
        def invoke(self, _messages):
            return AIMessage(content="retrieval_agent")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _FakeRouter(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.retrieval_agent.build_chat_model",
        lambda settings: _FakeSpecialist(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.graph_agent.build_chat_model",
        lambda settings: _FakeSpecialist(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.writer_agent.build_chat_model",
        lambda settings: _FakeSpecialist(),
    )

    from science_graphrag.agent.graph.supervisor import build_supervisor_graph

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()

    settings = MagicMock()
    settings.agent_max_tool_calls = 8
    settings.agent_runtime = "langgraph_supervisor_v1"
    settings.agent_supervisor_recursion_limit = 12
    settings.agent_semantic_query_fast_route = False

    graph = build_supervisor_graph(stores, settings)
    assert graph is not None


def test_agent_state_has_routing_fields() -> None:
    from science_graphrag.agent.graph.state import AgentState

    hints = typing.get_type_hints(AgentState)
    assert "specialist_results" in hints
    assert "current_specialist" in hints
    assert "routing_log" in hints
    assert "debug_events" in hints
    assert "thread_id" in hints
    assert "session_summary" in hints
    assert "answer_class" in hints
    assert "history_digest" in hints


def test_score_agent_case_specialist_sequence() -> None:
    from eval.agent_tools.metrics import score_agent_case

    result = {
        "answer": "test",
        "citations": [],
        "tool_trace": [{"tool": "idea_search"}, {"tool": "final_answer"}],
        "routing_log": [
            {"from": "supervisor", "to": "retrieval_agent"},
            {"from": "supervisor", "to": "writer_agent"},
        ],
    }
    gold = {
        "expected_specialist_sequence": ["retrieval_agent", "writer_agent"],
        "expected_tool_sequence": ["idea_search", "final_answer"],
        "min_tool_call_correctness": 0.5,
        "min_specialist_sequence_match": 0.5,
    }
    scores = score_agent_case(result, gold)
    assert "specialist_sequence_match" in scores
    assert scores["specialist_sequence_match"] >= 0.9
