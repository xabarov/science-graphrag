"""Deterministic ``RoutePlan`` builder (Phase 3, orchestration stabilization).

Translates :class:`QuestionFeatures` + :class:`TurnPolicy` into a concrete
:class:`RoutePlan`. This is the **single owner** of routing rules going
forward; ``supervisor_node`` only executes the plan and falls back to the
legacy LLM router when:

* the plan is missing (``feature flag off`` / older state metadata), **or**
* the plan explicitly raises ``replan_signal``.

Migration policy:

* All ``_should_force_*`` and ``_maybe_force_writer_after_retrieval`` rules
  in supervisor.py are intended to land here (Фаза 1.4 of the plan). The
  first cut covers the *first-hop* decisions; the *post-retrieval* rules
  are still consumed by the supervisor at runtime via the same feature
  bag (see ``planner_post_retrieval_handoff`` below).
"""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.coordination.question_features import (
    QuestionFeatures,
    extract_question_features,
)
from science_graphrag.agent.coordination.route_plan import (
    CompletionSignalId,
    RoutePlan,
    RouteStep,
    TerminationRule,
)
from science_graphrag.agent.coordination.turn_policy import TurnPolicy


def _writer_only_plan(reason: str) -> RoutePlan:
    return RoutePlan(
        steps=(
            RouteStep(
                specialist="writer_agent",
                expected_completion=("writer_ready",),
                reason=reason,
            ),
        ),
        termination=TerminationRule(rule_id="writer_immediate", reason=reason),
        planner="deterministic_v1",
    )


def _retrieval_then_writer(
    *, first_hop_reason: str, expected: tuple[CompletionSignalId, ...]
) -> RoutePlan:
    return RoutePlan(
        steps=(
            RouteStep(
                specialist="retrieval_agent",
                expected_completion=expected,
                reason=first_hop_reason,
            ),
            RouteStep(
                specialist="writer_agent",
                expected_completion=("writer_ready",),
                reason="terminal_synthesis",
            ),
        ),
        termination=TerminationRule(
            rule_id="writer_after_first_hop_completion",
            after_steps=1,
            reason=first_hop_reason,
        ),
        planner="deterministic_v1",
    )


def _graph_then_writer(*, first_hop_reason: str) -> RoutePlan:
    return RoutePlan(
        steps=(
            RouteStep(
                specialist="graph_agent",
                expected_completion=("graph_traversal_needed", "any_specialist_payload"),
                reason=first_hop_reason,
            ),
            RouteStep(
                specialist="writer_agent",
                expected_completion=("writer_ready",),
                reason="terminal_synthesis",
            ),
        ),
        termination=TerminationRule(
            rule_id="writer_after_first_hop_completion",
            after_steps=1,
            reason=first_hop_reason,
        ),
        planner="deterministic_v1",
    )


def _default_research_plan(*, reason: str) -> RoutePlan:
    """Open-ended retrieval-first plan that may replan via LLM after first hop."""
    return RoutePlan(
        steps=(
            RouteStep(
                specialist="retrieval_agent",
                expected_completion=("any_specialist_payload",),
                reason=reason,
            ),
        ),
        termination=TerminationRule(
            rule_id="default_supervisor_round_cap",
            reason="open_ended_research",
        ),
        planner="deterministic_v1",
    )


def build_route_plan(  # pylint: disable=too-many-return-statements,unused-argument
    *,
    features: QuestionFeatures,
    turn_policy: TurnPolicy | None,
    settings: Any | None = None,  # reserved for future per-flag overrides
) -> RoutePlan:
    """Compose a deterministic :class:`RoutePlan` for one turn.

    Precedence (planner-side):

    1. coordinator gate ``no_tools`` / ``clarify`` -> writer-only plan.
    2. workspace dual-evidence catalog compare -> retrieval first hop,
       overrides any ``route_hint=graph_agent`` from hybrid LLM (covers
       prior ``_should_force_retrieval_first_hop_workspace_dual_evidence``).
    3. ``answer_class=relation_tracing`` / explicit graph intent
       -> graph_agent first hop.
    4. explicit ``route_hint=writer_agent`` -> writer-only plan.
    5. otherwise -> default research (retrieval first), no termination cap
       beyond the supervisor round cap; planner may yield to LLM replan.
    """
    tp = turn_policy
    pol = str(getattr(tp, "tool_policy", "") or "").strip() if tp else ""
    if pol in {"no_tools", "clarify"}:
        return _writer_only_plan(reason=f"coordinator_gate:{getattr(tp, 'reason', '') or pol}")

    route_hint = str(getattr(tp, "route_hint", "") or "").strip() if tp else ""
    answer_class = str(getattr(tp, "suggested_answer_class", "") or "").strip() if tp else ""

    if (
        features.has_workspace
        and features.asks_for_dual_evidence
        and route_hint != "writer_agent"
        and answer_class != "relation_tracing"
        and not features.asks_for_relations
    ):
        return _retrieval_then_writer(
            first_hop_reason="workspace_dual_evidence_first_hop",
            expected=("minimal_bundle_ready", "any_specialist_payload"),
        )

    if route_hint == "graph_agent" or answer_class == "relation_tracing":
        return _graph_then_writer(
            first_hop_reason=(
                "coordinator_route_hint"
                if route_hint == "graph_agent"
                else "answer_class_relation_tracing"
            )
        )

    if route_hint == "writer_agent":
        return _writer_only_plan(reason="coordinator_route_hint")

    if features.asks_for_workspace_stats and features.has_workspace:
        return _retrieval_then_writer(
            first_hop_reason="workspace_stats_first_hop",
            expected=("minimal_bundle_ready",),
        )

    if features.asks_for_catalog_resolution and not features.asks_for_compare:
        return _retrieval_then_writer(
            first_hop_reason="catalog_resolution_first_hop",
            expected=("minimal_bundle_ready",),
        )

    return _default_research_plan(
        reason=(
            "coordinator_route_hint:retrieval_agent"
            if route_hint == "retrieval_agent"
            else "default_research_assumption"
        )
    )


