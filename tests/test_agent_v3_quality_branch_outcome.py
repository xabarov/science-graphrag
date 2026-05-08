"""Branch outcome taxonomy for agent_v3_quality rows."""

from __future__ import annotations

from eval.agent_v3_quality.branch_outcome import (
    aggregate_branch_outcomes,
    branch_outcome_from_branch,
    classify_branch_error,
)


def test_classify_ok() -> None:
    oc = classify_branch_error(None)
    assert oc["status"] == "ok"
    assert oc["error_kind"] is None


def test_classify_subprocess_timeout() -> None:
    oc = classify_branch_error("subprocess_timeout_after_120.0s: Command timed out")
    assert oc["status"] == "timeout"
    assert oc["error_kind"] == "subprocess_timeout"
    assert oc["timeout_seconds"] == 120.0


def test_classify_subprocess_exit() -> None:
    oc = classify_branch_error("subprocess_exit_1: boom")
    assert oc["status"] == "error"
    assert oc["error_kind"] == "subprocess_nonzero_exit"


def test_branch_outcome_from_branch() -> None:
    oc = branch_outcome_from_branch({"error": "subprocess_timeout_after_5.0s: x"})
    assert oc["status"] == "timeout"


def test_aggregate_branch_outcomes() -> None:
    cases = [
        {
            "case_id": "a",
            "baseline_outcome": classify_branch_error("subprocess_timeout_after_1.0s: x"),
            "candidate_outcome": classify_branch_error(None),
        },
        {
            "case_id": "b",
            "baseline_outcome": classify_branch_error(None),
            "candidate_outcome": classify_branch_error("HTTPStatusError: 500"),
        },
    ]
    agg = aggregate_branch_outcomes(cases)
    assert agg["cases_with_any_branch_non_ok"] == 2
    assert agg["baseline_status_counts"]["timeout"] == 1
    assert agg["candidate_status_counts"]["error"] == 1
    assert "a" in agg["baseline_timeout_cases"]
