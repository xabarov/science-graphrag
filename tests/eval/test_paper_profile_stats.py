"""Tests for eval/paper_profile_stats."""

from __future__ import annotations

from eval.paper_profile_stats import summarize_paper_profile_payloads


def test_summarize_paper_profile_payloads_rates() -> None:
    payloads = [
        {"year": 2020, "venue": "NeurIPS", "work_not_found": False},
        {"year": None, "venue": None},
        {"work_not_found": True},
    ]
    out = summarize_paper_profile_payloads(payloads)
    assert out["count"] == 3
    assert out["work_not_found"] == 1
    assert out["year_null"] == 1
    assert out["venue_null"] == 1
    assert out["year_null_rate_excluding_not_found"] == 0.5
