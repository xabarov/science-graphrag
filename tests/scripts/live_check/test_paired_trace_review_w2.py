"""Tests for W2 paired trace-review compare wrapper."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
_WRAPPER = _REPO / "scripts" / "live_check" / "paired_trace_review_w2.py"


def _minimal_review(metrics: dict) -> dict:
    return {
        "review_version": "trace-review-v1",
        "generated_at": "2026-05-14T00:00:00Z",
        "metrics": metrics,
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }


def _metrics(latency: float) -> dict:
    return {
        "tool_error_rate": 0.0,
        "missing_span_count": 0,
        "compaction_event_count": 0,
        "final_answer_missing_count": 0,
        "latency_p95_ms": latency,
        "compaction_churn_score": None,
    }


def test_paired_w2_compare_emits_operator_latency_verdict_within_budget(tmp_path: Path) -> None:
    base = tmp_path / "baseline.json"
    cand = tmp_path / "candidate.json"
    base.write_text(json.dumps(_minimal_review(_metrics(100.0))), encoding="utf-8")
    cand.write_text(json.dumps(_minimal_review(_metrics(120.0))), encoding="utf-8")
    out_j = tmp_path / "cmp.json"
    out_m = tmp_path / "cmp.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_WRAPPER),
            "--baseline",
            str(base),
            "--candidate",
            str(cand),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr
    payload = json.loads(out_j.read_text(encoding="utf-8"))
    gate = payload.get("operator_latency_verdict") or {}
    assert gate.get("verdict") == "in_budget"


def test_paired_w2_missing_baseline_exits_2(tmp_path: Path) -> None:
    missing = tmp_path / "nope.json"
    cand = tmp_path / "cand.json"
    cand.write_text(json.dumps(_minimal_review(_metrics(100.0))), encoding="utf-8")
    out_j = tmp_path / "cmp.json"
    out_m = tmp_path / "cmp.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_WRAPPER),
            "--baseline",
            str(missing),
            "--candidate",
            str(cand),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "not a file" in (r.stderr or "").lower()
