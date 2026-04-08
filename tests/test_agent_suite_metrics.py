"""Harness-aligned metrics for smolagents suite (post-hoc segmentation)."""

from __future__ import annotations

from pathlib import Path

from eval.layer1.spec import Layer1GoldSpec
from eval.references_harness.agent_suite_metrics import (
    harness_metrics_for_parsed_span,
    mean_metrics,
    style_hint_from_guess,
)

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1"


def test_style_hint_from_guess() -> None:
    assert style_hint_from_guess("bracket_numbered") == "bracket_numbered"
    assert style_hint_from_guess("numeric_dot") == "numeric_dot"
    assert style_hint_from_guess("Author year") == "author_year"
    assert style_hint_from_guess(None) is None


def test_harness_metrics_doi_refs_heavy_parsed_span() -> None:
    spec = Layer1GoldSpec.load(FIXTURE_ROOT / "doi_refs_heavy" / "gold.json")
    rb = spec.references_benchmark
    assert rb is not None
    lines = (
        (FIXTURE_ROOT / "doi_refs_heavy" / "article.md").read_text(encoding="utf-8").splitlines()
    )
    parsed = {"start_line": 11, "end_line": 15, "style_guess": "bracket_numbered"}
    m = harness_metrics_for_parsed_span(
        lines,
        rb.bibliography.start_line,
        rb.bibliography.end_line,
        rb.raw_entries,
        parsed,
        fallback_to_first_candidate=False,
    )
    assert m["entry_overlap_f1"] == 1.0
    assert m["count_abs_error"] == 0
    assert m["span_line_iou"] > 0.5


def test_mean_metrics_filters_errors() -> None:
    rows = [
        {"span_line_iou": 1.0, "entry_overlap_f1": 1.0, "wall_seconds": 1.0},
        {"metrics_error": "missing_or_invalid_span", "wall_seconds": 0.5},
    ]
    pm = mean_metrics(rows)
    assert pm["n_ok"] == 1.0
    assert pm["n_total"] == 2.0
    assert pm["mean_span_line_iou"] == 1.0
