"""Tests for server-side graph snapshot vs gold expectations."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.api.graph_snapshot_diff import (
    compare_graph_expectations_to_snapshot,
    extract_metrics_snapshot,
    snapshot_case_id,
)


def test_extract_metrics_snapshot_accepts_case_wrapped_shape() -> None:
    repo = Path(__file__).resolve().parents[1]
    path = repo / "eval/results/local-graph-yolov1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    snap = extract_metrics_snapshot(doc)
    assert snap is not None
    assert snap.get("cites_count") is not None
    assert snapshot_case_id(doc) == "yolov1"


def test_compare_graph_expectations_produces_rows() -> None:
    repo = Path(__file__).resolve().parents[1]
    path = repo / "eval/results/local-graph-yolov1.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    gold_path = repo / "tests/fixtures/benchmarks/layer1/yolov1/gold.json"
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    exp = gold.get("graph_expectations") or {}
    snap = extract_metrics_snapshot(doc)
    out = compare_graph_expectations_to_snapshot(exp, snap)
    assert out["rows"]
    assert any(r.get("field") == "cites_count" for r in out["rows"])
