"""Refresh / stale policy for thread insight snapshots."""

from __future__ import annotations

from typing import Any

from science_graphrag.agent.context.thread_insights_helpers import (
    RefreshDecision,
    StaleReason,
    _built_turn_from_prev_insight,
    _freshness_flags,
)
from science_graphrag.config import Settings


def decide_refresh(  # pylint: disable=too-many-return-statements
    *,
    digests: list[dict[str, Any]],
    turn_counter: int,
    prev_insight: dict[str, Any] | None,
    meta: dict[str, Any],
    settings: Settings,
) -> tuple[RefreshDecision, StaleReason | None]:
    """Explicit refresh/skip branches (policy table)."""
    min_d = int(settings.agent_thread_insights_min_digests)
    if len(digests) < min_d:
        return "skip_below_threshold", None

    circuit = meta.get("insight_circuit") if isinstance(meta.get("insight_circuit"), dict) else {}
    open_until = int(circuit.get("open_until_turn") or 0)
    if open_until and turn_counter < open_until:
        return "skip_circuit_open", None

    if settings.agent_thread_insights_force_manual_stale:
        return "refresh", "manual"

    if not isinstance(prev_insight, dict):
        return "refresh", None

    built_turn = _built_turn_from_prev_insight(prev_insight)
    if not built_turn:
        return "refresh", "turn_delta"

    td, ttl_hit, churn_hit = _freshness_flags(
        digests=digests,
        turn_counter=turn_counter,
        built_turn=built_turn,
        prev_insight=prev_insight,
        settings=settings,
    )
    if not td and not ttl_hit and not churn_hit:
        return "skip_fresh", None
    if churn_hit:
        return "refresh", "high_churn"
    if ttl_hit:
        return "refresh", "ttl"
    return "refresh", "turn_delta"
