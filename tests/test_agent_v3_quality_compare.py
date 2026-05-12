"""Snapshot compare for v3 quality judge artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from eval.agent_v3_quality.compare import _cost_gate_violations, compare_reports


def test_compare_reports_delta(tmp_path: Path) -> None:
    a = {
        "review_version": "agent-v3-quality-judge-v1",
        "summary": {
            "case_count": 2,
            "mean_weighted_score_baseline": 4.0,
            "mean_weighted_score_candidate": 4.2,
            "mean_delta": 0.2,
            "pairwise_candidate_win_rate": 0.5,
            "pairwise_baseline_win_rate": 0.25,
            "pairwise_tie_rate": 0.25,
            "hard_fail_count_baseline": 0,
            "hard_fail_count_candidate": 0,
        },
    }
    b = {
        "review_version": "agent-v3-quality-judge-v1",
        "summary": {
            "case_count": 2,
            "mean_weighted_score_baseline": 4.0,
            "mean_weighted_score_candidate": 4.5,
            "mean_delta": 0.5,
            "pairwise_candidate_win_rate": 0.75,
            "pairwise_baseline_win_rate": 0.0,
            "pairwise_tie_rate": 0.25,
            "hard_fail_count_baseline": 0,
            "hard_fail_count_candidate": 0,
        },
    }
    p1 = tmp_path / "a.json"
    p2 = tmp_path / "b.json"
    p1.write_text(json.dumps(a), encoding="utf-8")
    p2.write_text(json.dumps(b), encoding="utf-8")
    out = compare_reports(p1, p2)
    assert out["deltas"]["mean_weighted_score_candidate"] == 0.3
    assert out["deltas"]["pairwise_candidate_win_rate"] == 0.25
    assert "cost_delta" not in out["deltas"]


def test_compare_reports_includes_cost_delta_delta(tmp_path: Path) -> None:
    a = {
        "review_version": "agent-v3-quality-judge-v1",
        "summary": {
            "case_count": 1,
            "mean_delta": 0.0,
            "cost_delta": {"latency_p95_ratio": 1.1, "tokens_total_ratio": 1.2},
        },
    }
    b = {
        "review_version": "agent-v3-quality-judge-v1",
        "summary": {
            "case_count": 1,
            "mean_delta": 0.1,
            "cost_delta": {"latency_p95_ratio": 1.3, "tokens_total_ratio": 1.4},
        },
    }
    p1 = tmp_path / "x.json"
    p2 = tmp_path / "y.json"
    p1.write_text(json.dumps(a), encoding="utf-8")
    p2.write_text(json.dumps(b), encoding="utf-8")
    out = compare_reports(p1, p2)
    assert out["deltas"]["cost_delta"]["before"]["latency_p95_ratio"] == 1.1
    assert out["deltas"]["cost_delta"]["after"]["latency_p95_ratio"] == 1.3


def test_cost_gate_violations_absolute_and_regress() -> None:
    base = {
        "summary": {
            "cost_delta": {
                "latency_p95_ratio": 1.1,
                "tokens_total_ratio": 1.2,
            },
        },
    }
    cand = {
        "summary": {
            "cost_delta": {
                "latency_p95_ratio": 1.4,
                "tokens_total_ratio": 1.8,
            },
        },
    }
    errs = _cost_gate_violations(
        base,
        cand,
        max_candidate_latency_p95_ratio=1.3,
        max_candidate_tokens_total_ratio=1.7,
        max_latency_p95_ratio_regress=1.2,
        max_tokens_total_ratio_regress=1.3,
    )
    assert any("--max-latency-ratio" in e for e in errs)
    assert any("--max-tokens-ratio" in e for e in errs)
    assert any("latency_p95_ratio regressed" in e for e in errs)
    assert any("tokens_total_ratio regressed" in e for e in errs)