def planner_post_retrieval_handoff(  # pylint: disable=too-many-return-statements
    *,
    features: QuestionFeatures,
    tool_counts: dict[str, int],
    completion_state: str | None = None,
) -> str | None:
    """Decide whether retrieval already produced enough for writer handoff.

    Mirrors and replaces ``_maybe_force_writer_after_retrieval`` in
    ``supervisor.py`` once the migration is complete. ``tool_counts`` should
    be a dict of normalized tool names -> count of completed batches in the
    current turn.

    ``completion_state`` is the typed marker from
    ``specialist_results_v3.merge.completion_state`` (Phase 6). When the
    specialist explicitly reported ``minimal_bundle_ready``, the planner
    short-circuits to writer regardless of substring features.

    Returns the human-readable reason (used in ``routing_log``) or ``None``.
    """
    tool_names = {n for n, c in tool_counts.items() if c > 0}
    if "final_answer" in tool_names:
        return None

    cs = str(completion_state or "").strip()
    if cs == "minimal_bundle_ready":
        return "retrieval_completion_minimal_bundle"
    if cs == "writer_ready":
        return "retrieval_completion_writer_ready"

    if "workspace_inspect" in tool_names and features.asks_for_workspace_stats:
        return "retrieval_completion_workspace_stats"

    if (
        {"find_works", "paper_profile"}.issubset(tool_names)
        and not features.asks_for_compare
        and features.asks_for_catalog_resolution
    ):
        return "retrieval_completion_catalog_resolution"

    if (
        tool_counts.get("find_works", 0) >= 2
        and tool_counts.get("paper_profile", 0) >= 2
        and features.asks_for_dual_evidence
    ):
        if (
            features.asks_for_bibliography_gost
            and tool_counts.get("format_bibliography_gost", 0) < 1
        ):
            return None
        if features.asks_for_quotes and not any(
            tool_counts.get(t, 0) > 0 for t in ("paper_quote_search", "idea_search")
        ):
            return None
        return "retrieval_completion_dual_evidence_compare"

    if (
        any(t in tool_names for t in ("paper_quote_search", "idea_search"))
        and features.asks_for_anchor_free_quote
    ):
        return "retrieval_completion_quote_evidence"
    return None


def question_features_from_state(*, question: str, workspace_id: str | None) -> QuestionFeatures:
    """Convenience wrapper used by supervisor when caching is not needed."""
    return extract_question_features(question=question, workspace_id=workspace_id)


def derive_retrieval_completion_state(
    *,
    features: QuestionFeatures,
    tool_counts: dict[str, int],
    has_payloads: bool,
) -> CompletionSignalId:
    """Pick a typed ``completion_state`` for a retrieval-specialist hop.

    Reuses :func:`planner_post_retrieval_handoff` so the producer-side signal
    and the consumer-side handoff cannot drift apart. When the planner would
    deterministically hand off to writer for this combination of features +
    tool counts, the specialist marks its leg as ``minimal_bundle_ready``.
    Otherwise, the leg is generic ``any_specialist_payload`` (or
    ``evidence_insufficient`` when the hop produced no usable payloads).
    """
    if not has_payloads:
        if features.asks_for_workspace_stats and tool_counts.get("workspace_inspect", 0) > 0:
            return "any_specialist_payload"
        return "evidence_insufficient"
    handoff = planner_post_retrieval_handoff(
        features=features,
        tool_counts=tool_counts,
    )
    if handoff is not None:
        return "minimal_bundle_ready"
    return "any_specialist_payload"


def derive_graph_completion_state(
    *,
    has_payloads: bool,
    edge_search_count: int,
    cypher_query_count: int,
) -> CompletionSignalId:
    """Pick a typed ``completion_state`` for a graph-specialist hop."""
    if not has_payloads and edge_search_count == 0 and cypher_query_count == 0:
        return "evidence_insufficient"
    if edge_search_count > 0 or cypher_query_count > 0:
        return "graph_traversal_needed"
    return "any_specialist_payload"


__all__ = [
    "build_route_plan",
    "derive_graph_completion_state",
    "derive_retrieval_completion_state",
    "planner_post_retrieval_handoff",
    "question_features_from_state",
]
