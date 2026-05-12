"""Tests for ``eval.agent_v3_quality.judge_metrics`` helpers."""

from __future__ import annotations

from eval.agent_v3_quality.judge_metrics import cost_delta_from_cases


def test_cost_delta_from_cases_computes_p95_and_token_ratio() -> None:
    cases = [
        {
            "case_id": "a",
            "baseline": {"latency_ms": 100, "usage_total_tokens": 200},
            "candidate": {"latency_ms": 150, "usage_total_tokens": 300},
        },
        {
            "case_id": "b",
            "baseline": {"latency_ms": 200, "usage_total_tokens": 400},
            "candidate": {"latency_ms": 180, "usage_total_tokens": 360},
        },
    ]
    out = cost_delta_from_cases(cases)
    assert out is not None
    assert out["latency_p95_baseline_ms"] == 200.0
    assert out["latency_p95_candidate_ms"] == 180.0
    assert out["tokens_total_baseline"] == 600.0
    assert out["tokens_total_candidate"] == 660.0
    assert out["tokens_total_ratio"] == 1.1
