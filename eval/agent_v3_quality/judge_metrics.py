"""Aggregate weighted scores and pairwise rates for v3 quality judge reports."""

from __future__ import annotations

from typing import Any

from eval.agent_v3_quality.contract import RUBRIC_AXES, RUBRIC_WEIGHTS


def weighted_score_from_axes(scores: dict[str, Any] | None) -> float | None:
    """Weighted rubric score using ``contract.RUBRIC_WEIGHTS``."""

    if not isinstance(scores, dict):
        return None
    total = 0.0
    wsum = 0.0
    for axis in RUBRIC_AXES:
        raw = scores.get(axis)
        try:
            v = float(raw)
        except (TypeError, ValueError):
            continue
        w = RUBRIC_WEIGHTS[axis]
        total += w * v
        wsum += w
    if wsum <= 0:
        return None
    return total / wsum


def summarize_suite(  # pylint: disable=too-many-locals
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build top-level ``summary`` block from per-case rows (post-judge)."""

    n = len(cases)
    if not n:
        return {
            "case_count": 0,
            "mean_weighted_score_baseline": None,
            "mean_weighted_score_candidate": None,
            "mean_delta": None,
            "pairwise_candidate_win_rate": None,
            "pairwise_baseline_win_rate": None,
            "pairwise_tie_rate": None,
            "hard_fail_count_baseline": 0,
            "hard_fail_count_candidate": 0,
            "all_passed": True,
        }

    b_scores: list[float] = []
    c_scores: list[float] = []
    wins_b = wins_c = ties = 0
    hf_b = hf_c = 0

    family_counts: dict[str, dict[str, int]] = {}

    for row in cases:
        fam = str(row.get("family") or "unknown")
        if fam not in family_counts:
            family_counts[fam] = {"candidate_wins": 0, "baseline_wins": 0, "ties": 0}
        b = row.get("baseline") or {}
        c = row.get("candidate") or {}
        pw = row.get("pairwise") or {}

        wb = b.get("weighted_score")
        wc = c.get("weighted_score")
        if isinstance(wb, (int, float)):
            b_scores.append(float(wb))
        if isinstance(wc, (int, float)):
            c_scores.append(float(wc))

        winner = str(pw.get("winner") or "").strip().lower()
        if winner == "candidate":
            wins_c += 1
            family_counts[fam]["candidate_wins"] += 1
        elif winner == "baseline":
            wins_b += 1
            family_counts[fam]["baseline_wins"] += 1
        else:
            ties += 1
            family_counts[fam]["ties"] += 1

        hf_b += len(b.get("hard_fail_flags") or [])
        hf_c += len(c.get("hard_fail_flags") or [])

    mean_b = sum(b_scores) / len(b_scores) if b_scores else None
    mean_c = sum(c_scores) / len(c_scores) if c_scores else None
    mean_delta = (mean_c - mean_b) if mean_b is not None and mean_c is not None else None

    all_passed = all(bool(row.get("passed", True)) for row in cases)

    return {
        "case_count": n,
        "mean_weighted_score_baseline": round(mean_b, 4) if mean_b is not None else None,
        "mean_weighted_score_candidate": round(mean_c, 4) if mean_c is not None else None,
        "mean_delta": round(mean_delta, 4) if mean_delta is not None else None,
        "pairwise_candidate_win_rate": round(wins_c / n, 4),
        "pairwise_baseline_win_rate": round(wins_b / n, 4),
        "pairwise_tie_rate": round(ties / n, 4),
        "hard_fail_count_baseline": hf_b,
        "hard_fail_count_candidate": hf_c,
        "family_breakdown": family_counts,
        "all_passed": all_passed,
    }
