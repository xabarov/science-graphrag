"""Smoke tests for Phase 6 dual-validate framework."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.dual_validate.consistency_report import (
    ConsistencyReport,
    ExtractorInfo,
    validate_report_dict,
    write_report,
)
from scripts.dual_validate.extractors import ClaimsV2Extractor
from scripts.dual_validate.matcher import (
    Record,
    char_jaccard,
    classify_spot_check_priority,
    combined_score,
    jaccard,
    match_records,
    tokenize,
)


def test_tokenize_drops_stopwords_and_lowercases() -> None:
    assert tokenize("YOLO is a Real-Time Object Detector!") == {
        "yolo",
        "real",
        "time",
        "object",
        "detector",
    }


def test_jaccard_zero_on_empty() -> None:
    assert jaccard(set(), {"a"}) == 0.0
    assert jaccard({"a"}, set()) == 0.0


def test_match_records_greedy_bipartite() -> None:
    a = [
        Record(
            "a1",
            "YOLO processes images at 45 fps",
            {"polarity": "positive", "claim_type": "performance"},
        ),
        Record(
            "a2",
            "YOLO makes more localization errors",
            {"polarity": "negative", "claim_type": "limitation"},
        ),
        Record(
            "a3",
            "YOLO learns general object representations",
            {"polarity": "positive", "claim_type": "finding"},
        ),
    ]
    b = [
        Record(
            "b_00",
            "More localization errors with YOLO",
            {"polarity": "negative", "claim_type": "limitation"},
        ),
        Record(
            "b_01",
            "YOLO runs at 45 frames per second",
            {"polarity": "positive", "claim_type": "performance"},
        ),
        Record(
            "b_02",
            "YOLO is trained on PASCAL VOC",
            {"polarity": "neutral", "claim_type": "dataset"},
        ),
    ]
    res = match_records(a, b, min_score=0.20)
    pair_map = {p.a_id: p.b_id for p in res.pairs}
    assert pair_map["a1"] == "b_01"
    assert pair_map["a2"] == "b_00"
    assert "a3" in res.unmatched_a
    assert "b_02" in res.unmatched_b
    for p in res.pairs:
        assert p.field_disagreements == []


def test_match_records_field_disagreement_detected() -> None:
    a = [
        Record(
            "a1", "YOLO is fast at 45 fps", {"polarity": "positive", "claim_type": "performance"}
        )
    ]
    b = [
        Record("b_00", "YOLO runs at 45 fps", {"polarity": "neutral", "claim_type": "performance"})
    ]
    res = match_records(a, b)
    assert len(res.pairs) == 1
    assert res.pairs[0].field_disagreements == [
        {"field": "polarity", "a": "positive", "b": "neutral"}
    ]


def test_classify_spot_check_priority_branches() -> None:
    a = [Record(f"a{i}", "x", {"polarity": "positive", "claim_type": "method"}) for i in range(3)]
    no_diff = match_records(a, [])
    p, _ = classify_spot_check_priority(no_diff, a_total=3)
    assert p == "high"

    a = [Record("a1", "x", {"polarity": "positive", "claim_type": "method"})]
    b = [Record("b_00", "x", {"polarity": "positive", "claim_type": "finding"})]
    res = match_records(a, b, min_score=0.0)
    p, _ = classify_spot_check_priority(res, a_total=1)
    assert p == "medium"

    a = [Record("a1", "x", {"polarity": "positive", "claim_type": "method"})]
    b = [Record("b_00", "x", {"polarity": "positive", "claim_type": "method"})]
    res = match_records(a, b, min_score=0.0)
    p, _ = classify_spot_check_priority(res, a_total=1)
    assert p == "low"


def test_consistency_report_roundtrip(tmp_path: Path) -> None:
    rep = ConsistencyReport(
        pack_id="claims/corpus_x_v2",
        pack_path="tests/fixtures/benchmarks/claims/corpus_x_v2",
        layer="claims_v2",
        extractor_a=ExtractorInfo(role="human_authored_existing_gold", source="g.json", count=5),
        extractor_b=ExtractorInfo(
            role="llm_independent_extraction",
            source="article.md",
            model="deepseek/deepseek-v3.2",
            base_url="https://openrouter.ai/api/v1",
            prompt_hash="sha256:abc",
            count=4,
        ),
        matched_pairs=[],
        unmatched_a=[],
        unmatched_b=[],
        summary={
            "a_total": 5,
            "b_total": 4,
            "matched": 4,
            "unmatched_a": 1,
            "unmatched_b": 0,
            "field_agreements": {
                "polarity": {"agreed": 4, "disagreed": 0},
                "claim_type": {"agreed": 4, "disagreed": 0},
            },
        },
        spot_check_priority="medium",
        spot_check_priority_rationale="unmatched_a=1",
    )
    out = tmp_path / "consistency_report.json"
    write_report(rep, out)
    loaded = json.loads(out.read_text())
    assert validate_report_dict(loaded) == []
    assert loaded["schema_version"] == 1
    assert list(loaded.keys())[0] == "schema_version"


def test_claims_v2_discover_packs() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    extractor = ClaimsV2Extractor()
    packs = extractor.discover_packs(fixtures)
    assert len(packs) >= 20
    assert all((p / "gold.json").exists() for p in packs)
    assert any(p.name == "corpus_yolov1_v2" for p in packs)
    assert any(p.name.startswith("holdout_") for p in packs)


def test_claims_v2_build_call_spec_for_yolov1() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "claims" / "corpus_yolov1_v2"
    extractor = ClaimsV2Extractor()
    spec = extractor.build_call_spec(pack, model="deepseek/deepseek-v3.2", base_url="x")
    assert "object detection" in spec.user_prompt.lower()
    assert "yolo" in spec.user_prompt.lower()
    assert spec.response_format == "json_object"
    assert spec.temperature == 0.1


def test_claims_v2_parse_response_validates_enums() -> None:
    extractor = ClaimsV2Extractor()
    raw = json.dumps(
        {
            "claims": [
                {
                    "claim_text_normalized": "X is fast.",
                    "claim_type": "PERFORMANCE",
                    "polarity": "Positive",
                    "evidence_quote_short": "x runs at 45 fps",
                },
                {
                    "claim_text_normalized": "Y has bug.",
                    "claim_type": "weird-type",
                    "polarity": "garbage",
                    "evidence_quote_short": "",
                },
                {"claim_text_normalized": "", "claim_type": "method", "polarity": "positive"},
            ]
        }
    )
    parsed = extractor.parse_response(raw)
    assert len(parsed) == 2
    assert parsed[0]["claim_type"] == "performance"
    assert parsed[0]["polarity"] == "positive"
    assert parsed[1]["claim_type"] == "finding"
    assert parsed[1]["polarity"] == "neutral"


def test_claims_v2_parse_response_rejects_non_json() -> None:
    extractor = ClaimsV2Extractor()
    with pytest.raises(ValueError):
        extractor.parse_response("```json\n{not valid}\n```")


def test_char_jaccard_catches_morphology() -> None:
    a = "Detection performs well using anchor-free regression."
    b = "Anchor-free regression detector performs well."
    token_score = jaccard(tokenize(a), tokenize(b))
    char_score = char_jaccard(a, b, n=4)
    assert char_score > 0.0
    assert combined_score(a, b) >= token_score


def test_combined_scoring_beats_token_on_paraphrase() -> None:
    a = [
        Record(
            "yolov2_batchnorm_dropout_replace",
            (
                "YOLOv2 introduces batch normalization on every convolutional layer "
                "and removes dropout, improving mAP by more than two points."
            ),
            {"polarity": "positive", "claim_type": "method"},
        ),
    ]
    b = [
        Record(
            "b_00",
            "Adding batch normalization to YOLO improves mAP by more than 2%.",
            {"polarity": "positive", "claim_type": "method"},
        ),
    ]
    token_only = match_records(a, b, scoring="token", min_score=0.20)
    combined = match_records(a, b, scoring="combined")
    assert "yolov2_batchnorm_dropout_replace" in token_only.unmatched_a
    assert combined.pairs and combined.pairs[0].b_id == "b_00"


def test_claims_v2_rebuild_from_raw(tmp_path: Path) -> None:
    fixtures_src = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    src_pack = fixtures_src / "claims" / "corpus_yolov1_v2"
    layer1_src = fixtures_src / "layer1" / "yolov1"
    pack = tmp_path / "claims" / "corpus_yolov1_v2"
    pack.mkdir(parents=True)
    (pack / "gold.json").write_text((src_pack / "gold.json").read_text())
    layer1_dst = tmp_path / "layer1" / "yolov1"
    layer1_dst.mkdir(parents=True)
    (layer1_dst / "article.md").write_text((layer1_src / "article.md").read_text())
    raw = json.dumps(
        {
            "claims": [
                {
                    "claim_text_normalized": "YOLO frames detection as a single regression problem.",
                    "claim_type": "method",
                    "polarity": "positive",
                    "evidence_quote_short": "We frame object detection as a regression problem",
                }
            ]
        }
    )
    (pack / "consistency_report.raw.json").write_text(raw)
    extractor = ClaimsV2Extractor()
    run = extractor.rebuild_run_from_raw(
        pack, raw_path=pack / "consistency_report.raw.json", prior_report=None
    )
    assert run.structured_b and run.structured_b[0]["polarity"] == "positive"
    assert run.usage_tokens == {"total": 0}


class _StubEmbeddingScorer:
    """Deterministic stub for the embedding-cascade matcher tests.

    Returns a precomputed score for known pairs (order-insensitive) and 0.0 otherwise.
    Counts call invocations so tests can assert the cascade only consults embeddings
    for low-lexical pairs.
    """

    def __init__(self, scores: dict[frozenset, float]) -> None:
        self._scores = scores
        self.calls = 0

    def score(self, text_a: str, text_b: str) -> float:
        self.calls += 1
        return self._scores.get(frozenset({text_a, text_b}), 0.0)


def test_match_records_cascade_uses_embedding_only_when_lexical_low() -> None:
    a = [
        Record(
            "a_lex",
            "YOLO runs at 45 frames per second on a Titan X GPU",
            {"polarity": "positive", "claim_type": "performance"},
        ),
        Record(
            "a_emb",
            "high IoU threshold limits final accuracy",
            {"polarity": "negative", "claim_type": "limitation"},
        ),
    ]
    b = [
        Record(
            "b_lex",
            "YOLO runs at 45 frames per second",
            {"polarity": "positive", "claim_type": "performance"},
        ),
        Record(
            "b_emb",
            "training at high IoU threshold can degrade due to overfitting",
            {"polarity": "negative", "claim_type": "limitation"},
        ),
    ]
    scorer = _StubEmbeddingScorer(
        {
            frozenset({a[1].text, b[1].text}): 0.88,
        }
    )
    res = match_records(
        a,
        b,
        embedding_scorer=scorer,
        embedding_min_score=0.75,
        lexical_accept_threshold=0.50,
    )
    by_a = {p.a_id: p for p in res.pairs}
    assert by_a["a_lex"].score_source == "lexical"
    assert by_a["a_emb"].score_source == "embedding"
    assert by_a["a_emb"].score >= 0.75
    # cascade should query embeddings only for pairs whose lexical score
    # is below the accept threshold; the "a_lex / b_lex" pair must skip the call.
    assert scorer.calls < 4


def test_match_records_cascade_skips_embedding_below_floor() -> None:
    a = [
        Record(
            "a1",
            "Cascade R-CNN improves COCO AP by two to four points",
            {"polarity": "positive", "claim_type": "performance"},
        )
    ]
    b = [
        Record(
            "b_unrelated",
            "Object detection benefits from data augmentation",
            {"polarity": "neutral", "claim_type": "method"},
        )
    ]
    scorer = _StubEmbeddingScorer({frozenset({a[0].text, b[0].text}): 0.40})
    res = match_records(
        a,
        b,
        embedding_scorer=scorer,
        embedding_min_score=0.75,
        lexical_accept_threshold=0.50,
    )
    assert "a1" in res.unmatched_a
    assert "b_unrelated" in res.unmatched_b
    assert scorer.calls == 1


def test_promote_validation_status_idempotent(tmp_path: Path) -> None:
    from scripts.dual_extract_validate import _promote_validation_status

    pack = tmp_path / "claims_pack"
    pack.mkdir()
    gold_path = pack / "gold.json"
    gold_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "case_id": "x",
                "meta": {"validation_status": "draft", "needs_human_review": True},
                "expected_claims": [],
            }
        )
    )
    report_path = pack / "consistency_report.json"
    report_path.write_text("{}")

    changed_first = _promote_validation_status(gold_path, report_path=report_path, priority="low")
    assert changed_first is True
    after = json.loads(gold_path.read_text())
    assert after["meta"]["validation_status"] == "llm_dual_validated"
    assert after["meta"]["needs_human_review"] is False
    assert len(after["meta"]["validation_history"]) == 1

    changed_second = _promote_validation_status(gold_path, report_path=report_path, priority="medium")
    assert changed_second is False
    final = json.loads(gold_path.read_text())
    assert final["meta"]["validation_status"] == "llm_dual_validated"
    assert len(final["meta"]["validation_history"]) == 1


def test_openrouter_embedding_provider_caches_per_text(tmp_path: Path) -> None:
    """File cache hit short-circuits network calls; we mock the OpenAI client."""

    from unittest.mock import MagicMock

    from science_graphrag.embeddings import (
        OpenRouterEmbeddingProvider,
        OpenRouterEmbeddingSettings,
    )

    settings = OpenRouterEmbeddingSettings(
        api_key="stub",
        base_url="https://example.invalid",
        model="baai/bge-m3",
        cache_root=tmp_path,
        batch_size=8,
    )
    provider = OpenRouterEmbeddingProvider(settings)

    fake_resp = MagicMock()
    fake_resp.data = [
        MagicMock(embedding=[1.0, 0.0, 0.0]),
        MagicMock(embedding=[0.0, 1.0, 0.0]),
    ]
    provider._client.embeddings.create = MagicMock(return_value=fake_resp)  # type: ignore[attr-defined]

    out1 = provider.embed(["hello", "world"])
    assert out1.shape == (2, 3)
    assert provider.dim == 3

    out2 = provider.embed(["hello", "world"])
    assert out2.shape == (2, 3)
    assert provider._client.embeddings.create.call_count == 1  # type: ignore[attr-defined]


def test_claims_v2_dry_run_report_skeleton() -> None:
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "claims" / "corpus_yolov1_v2"
    extractor = ClaimsV2Extractor()
    gold_a = json.loads((pack / "gold.json").read_text())
    report = extractor.build_report(pack, run=None, gold_a=gold_a)
    assert report.layer == "claims_v2"
    assert report.summary["a_total"] == len(gold_a["expected_claims"])
    assert report.summary["b_total"] == 0
    assert report.spot_check_priority == "high"
    assert report.extractor_b.role.endswith("dry_run")
