"""Layer-1 benchmark infrastructure: gold format, metrics, fixture smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.layer1.metrics import prf1_tp_fp_fn, score_layer1
from eval.layer1.runner import run_case
from eval.layer1.spec import Layer1GoldSpec
from science_graphrag.config import Settings
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft, WorkType
from science_graphrag.ingestion.stages.references import extract_references

FIXTURE_YOLO = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1" / "yolov1"


def test_layer1_gold_spec_loads() -> None:
    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    assert spec.case_id == "yolov1"
    assert len(spec.authorships) == 4
    assert spec.references.expected_count == 24


def test_prf1_sets() -> None:
    p, r, f1, tp, fp, fn = prf1_tp_fp_fn({"a", "b"}, {"a", "c"})
    assert tp == 1 and fp == 1 and fn == 1
    assert p == pytest.approx(0.5)
    assert r == pytest.approx(0.5)


def test_score_layer1_deterministic() -> None:
    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    work = WorkDraft(
        title="You Only Look Once: Unified, Real-Time Object Detection",
        publication_year=2015,
        abstract="We present YOLO, a new approach to object detection.",
        work_type=WorkType.UNKNOWN,
    )
    auth = [
        AuthorshipDraft(author_position=1, author_raw_name="Joseph Redmon", raw_affiliations=[]),
    ]
    refs = [
        ReferenceDraft(raw_reference="dummy", arxiv_id="1505.00110"),
    ]
    m = score_layer1(work, auth, refs, spec)
    assert m.metadata.get("title_exact_normalized") is True
    assert m.authorships.get("names_recall", 1.0) < 1.0


def test_yolov1_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_YOLO / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 23


def test_run_case_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force heuristic path so CI does not call remote LLMs."""

    def _settings() -> Settings:
        return Settings(
            extraction_llm_api_key=None,
            extraction_llm_enabled=False,
        )

    monkeypatch.setattr("eval.layer1.runner.get_settings", _settings)
    report = run_case(FIXTURE_YOLO)
    assert report["case_id"] == "yolov1"
    assert "metrics" in report
    assert "predicted" in report
    assert report["diagnostics"]["document_id"] == "yolov1"
