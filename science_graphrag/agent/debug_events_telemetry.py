"""Aggregate ``debug_events`` rows into compact ``run_metadata`` telemetry (SSE + sync JSON)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class _TelemetryAccum:  # pylint: disable=too-few-public-methods
    """Mutable accumulator for a single pass over ``debug_events``."""

    __slots__ = (
        "shortlist_ratios",
        "deferred_schema_hits",
        "budget_stop_reasons",
        "miss_no_discovery",
        "activation_rates",
        "microcompact_triggers",
    )

    def __init__(self) -> None:
        self.shortlist_ratios: list[float] = []
        self.deferred_schema_hits = 0
        self.budget_stop_reasons: list[str] = []
        self.miss_no_discovery = 0
        self.activation_rates: list[float] = []
        self.microcompact_triggers = 0


def _accum_tool_search_result(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    raw_ratio = ev.get("shortlist_ratio")
    try:
        acc.shortlist_ratios.append(float(raw_ratio))
    except (TypeError, ValueError):
        pass
    refs = ev.get("deferred_schema_refs")
    if isinstance(refs, list) and refs:
        acc.deferred_schema_hits += 1
    try:
        acc.miss_no_discovery += int(ev.get("tool_search_miss_due_to_no_discovery") or 0)
    except (TypeError, ValueError):
        pass
    raw_ar = ev.get("deferred_tool_activation_rate")
    if raw_ar is None:
        return
    try:
        acc.activation_rates.append(float(raw_ar))
    except (TypeError, ValueError):
        pass


def _accum_budget_stop_decision(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    reason = str(ev.get("code") or "").strip()
    if reason:
        acc.budget_stop_reasons.append(reason)


def _accum_tool_message_compact_audit(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    try:
        acc.microcompact_triggers += int(ev.get("tool_message_microcompact_triggered_count") or 0)
    except (TypeError, ValueError):
        pass


_EVENT_HANDLERS: dict[str, Callable[[dict[str, Any], _TelemetryAccum], None]] = {
    "tool_search_result": _accum_tool_search_result,
    "budget_stop_decision": _accum_budget_stop_decision,
    "tool_message_compact_audit": _accum_tool_message_compact_audit,
}


def extract_runtime_telemetry_from_debug_events(
    debug_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate shortlist/budget telemetry from debug events for run_metadata."""
    acc = _TelemetryAccum()
    for ev in debug_events:
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("type") or "")
        handler = _EVENT_HANDLERS.get(etype)
        if handler is not None:
            handler(ev, acc)

    telemetry: dict[str, Any] = {}
    if acc.shortlist_ratios:
        telemetry["tool_search_shortlist_ratio_avg"] = round(
            sum(acc.shortlist_ratios) / len(acc.shortlist_ratios), 4
        )
    if acc.deferred_schema_hits:
        telemetry["tool_search_deferred_schema_events"] = acc.deferred_schema_hits
    if acc.budget_stop_reasons:
        telemetry["budget_stop_reasons"] = acc.budget_stop_reasons
    if acc.miss_no_discovery:
        telemetry["tool_search_miss_due_to_no_discovery"] = int(acc.miss_no_discovery)
    if acc.activation_rates:
        telemetry["deferred_tool_activation_rate"] = round(
            sum(acc.activation_rates) / len(acc.activation_rates), 4
        )
    if acc.microcompact_triggers > 0:
        telemetry["tool_message_microcompact_triggered_count"] = int(acc.microcompact_triggers)
    return telemetry
