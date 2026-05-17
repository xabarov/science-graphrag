"""Runtime-owned terminal outcome vocabulary (smolagents Phase 3).

``terminal_reason`` describes how a turn ended from the runtime's perspective.
Audit-only mismatch signals (tool trace vs Phoenix) live in
``audit_diagnostics`` and must not overwrite ``terminal_reason``.
"""

from __future__ import annotations

from typing import Any, Literal

from science_graphrag.agent.final_answer_policy import has_completed_final_answer_tool
from science_graphrag.agent.final_answer_validation import (
    REASON_GENERIC_FALLBACK_WITH_EVIDENCE,
    AnswerKind,
    classify_answer_kind,
    is_generic_fallback_answer,
)
TerminalReason = Literal[
    "final_answer_ok",
    "partial_final_answer",
    "budget_exhausted_with_partial",
    "budget_exhausted_without_evidence",
    "coordinator_gate_fallback",
    "validation_failed",
]

# Documented vocabulary; computed only in live/audit harnesses, not in runtime terminal_reason.
AUDIT_TOOL_TRACE_MISSING_FINAL_ANSWER = "tool_trace_missing_final_answer"
AUDIT_PHOENIX_MISSING_FINAL_ANSWER_SPAN = "phoenix_missing_final_answer_span"

_BUDGET_CUTOFF_CODES = frozenset(
    {
        "agent_response_budget_cutoff",
    }
)


