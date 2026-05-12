"""Aggregate weighted scores and pairwise rates for v3 quality judge reports."""

from __future__ import annotations

import math
from typing import Any

from eval.agent_v3_quality.contract import RUBRIC_AXES, RUBRIC_WEIGHTS


def _coerce_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _p95(values: list[float]) -> float | None:
    """Nearest-rank p95 on a non-empty sorted sample."""

    if not values:
        return None
    s = sorted(values)
    n = len(s)
    if n == 1:
        return s[0]
    # 1-based rank k = ceil(0.95 * n), clamp to [1, n]
    k = int(math.ceil(0.95 * float(n)))
    k = max(1, min(n, k))
    return s[k - 1]


def cost_delta_from_cases(cases: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Wave F1: latency p95 + token totals per branch (baseline vs candidate in-suite).

    Reads per-case ``baseline`` / ``candidate`` dicts after judge merge:
    ``latency_ms`` and ``usage_total_tokens`` (or nested ``run_metadata.usage.total_tokens``).
    """

    b_lat: list[float] = []
    c_lat: list[float] = []
    b_tok_sum = 0
    c_tok_sum = 0
    b_tok_n = 0
    c_tok_n = 0

    for row in cases:
        b = row.get("baseline") if isinstance(row.get("baseline"), dict) else {}
        c = row.get("candidate") if isinstance(row.get("candidate"), dict) else {}
        bl = _coerce_float(b.get("latency_ms"))
        cl = _coerce_float(c.get("latency_ms"))
        if bl is not None and bl >= 0:
            b_lat.append(bl)
        if cl is not None and cl >= 0:
            c_lat.append(cl)

        bt = _coerce_float(b.get("usage_total_tokens"))
        if bt is None and isinstance(b.get("run_metadata"), dict):
            us = (b["run_metadata"] or {}).get("usage")
            if isinstance(us, dict):
                bt = _coerce_float(us.get("total_tokens"))
        ct = _coerce_float(c.get("usage_total_tokens"))
        if ct is None and isinstance(c.get("run_metadata"), dict):
            us = (c["run_metadata"] or {}).get("usage")
            if isinstance(us, dict):
                ct = _coerce_float(us.get("total_tokens"))
        if bt is not None and bt >= 0:
            b_tok_sum += bt
            b_tok_n += 1
        if ct is not None and ct >= 0:
            c_tok_sum += ct
            c_tok_n += 1

    p95_b = _p95(b_lat)
    p95_c = _p95(c_lat)
    if p95_b is None and p95_c is None and b_tok_n == 0 and c_tok_n == 0:
        return None

    lat_ratio = None
    if p95_b is not None and p95_b > 0 and p95_c is not None:
        lat_ratio = round(p95_c / p95_b, 4)
    tok_ratio = None
    if b_tok_sum > 0:
        tok_ratio = round(c_tok_sum / b_tok_sum, 4)

    return {
        "latency_p95_baseline_ms": round(p95_b, 2) if p95_b is not None else None,
        "latency_p95_candidate_ms": round(p95_c, 2) if p95_c is not None else None,
        "latency_p95_ratio": lat_ratio,
        "tokens_total_baseline": round(b_tok_sum, 2) if b_tok_n else None,
        "tokens_total_candidate": round(c_tok_sum, 2) if c_tok_n else None,
        "tokens_total_ratio": tok_ratio,
        "cases_with_latency_samples": len(b_lat),
        "cases_with_token_samples_baseline": b_tok_n,
        "cases_with_token_samples_candidate": c_tok_n,
    }


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
