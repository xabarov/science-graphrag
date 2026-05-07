"""Declarative orchestration plan (Phase 1, orchestration stabilization 2026-05-07).

Replaces ad-hoc imperative ``if route_hint == X`` chains in
``supervisor_node`` with an explicit ``RoutePlan`` produced by the planner
(see :mod:`science_graphrag.agent.coordination.route_planner`) and consumed by
the supervisor (see :mod:`science_graphrag.agent.graph.supervisor`).

Design notes:

* ``RoutePlan`` is **declarative**: a list of ordered ``RouteStep`` entries
  plus a ``TerminationRule`` and an optional ``replan_signal``.
* ``CompletionSignal`` is a **typed** marker (``Literal``-style ``str`` enum).
  Substring/regex inspection of the user prompt happens **only** in the
  feature extractor (see ``question_features``); planner rules consume
  features, never the raw text.
* The plan is serialized into ``state.metadata.turn_policy.route_plan`` so
  trace/SSE/debug stay backward compatible with legacy runs that have no
  plan attached.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

# Schema version for ``state.metadata.turn_policy.route_plan``.
# Bump when the on-the-wire shape changes incompatibly.
ROUTE_PLAN_SCHEMA_VERSION: int = 1

Specialist = Literal["retrieval_agent", "graph_agent", "writer_agent"]
TerminationRuleId = Literal[
    "writer_after_steps",
    "writer_after_first_hop_completion",
    "writer_immediate",
    "default_supervisor_round_cap",
]
ReplanReason = Literal[
    "evidence_insufficient",
    "needs_graph_traversal",
    "specialist_failure",
    "explicit_route_hint",
]
CompletionSignalId = Literal[
    "minimal_bundle_ready",
    "evidence_insufficient",
    "partial_failure_recoverable",
    "graph_traversal_needed",
    "writer_ready",
    "any_specialist_payload",
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompletionSignal:
    """Typed completion marker emitted by a specialist (or planner heuristic)."""

    signal_id: CompletionSignalId
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view for state metadata serialization."""
        return {"signal_id": str(self.signal_id), "detail": str(self.detail or "")}


@dataclass(frozen=True)
class RouteStep:
    """One ordered specialist hop expected by the planner."""

    specialist: Specialist
    expected_completion: tuple[CompletionSignalId, ...] = ()
    budget_hint: int | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view for state metadata serialization."""
        return {
            "specialist": str(self.specialist),
            "expected_completion": [str(x) for x in self.expected_completion],
            "budget_hint": (None if self.budget_hint is None else int(self.budget_hint)),
            "reason": str(self.reason or ""),
        }


@dataclass(frozen=True)
class TerminationRule:
    """Rule that decides when the plan hands off to writer / END."""

    rule_id: TerminationRuleId
    after_steps: int | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view for state metadata serialization."""
        return {
            "rule_id": str(self.rule_id),
            "after_steps": (None if self.after_steps is None else int(self.after_steps)),
            "reason": str(self.reason or ""),
        }


