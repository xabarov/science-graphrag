"""Unit tests for claims benchmark harness (Wave H1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.claims.heuristic_extract import extract_claims_anchor_harness
from eval.claims.metrics import score_claims_extraction
from eval.claims.runner import discover_claims_case_dirs, run_claims_case

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "claims"


def test_score_claims_contract_only() -> None:
    """Contract-only gold accepts empty prediction list."""
    gold = {"contract_only": True, "expected_claims": []}
    m = score_claims_extraction([], gold)
    assert m["passed"] is True


def test_score_claims_recall_partial() -> None:
    """Partial claim_id recall can still pass when min_claim_recall is lowered."""
    gold = {
        "expected_claims": [
            {"claim_id": "a", "anchor_phrase": "x"},
            {"claim_id": "b", "anchor_phrase": "y"},
        ],
        "min_claim_recall": 0.5,
    }
    preds = [{"claim_id": "a"}]
    m = score_claims_extraction(preds, gold)
    assert m["claim_recall"] == pytest.approx(0.5)
    assert m["passed"] is True


def test_anchor_harness_finds_phrase() -> None:
    """Anchor harness emits a prediction when anchor phrase is present."""
    gold = {
        "expected_claims": [
            {
                "claim_id": "c1",
                "anchor_phrase": "hello world",
                "claim_type": "test",
            }
        ]
    }
    preds = extract_claims_anchor_harness("prefix hello world suffix", gold)
    assert len(preds) == 1
    assert preds[0]["claim_id"] == "c1"


def test_discover_claims_mini_tier() -> None:
    """claims_mini tier discovers exactly five corpus-derived cases."""
    cases = discover_claims_case_dirs(FIXTURES, tier="claims_mini")
    ids = {p.name for p in cases}
    assert "yolov1_speed_claim" in ids
    assert len(ids) == 5


def test_run_claims_case_speed_fixture() -> None:
    """End-to-end case run passes with default anchor harness."""
    case = FIXTURES / "yolov1_speed_claim"
    report = run_claims_case(case)
    assert report["metrics"]["passed"] is True
    assert report["metrics"]["claim_recall"] == 1.0


def test_run_claims_case_with_stub_fails_non_contract() -> None:
    """Empty extractor fails non-contract gold."""
    case = FIXTURES / "yolov1_speed_claim"

    def _stub(_article: str, _gold: dict) -> list:
        return []

    report = run_claims_case(case, extract_fn=_stub)
    assert report["metrics"]["passed"] is False


def test_suite_contract_tier_passes() -> None:
    """claims_merge_contract tier runs only the contract-shape case."""

    cases = discover_claims_case_dirs(FIXTURES, tier="claims_merge_contract")
    assert [p.name for p in cases] == ["claims_contract_shape"]
    for c in cases:
        report = run_claims_case(c)
        assert report["metrics"]["passed"] is True


def test_all_gold_files_parse() -> None:
    """Every claims fixture gold uses schema_version 1."""
    for gold_path in FIXTURES.glob("*/gold.json"):
        data = json.loads(gold_path.read_text(encoding="utf-8"))
        assert data.get("schema_version") == 1
