"""Tests for trace_regression_compare CLI."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[3]
_COMPARE = _REPO / "scripts" / "live_check" / "trace_regression_compare.py"


def _minimal_review(metrics: dict) -> dict:
    return {
        "review_version": "trace-review-v1",
        "generated_at": "2026-05-05T00:00:00Z",
        "metrics": metrics,
        "verdict": {"status": "pass", "fail_reasons": [], "warn_reasons": []},
    }


def test_regression_identical_passes(tmp_path: Path) -> None:
    doc = _minimal_review(
        {
            "tool_error_rate": 0.0,
            "missing_span_count": 0,
            "compaction_event_count": 0,
            "final_answer_missing_count": 0,
            "latency_p95_ms": None,
            "compaction_churn_score": None,
        }
    )
    p = tmp_path / "x.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(p),
            "--candidate",
            str(p),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0
    assert json.loads(out_j.read_text())["status"] == "pass"


def test_regression_version_mismatch_exit_2(tmp_path: Path) -> None:
    base = _minimal_review({"missing_span_count": 0})
    cand = dict(base)
    cand["review_version"] = "trace-review-v0"
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(tmp_path / "o.json"),
            "--out-md",
            str(tmp_path / "o.md"),
        ],
        check=False,
    )
    assert r.returncode == 2


def test_regression_missing_span_fail(tmp_path: Path) -> None:
    base = _minimal_review({"missing_span_count": 0})
    cand = _minimal_review({"missing_span_count": 2})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert payload["status"] == "fail"


def test_regression_compaction_churn_increase_fail(tmp_path: Path) -> None:
    base = _minimal_review({"compaction_churn_score": 0.0})
    cand = _minimal_review({"compaction_churn_score": 2.0})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert payload["status"] == "fail"
    assert any("compaction_churn_increase" in x for x in payload["fail_reasons"])


def test_regression_min_side_llm_cache_read_ratio_fail(tmp_path: Path) -> None:
    base = _minimal_review({"side_llm_cache_read_ratio_avg": 0.9})
    cand = _minimal_review({"side_llm_cache_read_ratio_avg": 0.5})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--min-side-llm-cache-read-ratio",
            "0.6",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert any("side_llm_cache_read_ratio_avg" in x for x in payload["fail_reasons"])


def test_regression_min_insight_recall_fail(tmp_path: Path) -> None:
    base = _minimal_review({"insight_recall_at_k": 1.0})
    cand = _minimal_review({"insight_recall_at_k": 0.5})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--min-insight-recall-at-k",
            "0.9",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert any("insight_recall_at_k" in x for x in payload["fail_reasons"])


def test_regression_max_stale_summary_error_rate_fail(tmp_path: Path) -> None:
    base = _minimal_review({"stale_summary_error_rate": 0.0})
    cand = _minimal_review({"stale_summary_error_rate": 0.2})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--max-stale-summary-error-rate",
            "0.1",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert any("stale_summary_error_rate" in x for x in payload["fail_reasons"])


def test_regression_min_side_llm_skipped_when_metric_absent(tmp_path: Path) -> None:
    base = _minimal_review({"missing_span_count": 0})
    cand = _minimal_review({"missing_span_count": 0})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--min-side-llm-cache-read-ratio",
            "0.6",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 0


def test_regression_verdict_not_worse_fails_by_default(tmp_path: Path) -> None:
    base = _minimal_review({"missing_span_count": 0})
    cand = _minimal_review({"missing_span_count": 0})
    base["verdict"] = {"status": "pass", "fail_reasons": [], "warn_reasons": []}
    cand["verdict"] = {"status": "warn", "fail_reasons": [], "warn_reasons": ["x"]}
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert any("verdict_regressed" in x for x in payload["fail_reasons"])


def test_regression_verdict_gate_can_be_disabled(tmp_path: Path) -> None:
    base = _minimal_review({"missing_span_count": 0})
    cand = _minimal_review({"missing_span_count": 0})
    base["verdict"] = {"status": "pass", "fail_reasons": [], "warn_reasons": []}
    cand["verdict"] = {"status": "warn", "fail_reasons": [], "warn_reasons": ["x"]}
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--no-enforce-verdict-not-worse",
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 0


def test_regression_unnecessary_tool_calls_avg_increase_warns_exit_3(tmp_path: Path) -> None:
    base = _minimal_review({"unnecessary_tool_calls_avg": 0.0})
    cand = _minimal_review({"unnecessary_tool_calls_avg": 1.0})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 3
    payload = json.loads(out_j.read_text())
    assert payload["status"] == "warn"
    assert any("unnecessary_tool_calls_avg_increase" in x for x in payload["warn_reasons"])
    assert payload["delta"]["unnecessary_tool_calls_avg"] == 1.0


def test_regression_unnecessary_tool_calls_avg_fail_policy(tmp_path: Path) -> None:
    base = _minimal_review({"unnecessary_tool_calls_avg": 0.0})
    cand = _minimal_review({"unnecessary_tool_calls_avg": 2.0})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--fail-on",
            "new_missing_spans,tool_error_increase,final_answer_missing_increase,"
            "compaction_churn_increase,unnecessary_tool_calls_avg_increase",
            "--warn-on",
            "latency_p95_increase,shortlist_ratio_increase",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert payload["status"] == "fail"
    assert any("unnecessary_tool_calls_avg_increase" in x for x in payload["fail_reasons"])


def test_regression_claim_grounding_thresholds_fail(tmp_path: Path) -> None:
    base = _minimal_review({"claim_grounding_precision": 1.0, "claim_grounding_recall": 1.0})
    cand = _minimal_review({"claim_grounding_precision": 0.4, "claim_grounding_recall": 0.5})
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    b.write_text(json.dumps(base), encoding="utf-8")
    c.write_text(json.dumps(cand), encoding="utf-8")
    out_j = tmp_path / "o.json"
    out_m = tmp_path / "o.md"
    r = subprocess.run(
        [
            sys.executable,
            str(_COMPARE),
            "--baseline",
            str(b),
            "--candidate",
            str(c),
            "--min-claim-grounding-precision",
            "0.8",
            "--min-claim-grounding-recall",
            "0.8",
            "--out-json",
            str(out_j),
            "--out-md",
            str(out_m),
        ],
        check=False,
    )
    assert r.returncode == 1
    payload = json.loads(out_j.read_text())
    assert any("claim_grounding_precision" in x for x in payload["fail_reasons"])
    assert any("claim_grounding_recall" in x for x in payload["fail_reasons"])