@dataclass(frozen=True)
class RoutePlan:
    """Declarative orchestration plan for one agent turn."""

    steps: tuple[RouteStep, ...]
    termination: TerminationRule
    planner: str = "deterministic_v1"
    replan_signal: ReplanReason | None = None
    schema_version: int = ROUTE_PLAN_SCHEMA_VERSION
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict view for state metadata serialization."""
        return {
            "schema_version": int(self.schema_version),
            "planner": str(self.planner),
            "steps": [s.to_dict() for s in self.steps],
            "termination": self.termination.to_dict(),
            "replan_signal": (None if self.replan_signal is None else str(self.replan_signal)),
            "notes": [str(x) for x in self.notes],
        }

    def first_step(self) -> RouteStep | None:
        """Return the head step (or None for empty plans)."""
        return self.steps[0] if self.steps else None

    def step_for_index(self, index: int) -> RouteStep | None:
        """Return the step at ``index`` or None when the index is out of range."""
        if 0 <= index < len(self.steps):
            return self.steps[index]
        return None


# ---------------------------------------------------------------------------
# Serialization helpers (state metadata <-> dataclasses)
# ---------------------------------------------------------------------------


def _coerce_specialist(raw: Any) -> Specialist | None:
    s = str(raw or "").strip()
    if s in {"retrieval_agent", "graph_agent", "writer_agent"}:
        return s  # type: ignore[return-value]
    return None


def _coerce_signals(raw: Any) -> tuple[CompletionSignalId, ...]:
    out: list[CompletionSignalId] = []
    if not isinstance(raw, (list, tuple)):
        return tuple(out)
    for item in raw:
        s = str(item or "").strip()
        if s in {
            "minimal_bundle_ready",
            "evidence_insufficient",
            "partial_failure_recoverable",
            "graph_traversal_needed",
            "writer_ready",
            "any_specialist_payload",
        }:
            out.append(s)  # type: ignore[arg-type]
    return tuple(out)


def deserialize_route_plan(payload: Any) -> RoutePlan | None:
    """Best-effort reverse of :meth:`RoutePlan.to_dict`. Returns None if invalid."""
    if not isinstance(payload, dict):
        return None
    try:
        steps_raw = payload.get("steps")
        steps: list[RouteStep] = []
        if isinstance(steps_raw, list):
            for s in steps_raw:
                if not isinstance(s, dict):
                    continue
                spec = _coerce_specialist(s.get("specialist"))
                if spec is None:
                    continue
                bh = s.get("budget_hint")
                steps.append(
                    RouteStep(
                        specialist=spec,
                        expected_completion=_coerce_signals(s.get("expected_completion")),
                        budget_hint=(int(bh) if isinstance(bh, int) else None),
                        reason=str(s.get("reason") or ""),
                    )
                )
        term_raw = payload.get("termination") or {}
        rule_id = str((term_raw or {}).get("rule_id") or "default_supervisor_round_cap")
        if rule_id not in {
            "writer_after_steps",
            "writer_after_first_hop_completion",
            "writer_immediate",
            "default_supervisor_round_cap",
        }:
            rule_id = "default_supervisor_round_cap"
        after_raw = (term_raw or {}).get("after_steps")
        termination = TerminationRule(
            rule_id=rule_id,  # type: ignore[arg-type]
            after_steps=(int(after_raw) if isinstance(after_raw, int) else None),
            reason=str((term_raw or {}).get("reason") or ""),
        )
        replan_raw = payload.get("replan_signal")
        replan: ReplanReason | None = None
        if isinstance(replan_raw, str) and replan_raw in {
            "evidence_insufficient",
            "needs_graph_traversal",
            "specialist_failure",
            "explicit_route_hint",
        }:
            replan = replan_raw  # type: ignore[assignment]
        notes_raw = payload.get("notes")
        notes: tuple[str, ...] = (
            tuple(str(x) for x in notes_raw) if isinstance(notes_raw, list) else tuple()
        )
        return RoutePlan(
            steps=tuple(steps),
            termination=termination,
            planner=str(payload.get("planner") or "deterministic_v1"),
            replan_signal=replan,
            schema_version=int(payload.get("schema_version") or ROUTE_PLAN_SCHEMA_VERSION),
            notes=notes,
        )
    except (TypeError, ValueError):
        return None


def route_plan_from_metadata(metadata: Any) -> RoutePlan | None:
    """Read RoutePlan from ``state.metadata.turn_policy.route_plan`` if present."""
    if not isinstance(metadata, dict):
        return None
    tp = metadata.get("turn_policy") if isinstance(metadata.get("turn_policy"), dict) else None
    if not isinstance(tp, dict):
        return None
    return deserialize_route_plan(tp.get("route_plan"))


__all__ = [
    "ROUTE_PLAN_SCHEMA_VERSION",
    "CompletionSignal",
    "CompletionSignalId",
    "ReplanReason",
    "RoutePlan",
    "RouteStep",
    "Specialist",
    "TerminationRule",
    "TerminationRuleId",
    "deserialize_route_plan",
    "route_plan_from_metadata",
]
