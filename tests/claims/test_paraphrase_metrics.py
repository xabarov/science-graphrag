"""Unit tests for BT6 claims paraphrase scoring and distractor article builder."""

from __future__ import annotations

import json
from pathlib import Path

from eval.claims.article_source import read_claims_article
from eval.claims.distractor_article import augment_article_with_distractors
from eval.claims.metrics import score_claims_paraphrase_extraction

REPO = Path(__file__).resolve().parents[2]


def test_read_claims_article_resolves_layer1_fixture() -> None:
    case = REPO / "tests" / "fixtures" / "benchmarks" / "claims" / "corpus_yolov1_v2"
    text = read_claims_article(case)
    assert len(text) > 200
    assert "YOLO" in text or "yolo" in text.lower()


def test_read_claims_article_nested_paraphrase_suite_path(tmp_path: Path) -> None:
    """``source_layer1_fixture`` must resolve when case lives under ``claims/<suite>/``."""

    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    (repo / "pyproject.toml").write_text('[project]\nname="t"\nversion="0"\n', encoding="utf-8")
    layer = repo / "tests" / "fixtures" / "benchmarks" / "layer1" / "yolov1"
    layer.mkdir(parents=True)
    (layer / "article.md").write_text("YOLO unified detection " * 80, encoding="utf-8")
    case = (
        repo / "tests" / "fixtures" / "benchmarks" / "claims" / "paraphrase_pilot" / "nested_case"
    )
    case.mkdir(parents=True)
    (case / "gold.json").write_text(
        json.dumps({"source_layer1_fixture": "yolov1"}),
        encoding="utf-8",
    )
    text = read_claims_article(case)
    assert len(text) > 200
    assert "yolo" in text.lower()


def test_augment_article_with_distractors_appends_neighbor_excerpt() -> None:
    gold = {
        "distractor_strategy": {
            "type": "neighboring_paper_paragraphs",
            "neighbor_corpus_work_ids": ["yolov1"],
            "max_distractor_paragraphs": 1,
        }
    }
    body, aug = augment_article_with_distractors("MAIN BODY", gold, repo_root=REPO)
    assert aug is True
    assert "MAIN BODY" in body
    assert "Distractor context: yolov1" in body


def test_score_claims_paraphrase_rouge_only_no_openrouter() -> None:
    gold = {
        "expected_claims": [
            {
                "claim_id": "c1",
                "claim_text_normalized": "alpha beta gamma delta",
                "match_mode": "rouge_l",
            }
        ],
        "min_claim_recall": 0.5,
        "claim_match_mode": "claim_id_or_normalized_text",
    }
    preds = [{"claim_text": "alpha beta gamma delta epsilon"}]
    m = score_claims_paraphrase_extraction(preds, None, gold, settings=None)
    assert m.get("paraphrase_scoring") is True
    assert m.get("claim_recall") == 1.0
    assert m.get("passed") is True


def test_score_claims_paraphrase_precision_drop_gate() -> None:
    gold = {
        "expected_claims": [
            {
                "claim_id": "c1",
                "claim_text_normalized": "unique phrase one two three",
                "match_mode": "rouge_l",
            }
        ],
        "min_claim_recall": 0.5,
        "max_precision_drop_with_distractors": 0.15,
    }
    plain = [{"claim_text": "unique phrase one two three four"}]
    distracted = [
        {"claim_text": "unique phrase one two three four"},
        {"claim_text": "unique phrase one two three four"},
    ]
    m = score_claims_paraphrase_extraction(plain, distracted, gold, settings=None)
    assert m.get("precision_drop_with_distractors", 0) <= 0.15 + 1e-6
    assert m.get("passed") is True
