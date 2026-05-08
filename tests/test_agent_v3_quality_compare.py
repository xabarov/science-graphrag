"""Snapshot compare for v3 quality judge artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from eval.agent_v3_quality.compare import compare_reports


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
