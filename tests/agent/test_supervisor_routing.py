from __future__ import annotations

import typing
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


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


def test_supervisor_router_prompt_excludes_tool_transcript(monkeypatch) -> None:
    captured_messages = []

    class _CapturingRouter:
        def invoke(self, messages):
            captured_messages.append(list(messages))
            return AIMessage(content="writer_agent")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _CapturingRouter(),
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

    from science_graphrag.agent.graph.supervisor import _build_supervisor_route_messages

    state = {
        "messages": [
            HumanMessage(content="How is paper A related to paper B?"),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "edge_search",
                        "args": {"node_id": "paper-a"},
                        "id": "call_1",
                        "type": "tool_call",
                    }
                ],
            ),
            ToolMessage(content='{"row_count": 1}', tool_call_id="call_1", name="edge_search"),
        ],
        "metadata": {"raw_user_question": "How is paper A related to paper B?"},
        "specialist_results": {"graph_agent": [{"path_count": 1}]},
    }
    route_messages = _build_supervisor_route_messages(state)
    response = _CapturingRouter().invoke(route_messages)

    assert response.content == "writer_agent"
    assert captured_messages
    sent = captured_messages[0]
    assert all(isinstance(msg, HumanMessage) for msg in sent)
    assert len(sent) == 3
    assert "specialist_results" in sent[-1].content


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


def test_supervisor_invalid_router_token_routes_to_writer_not_retrieval(monkeypatch) -> None:
    """Garbage supervisor output must not default to retrieval_agent (Coordinator Gate hardening)."""

    class _BadRouter:
        def invoke(self, _messages):
            return AIMessage(content="I will pick retrieval_agent for you")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _BadRouter(),
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

    from science_graphrag.agent.graph.state import build_initial_agent_state
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
    state = build_initial_agent_state(
        question="Explain attention mechanism in transformers briefly",
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v1",
    )
    out = graph.invoke(state)
    routes = list(out.get("routing_log") or [])
    assert routes
    assert routes[0].get("to") == "writer_agent"


def test_supervisor_coordinator_gate_skips_llm_for_greeting(monkeypatch) -> None:
    """First-turn no_tools policy must not invoke supervisor routing LLM."""

    def _boom(*_a, **_k):
        raise AssertionError("supervisor routing LLM must not be called")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: type("_B", (), {"invoke": staticmethod(_boom)})(),
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

    from science_graphrag.agent.graph.state import build_initial_agent_state
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
    state = build_initial_agent_state(
        question="привет",
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v1",
    )
    out = graph.invoke(state)
    routes = list(out.get("routing_log") or [])
    assert routes
    assert routes[0].get("to") == "writer_agent"
    assert str(routes[0].get("reason") or "").startswith("coordinator_gate:")


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
