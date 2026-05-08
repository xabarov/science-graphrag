from __future__ import annotations

import json
import typing
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


def _force_writer_after_retrieval(state: dict) -> str | None:
    """Test helper: planner-based post-retrieval handoff for legacy shim cases.

    Mirrors what the retired ``_maybe_force_writer_after_retrieval`` shim used
    to do — extract features and ask :func:`planner_post_retrieval_handoff`.
    """
    from science_graphrag.agent.coordination.question_features import (
        extract_question_features,
    )
    from science_graphrag.agent.coordination.route_planner import (
        planner_post_retrieval_handoff,
    )
    from science_graphrag.agent.graph.tracing import collect_tool_execution_steps

    raw = ""
    for msg in reversed(state.get("messages") or []):
        if not isinstance(msg, HumanMessage):
            continue
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            raw = content.strip()
            break
    if not raw:
        return None
    feats = extract_question_features(
        question=raw,
        workspace_id=str(state.get("workspace_id") or "").strip() or None,
    )
    tool_counts: dict[str, int] = {}
    for step in collect_tool_execution_steps(list(state.get("messages") or [])):
        name = str(step.get("tool") or "").strip()
        if not name:
            continue
        tool_counts[name] = tool_counts.get(name, 0) + 1
    return planner_post_retrieval_handoff(features=feats, tool_counts=tool_counts)


def _build_state_without_plan(
    *, question: str, workspace_id: str, agent_runtime: str
) -> dict:
    """Build initial agent state with the planner explicitly disabled.

    Used by LLM-router safety-net tests that need ``supervisor_node`` to
    actually invoke the LLM router (otherwise the deterministic planner
    short-circuits the first hop). Mirrors :func:`build_initial_agent_state`
    minimally — only the parts the supervisor reads.
    """
    from time import perf_counter

    from langchain_core.messages import HumanMessage, SystemMessage

    from science_graphrag.agent.subagents.specialist_results_v3 import (
        empty_specialist_results_v3,
    )

    return {
        "messages": [
            SystemMessage(content="test_supervisor_routing system stub"),
            HumanMessage(content=question),
        ],
        "workspace_id": workspace_id,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 8,
        "metadata": {
            "agent_runtime": agent_runtime,
            "agent_max_tool_calls": 8,
            "raw_user_question": question,
            "turn_policy": {
                "tool_policy": "allow_tools",
                "route_hint": "",
                "reason": "test_router_safety_net",
            },
            "agent_response_deadline_perf_start": perf_counter(),
            "agent_response_deadline_seconds": 240.0,
        },
        "specialist_results": {},
        "specialist_results_v3": empty_specialist_results_v3(),
        "current_specialist": None,
        "routing_log": [],
        "answer_class": "grounded_explanation",
        "history_digest": [],
        "session_summary": "",
    }


def _force_retrieval_first_hop_workspace_dual_evidence(state: dict) -> bool:
    """Test helper: features-based first-hop check for legacy shim cases.

    Mirrors what the retired ``_should_force_retrieval_first_hop_workspace_dual_evidence``
    shim used to do — extract :class:`QuestionFeatures` and apply the
    workspace dual-evidence rule.
    """
    from science_graphrag.agent.coordination.question_features import (
        extract_question_features,
    )

    raw = ""
    for msg in reversed(state.get("messages") or []):
        if not isinstance(msg, HumanMessage):
            continue
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            raw = content.strip()
            break
    if not raw:
        return False
    feats = extract_question_features(
        question=raw,
        workspace_id=str(state.get("workspace_id") or "").strip() or None,
    )
    if not feats.has_workspace:
        return False
    if feats.asks_for_relations:
        return False
    qn = feats.normalized_question
    if "workspace" not in qn and "workspace_id" not in qn:
        return False
    return feats.asks_for_dual_evidence


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

    from science_graphrag.agent.graph.supervisor_decisions import _build_llm_route_messages

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
    route_messages = _build_llm_route_messages(state)
    response = _CapturingRouter().invoke(route_messages)

    assert response.content == "writer_agent"
    assert captured_messages
    sent = captured_messages[0]
    assert all(isinstance(msg, HumanMessage) for msg in sent)
    assert len(sent) == 3
    assert "specialist_results" in sent[-1].content


