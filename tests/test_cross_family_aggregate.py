"""Tests for cross-family judge aggregation (Wave F4)."""

from __future__ import annotations

from eval.agent_v3_quality.cross_family_aggregate import compute_inter_judge_agreement


def _doc(case_id: str, winner: str) -> dict:
    return {
        "cases": [
            {
                "case_id": case_id,
                "pairwise": {"winner": winner},
            },
        ],
    }


def test_inter_judge_agreement_perfect() -> None:
    d1 = _doc("c1", "candidate")
    d2 = _doc("c1", "candidate")
    d3 = _doc("c1", "candidate")
    out = compute_inter_judge_agreement([d1, d2, d3])
    assert out["inter_judge_agreement_rate"] == 1.0
    assert out["cases_compared"] == 1


def test_inter_judge_agreement_split() -> None:
    d1 = _doc("c1", "candidate")
    d2 = _doc("c1", "baseline")
    out = compute_inter_judge_agreement([d1, d2])
    assert out["inter_judge_agreement_rate"] == 0.0
    assert out["cases_compared"] == 1
