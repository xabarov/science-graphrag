"""Unit tests for runtime terminal_reason resolution (Phase 3)."""

from __future__ import annotations

from science_graphrag.agent.final_answer_validation import (
    REASON_GENERIC_FALLBACK_WITH_EVIDENCE,
    validate_final_answer,
)
from science_graphrag.agent.runtime_answer_salvage import RUNTIME_FALLBACK_ANSWER
from science_graphrag.agent.terminal_reason import (
    budget_pressure_detected,
    compute_audit_diagnostics,
    debug_events_has_budget_cutoff,
    resolve_terminal_reason,
    routing_log_indicates_coordinator_gate_fallback,
)


def test_routing_log_coordinator_gate_without_retrieval() -> None:
    routing = [
        {
            "from": "supervisor",
            "to": "writer_agent",
            "reason": "coordinator_gate:no_tools",
        }
    ]
    assert routing_log_indicates_coordinator_gate_fallback(routing) is True


def test_routing_log_coordinator_gate_with_retrieval_not_fallback() -> None:
    routing = [
        {"from": "supervisor", "to": "retrieval_agent", "reason": "first_hop"},
        {"from": "supervisor", "to": "writer_agent", "reason": "coordinator_gate:x"},
    ]
    assert routing_log_indicates_coordinator_gate_fallback(routing) is False


def test_budget_pressure_from_debug_event() -> None:
    assert debug_events_has_budget_cutoff(
        [{"type": "budget_stop_decision", "code": "agent_response_budget_cutoff"}]
    )
    assert budget_pressure_detected(
        routing_log=None,
        debug_events=[{"type": "warning", "code": "agent_response_budget_cutoff"}],
    )


def test_resolve_final_answer_ok() -> None:
    verdict = validate_final_answer(
        answer="Grounded answer.",
        citations=[{"url": "https://example.org"}],
    )
    reason = resolve_terminal_reason(
        answer="Grounded answer.",
        validation_verdict=verdict,
        tool_trace=[type("T", (), {"tool": "final_answer"})()],
    )
    assert reason == "final_answer_ok"


def test_resolve_coordinator_gate_fallback() -> None:
    verdict = validate_final_answer(
        answer=RUNTIME_FALLBACK_ANSWER,
        citations=[],
    )
    reason = resolve_terminal_reason(
        answer=RUNTIME_FALLBACK_ANSWER,
        validation_verdict=verdict,
        routing_log=[
            {
                "from": "supervisor",
                "to": "writer_agent",
                "reason": "coordinator_gate:clarify",
            }
        ],
        fallback_answer_used=True,
    )
    assert reason == "coordinator_gate_fallback"


def test_resolve_budget_exhausted_with_partial() -> None:
    verdict = validate_final_answer(
        answer="Partial synthesis with explicit limitations on metadata-only sources.",
        citations=[{"work_id": "w1"}],
        specialist_results_v3={"merge": {"completion_state": "partial"}},
    )
    partial_text = "Partial synthesis with explicit limitations on metadata-only sources."
    reason = resolve_terminal_reason(
        answer=partial_text,
        validation_verdict=verdict,
        routing_log=[{"reason": "budget_exhausted", "to": "writer_agent"}],
        partial_salvage_applied=True,
    )
    assert reason == "budget_exhausted_with_partial"


def test_resolve_validation_failed_generic_fallback_with_evidence() -> None:
    verdict = validate_final_answer(
        answer=RUNTIME_FALLBACK_ANSWER,
        citations=[{"work_id": "w1"}],
    )
    assert REASON_GENERIC_FALLBACK_WITH_EVIDENCE in verdict["reasons"]
    reason = resolve_terminal_reason(
        answer=RUNTIME_FALLBACK_ANSWER,
        validation_verdict=verdict,
        routing_log=[{"reason": "post_retrieval_handoff", "to": "writer_agent"}],
        fallback_answer_used=True,
    )
    assert reason == "validation_failed"


def test_compute_audit_diagnostics_missing_final_answer_tool() -> None:
    diag = compute_audit_diagnostics(tool_trace=[type("T", (), {"tool": "web_search"})()])
    assert diag["tool_trace_missing_final_answer"] is True


def test_resolve_budget_exhausted_without_evidence() -> None:
    verdict = validate_final_answer(answer=RUNTIME_FALLBACK_ANSWER, citations=[])
    reason = resolve_terminal_reason(
        answer=RUNTIME_FALLBACK_ANSWER,
        validation_verdict=verdict,
        routing_log=[{"reason": "budget_exhausted", "to": "writer_agent"}],
    )
    assert reason == "budget_exhausted_without_evidence"


def test_resolve_validation_failed_on_empty_answer() -> None:
    verdict = validate_final_answer(answer="", citations=[])
    reason = resolve_terminal_reason(
        answer="",
        validation_verdict=verdict,
    )
    assert reason == "validation_failed"


def test_resolve_partial_final_answer_without_budget() -> None:
    verdict = validate_final_answer(
        answer="Partial answer with explicit limitations on metadata-only sources.",
        citations=[{"work_id": "w1"}],
        specialist_results_v3={"merge": {"completion_state": "partial"}},
    )
    reason = resolve_terminal_reason(
        answer="Partial answer with explicit limitations on metadata-only sources.",
        validation_verdict=verdict,
        tool_trace=[type("T", (), {"tool": "final_answer"})()],
    )
    assert reason == "partial_final_answer"