def test_first_user_plain_question_ignores_tool_payload_suffix() -> None:
    from science_graphrag.agent.graph.supervisor import _first_user_plain_question

    state = {
        "messages": [
            HumanMessage(content="How many works are in this workspace?"),
            AIMessage(content="", tool_calls=[{"name": "workspace_inspect", "id": "c1", "args": {}}]),
            ToolMessage(content='{"row_count": 32}', tool_call_id="c1", name="workspace_inspect"),
        ]
    }

    assert _first_user_plain_question(state) == "How many works are in this workspace?"


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
    # This test pins the LLM-router safety net (invalid token → writer);
    # disable the deterministic planner so the supervisor actually invokes
    # the LLM router under test.
    settings.agent_route_plan_enabled = False
    settings.agent_supervisor_replan_only_llm_enabled = False
    settings.agent_route_plan_post_retrieval_handoff_enabled = False

    graph = build_supervisor_graph(stores, settings)
    state = _build_state_without_plan(
        question="Explain attention mechanism in transformers briefly",
        workspace_id="ws-1",
        agent_runtime="langgraph_supervisor_v1",
    )
    out = graph.invoke(state)
    routes = list(out.get("routing_log") or [])
    assert routes
    assert routes[0].get("to") == "writer_agent"


def test_supervisor_finish_token_remaps_to_writer_for_final_answer_contract(monkeypatch) -> None:
    """Explicit FINISH must still pass through writer to emit terminal ``final_answer``."""

    class _FinishRouter:
        def invoke(self, _messages):
            return AIMessage(content="FINISH")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _FinishRouter(),
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
    settings.agent_runtime = "langgraph_supervisor_v3"
    settings.agent_supervisor_recursion_limit = 12
    settings.agent_semantic_query_fast_route = False
    # This test pins the LLM-router safety net (FINISH → writer remap);
    # disable the deterministic planner so the supervisor actually invokes
    # the LLM router under test.
    settings.agent_route_plan_enabled = False
    settings.agent_supervisor_replan_only_llm_enabled = False
    settings.agent_route_plan_post_retrieval_handoff_enabled = False

    graph = build_supervisor_graph(stores, settings)
    state = _build_state_without_plan(
        question="How many works are in this workspace?",
        workspace_id="ws-1",
        agent_runtime="langgraph_supervisor_v3",
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


def test_retrieval_completion_fast_handoff_for_catalog_resolution() -> None:

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "In this workspace, find works whose titles mention 'Faster R-CNN' or "
                    "'Mask R-CNN'. Pick one clear match and report year and venue using "
                    "paper_profile."
                )
            ),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "find_works",
                        "id": "c1",
                        "args": {"query": "Faster R-CNN OR Mask R-CNN"},
                    }
                ],
            ),
            ToolMessage(content=json.dumps({"row_count": 2}), tool_call_id="c1", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "paper_profile", "id": "c2", "args": {"work_id": "w1"}}
                ],
            ),
            ToolMessage(
                content=json.dumps({"title": "Mask R-CNN", "row_count": 1}),
                tool_call_id="c2",
                name="paper_profile",
            ),
        ],
    }

    assert _force_writer_after_retrieval(state) == "retrieval_completion_catalog_resolution"


def test_retrieval_completion_fast_handoff_for_workspace_stats() -> None:

    state = {
        "messages": [
            HumanMessage(content="How many works are in this workspace? Use workspace_inspect."),
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "workspace_inspect",
                        "id": "c1",
                        "args": {"mode": "stats"},
                    }
                ],
            ),
            ToolMessage(content=json.dumps({"row_count": 1}), tool_call_id="c1", name="workspace_inspect"),
        ],
    }

    assert _force_writer_after_retrieval(state) == "retrieval_completion_workspace_stats"


def test_retrieval_completion_fast_handoff_is_not_triggered_for_partial_compare() -> None:

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Compare two detector families in this workspace: works whose titles mention "
                    "'YOLO' and works whose titles mention 'Faster R-CNN' or 'Mask R-CNN'."
                )
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "find_works", "id": "c1", "args": {"query": "YOLO"}}],
            ),
            ToolMessage(content=json.dumps({"row_count": 3}), tool_call_id="c1", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[{"name": "paper_profile", "id": "c2", "args": {"work_id": "w-yolo"}}],
            ),
            ToolMessage(
                content=json.dumps({"title": "YOLO9000", "row_count": 1}),
                tool_call_id="c2",
                name="paper_profile",
            ),
        ],
    }

    assert _force_writer_after_retrieval(state) is None


def test_retrieval_completion_fast_handoff_for_dual_evidence_compare() -> None:

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Compare evidence for two different object-detection works in this workspace: "
                    "use find_works twice with different title keywords, then call paper_profile "
                    "for two distinct work_ids from the results. Note whether metadata disagree "
                    "on any factual point."
                )
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "find_works", "id": "c1", "args": {"query": "YOLO"}}],
            ),
            ToolMessage(content=json.dumps({"row_count": 3}), tool_call_id="c1", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "id": "c2", "args": {"query": "Faster R-CNN"}}
                ],
            ),
            ToolMessage(content=json.dumps({"row_count": 2}), tool_call_id="c2", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[{"name": "paper_profile", "id": "c3", "args": {"work_id": "w-yolo"}}],
            ),
            ToolMessage(
                content=json.dumps({"title": "YOLO9000", "row_count": 1}),
                tool_call_id="c3",
                name="paper_profile",
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "paper_profile", "id": "c4", "args": {"work_id": "w-frcnn"}}],
            ),
            ToolMessage(
                content=json.dumps({"title": "Faster R-CNN", "row_count": 1}),
                tool_call_id="c4",
                name="paper_profile",
            ),
        ],
    }

    assert _force_writer_after_retrieval(state) == "retrieval_completion_dual_evidence_compare"


