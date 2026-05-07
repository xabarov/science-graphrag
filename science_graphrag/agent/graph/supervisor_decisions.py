"""Pure decision helpers extracted from ``supervisor_node`` (Phase 7.1).

Each function in this module is **side-effect free**: it only reads
``AgentState`` and ``Settings`` and returns a small dataclass / Optional
string. All I/O (LangGraph state mutation, LLM calls, span events) stays in
``science_graphrag.agent.graph.supervisor``.

Boundaries (matches orchestration-stabilization-plan-2026-05-07):

* ``compute_first_hop_decision``       — replaces inline ``if not prior``
  block in ``supervisor_node`` (route_hint, dual-evidence force, fast route).
* ``compute_post_retrieval_handoff``   — wraps both legacy
  ``_maybe_force_writer_after_retrieval`` and the new planner-based
  ``planner_post_retrieval_handoff``; flag ``agent_route_plan_post_retrieval_handoff_enabled``
  selects which one.
* ``compute_round_cap_decision``       — replaces the supervisor round cap
  branch.
* ``should_skip_llm_router``           — answers Phase 4: did the plan
  already pre-decide the next hop, or do we need ``maybe_replan`` (LLM call)?
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage

from science_graphrag.agent.coordination.deterministic import graph_intent_heuristic
from science_graphrag.agent.coordination.question_features import (
    QuestionFeatures,
    extract_question_features,
)
from science_graphrag.agent.coordination.route_plan import (
    RoutePlan,
    route_plan_from_metadata,
)
from science_graphrag.agent.coordination.route_planner import (
    planner_post_retrieval_handoff as _planner_post_retrieval_handoff,
)
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.tracing import collect_tool_execution_steps

# --- Specialist names -------------------------------------------------------
RETRIEVAL_SPECIALIST = "retrieval_agent"
GRAPH_SPECIALIST = "graph_agent"
WRITER_SPECIALIST = "writer_agent"


@dataclass(frozen=True)
class FirstHopDecision:
    """Result of ``compute_first_hop_decision``."""

    specialist: str
    reason: str
    extra: dict[str, Any] | None = None


@dataclass(frozen=True)
class RoundCapDecision:
    """Result of ``compute_round_cap_decision``."""

    triggered: bool
    supervisor_hops: int
    reason: str = "supervisor_round_cap"


def first_user_plain_question(state: AgentState) -> str:
    """Return the first user message text (mirrors supervisor.py)."""
    meta = state.get("metadata") or {}
    raw = meta.get("raw_user_question")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    for msg in reversed(state.get("messages") or []):
        if not isinstance(msg, HumanMessage):
            continue
        content = getattr(msg, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return ""


def normalized_question(text: str) -> str:
    """Lower-case, whitespace-collapsed view of the user prompt."""
    return " ".join(str(text or "").strip().lower().split())


def _features_from_state(state: AgentState) -> QuestionFeatures:
    """Read cached ``question_features`` from metadata, or compute on demand.

    The cache is populated by ``build_initial_agent_state`` when
    ``agent_route_plan_enabled`` is true; deserialization is a pure dict ->
    dataclass step (no LLM, no I/O), so falling back to recomputation is
    fine but unnecessary when the cache is present.
    """
    meta = state.get("metadata") or {}
    tp = meta.get("turn_policy") if isinstance(meta, dict) else None
    if isinstance(tp, dict):
        cached = tp.get("question_features")
        feats = QuestionFeatures.from_dict(cached) if isinstance(cached, dict) else None
        if feats is not None:
            return feats
    return extract_question_features(
        question=first_user_plain_question(state),
        workspace_id=str(state.get("workspace_id") or "").strip() or None,
    )


def _route_plan(state: AgentState) -> RoutePlan | None:
    return route_plan_from_metadata(state.get("metadata"))


def _tool_counts(state: AgentState) -> dict[str, int]:
    counts: dict[str, int] = {}
    for step in collect_tool_execution_steps(list(state.get("messages") or [])):
        name = str(step.get("tool") or "").strip()
        if not name:
            continue
        counts[name] = counts.get(name, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Public decisions
# ---------------------------------------------------------------------------


def compute_first_hop_decision(  # pylint: disable=too-many-return-statements,too-many-boolean-expressions
    *,
    state: AgentState,
    settings: Any,
    tool_policy: str,
    route_hint: str,
    answer_class: str,
) -> FirstHopDecision | None:
    """Return deterministic first-hop choice, or None to defer to LLM router.

    Order of precedence:

    1. RoutePlan (when ``agent_route_plan_enabled``) — first step wins.
    2. Workspace dual-evidence catalog compare override (legacy heuristic).
    3. Coordinator ``route_hint`` (graph_agent / writer_agent / retrieval_agent).
    4. Semantic fast-route flag.
    """
    if tool_policy != "allow_tools":
        return None

    plan = _route_plan(state)
    if plan is not None and plan.steps:
        first = plan.first_step()
        if first is not None:
            return FirstHopDecision(
                specialist=str(first.specialist),
                reason=first.reason or "route_plan_first_step",
                extra={"route_hint": route_hint or None, "from_route_plan": True},
            )

    feats = _features_from_state(state)

    # Legacy: workspace dual-evidence first-hop force (overrides graph route_hint).
    if (
        feats.has_workspace
        and feats.asks_for_dual_evidence
        and "workspace" in feats.normalized_question
        and route_hint != WRITER_SPECIALIST
        and answer_class != "relation_tracing"
        and not graph_intent_heuristic(feats.raw_question)
    ):
        return FirstHopDecision(
            specialist=RETRIEVAL_SPECIALIST,
            reason="workspace_dual_evidence_first_hop",
            extra={"route_hint": route_hint or None},
        )

    if route_hint == GRAPH_SPECIALIST or answer_class == "relation_tracing":
        reason = (
            "coordinator_route_hint"
            if route_hint == GRAPH_SPECIALIST
            else "answer_class_relation_tracing"
        )
        return FirstHopDecision(
            specialist=GRAPH_SPECIALIST,
            reason=reason,
            extra={"route_hint": route_hint or None},
        )

    if route_hint == WRITER_SPECIALIST:
        return FirstHopDecision(
            specialist=WRITER_SPECIALIST,
            reason="coordinator_route_hint",
        )

    if route_hint == RETRIEVAL_SPECIALIST and bool(
        getattr(settings, "agent_semantic_query_fast_route", False)
    ):
        if feats.raw_question and not feats.asks_for_relations:
            return FirstHopDecision(
                specialist=RETRIEVAL_SPECIALIST,
                reason="semantic_fast_route",
            )
    return None


def compute_post_retrieval_handoff(
    *,
    state: AgentState,
    settings: Any,
    legacy_fn: Any,
) -> str | None:
    """Decide whether retrieval finished and writer can take over.

    ``legacy_fn`` is the (still-present) imperative
    ``_maybe_force_writer_after_retrieval`` from supervisor.py — called for
    backward compatibility when the planner-based path is not enabled.
    """
    if str(state.get("current_specialist") or "").strip() != RETRIEVAL_SPECIALIST:
        return None

    use_planner = bool(getattr(settings, "agent_route_plan_post_retrieval_handoff_enabled", False))
    plan_attached = _route_plan(state) is not None

    if use_planner and plan_attached:
        feats = _features_from_state(state)
        v3 = state.get("specialist_results_v3")
        cs: str | None = None
        if isinstance(v3, dict):
            merge = v3.get("merge")
            if isinstance(merge, dict):
                raw = merge.get("completion_state")
                if isinstance(raw, str) and raw.strip():
                    cs = raw.strip()
        return _planner_post_retrieval_handoff(
            features=feats,
            tool_counts=_tool_counts(state),
            completion_state=cs,
        )

    if callable(legacy_fn):
        return legacy_fn(state)
    return None


def compute_round_cap_decision(*, state: AgentState, settings: Any) -> RoundCapDecision:
    """Return whether supervisor round cap is hit."""
    prior = list(state.get("routing_log") or [])
    sup_hops = len([x for x in prior if isinstance(x, dict) and x.get("from") == "supervisor"])
    max_rounds = int(getattr(settings, "agent_supervisor_max_rounds", 0) or 0)
    triggered = sup_hops >= max_rounds > 0
    return RoundCapDecision(triggered=triggered, supervisor_hops=sup_hops)


def should_skip_llm_router(  # pylint: disable=too-many-return-statements
    *, state: AgentState, settings: Any
) -> str | None:
    """Phase 4: when a plan exists, skip LLM router by following the plan.

    Returns the next specialist name (one of retrieval/graph/writer) or
    ``None`` meaning "fall through to legacy LLM routing".

    The decision is gated by ``agent_supervisor_replan_only_llm_enabled`` so
    rollout can be staged.

    Open-ended plans (``default_supervisor_round_cap`` termination) deliberately
    return ``None`` once their fixed steps are exhausted — that is exactly the
    case where we still want LLM-driven re-planning rather than forcing the
    writer prematurely.
    """
    if not bool(getattr(settings, "agent_supervisor_replan_only_llm_enabled", False)):
        return None
    plan = _route_plan(state)
    if plan is None:
        return None
    if plan.replan_signal:
        # Plan explicitly asked for an LLM replan call; let supervisor invoke LLM.
        return None
    prior = list(state.get("routing_log") or [])
    sup_hops = len([x for x in prior if isinstance(x, dict) and x.get("from") == "supervisor"])

    # First hop already handled by ``compute_first_hop_decision``;
    # after that we follow plan.steps[1:] one by one.
    next_index = sup_hops  # 0-based; first hop covered by step 0
    if next_index >= len(plan.steps):
        if plan.termination.rule_id == "default_supervisor_round_cap":
            return None
        return WRITER_SPECIALIST
    step = plan.step_for_index(next_index)
    if step is None:
        return (
            None
            if plan.termination.rule_id == "default_supervisor_round_cap"
            else WRITER_SPECIALIST
        )
    return str(step.specialist)


__all__ = [
    "FirstHopDecision",
    "RoundCapDecision",
    "compute_first_hop_decision",
    "compute_post_retrieval_handoff",
    "compute_round_cap_decision",
    "first_user_plain_question",
    "normalized_question",
    "should_skip_llm_router",
]
