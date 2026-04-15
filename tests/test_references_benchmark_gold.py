"""Gold consistency for ``references_benchmark`` (layer-1 fixtures)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.layer1.spec import Layer1GoldSpec
from eval.references_harness.metrics import gold_line_set_for_span_iou
from eval.references_harness.runner import run_case
from eval.references_harness.scope_segmentation import (
    _post_split_collapsed_bracket_blob,
    pred_raw_entries_from_bibliography_excerpt,
)
from eval.references_harness.validate import assert_references_benchmark_consistent

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1"


def _tier_cases() -> list[str]:
    data = json.loads((FIXTURE_ROOT / "case_tiers.json").read_text(encoding="utf-8"))
    return list(data.get("references_benchmark_v1", []))


def _full_tier_cases() -> list[str]:
    data = json.loads((FIXTURE_ROOT / "case_tiers.json").read_text(encoding="utf-8"))
    return list(data.get("references_benchmark_full", []))


@pytest.mark.parametrize("case_id", _tier_cases())
def test_references_benchmark_gold_loads(case_id: str) -> None:
    """Each tier case has a parsable ``references_benchmark`` block."""
    path = FIXTURE_ROOT / case_id / "gold.json"
    spec = Layer1GoldSpec.load(path)
    assert spec.references_benchmark is not None, case_id


@pytest.mark.parametrize("case_id", _tier_cases())
def test_references_benchmark_consistent_with_article(case_id: str) -> None:
    """manual vs silver validation rules from ``assert_references_benchmark_consistent``."""
    spec = Layer1GoldSpec.load(FIXTURE_ROOT / case_id / "gold.json")
    rb = spec.references_benchmark
    assert rb is not None
    assert_references_benchmark_consistent(FIXTURE_ROOT / case_id / "article.md", rb)


@pytest.mark.parametrize("case_id", _full_tier_cases())
def test_references_benchmark_full_tier_gold_loads(case_id: str) -> None:
    """All ``references_benchmark_full`` tier fixtures expose ``references_benchmark``."""
    path = FIXTURE_ROOT / case_id / "gold.json"
    spec = Layer1GoldSpec.load(path)
    assert spec.references_benchmark is not None, case_id


@pytest.mark.parametrize("case_id", _full_tier_cases())
def test_references_benchmark_full_tier_consistent_with_article(case_id: str) -> None:
    spec = Layer1GoldSpec.load(FIXTURE_ROOT / case_id / "gold.json")
    rb = spec.references_benchmark
    assert rb is not None
    assert_references_benchmark_consistent(FIXTURE_ROOT / case_id / "article.md", rb)


def test_heuristic_modes_run_without_error() -> None:
    """Smoke: deterministic modes produce reports for one small case."""
    for mode in ("heuristic_full", "heuristic_scope", "heuristic_bib_gold"):
        r = run_case(FIXTURE_ROOT, "doi_refs_heavy", mode)  # type: ignore[arg-type]
        assert r.error is None
        assert r.gold_entry_count == 5
        assert r.pred_entry_count >= 1


def test_post_split_collapsed_bracket_blob_splits_merged_excerpt() -> None:
    """LLM may return one string with multiple ``[n]`` blocks; recover entries."""
    merged = ["[1] First.\n[2] Second."]
    out = _post_split_collapsed_bracket_blob(merged)
    assert len(out) == 2
    assert out[0].startswith("[1]") and out[1].startswith("[2]")


def test_pred_entries_from_excerpt_matches_gold_count_bracket() -> None:
    """scope_llm-style split on bracket bibliography (plan A1)."""
    spec = Layer1GoldSpec.load(FIXTURE_ROOT / "doi_refs_heavy" / "gold.json")
    rb = spec.references_benchmark
    assert rb is not None
    article = (FIXTURE_ROOT / "doi_refs_heavy" / "article.md").read_text(encoding="utf-8")
    lines = article.splitlines()
    block = "\n".join(lines[rb.bibliography.start_line - 1 : rb.bibliography.end_line])
    pred = pred_raw_entries_from_bibliography_excerpt(block, "numbered")
    assert len(pred) == len(rb.raw_entries)


def test_gold_line_set_for_span_iou_includes_heading_when_present() -> None:
    article = (FIXTURE_ROOT / "doi_refs_heavy" / "article.md").read_text(encoding="utf-8")
    lines = article.splitlines()
    spec = Layer1GoldSpec.load(FIXTURE_ROOT / "doi_refs_heavy" / "gold.json")
    rb = spec.references_benchmark
    assert rb is not None
    g0, g1 = rb.bibliography.start_line, rb.bibliography.end_line
    s = gold_line_set_for_span_iou(lines, g0, g1)
    assert g0 in s and g1 in s
    # Heading is two lines above first [1] when a blank line sits between (see article.md).
    heading_1based = next(i for i, ln in enumerate(lines, start=1) if ln.strip() == "## References")
    assert heading_1based in s
