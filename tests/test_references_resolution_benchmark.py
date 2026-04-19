"""Unit tests for references_resolution benchmark harness (v1, advisory)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.references_resolution.metrics import score_references_resolution
from eval.references_resolution.runner import (
    default_resolve_predictions,
    discover_references_resolution_case_dirs,
    run_references_resolution_case,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "references_resolution"


def test_score_references_contract_only_empty_ok() -> None:
    """Contract-only accepts an empty prediction list when shape checks are disabled."""

    gold = {"contract_only": True, "expected_resolutions": []}
    m = score_references_resolution([], gold)
    assert m["passed"] is True


def test_score_references_recall_partial() -> None:
    """Recall threshold can be lowered for partial matches."""

    gold = {
        "expected_resolutions": [
            {"raw_citation_span_id": "a", "canonical_key": "doi:10.1/a"},
            {"raw_citation_span_id": "b", "canonical_key": "doi:10.1/b"},
        ],
        "min_resolution_recall": 0.5,
    }
    preds = [{"raw_citation_span_id": "a", "canonical_key": "doi:10.1/a"}]
    m = score_references_resolution(preds, gold)
    assert m["resolution_recall"] == pytest.approx(0.5)
    assert m["passed"] is True


def test_discover_refs_mini_tier() -> None:
    """refs_mini tier discovers three synthetic cases."""

    cases = discover_references_resolution_case_dirs(FIXTURES, tier="refs_mini")
    ids = {p.name for p in cases}
    assert ids == {
        "refs_mini_arxiv_id",
        "refs_mini_doi_pair",
        "refs_mini_work_id",
    }


def test_default_resolve_reads_synthetic_predictions() -> None:
    """Synthetic harness loads predictions embedded in gold."""

    case = FIXTURES / "refs_mini_doi_pair"
    gold = json.loads((case / "gold.json").read_text(encoding="utf-8"))
    preds = default_resolve_predictions(case, gold)
    assert len(preds) == 2


def test_run_references_case_doi_pair() -> None:
    """End-to-end case run passes with synthetic harness."""

    case = FIXTURES / "refs_mini_doi_pair"
    report = run_references_resolution_case(case)
    assert report["metrics"]["passed"] is True
    assert report["metrics"]["resolution_recall"] == pytest.approx(1.0)


def test_run_references_contract_tier() -> None:
    """refs_merge_contract tier runs only the contract-shape case."""

    cases = discover_references_resolution_case_dirs(FIXTURES, tier="refs_merge_contract")
    assert [p.name for p in cases] == ["refs_contract_shape"]
    for c in cases:
        report = run_references_resolution_case(c)
        assert report["metrics"]["passed"] is True
