from __future__ import annotations

from science_graphrag.agent.coordination.question_features import extract_question_features
from science_graphrag.agent.coordination.route_planner import build_route_plan
from science_graphrag.agent.coordination.turn_policy import TurnPolicy
from science_graphrag.agent.external_fast_path import pure_external_web_fast_path_intent
from science_graphrag.config import Settings


def _tp(**kwargs: object) -> TurnPolicy:
    return TurnPolicy(
        conversation_intent="research_task",
        tool_policy="allow_tools",
        route_hint=str(kwargs.get("route_hint", "retrieval_agent")),
        reason="test",
        suggested_answer_class="grounded_explanation",
        confidence=1.0,
        classifier="deterministic",
    )


def test_pure_external_web_fast_path_intent_true_for_web_scholar_prompt() -> None:
    feats = extract_question_features(
        question="Use web search and Semantic Scholar for SAM 3 trends, then PDF if OA.",
        workspace_id="ws-1",
    )
    assert pure_external_web_fast_path_intent(feats) is True


def test_pure_external_web_fast_path_intent_false_for_dual_evidence() -> None:
    feats = extract_question_features(
        question=(
            "Compare evidence for two works in this workspace using find_works and paper_profile."
        ),
        workspace_id="ws-1",
    )
    assert pure_external_web_fast_path_intent(feats) is False


def test_build_route_plan_skips_fast_path_when_flag_off() -> None:
    feats = extract_question_features(
        question="Web search hot trends in diffusion models for CV.",
        workspace_id="ws-1",
    )
    settings = Settings.model_construct(agent_external_research_fast_path_enabled=False)
    plan = build_route_plan(features=feats, turn_policy=_tp(), settings=settings)
    assert plan.steps[0].reason != "external_fast_path"
