"""Pure decision helpers extracted from ``supervisor_node`` (Phase 7.1).

Each function in this module is **side-effect free**: it only reads
``AgentState`` and ``Settings`` and returns a small dataclass / Optional
string. All I/O (LangGraph state mutation, LLM calls, span events) stays in
``science_graphrag.agent.graph.supervisor``.

Boundaries (historical design ref: ``docs/analysis/_archive/orchestration-stabilization-plan-2026-05-07.md`` §4):

* ``compute_first_hop_decision``       — replaces inline ``if not prior``
  block in ``supervisor_node`` and resolves the first hop via the same
  planner contract whether the plan came from state metadata or was
  reconstructed on demand for older/no-plan states.
* ``compute_post_retrieval_handoff``   — asks the planner-based
  ``planner_post_retrieval_handoff`` over typed question features and
  completion-state markers.
* ``compute_round_cap_decision``       — replaces the supervisor round cap
  branch.
* ``should_skip_llm_router``           — answers Phase 4: did the plan
  already pre-decide the next hop, or do we need ``maybe_replan`` (LLM call)?
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.messages import HumanMessage

from science_graphrag.agent.coordination.question_features import (
    QuestionFeatures,
    extract_question_features,
)
from science_graphrag.agent.coordination.route_plan import (
    RoutePlan,
    route_plan_from_metadata,
)
from science_graphrag.agent.coordination.route_planner import (
    build_route_plan,
    planner_post_retrieval_handoff as _planner_post_retrieval_handoff,
)
from science_graphrag.agent.coordination.turn_policy import TurnPolicy
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.tracing import collect_tool_execution_steps
from science_graphrag.agent.llm.chat import (
    agent_chat_transport_max_attempts,
    ensure_messages_safe_for_generation,
)
from science_graphrag.llm.concurrency import invoke_chat_gated
from science_graphrag.observability.spans import (
    SpanAttributes,
    add_span_event,
    chain_span,
    llm_span,
)

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


def _turn_policy_from_state_inputs(
    *,
    state: AgentState,
    tool_policy: str,
    route_hint: str,
    answer_class: str,
) -> TurnPolicy:
    """Reconstruct a minimal ``TurnPolicy`` for no-plan states."""
    meta = state.get("metadata") or {}
    raw_tp = meta.get("turn_policy") if isinstance(meta, dict) else None
    tp = raw_tp if isinstance(raw_tp, dict) else {}
    conversation_intent = str(tp.get("conversation_intent") or "research_task").strip()
    if conversation_intent not in {"research_task", "small_talk", "meta", "ambiguous"}:
        conversation_intent = "research_task"
    classifier = str(tp.get("classifier") or "fallback").strip()
    if classifier not in {"deterministic", "llm", "fallback"}:
        classifier = "fallback"
    try:
        confidence = float(tp.get("confidence", 1.0) or 1.0)
    except Exception:  # noqa: BLE001
        confidence = 1.0
    return TurnPolicy(
        conversation_intent=conversation_intent,  # type: ignore[arg-type]
        tool_policy=str(tool_policy or "allow_tools").strip() or "allow_tools",  # type: ignore[arg-type]
        route_hint=str(route_hint or "").strip() or "retrieval_agent",  # type: ignore[arg-type]
        reason=str(tp.get("reason") or "planner_fallback_from_state").strip()
        or "planner_fallback_from_state",
        suggested_answer_class=str(answer_class or "").strip() or "grounded_explanation",
        confidence=confidence,
        classifier=classifier,  # type: ignore[arg-type]
    )


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

    1. Persisted RoutePlan from ``metadata.turn_policy.route_plan``.
    2. If the state has no persisted plan, rebuild a transient RoutePlan from
       the same ``QuestionFeatures`` + ``TurnPolicy`` inputs.
    3. Only when the planner yields no step do we fall through to the LLM router.
    """
    if tool_policy != "allow_tools":
        return None

    plan = _route_plan(state)
    if plan is None and bool(getattr(settings, "agent_route_plan_enabled", False)):
        feats = _features_from_state(state)
        transient_tp = _turn_policy_from_state_inputs(
            state=state,
            tool_policy=tool_policy,
            route_hint=route_hint,
            answer_class=answer_class,
        )
        plan = build_route_plan(features=feats, turn_policy=transient_tp, settings=settings)
    if plan is not None and plan.steps:
        first = plan.first_step()
        if first is not None:
            return FirstHopDecision(
                specialist=str(first.specialist),
                reason=first.reason or "route_plan_first_step",
                extra={"route_hint": route_hint or None, "from_route_plan": True},
            )
    return None


def compute_post_retrieval_handoff(
    *,
    state: AgentState,
    settings: Any,  # pylint: disable=unused-argument  # reserved for future per-flag overrides
) -> str | None:
    """Decide whether retrieval finished and writer can take over.

    Always reads features through :func:`extract_question_features` and asks
    :func:`planner_post_retrieval_handoff` — the same path the planner uses
    when a ``RoutePlan`` is attached. The legacy `legacy_fn` parameter and
    the parallel substring tables in ``supervisor.py`` are gone as of
    2026-05-08; substring rules live in
    :mod:`science_graphrag.agent.coordination.question_features` only.
    """
    if str(state.get("current_specialist") or "").strip() != RETRIEVAL_SPECIALIST:
        return None

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


