"""Phase 1–4 regression tests: RoutePlan / QuestionFeatures / planner / supervisor decisions."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from science_graphrag.agent.coordination.question_features import (
    QuestionFeatures,
    extract_question_features,
)
from science_graphrag.agent.coordination.route_plan import (
    ROUTE_PLAN_SCHEMA_VERSION,
    RoutePlan,
    RouteStep,
    TerminationRule,
    deserialize_route_plan,
    route_plan_from_metadata,
)
from science_graphrag.agent.coordination.route_planner import (
    build_route_plan,
    planner_post_retrieval_handoff,
)
from science_graphrag.agent.coordination.turn_policy import TurnPolicy

# ---------------------------------------------------------------------------
# RoutePlan serialization
# ---------------------------------------------------------------------------


def test_route_plan_round_trip_via_dict() -> None:
    plan = RoutePlan(
        steps=(
            RouteStep(
                specialist="retrieval_agent",
                expected_completion=("minimal_bundle_ready",),
                budget_hint=4,
                reason="catalog_resolution_first_hop",
            ),
            RouteStep(specialist="writer_agent", reason="terminal_synthesis"),
        ),
        termination=TerminationRule(
            rule_id="writer_after_first_hop_completion",
            after_steps=1,
            reason="catalog_resolution_first_hop",
        ),
        replan_signal=None,
        notes=("phase1_test",),
    )
    payload = plan.to_dict()
    assert payload["schema_version"] == ROUTE_PLAN_SCHEMA_VERSION
    restored = deserialize_route_plan(payload)
    assert restored is not None
    assert restored.steps[0].specialist == "retrieval_agent"
    assert restored.termination.rule_id == "writer_after_first_hop_completion"
    assert restored.notes == ("phase1_test",)


def test_route_plan_from_metadata_returns_none_for_legacy_state() -> None:
    metadata = {"turn_policy": {"tool_policy": "allow_tools"}}
    assert route_plan_from_metadata(metadata) is None


def test_deserialize_route_plan_rejects_invalid_specialist() -> None:
    payload = {"steps": [{"specialist": "unknown"}], "termination": {"rule_id": "writer_immediate"}}
    plan = deserialize_route_plan(payload)
    assert plan is not None
    assert plan.steps == ()


# ---------------------------------------------------------------------------
# QuestionFeatures
# ---------------------------------------------------------------------------


def test_question_features_compare_dual_evidence_workspace() -> None:
    raw = (
        "Compare evidence for two different object-detection works in this workspace: "
        "use find_works twice with different title keywords, then call paper_profile "
        "for two distinct work_ids."
    )
    feats = extract_question_features(question=raw, workspace_id="ws-1")
    assert feats.has_workspace is True
    assert feats.asks_for_compare is True
    assert feats.asks_for_dual_evidence is True
    assert feats.asks_for_relations is False
    assert "compare evidence" in feats.matched_markers


def test_question_features_relation_tracing() -> None:
    feats = extract_question_features(
        question="Show the citation chain between paper A and paper B",
        workspace_id="ws-1",
    )
    assert feats.asks_for_relations is True


def test_question_features_workspace_stats_ru() -> None:
    feats = extract_question_features(
        question="Сколько работ в этом workspace?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_workspace_stats is True
    assert feats.language in ("ru", "mixed")


def test_question_features_asks_for_web_research_ru() -> None:
    feats = extract_question_features(
        question="что говорят об этой теме в интернете?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_web_research is True
    assert "интернет" in feats.matched_markers


def test_question_features_asks_for_web_research_en_online() -> None:
    feats = extract_question_features(
        question="What are people saying online about this topic?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_web_research is True


def test_question_features_asks_for_arxiv_preprint() -> None:
    feats = extract_question_features(
        question="Find recent preprints on arXiv about object detection",
        workspace_id="ws-1",
    )
    assert feats.asks_for_arxiv is True
    assert "arxiv" in feats.matched_markers


def test_question_features_asks_for_arxiv_id_shape() -> None:
    feats = extract_question_features(
        question="Summarize paper 2301.07012 and related work",
        workspace_id="ws-1",
    )
    assert feats.asks_for_arxiv is True
    assert "arxiv_id_shape" in feats.matched_markers


def test_question_features_asks_for_unpaywall_open_access() -> None:
    feats = extract_question_features(
        question="Is there a legal open access PDF for DOI 10.1038/nature12373?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_unpaywall is True


def test_question_features_ru_instruction_with_english_terms_stays_ru() -> None:
    feats = extract_question_features(
        question=(
            "Для рабочей области Object Detection сравни статьи по transfer learning "
            "in computer vision: сначала составь план исследования, затем дай ответ."
        ),
        workspace_id="ws-1",
    )
    assert feats.language == "ru"


# ---------------------------------------------------------------------------
# build_route_plan
# ---------------------------------------------------------------------------


def _tp(*, route_hint: str, tool_policy: str = "allow_tools", reason: str = "stub") -> TurnPolicy:
    return TurnPolicy(
        conversation_intent="research_task",
        tool_policy=tool_policy,
        route_hint=route_hint,
        reason=reason,
        suggested_answer_class="grounded_explanation",
        confidence=1.0,
        classifier="deterministic",
    )


def test_build_route_plan_writer_only_for_no_tools_gate() -> None:
    feats = extract_question_features(question="привет", workspace_id="ws-1")
    plan = build_route_plan(
        features=feats,
        turn_policy=_tp(route_hint="writer_agent", tool_policy="no_tools", reason="small_talk"),
    )
    assert [s.specialist for s in plan.steps] == ["writer_agent"]
    assert plan.termination.rule_id == "writer_immediate"


def test_build_route_plan_dual_evidence_overrides_graph_route_hint() -> None:
    feats = extract_question_features(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice with different title keywords, then paper_profile."
        ),
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint="graph_agent"))
    assert plan.steps[0].specialist == "retrieval_agent"
    assert plan.steps[0].reason == "workspace_dual_evidence_first_hop"
    assert plan.termination.rule_id == "writer_after_first_hop_completion"


def test_build_route_plan_relation_tracing_picks_graph_first() -> None:
    feats = extract_question_features(
        question="Show citation chain between paper A and paper B",
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint="graph_agent"))
    assert plan.steps[0].specialist == "graph_agent"


def test_build_route_plan_default_research_for_open_ended_prompt() -> None:
    feats = extract_question_features(
        question="Briefly explain attention mechanism in transformers",
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint="retrieval_agent"))
    assert plan.steps[0].specialist == "retrieval_agent"
    assert plan.termination.rule_id == "default_supervisor_round_cap"


# ---------------------------------------------------------------------------
# planner_post_retrieval_handoff parity with legacy supervisor heuristic
# ---------------------------------------------------------------------------


def test_planner_post_retrieval_handoff_workspace_stats() -> None:
    feats = extract_question_features(
        question="How many works are in this workspace? Use workspace_inspect.",
        workspace_id="ws-1",
    )
    reason = planner_post_retrieval_handoff(features=feats, tool_counts={"workspace_inspect": 1})
    assert reason == "retrieval_completion_workspace_stats"


def test_planner_post_retrieval_handoff_catalog_resolution() -> None:
    feats = extract_question_features(
        question=(
            "In this workspace find works whose titles mention 'Faster R-CNN' or 'Mask R-CNN'. "
            "Pick one clear match and report year and venue using paper_profile."
        ),
        workspace_id="ws-1",
    )
    reason = planner_post_retrieval_handoff(
        features=feats,
        tool_counts={"find_works": 1, "paper_profile": 1},
    )
    assert reason == "retrieval_completion_catalog_resolution"


def test_planner_post_retrieval_handoff_dual_evidence_compare_gates_on_gost() -> None:
    feats = extract_question_features(
        question=(
            "Compare two detector families and produce a bibliography: use find_works twice, "
            "call paper_profile for two distinct work_ids, then format a GOST bibliography."
        ),
        workspace_id="ws-1",
    )
    reason = planner_post_retrieval_handoff(
        features=feats,
        tool_counts={"find_works": 2, "paper_profile": 2},
    )
    # waits for format_bibliography_gost
    assert reason is None


# ---------------------------------------------------------------------------
# state.metadata.turn_policy.route_plan integration
# ---------------------------------------------------------------------------


def test_state_writes_route_plan_when_flag_enabled(monkeypatch) -> None:
    from science_graphrag.agent.graph.state import build_initial_agent_state

    settings_stub = MagicMock()
    settings_stub.agent_route_plan_enabled = True
    settings_stub.agent_away_summary_enabled = False
    settings_stub.agent_post_compact_paper_sources_enabled = False
    settings_stub.agent_research_plan_tool_enabled = False
    settings_stub.agent_max_parallel_subagents = 4
    settings_stub.agent_step_timeout_seconds = 240.0
    settings_stub.agent_turn_policy_classifier = "rules_v0"
    settings_stub.agent_turn_policy_llm_enabled = False
    settings_stub.agent_turn_policy_confidence_threshold = 0.6
    settings_stub.extraction_llm_api_key = ""

    monkeypatch.setattr("science_graphrag.agent.graph.state.get_settings", lambda: settings_stub)

    state = build_initial_agent_state(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice."
        ),
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v3",
        settings=settings_stub,
    )
    tp = state["metadata"]["turn_policy"]
    assert "route_plan" in tp
    assert tp["route_plan"]["schema_version"] == ROUTE_PLAN_SCHEMA_VERSION
    assert tp["route_plan"]["steps"][0]["specialist"] == "retrieval_agent"
    assert tp["question_features"]["asks_for_dual_evidence"] is True


def test_state_omits_route_plan_when_flag_off(monkeypatch) -> None:
    from science_graphrag.agent.graph.state import build_initial_agent_state

    settings_stub = MagicMock()
    settings_stub.agent_route_plan_enabled = False
    settings_stub.agent_away_summary_enabled = False
    settings_stub.agent_post_compact_paper_sources_enabled = False
    settings_stub.agent_research_plan_tool_enabled = False
    settings_stub.agent_max_parallel_subagents = 4
    settings_stub.agent_step_timeout_seconds = 240.0
    settings_stub.agent_turn_policy_classifier = "rules_v0"
    settings_stub.agent_turn_policy_llm_enabled = False
    settings_stub.agent_turn_policy_confidence_threshold = 0.6
    settings_stub.extraction_llm_api_key = ""

    monkeypatch.setattr("science_graphrag.agent.graph.state.get_settings", lambda: settings_stub)

    state = build_initial_agent_state(
        question="Briefly explain attention",
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v3",
        settings=settings_stub,
    )
    tp = state["metadata"]["turn_policy"]
    assert "route_plan" not in tp


def test_compute_first_hop_decision_rebuilds_transient_plan_when_state_has_no_plan() -> None:
    from science_graphrag.agent.graph.supervisor_decisions import compute_first_hop_decision

    state = {
        "messages": [
            HumanMessage(
                content=(
                    "Compare evidence for two object-detection works in this workspace and "
                    "use find_works twice before paper_profile."
                )
            )
        ],
        "workspace_id": "ws-1",
        "metadata": {
            "raw_user_question": (
                "Compare evidence for two object-detection works in this workspace and "
                "use find_works twice before paper_profile."
            ),
            "turn_policy": {
                "conversation_intent": "research_task",
                "tool_policy": "allow_tools",
                "route_hint": "graph_agent",
                "reason": "hybrid_route_hint",
                "suggested_answer_class": "grounded_explanation",
                "classifier": "llm",
                "confidence": 0.91,
            },
        },
    }
    settings_stub = MagicMock()
    settings_stub.agent_semantic_query_fast_route = False

    decision = compute_first_hop_decision(
        state=state,
        settings=settings_stub,
        tool_policy="allow_tools",
        route_hint="graph_agent",
        answer_class="grounded_explanation",
    )

    assert decision is not None
    assert decision.specialist == "retrieval_agent"
    assert decision.reason == "workspace_dual_evidence_first_hop"
    assert decision.extra == {"route_hint": "graph_agent", "from_route_plan": True}


# ---------------------------------------------------------------------------
# supervisor + RoutePlan integration
# ---------------------------------------------------------------------------


def test_supervisor_uses_route_plan_first_step_when_attached(monkeypatch) -> None:
    """Phase 1.3 acceptance: supervisor reads RoutePlan instead of inline branches."""

    captured: list[int] = []

    class _CountingRouter:
        def invoke(self, _messages):
            captured.append(1)
            return AIMessage(content="writer_agent")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _CountingRouter(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.retrieval_subgraph.build_chat_model",
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

    settings_stub = MagicMock()
    settings_stub.agent_max_tool_calls = 8
    settings_stub.agent_runtime = "langgraph_supervisor_v3"
    settings_stub.agent_supervisor_recursion_limit = 12
    settings_stub.agent_semantic_query_fast_route = False
    settings_stub.agent_route_plan_enabled = True
    settings_stub.agent_route_plan_post_retrieval_handoff_enabled = False
    settings_stub.agent_supervisor_replan_only_llm_enabled = False
    settings_stub.agent_supervisor_max_rounds = 10
    settings_stub.agent_subagent_lifecycle_enhanced_enabled = False
    settings_stub.agent_away_summary_enabled = False
    settings_stub.agent_post_compact_paper_sources_enabled = False
    settings_stub.agent_research_plan_tool_enabled = False
    settings_stub.agent_max_parallel_subagents = 4
    settings_stub.agent_step_timeout_seconds = 240.0
    settings_stub.agent_turn_policy_classifier = "rules_v0"
    settings_stub.agent_turn_policy_llm_enabled = False
    settings_stub.agent_turn_policy_confidence_threshold = 0.6
    settings_stub.extraction_llm_api_key = ""

    monkeypatch.setattr("science_graphrag.agent.graph.state.get_settings", lambda: settings_stub)

    from science_graphrag.agent.graph.state import build_initial_agent_state
    from science_graphrag.agent.graph.supervisor import build_supervisor_graph

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()

    graph = build_supervisor_graph(stores, settings_stub)
    state = build_initial_agent_state(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice."
        ),
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v3",
        settings=settings_stub,
    )
    out = graph.invoke(state)
    routes = list(out.get("routing_log") or [])
    assert routes
    # First hop respects the RoutePlan (retrieval_agent for dual evidence).
    assert routes[0]["to"] == "retrieval_agent"
    assert routes[0]["reason"] == "workspace_dual_evidence_first_hop"
    # Plan picks first hop deterministically; LLM router is not invoked for it.
    assert len(captured) <= 1, "LLM router must run at most for post-first-hop replan"


def test_supervisor_replan_only_skips_llm_for_writer_step(monkeypatch) -> None:
    """Phase 4: when replan_only flag is on and plan attached, supervisor skips LLM."""

    class _NeverCalledRouter:
        def invoke(self, _messages):
            raise AssertionError("LLM router must not run when plan covers next step")

    class _FakeSpecialist:
        def bind_tools(self, _tools):
            return self

        def invoke(self, _messages):
            return AIMessage(content="done", tool_calls=[])

    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: _NeverCalledRouter(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.graph.nodes.retrieval_subgraph.build_chat_model",
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

    settings_stub = MagicMock()
    settings_stub.agent_max_tool_calls = 8
    settings_stub.agent_runtime = "langgraph_supervisor_v3"
    settings_stub.agent_supervisor_recursion_limit = 12
    settings_stub.agent_semantic_query_fast_route = False
    settings_stub.agent_route_plan_enabled = True
    settings_stub.agent_route_plan_post_retrieval_handoff_enabled = False
    settings_stub.agent_supervisor_replan_only_llm_enabled = True
    settings_stub.agent_supervisor_max_rounds = 10
    settings_stub.agent_subagent_lifecycle_enhanced_enabled = False
    settings_stub.agent_away_summary_enabled = False
    settings_stub.agent_post_compact_paper_sources_enabled = False
    settings_stub.agent_research_plan_tool_enabled = False
    settings_stub.agent_max_parallel_subagents = 4
    settings_stub.agent_step_timeout_seconds = 240.0
    settings_stub.agent_turn_policy_classifier = "rules_v0"
    settings_stub.agent_turn_policy_llm_enabled = False
    settings_stub.agent_turn_policy_confidence_threshold = 0.6
    settings_stub.extraction_llm_api_key = ""

    monkeypatch.setattr("science_graphrag.agent.graph.state.get_settings", lambda: settings_stub)

    from science_graphrag.agent.graph.state import build_initial_agent_state
    from science_graphrag.agent.graph.supervisor import build_supervisor_graph

    stores = MagicMock()
    stores.neo4j = MagicMock()
    stores.qdrant_chunks = MagicMock()
    stores.qdrant_works = MagicMock()

    graph = build_supervisor_graph(stores, settings_stub)
    state = build_initial_agent_state(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "use find_works twice."
        ),
        workspace_id="ws-1",
        max_tool_calls=8,
        agent_runtime="langgraph_supervisor_v3",
        settings=settings_stub,
    )
    out = graph.invoke(state)
    routes = [r for r in (out.get("routing_log") or []) if r.get("from") == "supervisor"]
    assert routes
    # Two supervisor hops in the plan: retrieval_agent then writer_agent.
    targets = [r["to"] for r in routes]
    assert targets[0] == "retrieval_agent"
    # Subsequent supervisor hops follow the plan deterministically without LLM.
    assert "writer_agent" in targets


# ---------------------------------------------------------------------------
# Smoke: feature extractor matches existing supervisor heuristic
# ---------------------------------------------------------------------------


def test_question_features_smoke_supervisor_compat() -> None:
    """``QuestionFeatures`` produces the same first-hop verdicts as legacy heuristic."""
    feats = extract_question_features(
        question=(
            "Compare evidence for two different object-detection works in this workspace: "
            "Finish with final_answer and citations for both work_ids."
        ),
        workspace_id="2678c5f1-1b31-4aac-92c9-6bd0f4472b23",
    )
    # Boilerplate "citations" must NOT trigger graph intent (regression for 2026-05-07).
    assert feats.asks_for_relations is False
    assert feats.asks_for_dual_evidence is True


# ---------------------------------------------------------------------------
# Direct sanity: ``planner_post_retrieval_handoff`` quote evidence.
# ---------------------------------------------------------------------------


def test_planner_post_retrieval_handoff_quote_evidence() -> None:
    feats = extract_question_features(
        question=("Find one anchor-free quote one short snippet from a workspace paper."),
        workspace_id="ws-1",
    )
    reason = planner_post_retrieval_handoff(
        features=feats,
        tool_counts={"paper_quote_search": 1},
    )
    assert reason == "retrieval_completion_quote_evidence"


def test_planner_post_retrieval_handoff_web_research_requires_fetch() -> None:
    feats = extract_question_features(
        question="what are people saying online about this topic?",
        workspace_id="ws-1",
    )
    reason_only_search = planner_post_retrieval_handoff(
        features=feats,
        tool_counts={"web_search": 1},
    )
    assert reason_only_search is None
    reason_with_fetch = planner_post_retrieval_handoff(
        features=feats,
        tool_counts={"web_search": 1, "web_fetch": 1},
    )
    assert reason_with_fetch == "retrieval_completion_web_research"


def test_planner_post_retrieval_handoff_arxiv_search_or_fetch() -> None:
    feats = extract_question_features(
        question="Find recent arXiv preprints about diffusion models",
        workspace_id=None,
    )
    assert feats.asks_for_arxiv is True
    assert (
        planner_post_retrieval_handoff(features=feats, tool_counts={"arxiv_search": 1})
        == "retrieval_completion_arxiv_research"
    )
    assert (
        planner_post_retrieval_handoff(features=feats, tool_counts={"arxiv_fetch": 1})
        == "retrieval_completion_arxiv_research"
    )


def test_planner_post_retrieval_handoff_arxiv_does_not_short_circuit_dual_evidence() -> None:
    raw = (
        "Compare evidence for two different object-detection works in this workspace: "
        "use find_works twice with different title keywords, then call paper_profile "
        "for two distinct work_ids. Mention arxiv:2301.07012 as an example id."
    )
    feats = extract_question_features(question=raw, workspace_id="ws-1")
    assert feats.asks_for_dual_evidence is True
    assert feats.asks_for_arxiv is True
    assert planner_post_retrieval_handoff(features=feats, tool_counts={"arxiv_search": 1}) is None


def test_planner_post_retrieval_handoff_web_and_arxiv_when_both_intents() -> None:
    feats = extract_question_features(
        question="Search arXiv for GAN papers and also fetch what people say online about GANs",
        workspace_id=None,
    )
    assert feats.asks_for_arxiv is True
    assert feats.asks_for_web_research is True
    assert (
        planner_post_retrieval_handoff(
            features=feats,
            tool_counts={"web_fetch": 1, "arxiv_search": 1},
        )
        == "retrieval_completion_web_arxiv_research"
    )


def test_question_features_to_dict_serializable() -> None:
    feats = extract_question_features(question="how many papers?", workspace_id="ws-1")
    payload = feats.to_dict()
    json.dumps(payload)  # serializable
    assert payload["asks_for_workspace_stats"] is True


def test_route_plan_default_research_when_route_hint_writer_only() -> None:
    feats = extract_question_features(question="say hi", workspace_id=None)
    plan = build_route_plan(
        features=feats, turn_policy=_tp(route_hint="writer_agent", tool_policy="no_tools")
    )
    assert [s.specialist for s in plan.steps] == ["writer_agent"]


def test_question_features_used_for_round_trip() -> None:
    feats = extract_question_features(question="привет", workspace_id="ws-1")
    feats2 = QuestionFeatures(**{**feats.__dict__})
    assert feats2.normalized_question == feats.normalized_question


def test_planner_returns_default_for_open_ended_workspace_question() -> None:
    feats = extract_question_features(
        question="Tell me about authors who work on transformers",
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint="retrieval_agent"))
    assert plan.steps[0].specialist == "retrieval_agent"


def test_question_features_round_trip_via_dict() -> None:
    """``QuestionFeatures.from_dict`` must invert ``to_dict`` exactly."""
    feats = extract_question_features(
        question="Compare evidence for two different works in workspace ws-1.",
        workspace_id="ws-1",
    )
    payload = feats.to_dict()
    restored = QuestionFeatures.from_dict(payload)
    assert restored is not None
    assert restored == feats


def test_question_features_from_dict_rejects_garbage_payload() -> None:
    assert QuestionFeatures.from_dict(None) is None
    assert QuestionFeatures.from_dict({"language": "en"}) is None  # missing normalized_question
    assert QuestionFeatures.from_dict([]) is None


def test_should_skip_llm_router_open_ended_plan_falls_through_to_llm() -> None:
    """Default research plan must let LLM decide after first hop is exhausted."""
    from science_graphrag.agent.graph.supervisor_decisions import should_skip_llm_router

    feats = extract_question_features(
        question="Tell me about authors who work on transformers",
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint="retrieval_agent"))
    assert plan.termination.rule_id == "default_supervisor_round_cap"

    settings = MagicMock()
    settings.agent_supervisor_replan_only_llm_enabled = True

    state = {
        "metadata": {"turn_policy": {"route_plan": plan.to_dict()}},
        # One supervisor hop already happened (retrieval done).
        "routing_log": [{"from": "supervisor", "to": "retrieval_agent"}],
    }
    assert should_skip_llm_router(state=state, settings=settings) is None


def test_should_skip_llm_router_terminating_plan_lands_on_writer() -> None:
    """Bounded plans (writer_after_first_hop_completion) deterministically pick writer."""
    from science_graphrag.agent.graph.supervisor_decisions import should_skip_llm_router

    feats = extract_question_features(
        question="how many papers are in this workspace?",
        workspace_id="ws-1",
    )
    plan = build_route_plan(features=feats, turn_policy=_tp(route_hint=""))
    assert plan.termination.rule_id == "writer_after_first_hop_completion"

    settings = MagicMock()
    settings.agent_supervisor_replan_only_llm_enabled = True

    state = {
        "metadata": {"turn_policy": {"route_plan": plan.to_dict()}},
        "routing_log": [{"from": "supervisor", "to": "retrieval_agent"}],
    }
    assert should_skip_llm_router(state=state, settings=settings) == "writer_agent"


def test_supervisor_decisions_consume_cached_question_features() -> None:
    """``_features_from_state`` must reuse cached features instead of recomputing."""
    from science_graphrag.agent.graph import supervisor_decisions as sd

    state = {
        "metadata": {
            "raw_user_question": "ignored fallback",
            "turn_policy": {
                "question_features": {
                    "raw_question": "Compare evidence for two different works",
                    "normalized_question": "compare evidence for two different works",
                    "has_workspace": True,
                    "language": "en",
                    "asks_for_compare": True,
                    "asks_for_dual_evidence": True,
                    "asks_for_relations": False,
                    "matched_markers": ["compare evidence", "two different"],
                }
            },
        },
        "workspace_id": "ws-1",
    }
    feats = sd._features_from_state(state)  # pylint: disable=protected-access
    assert feats.normalized_question == "compare evidence for two different works"
    assert feats.asks_for_dual_evidence is True
    assert feats.matched_markers == ("compare evidence", "two different")


# Smoke: ToolMessage input is irrelevant for feature extractor (no crash).
def test_feature_extractor_robust_to_tool_message_state() -> None:
    state_messages = [
        HumanMessage(content="how many works are in this workspace?"),
        AIMessage(content="", tool_calls=[]),
        ToolMessage(content="{}", tool_call_id="c1", name="workspace_inspect"),
    ]
    _ = state_messages  # only build_features uses raw question, not messages
    feats = extract_question_features(
        question="how many works are in this workspace?",
        workspace_id="ws-1",
    )
    assert feats.asks_for_workspace_stats is True
