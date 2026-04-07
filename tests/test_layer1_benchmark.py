"""Layer-1 benchmark infrastructure: gold format, metrics, fixture smoke."""

from __future__ import annotations

from pathlib import Path

import pytest

from eval.layer1.metrics import _norm_abstract_match, prf1_tp_fp_fn, score_layer1
from eval.layer1.runner import run_case
from eval.layer1.spec import Layer1GoldSpec
from eval.layer1.threshold_profiles import apply_layer1_threshold_profile
from science_graphrag.config import Settings
from science_graphrag.domain.models import AuthorshipDraft, ReferenceDraft, WorkDraft, WorkType
from science_graphrag.ingestion.stages.references import extract_references

FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "layer1"
FIXTURE_YOLO = FIXTURE_ROOT / "yolov1"
FIXTURE_DOI_HEAVY = FIXTURE_ROOT / "doi_refs_heavy"
FIXTURE_ARXIV_HEAVY = FIXTURE_ROOT / "arxiv_refs_heavy"
FIXTURE_NOISY = FIXTURE_ROOT / "noisy_layout_stub"
FIXTURE_RETINANET_REAL = FIXTURE_ROOT / "retinanet_focal_realpdf"
FIXTURE_FCOS_REAL = FIXTURE_ROOT / "fcos_realpdf"


def test_layer1_gold_spec_loads() -> None:
    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    assert spec.case_id == "yolov1"
    assert len(spec.authorships) == 4
    assert spec.references.expected_count == 44


def test_apply_student_mistral_threshold_profile() -> None:
    spec = Layer1GoldSpec.load(FIXTURE_YOLO / "gold.json")
    assert spec.quality_thresholds is None
    merged = apply_layer1_threshold_profile(spec, "student_mistral")
    assert merged.quality_thresholds is not None
    assert merged.quality_thresholds.require_title_match is False
    assert merged.quality_thresholds.min_title_rouge_l is not None


def test_norm_abstract_match_hyphen_variants() -> None:
    assert _norm_abstract_match("a\u2011b") == _norm_abstract_match("a-b")
    assert _norm_abstract_match("Keypoint\u2011based").startswith(
        _norm_abstract_match("Keypoint-"),
    )


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
    assert float(m.metadata.get("title_rouge_l", 0.0)) >= 0.99
    assert float(m.metadata.get("title_token_f1", 0.0)) >= 0.99
    assert m.authorships.get("names_recall", 1.0) < 1.0
    assert m.contract.get("passed") is False


def test_yolov1_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_YOLO / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 23


def test_doi_heavy_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_DOI_HEAVY / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 4


def test_arxiv_heavy_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_ARXIV_HEAVY / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 5


def test_noisy_layout_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_NOISY / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 2


def test_retinanet_realpdf_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_RETINANET_REAL / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 36


def test_fcos_realpdf_fixture_reference_heuristic_count() -> None:
    text = (FIXTURE_FCOS_REAL / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= 26


@pytest.mark.parametrize(
    ("rel_dir", "minimum"),
    [
        ("detr_realpdf", 46),
        ("ssd_realpdf", 22),
        ("efficientdet_realpdf", 44),
        ("yolov3_realpdf", 18),
        ("centernet_realpdf", 40),
    ],
)
def test_additional_realpdf_fixture_reference_heuristic_count(rel_dir: str, minimum: int) -> None:
    text = (FIXTURE_ROOT / rel_dir / "article.md").read_text(encoding="utf-8")
    refs = extract_references(text)
    assert len(refs) >= minimum


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
    assert report["gold_path"].endswith("gold.json")
    assert "metrics" in report
    assert "predicted" in report
    assert report["diagnostics"]["document_id"] == "yolov1"
    assert report["metrics"]["contract"]["passed"] is True
