"""Metrics aggregation for v3 quality judge."""

from __future__ import annotations

from eval.agent_v3_quality.judge_metrics import summarize_suite, weighted_score_from_axes


def test_weighted_score() -> None:
    scores = {
        k: 4
        for k in (
            "correctness",
            "completeness",
            "groundedness",
            "synthesis_quality",
            "usefulness",
            "brevity_discipline",
        )
    }
    ws = weighted_score_from_axes(scores)
    assert ws is not None
    assert abs(ws - 4.0) < 0.01


def test_summarize_suite_pairwise_rates() -> None:
    cases = [
        {
            "family": "workspace_stats",
            "baseline": {"weighted_score": 4.0, "hard_fail_flags": []},
            "candidate": {"weighted_score": 4.5, "hard_fail_flags": []},
            "pairwise": {"winner": "candidate"},
            "passed": True,
        },
        {
            "family": "workspace_stats",
            "baseline": {"weighted_score": 4.0, "hard_fail_flags": []},
            "candidate": {"weighted_score": 3.5, "hard_fail_flags": []},
            "pairwise": {"winner": "baseline"},
            "passed": True,
        },
    ]
    s = summarize_suite(cases)
    assert s["case_count"] == 2
    assert s["pairwise_candidate_win_rate"] == 0.5
    assert s["pairwise_baseline_win_rate"] == 0.5
    assert s["pairwise_tie_rate"] == 0.0
