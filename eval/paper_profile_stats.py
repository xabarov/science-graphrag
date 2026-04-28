"""Aggregate null rates from ``paper_profile`` tool payloads (offline / OD dumps)."""

from __future__ import annotations

from typing import Any, Iterable


def summarize_paper_profile_payloads(payloads: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Count presence of ``year`` / ``venue`` across ``paper_profile``-shaped dicts.

    Used for phase A3 acceptance: track metadata completeness without a live LLM.
    """
    total = 0
    year_null = 0
    venue_null = 0
    work_not_found = 0
    for p in payloads:
        if not isinstance(p, dict):
            continue
        total += 1
        if p.get("work_not_found"):
            work_not_found += 1
            continue
        if p.get("year") is None:
            year_null += 1
        if p.get("venue") is None:
            venue_null += 1
    denom = max(1, total - work_not_found)
    return {
        "count": total,
        "work_not_found": work_not_found,
        "year_null": year_null,
        "venue_null": venue_null,
        "year_null_rate_excluding_not_found": round(year_null / denom, 4),
        "venue_null_rate_excluding_not_found": round(venue_null / denom, 4),
    }
