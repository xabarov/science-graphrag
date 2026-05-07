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
        "schema_bytes_saved",
        "tool_use_summary_batches",
        "tool_use_summary_rows",
        "tool_use_summary_ratios",
        "runtime_monitor_events",
        "runtime_monitor_degraded_hits",
        "runtime_monitor_timeout_hits",
        "runtime_monitor_last",
        "mcp_audit_events",
        "mcp_audit_denies",
        "mcp_audit_failures",
        "mcp_audit_last",
        "lsp_audit_events",
        "lsp_audit_degraded_hits",
        "lsp_audit_timeout_hits",
        "lsp_audit_last",
    )

    def __init__(self) -> None:
        self.shortlist_ratios: list[float] = []
        self.deferred_schema_hits = 0
        self.budget_stop_reasons: list[str] = []
        self.miss_no_discovery = 0
        self.activation_rates: list[float] = []
        self.microcompact_triggers = 0
        self.schema_bytes_saved = 0
        self.tool_use_summary_batches = 0
        self.tool_use_summary_rows = 0
        self.tool_use_summary_ratios: list[float] = []
        self.runtime_monitor_events = 0
        self.runtime_monitor_degraded_hits = 0
        self.runtime_monitor_timeout_hits = 0
        self.runtime_monitor_last: dict[str, Any] | None = None
        self.mcp_audit_events = 0
        self.mcp_audit_denies = 0
        self.mcp_audit_failures = 0
        self.mcp_audit_last: dict[str, Any] | None = None
        self.lsp_audit_events = 0
        self.lsp_audit_degraded_hits = 0
        self.lsp_audit_timeout_hits = 0
        self.lsp_audit_last: dict[str, Any] | None = None


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
    if raw_ar is not None:
        try:
            acc.activation_rates.append(float(raw_ar))
        except (TypeError, ValueError):
            pass
    try:
        acc.schema_bytes_saved += int(ev.get("tool_schema_bytes_saved") or 0)
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


def _accum_runtime_monitor(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    acc.runtime_monitor_events += 1
    if bool(ev.get("degraded")):
        acc.runtime_monitor_degraded_hits += 1
    if bool(ev.get("timeout_hit")):
        acc.runtime_monitor_timeout_hits += 1
    acc.runtime_monitor_last = {
        "task_id": ev.get("task_id"),
        "state": ev.get("state"),
        "source": ev.get("source"),
        "degraded": bool(ev.get("degraded")) if ev.get("degraded") is not None else None,
        "timeout_hit": bool(ev.get("timeout_hit")) if ev.get("timeout_hit") is not None else None,
    }


def _accum_mcp_audit(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    acc.mcp_audit_events += 1
    phase = str(ev.get("phase") or "")
    if phase == "deny" or ev.get("deny_reason"):
        acc.mcp_audit_denies += 1
    if ev.get("ok") is False:
        acc.mcp_audit_failures += 1
    acc.mcp_audit_last = {
        "phase": phase or None,
        "server": ev.get("server"),
        "tool": ev.get("tool"),
        "resource_uri": ev.get("resource_uri"),
        "ok": ev.get("ok"),
        "deny_reason": ev.get("deny_reason"),
        "auth_status": ev.get("auth_status"),
    }


def _accum_lsp_audit(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    acc.lsp_audit_events += 1
    if bool(ev.get("degraded")):
        acc.lsp_audit_degraded_hits += 1
    if bool(ev.get("timeout_hit")):
        acc.lsp_audit_timeout_hits += 1
    acc.lsp_audit_last = {
        "operation": ev.get("operation"),
        "ok": ev.get("ok"),
        "payload_budget_items": ev.get("payload_budget_items"),
        "degraded": ev.get("degraded"),
        "timeout_hit": ev.get("timeout_hit"),
    }


def _accum_tool_use_summary_batch(ev: dict[str, Any], acc: _TelemetryAccum) -> None:
    acc.tool_use_summary_batches += 1
    try:
        acc.tool_use_summary_rows += int(ev.get("count") or 0)
    except (TypeError, ValueError):
        pass
    rows = ev.get("rows")
    if not isinstance(rows, list):
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        ratio = row.get("compression_ratio_vs_original")
        if isinstance(ratio, (int, float)):
            acc.tool_use_summary_ratios.append(float(ratio))


_EVENT_HANDLERS: dict[str, Callable[[dict[str, Any], _TelemetryAccum], None]] = {
    "tool_search_result": _accum_tool_search_result,
    "budget_stop_decision": _accum_budget_stop_decision,
    "tool_message_compact_audit": _accum_tool_message_compact_audit,
    "tool_use_summary_batch": _accum_tool_use_summary_batch,
    "runtime_monitor": _accum_runtime_monitor,
    "mcp_audit": _accum_mcp_audit,
    "lsp_audit": _accum_lsp_audit,
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
            continue
        # Legacy/alternate envelopes (keep tolerant).
        if etype == "streamable_tool_hint":
            inner = ev.get("hint") if isinstance(ev.get("hint"), dict) else ev
            if isinstance(inner, dict):
                it = str(inner.get("type") or "")
                h2 = _EVENT_HANDLERS.get(it)
                if h2 is not None:
                    h2(inner, acc)

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
    if acc.schema_bytes_saved > 0:
        telemetry["tool_schema_bytes_saved"] = int(acc.schema_bytes_saved)
    if acc.tool_use_summary_batches > 0:
        telemetry["tool_use_summary_batch_count"] = int(acc.tool_use_summary_batches)
    if acc.tool_use_summary_rows > 0:
        telemetry["tool_use_summary_row_count"] = int(acc.tool_use_summary_rows)
    if acc.tool_use_summary_ratios:
        telemetry["tool_use_summary_compression_ratio_avg"] = round(
            sum(acc.tool_use_summary_ratios) / len(acc.tool_use_summary_ratios), 4
        )
    if acc.runtime_monitor_events:
        rm: dict[str, Any] = {
            "event_count": int(acc.runtime_monitor_events),
            "degraded_hits": int(acc.runtime_monitor_degraded_hits),
            "timeout_hits": int(acc.runtime_monitor_timeout_hits),
        }
        if acc.runtime_monitor_last:
            rm["last"] = dict(acc.runtime_monitor_last)
        telemetry["runtime_monitor_audit"] = rm
    if acc.mcp_audit_events:
        mc: dict[str, Any] = {
            "event_count": int(acc.mcp_audit_events),
            "deny_hits": int(acc.mcp_audit_denies),
            "ok_false_hits": int(acc.mcp_audit_failures),
        }
        if acc.mcp_audit_last:
            mc["last"] = dict(acc.mcp_audit_last)
        telemetry["mcp_audit_summary"] = mc
    if acc.lsp_audit_events:
        ls: dict[str, Any] = {
            "event_count": int(acc.lsp_audit_events),
            "degraded_hits": int(acc.lsp_audit_degraded_hits),
            "timeout_hits": int(acc.lsp_audit_timeout_hits),
        }
        if acc.lsp_audit_last:
            ls["last"] = dict(acc.lsp_audit_last)
        telemetry["lsp_audit_summary"] = ls
    return telemetry