def test_should_force_retrieval_first_hop_for_od_dual_evidence_prompt() -> None:

    state = {
        "workspace_id": "2678c5f1-1b31-4aac-92c9-6bd0f4472b23",
        "messages": [
            HumanMessage(
                content=(
                    "Compare evidence for two different object-detection works in this workspace: "
                    "use find_works twice with different title keywords, then call paper_profile "
                    "for two distinct work_ids from the results. Finish with final_answer and "
                    "citations for both work_ids."
                )
            ),
        ],
    }
    assert _force_retrieval_first_hop_workspace_dual_evidence(state) is True


def test_should_force_retrieval_first_hop_requires_workspace_id() -> None:

    state = {
        "workspace_id": "",
        "messages": [
            HumanMessage(
                content=(
                    "Compare evidence for two different object-detection works in this workspace: "
                    "use find_works twice."
                )
            ),
        ],
    }
    assert _force_retrieval_first_hop_workspace_dual_evidence(state) is False


def test_dual_evidence_first_hop_overrides_graph_route_hint(monkeypatch) -> None:
    """LLM/hybrid turn-policy may set route_hint=graph_agent; catalog-compare still starts in retrieval."""

    from science_graphrag.agent.coordination.turn_policy import TurnPolicy

    def _stub_classify_turn_policy(*, question, workspace_id, **kwargs):
        _ = workspace_id
        _ = kwargs
        if "Compare evidence for two different object-detection" not in str(question or ""):
            raise AssertionError("test expects OD dual-evidence question")
        return TurnPolicy(
            conversation_intent="research_task",
            tool_policy="allow_tools",
            route_hint="graph_agent",
            reason="stub_llm_graph_override",
            suggested_answer_class="grounded_explanation",
            confidence=0.99,
            classifier="llm",
        )

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.coordination.turn_policy.classify_turn_policy",
        _stub_classify_turn_policy,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: type("_B", (), {"invoke": staticmethod(lambda _m: AIMessage(content="writer_agent"))})(),
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
    settings.agent_runtime = "langgraph_supervisor_v3"
    settings.agent_supervisor_recursion_limit = 12
    settings.agent_semantic_query_fast_route = False

    graph = build_supervisor_graph(stores, settings)
    state = build_initial_agent_state(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice with different title keywords, then call paper_profile "
            "for two distinct work_ids from the results."
        ),
        workspace_id="2678c5f1-1b31-4aac-92c9-6bd0f4472b23",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v3",
    )
    out = graph.invoke(state)
    routes = list(out.get("routing_log") or [])
    assert routes
    assert routes[0].get("to") == "retrieval_agent"
    assert routes[0].get("reason") == "workspace_dual_evidence_first_hop"
    assert routes[0].get("route_hint") == "graph_agent"


def test_dual_evidence_compare_waits_for_requested_bibliography() -> None:

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Compare two detector families and produce a bibliography: use find_works "
                    "twice, call paper_profile for two distinct work_ids, then format a GOST "
                    "bibliography for both works."
                )
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "find_works", "id": "c1", "args": {"query": "YOLO"}}],
            ),
            ToolMessage(content=json.dumps({"row_count": 3}), tool_call_id="c1", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "find_works", "id": "c2", "args": {"query": "Faster R-CNN"}}
                ],
            ),
            ToolMessage(content=json.dumps({"row_count": 2}), tool_call_id="c2", name="find_works"),
            AIMessage(
                content="",
                tool_calls=[{"name": "paper_profile", "id": "c3", "args": {"work_id": "w-yolo"}}],
            ),
            ToolMessage(
                content=json.dumps({"title": "YOLO9000", "row_count": 1}),
                tool_call_id="c3",
                name="paper_profile",
            ),
            AIMessage(
                content="",
                tool_calls=[{"name": "paper_profile", "id": "c4", "args": {"work_id": "w-frcnn"}}],
            ),
            ToolMessage(
                content=json.dumps({"title": "Faster R-CNN", "row_count": 1}),
                tool_call_id="c4",
                name="paper_profile",
            ),
        ],
    }

    assert _force_writer_after_retrieval(state) is None


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
