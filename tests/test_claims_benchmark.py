"""Unit tests for claims benchmark harness (Wave H1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.claims.heuristic_extract import extract_claims_anchor_harness
from eval.claims.metrics import score_claims_extraction
from eval.claims.runner import (
    discover_claims_case_dirs,
    extract_claims_production_path,
    run_claims_case,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "claims"


def test_production_claims_extractor_matches_ingestion_stub(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production lane returns ([], diagnostics) without LLM credentials (CI-safe)."""

    for key in (
        "SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY",
        "MAIN_LLM_API_KEY",
        "API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    raw = extract_claims_production_path("any text", {})
    assert isinstance(raw, tuple)
    preds, diag = raw
    assert preds == []
    assert diag.get("llm_error_message") == "missing extraction_llm_api_key"


def test_score_claims_contract_only() -> None:
    """Contract-only gold accepts empty prediction list."""
    gold = {"contract_only": True, "expected_claims": []}
    m = score_claims_extraction([], gold)
    assert m["passed"] is True


def test_score_claims_text_mode_without_claim_id() -> None:
    """claim_id_or_normalized_text matches via prediction text fields."""

    gold = {
        "claim_match_mode": "claim_id_or_normalized_text",
        "expected_claims": [
            {
                "claim_id": "x1",
                "claim_text_normalized": "neural network proposes",
            }
        ],
        "min_claim_recall": 1.0,
    }
    preds = [{"claim_text": "The neural network proposes a solution"}]
    m = score_claims_extraction(preds, gold)
    assert m["passed"] is True
    assert m["claim_recall"] == pytest.approx(1.0)


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


def test_discover_claims_corpus_v2_mini_tier() -> None:
    """claims_corpus_v2_mini discovers five corpus-derived cases."""

    cases = discover_claims_case_dirs(FIXTURES, tier="claims_corpus_v2_mini")
    assert len(cases) == 5


def test_discover_claims_pilot_tier() -> None:
    """claims_pilot discovers ten cases."""

    cases = discover_claims_case_dirs(FIXTURES, tier="claims_pilot")
    assert len(cases) == 10


def test_discover_claims_pilot_train_excludes_holdout() -> None:
    """claims_pilot_train excludes benchmark_holdout cases."""

    cases = discover_claims_case_dirs(FIXTURES, tier="claims_pilot_train")
    ids = {p.name for p in cases}
    assert "corpus_cascade_rcnn_stages" not in ids
    assert "corpus_efficientdet_compound" not in ids
    assert len(ids) == 8


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