_LLM_ROUTING_PROMPT = """You are a supervisor for scholarly research agents.
Available specialists:
- retrieval_agent: workspace inventory (workspace_inspect), full-text work search (find_works),
  paper profiles, semantic idea_search / paper_quote_search, bibliography formatting
- graph_agent: structural graph only — edge neighborhoods and read-only Cypher (no full-text work search)
- writer_agent: synthesize final answer with citations

If the user needs to find papers by title, author name fragment, or keywords without a known work id,
prefer retrieval_agent (find_works). Use graph_agent when the question is about relations, paths,
or patterns between known entities.

If the user compares two papers inside a workspace using catalog tools (find_works + paper_profile)
without explicit graph vocabulary (neighbors, paths, cypher, edge_search), prefer retrieval_agent —
do not start with graph_agent.

When the question requires mixed corpus evidence (semantic chunks plus verbatim quotes), keep routing
to retrieval_agent until idea_search / paper_quote_search have been tried unless specialist_results
already show those paths failed.

Given the user question and accumulated specialist_results, decide the next specialist.
Respond with exactly one token:
retrieval_agent | graph_agent | writer_agent | FINISH
"""

_ROUTE_FINISH_TOKEN = "finish"


@dataclass(frozen=True)
class ReplanDecision:
    """Result of ``maybe_replan_via_llm``."""

    specialist: str
    finish_remapped: bool
    invalid_token: bool


def _build_llm_route_messages(state: AgentState) -> list[HumanMessage]:
    """Provider-safe routing prompt assembled without tool-call replay.

    Mirrors the previous private helper in ``supervisor.py``; lives here
    to keep the LLM-routing seam self-contained.
    """
    specialist_context = str(state.get("specialist_results") or {})
    user_question = first_user_plain_question(state)
    v3_merge = ""
    v3 = state.get("specialist_results_v3")
    if isinstance(v3, dict):
        merge = v3.get("merge")
        if isinstance(merge, dict):
            v3_merge = json.dumps(merge, ensure_ascii=True, default=str)[:4000]
    msgs = [
        HumanMessage(content=_LLM_ROUTING_PROMPT),
        HumanMessage(content=f"user_question={user_question[:4000]}"),
        HumanMessage(content=f"specialist_results={specialist_context[:12000]}"),
    ]
    if v3_merge:
        msgs.append(HumanMessage(content=f"specialist_results_v3_merge={v3_merge}"))
    return msgs


def maybe_replan_via_llm(
    *,
    state: AgentState,
    settings: Any,
    llm: Any,
    invoke: Callable[..., Any] = invoke_chat_gated,
    budget_left: int,
) -> ReplanDecision:
    """Invoke the LLM router and normalize its single-token output.

    Encapsulates everything that used to live inline in ``supervisor_node``:
    prompt assembly, span emission, transport policy attributes, the FINISH
    -> writer remap (writer must own the terminal ``final_answer`` contract),
    and the invalid-token fallback. Returns a typed :class:`ReplanDecision`
    so the supervisor only deals with routing-log emission.
    """
    valid = {RETRIEVAL_SPECIALIST, GRAPH_SPECIALIST, WRITER_SPECIALIST, _ROUTE_FINISH_TOKEN}
    route_msgs = _build_llm_route_messages(state)
    transport = float(getattr(settings, "extraction_llm_timeout_seconds", 60.0))
    max_attempts = agent_chat_transport_max_attempts(settings)
    with chain_span(
        "agent.supervisor.route",
        {"agent.budget_remaining": int(budget_left)},
    ):
        with llm_span(
            "llm.agent.supervisor_route",
            {
                **SpanAttributes.llm_runtime_policy_attributes(
                    pool_name="agent_chat",
                    transport_timeout_seconds=transport,
                    timeout_contract="transport_with_operation_deadline",
                    retry_extra_budget=0,
                    operation_deadline_seconds=min(900.0, transport * float(max_attempts)),
                    transport_max_attempts=max_attempts,
                ),
                "llm.invocation_name": "agent_supervisor_route",
            },
        ):
            response = invoke(
                llm,
                ensure_messages_safe_for_generation(route_msgs),
                pool_name="agent_chat",
                settings=settings,
            )
    choice = str(getattr(response, "content", "") or "").strip().lower()
    invalid_token = choice not in valid
    if invalid_token:
        add_span_event(
            "agent.supervisor.invalid_route_token",
            {"token": choice[:80]},
        )
        choice = WRITER_SPECIALIST
    selected = choice
    finish_remapped = False
    if selected == _ROUTE_FINISH_TOKEN:
        # Writer owns the terminal ``final_answer`` contract; END skips that.
        selected = WRITER_SPECIALIST
        finish_remapped = True
        add_span_event(
            "agent.supervisor.finish_remapped_to_writer",
            {"budget_left": int(budget_left)},
        )
    add_span_event(
        "agent.supervisor.route_selected",
        {"to": selected, "budget_left": int(budget_left)},
    )
    return ReplanDecision(
        specialist=selected,
        finish_remapped=finish_remapped,
        invalid_token=invalid_token,
    )


__all__ = [
    "FirstHopDecision",
    "ReplanDecision",
    "RoundCapDecision",
    "compute_first_hop_decision",
    "compute_post_retrieval_handoff",
    "compute_round_cap_decision",
    "first_user_plain_question",
    "maybe_replan_via_llm",
    "normalized_question",
    "should_skip_llm_router",
]
