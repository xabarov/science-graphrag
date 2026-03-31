"""Unit tests for layer-2 semantic scoring (no LLM)."""

from __future__ import annotations

from eval.layer2.metrics import score_semantic
from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.config import Settings
from science_graphrag.domain.semantic_models import (
    SemanticEvidenceV1,
    SemanticExtractionV1,
    SemanticMethodV1,
)


def test_score_semantic_no_llm_smoke_passes() -> None:
    gold = SemanticGoldSpec.model_validate(
        {
            "case_id": "x",
            "min_method_names": 0,
            "expected_method_names_normalized": [],
            "allow_empty_when_no_llm": True,
        },
    )
    pred = SemanticExtractionV1(document_id="x", methods=[], datasets=[])
    settings = Settings(extraction_llm_enabled=False)
    m = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=settings.extraction_llm_enabled,
        confidence_threshold=0.35,
    )
    assert m.passed


def test_score_semantic_with_llm_expected_names() -> None:
    gold = SemanticGoldSpec.model_validate(
        {
            "case_id": "x",
            "min_method_names": 1,
            "expected_method_names_normalized": ["yolo"],
            "allow_empty_when_no_llm": False,
        },
    )
    pred = SemanticExtractionV1(
        document_id="x",
        methods=[
            SemanticMethodV1(
                name="YOLO",
                confidence=0.9,
                evidence=[SemanticEvidenceV1(quote="YOLO")],
            ),
        ],
        datasets=[],
    )
    m = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=True,
        confidence_threshold=0.35,
    )
    assert m.passed
    assert m.recall_methods_num >= 1


def test_score_semantic_recall_threshold_enforced() -> None:
    gold = SemanticGoldSpec.model_validate(
        {
            "case_id": "x",
            "min_method_names": 0,
            "min_method_recall_ratio": 1.0,
            "expected_method_names_normalized": ["yolo", "fast yolo"],
            "allow_empty_when_no_llm": False,
        },
    )
    pred = SemanticExtractionV1(
        document_id="x",
        methods=[
            SemanticMethodV1(
                name="YOLO",
                confidence=0.9,
                evidence=[SemanticEvidenceV1(quote="YOLO")],
            ),
        ],
        datasets=[],
    )
    m = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=True,
        confidence_threshold=0.35,
    )
    assert not m.passed
    assert "method_recall_below_min" in m.notes


def test_score_semantic_substring_alias_matches_long_method_name() -> None:
    """Gold short tokens (e.g. gfl) match long predicted names containing them."""

    gold = SemanticGoldSpec.model_validate(
        {
            "case_id": "x",
            "min_method_names": 1,
            "expected_method_names_normalized": ["gfl", "generalized focal loss"],
            "allow_empty_when_no_llm": False,
        },
    )
    pred = SemanticExtractionV1(
        document_id="x",
        methods=[
            SemanticMethodV1(
                name="Generalized Focal Loss (GFL)",
                confidence=0.9,
                evidence=[SemanticEvidenceV1(quote="GFL")],
            ),
        ],
        datasets=[],
    )
    m = score_semantic(
        pred,
        gold,
        extraction_llm_enabled=True,
        confidence_threshold=0.35,
    )
    assert m.passed
    assert m.recall_methods_num == 2
