#!/usr/bin/env python3
"""Pilot KPI helper: p50/p95 latency for GET /v1/works and POST /v1/query.

Usage (from repo root, .venv active or use .venv/bin/python):
  BASE=http://127.0.0.1:8787 N=40 .venv/bin/python scripts/pilot_measure_latency.py

Requires a running API. Attach KPI numbers to ``docs/runbooks/pilot-checklist.md``
or your release record when filing a pilot.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from statistics import median


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    w = k - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def _timed_ms(fn) -> float:
    """Run fn() and return elapsed milliseconds."""

    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000.0


def _fetch_works(base: str) -> None:
    url = f"{base}/v1/works?limit=10&offset=0"
    with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
        resp.read()


def _post_query(base: str, body: bytes) -> None:
    req = urllib.request.Request(  # noqa: S310
        f"{base}/v1/query",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        resp.read()


def main() -> int:
    """Print JSON with latency stats for works list and query endpoints."""

    base = os.environ.get("BASE", "http://127.0.0.1:8787").rstrip("/")
    n = int(os.environ.get("N", "30"))
    query_body = json.dumps({"query": "pilot latency probe", "top_k": 3}).encode("utf-8")

    works_ms: list[float] = []
    query_ms: list[float] = []

    for _ in range(n):
        works_ms.append(_timed_ms(lambda: _fetch_works(base)))
        query_ms.append(_timed_ms(lambda: _post_query(base, query_body)))

    def summarize(xs: list[float]) -> dict[str, float]:
        s = sorted(xs)
        return {
            "n": float(len(s)),
            "p50_ms": median(s),
            "p95_ms": _percentile(s, 95),
            "max_ms": max(s) if s else 0.0,
        }

    out = {
        "base": base,
        "works": summarize(works_ms),
        "query": summarize(query_ms),
    }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except urllib.error.URLError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        raise SystemExit(1) from e