def _merge_block(specialist_results_v3: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(specialist_results_v3, dict):
        return {}
    merge = specialist_results_v3.get("merge")
    return merge if isinstance(merge, dict) else {}


def routing_log_has_budget_exhausted(routing_log: list[dict[str, Any]] | None) -> bool:
    for entry in list(routing_log or []):
        if not isinstance(entry, dict):
            continue
        if str(entry.get("reason") or "").strip() == "budget_exhausted":
            return True
    return False


def routing_log_indicates_coordinator_gate_fallback(
    routing_log: list[dict[str, Any]] | None,
) -> bool:
    """True when supervisor routed writer-only via coordinator gate without retrieval."""
    legs = [x for x in list(routing_log or []) if isinstance(x, dict)]
    if not legs:
        return False
    has_coordinator = any(
        "coordinator_gate" in str(entry.get("reason") or "") for entry in legs
    )
    if not has_coordinator:
        return False
    has_retrieval_leg = any(
        str(entry.get("to") or "").strip() == "retrieval_agent" for entry in legs
    )
    return not has_retrieval_leg


def debug_events_has_budget_cutoff(debug_events: list[dict[str, Any]] | None) -> bool:
    for ev in list(debug_events or []):
        if not isinstance(ev, dict):
            continue
        etype = str(ev.get("type") or "")
        code = str(ev.get("code") or "")
        if etype == "budget_stop_decision" and code in _BUDGET_CUTOFF_CODES:
            return True
        if etype == "warning" and code in _BUDGET_CUTOFF_CODES:
            return True
    return False


def budget_pressure_detected(
    *,
    routing_log: list[dict[str, Any]] | None,
    debug_events: list[dict[str, Any]] | None,
    deadline_partial_used: bool = False,
) -> bool:
    return (
        deadline_partial_used
        or routing_log_has_budget_exhausted(routing_log)
        or debug_events_has_budget_cutoff(debug_events)
    )


def tool_trace_has_final_answer(tool_trace: list[Any]) -> bool:
    for entry in list(tool_trace or []):
        name = getattr(entry, "tool", None) if not isinstance(entry, dict) else entry.get("tool")
        if str(name or "").strip() == "final_answer":
            return True
    return False


def compute_audit_diagnostics(
    *,
    tool_trace: list[Any] | None,
    messages: list[Any] | None = None,
) -> dict[str, bool]:
    """Audit-layer signals; independent from runtime ``terminal_reason``."""
    has_trace_final = tool_trace_has_final_answer(tool_trace)
    completed = has_completed_final_answer_tool(list(messages or [])) if messages else False
    return {
        AUDIT_TOOL_TRACE_MISSING_FINAL_ANSWER: bool(
            (messages and not completed) or (tool_trace is not None and not has_trace_final)
        ),
    }


def resolve_terminal_reason(
    *,
    answer: str,
    validation_verdict: dict[str, Any],
    specialist_results_v3: dict[str, Any] | None = None,
    routing_log: list[dict[str, Any]] | None = None,
    debug_events: list[dict[str, Any]] | None = None,
    tool_trace: list[Any] | None = None,
    messages: list[Any] | None = None,
    fallback_answer_used: bool = False,
    deadline_partial_used: bool = False,
    partial_salvage_applied: bool = False,
) -> TerminalReason:
    """Pick a single runtime terminal reason from answer + turn context."""
    merge = _merge_block(specialist_results_v3)
    answer_kind: AnswerKind = validation_verdict.get("answer_kind") or classify_answer_kind(
        answer=answer, merge=merge
    )
    ev_present = bool(validation_verdict.get("evidence_present"))
    status = str(validation_verdict.get("status") or "ok")
    reasons = list(validation_verdict.get("reasons") or [])
    budget_hit = budget_pressure_detected(
        routing_log=routing_log,
        debug_events=debug_events,
        deadline_partial_used=deadline_partial_used,
    )
    coordinator_fallback = routing_log_indicates_coordinator_gate_fallback(routing_log)
    has_final_tool = tool_trace_has_final_answer(tool_trace) or (
        has_completed_final_answer_tool(list(messages or [])) if messages else False
    )

    if REASON_GENERIC_FALLBACK_WITH_EVIDENCE in reasons or (
        status == "fail" and is_generic_fallback_answer(answer) and ev_present
    ):
        if budget_hit and ev_present:
            return "budget_exhausted_with_partial"
        if coordinator_fallback:
            return "coordinator_gate_fallback"
        return "validation_failed"

    if coordinator_fallback and (
        fallback_answer_used
        or is_generic_fallback_answer(answer)
        or answer_kind in {"fallback", "empty"}
    ):
        return "coordinator_gate_fallback"

    if budget_hit:
        if (
            partial_salvage_applied
            or answer_kind == "partial"
            or (ev_present and not is_generic_fallback_answer(answer))
        ):
            return "budget_exhausted_with_partial"
        return "budget_exhausted_without_evidence"

    if answer_kind == "partial" or partial_salvage_applied:
        return "partial_final_answer"

    if status == "fail":
        return "validation_failed"

    if has_final_tool and answer_kind in {"complete", "partial"}:
        return "final_answer_ok"

    if is_generic_fallback_answer(answer) and not ev_present:
        return "budget_exhausted_without_evidence"

    if answer_kind == "empty":
        return "validation_failed"

    return "final_answer_ok"


def attach_terminal_reason_to_verdict(
    verdict: dict[str, Any],
    terminal_reason: TerminalReason,
) -> dict[str, Any]:
    """Return a copy of *verdict* with ``terminal_reason`` set."""
    out = dict(verdict)
    out["terminal_reason"] = terminal_reason
    return out


def build_terminal_outcome_debug_event(
    *,
    terminal_reason: TerminalReason,
    validation_verdict: dict[str, Any],
    audit_diagnostics: dict[str, bool] | None = None,
) -> dict[str, Any]:
    return {
        "type": "terminal_outcome",
        "terminal_reason": terminal_reason,
        "validation_status": validation_verdict.get("status"),
        "answer_kind": validation_verdict.get("answer_kind"),
        "audit_diagnostics": dict(audit_diagnostics or {}),
    }


def maybe_append_terminal_outcome_event(
    debug_events: list[dict[str, Any]],
    *,
    terminal_reason: TerminalReason,
    validation_verdict: dict[str, Any],
    audit_diagnostics: dict[str, bool] | None = None,
    replace_existing: bool = True,
) -> dict[str, Any]:
    if replace_existing:
        debug_events[:] = [
            ev
            for ev in debug_events
            if not (isinstance(ev, dict) and ev.get("type") == "terminal_outcome")
        ]
    event = build_terminal_outcome_debug_event(
        terminal_reason=terminal_reason,
        validation_verdict=validation_verdict,
        audit_diagnostics=audit_diagnostics,
    )
    debug_events.append(event)
    return event


__all__ = [
    "AUDIT_PHOENIX_MISSING_FINAL_ANSWER_SPAN",
    "AUDIT_TOOL_TRACE_MISSING_FINAL_ANSWER",
    "TerminalReason",
    "attach_terminal_reason_to_verdict",
    "budget_pressure_detected",
    "build_terminal_outcome_debug_event",
    "compute_audit_diagnostics",
    "debug_events_has_budget_cutoff",
    "maybe_append_terminal_outcome_event",
    "resolve_terminal_reason",
    "routing_log_has_budget_exhausted",
    "routing_log_indicates_coordinator_gate_fallback",
    "tool_trace_has_final_answer",
]
