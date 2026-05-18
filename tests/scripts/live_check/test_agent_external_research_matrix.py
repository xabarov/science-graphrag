from __future__ import annotations

from pathlib import Path

from scripts.live_check.agent_external_research_matrix import (
    _family_issues,
    _flags_for_families,
    evaluate_matrix_gates,
    load_matrix_cases,
)


def test_load_matrix_fixture_has_minimum_cases() -> None:
    fixture = (
        Path(__file__).resolve().parents[3] / "eval/fixtures/agent_external_research_matrix.json"
    )
    cases = load_matrix_cases(fixture, suite=None, suites_filter=None)
    assert len(cases) >= 20
    suites = {c["suite"] for c in cases}
    assert "corpus_only" in suites
    assert "product_official" in suites


def test_family_issues_detects_forbidden_web() -> None:
    issues = _family_issues(
        tool_names=["web_search", "final_answer"],
        expected=["final_answer"],
        forbidden=["web"],
    )
    assert "forbidden_family:web" in issues


def test_flags_for_families_official_web_lookup_counts_as_web() -> None:
    flags = _flags_for_families(["official_web_lookup", "final_answer"])
    assert flags["web"] is True
    assert flags["official"] is True


def test_evaluate_matrix_gates_uses_ratio_thresholds() -> None:
    gates = evaluate_matrix_gates(
        {
            "runtime_ok_cases": 12,
            "tool_trace_ok_cases": 11,
            "phoenix_ok_cases": 10,
            "matrix_ok_cases": 11,
            "with_final_answer": 16,
            "generic_fallback_with_evidence_cases": 0,
        },
        total_cases=20,
    )
    assert gates["all_ok"] is True
    assert gates["checks"]["runtime_ok_cases"]["minimum"] == 11
