"""Regression guard: advisory phantom count must not exceed frozen baseline (BT1)."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE = REPO_ROOT / "eval" / "results" / "benchmark-trust-baseline.json"
_SUMMARY = REPO_ROOT / "eval" / "results" / "benchmark-metrics-summary.json"


def test_advisory_phantom_count_not_above_baseline() -> None:
    """CI/local: current summary must not report more phantoms than the committed baseline."""

    if not _BASELINE.is_file() or not _SUMMARY.is_file():
        return
    baseline = json.loads(_BASELINE.read_text(encoding="utf-8"))
    current = json.loads(_SUMMARY.read_text(encoding="utf-8"))
    b = baseline.get("advisory_phantom_count")
    c = (current.get("decision_gate") or {}).get("criteria", {}).get("advisory_phantom_count")
    if b is None or c is None:
        return
    assert int(c) <= int(b), f"phantom regression: current={c} baseline_cap={b}"
