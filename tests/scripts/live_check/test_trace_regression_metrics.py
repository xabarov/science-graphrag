"""Tests for trace_regression_metrics helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts" / "live_check"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from trace_regression_metrics import (  # pylint: disable=import-error,wrong-import-position
    load_review,
    metric,
    metric_optional_any,
    metric_optional_float,
    verdict_rank,
)


def test_load_review_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "r.json"
    doc = {"review_version": "trace-review-v1", "metrics": {"latency_p95_ms": 12.5}}
    p.write_text(json.dumps(doc), encoding="utf-8")
    assert load_review(p) == doc


def test_metric_and_optional() -> None:
    base = {"metrics": {"x": 3, "y": None}}
    assert metric(base, "x") == 3.0
    assert metric(base, "missing") == 0.0
    assert metric_optional_float(base, "x") == 3.0
    assert metric_optional_float(base, "y") is None
    assert metric_optional_float(base, "z") is None
    cand = {"metrics": {"claim_grounding_precision": 0.4}}
    assert metric_optional_any(cand, ("claim_precision", "claim_grounding_precision")) == 0.4


def test_verdict_rank_ordering() -> None:
    assert verdict_rank({"verdict": {"status": "fail"}}) < verdict_rank(
        {"verdict": {"status": "warn"}}
    )
    assert verdict_rank({"verdict": {"status": "warn"}}) < verdict_rank(
        {"verdict": {"status": "pass"}}
    )
