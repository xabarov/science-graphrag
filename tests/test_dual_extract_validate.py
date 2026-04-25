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

    changed_second = _promote_validation_status(
        gold_path, report_path=report_path, priority="medium"
    )
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


# ---------------------------------------------------------------------------
# Phase 6.C — lenient JSON parsing (raw_decode + fenced fallback)
# ---------------------------------------------------------------------------


def test_parse_json_object_lenient_strict() -> None:
    from scripts.dual_validate.extractors.base import parse_json_object_lenient

    obj = parse_json_object_lenient('  {"a": 1}  ')
    assert obj == {"a": 1}


def test_parse_json_object_lenient_unwraps_fences() -> None:
    from scripts.dual_validate.extractors.base import parse_json_object_lenient

    raw = '```json\n{"a": 2}\n```'
    assert parse_json_object_lenient(raw) == {"a": 2}


def test_parse_json_object_lenient_extracts_first_object_with_trailing_text() -> None:
    from scripts.dual_validate.extractors.base import parse_json_object_lenient

    raw = '{"a": 3, "b": [1,2]}\n\n## Notes\nthis is commentary that broke strict json.loads'
    assert parse_json_object_lenient(raw) == {"a": 3, "b": [1, 2]}


def test_parse_json_object_lenient_raises_on_garbage() -> None:
    from scripts.dual_validate.extractors.base import parse_json_object_lenient

    with pytest.raises(ValueError):
        parse_json_object_lenient("totally not json")


# ---------------------------------------------------------------------------
# Phase 6.C — concept_topic_v2 extractor
# ---------------------------------------------------------------------------


def test_concept_topic_v2_discover_packs() -> None:
    from scripts.dual_validate.extractors import ConceptTopicV2Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    packs = ConceptTopicV2Extractor().discover_packs(fixtures)
    assert len(packs) >= 9
    assert all(p.name.startswith("corpus_") and p.name.endswith("_v2") for p in packs)


def test_concept_topic_v2_build_call_spec_lists_frozen() -> None:
    from scripts.dual_validate.extractors import ConceptTopicV2Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "concept_topic" / "corpus_yolov1_v2"
    spec = ConceptTopicV2Extractor().build_call_spec(
        pack, model="deepseek/deepseek-v3.2", base_url="x"
    )
    assert "anchor_based" in spec.user_prompt
    assert "focal_loss" in spec.user_prompt
    assert spec.response_format == "json_object"


def test_concept_topic_v2_parse_response_validates_status() -> None:
    from scripts.dual_validate.extractors import ConceptTopicV2Extractor

    raw = json.dumps(
        {
            "labels": [
                {
                    "concept_id": "anchor_based",
                    "status": "PRESENT",
                    "evidence_quote": "uses k anchors",
                },
                {
                    "concept_id": "focal_loss",
                    "status": "absent",
                    "rationale": "predates focal loss",
                },
                {"concept_id": "anchor_based", "status": "absent", "rationale": "dup"},
                {"concept_id": "", "status": "present"},
                {"concept_id": "x", "status": "garbage"},
            ]
        }
    )
    parsed = ConceptTopicV2Extractor().parse_response(raw)
    assert [e["concept_id"] for e in parsed] == ["anchor_based", "focal_loss"]
    assert parsed[0]["status"] == "present"
    assert parsed[1]["status"] == "absent"


def test_concept_topic_v2_build_report_flips_drive_priority() -> None:
    from scripts.dual_validate.extractors import ConceptTopicV2Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "concept_topic" / "corpus_yolov1_v2"
    extractor = ConceptTopicV2Extractor()
    gold_a = json.loads((pack / "gold.json").read_text())
    report_dry = extractor.build_report(pack, run=None, gold_a=gold_a)
    assert report_dry.summary["a_total"] >= 5
    assert report_dry.spot_check_priority == "high"


# ---------------------------------------------------------------------------
# Phase 6.C — contradictions_v1 extractor
# ---------------------------------------------------------------------------


def test_contradictions_v1_discover_and_build_call_spec() -> None:
    from scripts.dual_validate.extractors import ContradictionsV1Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    extractor = ContradictionsV1Extractor()
    packs = extractor.discover_packs(fixtures)
    assert len(packs) >= 5
    spec = extractor.build_call_spec(packs[0], model="deepseek/deepseek-v3.2", base_url="x")
    assert "ARTICLE_A" in spec.user_prompt and "ARTICLE_B" in spec.user_prompt


def test_contradictions_v1_parse_response_normalises_enums() -> None:
    from scripts.dual_validate.extractors import ContradictionsV1Extractor

    raw = json.dumps(
        {
            "contradiction_found": True,
            "claim_a_text": "A says X",
            "claim_b_text": "B says not X",
            "claim_a_quote": "A quote",
            "claim_b_quote": "B quote",
            "contradiction_type": "ERA_SHIFT",
            "severity": "Direct",
            "rationale": "ok",
        }
    )
    parsed = ContradictionsV1Extractor().parse_response(raw)
    assert parsed[0]["contradiction_type"] == ""  # uppercase rejected → not in allowed set
    assert parsed[0]["severity"] == "direct"
    assert parsed[0]["contradiction_found"] is True


def test_contradictions_v1_build_report_unmatched_when_b_says_no() -> None:
    from scripts.dual_validate.extractors import ContradictionsV1Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "contradictions_v1" / "pair_01_faster_rcnn_vs_retinanet_focal"
    extractor = ContradictionsV1Extractor()
    gold_a = json.loads((pack / "gold.json").read_text())
    report = extractor.build_report(pack, run=None, gold_a=gold_a)
    assert report.summary["unmatched_a"] == 1
    assert report.spot_check_priority == "high"


# ---------------------------------------------------------------------------
# Phase 6.C — idea_assist_live extractor
# ---------------------------------------------------------------------------


def test_idea_assist_live_discover_and_parse() -> None:
    from scripts.dual_validate.extractors import IdeaAssistLiveExtractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    extractor = IdeaAssistLiveExtractor()
    packs = extractor.discover_packs(fixtures)
    assert len(packs) >= 4
    raw = json.dumps(
        {
            "pool_relevance": [
                {"claim_id": "yolov1_speed_45_155_fps", "relevance": "high", "rationale": "ok"},
                {"claim_id": "extra_unknown_id", "relevance": "low", "rationale": "ok"},
            ],
            "pool_sufficiency": "thin",
            "pool_sufficiency_rationale": "only 2 truly relevant",
            "forbidden_substrings_quality": "appropriate",
            "forbidden_substrings_rationale": "good",
            "reference_hypothesis_quality": "plausible",
            "reference_hypothesis_rationale": "ok",
            "overall_assessment": "needs_revision",
            "issues": ["pool too narrow"],
        }
    )
    parsed = extractor.parse_response(raw)
    assert parsed[0]["pool_sufficiency"] == "thin"
    assert parsed[0]["pool_relevance"][1]["relevance"] == "low"
    assert parsed[0]["issues"] == ["pool too narrow"]


def test_idea_assist_live_classify_priority() -> None:
    from scripts.dual_validate.extractors import IdeaAssistLiveExtractor

    extractor = IdeaAssistLiveExtractor()
    review_low = {
        "pool_relevance": [{"claim_id": "x", "relevance": "high"}],
        "pool_sufficiency": "sufficient",
        "forbidden_substrings_quality": "appropriate",
        "reference_hypothesis_quality": "plausible",
        "overall_assessment": "ok",
    }
    assert extractor._classify_priority(review_low)[0] == "low"

    review_med = dict(review_low, pool_sufficiency="thin")
    assert extractor._classify_priority(review_med)[0] == "medium"

    review_high = dict(review_low, pool_relevance=[{"claim_id": "x", "relevance": "low"}])
    assert extractor._classify_priority(review_high)[0] == "high"


# ---------------------------------------------------------------------------
# Phase 6.C — dedup extractors (authors / institutions / venues / methods / datasets)
# ---------------------------------------------------------------------------


def test_dedup_authors_extractor_discovers_pack_and_builds_prompt() -> None:
    from scripts.dual_validate.extractors import DedupAuthorsV1Extractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    extractor = DedupAuthorsV1Extractor()
    packs = extractor.discover_packs(fixtures)
    assert len(packs) == 1 and packs[0].name == "authors_v1"
    spec = extractor.build_call_spec(packs[0], model="m", base_url="x")
    assert "Resolve the author records" in spec.user_prompt
    assert "entity_id:" in spec.user_prompt


def test_dedup_parse_response_drops_unknown_ids_and_completes_singletons() -> None:
    from scripts.dual_validate.extractors.dedup_v1 import (
        DedupAuthorsV1Extractor,
        _validate_clusters,
    )

    raw = json.dumps(
        {
            "clusters": [
                {
                    "cluster_id": "c1",
                    "entity_ids": ["auth_redmon_joseph_full", "auth_redmon_j_initial"],
                },
                {"cluster_id": "c_bad", "entity_ids": ["nonexistent_id"]},
            ],
            "negative_pairs": [],
        }
    )
    parsed = DedupAuthorsV1Extractor().parse_response(raw)
    assert parsed[0]["clusters"][0]["cluster_id"] == "c1"
    valid = {"auth_redmon_joseph_full", "auth_redmon_j_initial", "auth_other"}
    cleaned = _validate_clusters(parsed[0]["clusters"], valid)
    cluster_ids_by_size = sorted(len(c["entity_ids"]) for c in cleaned)
    assert cluster_ids_by_size == [1, 2]  # one merged + one singleton (auth_other)


def test_dedup_pair_counting_metrics_perfect_agreement() -> None:
    from scripts.dual_validate.extractors.dedup_v1 import _pair_counting_metrics

    a = {"x": "c1", "y": "c1", "z": "c2"}
    b = {"x": "alpha", "y": "alpha", "z": "beta"}  # same partition, different labels
    metrics = _pair_counting_metrics(a, b)
    assert metrics["pair_f1"] == 1.0
    assert metrics["adjusted_rand_index"] == 1.0


def test_dedup_pair_counting_metrics_split_cluster() -> None:
    from scripts.dual_validate.extractors.dedup_v1 import _pair_counting_metrics

    # 4-element example so ARI cleanly drops below 1.0 (3-element split makes
    # ARI exactly 0 by the Hubert-Arabie formulation, which is unintuitive).
    a = {"w": "c1", "x": "c1", "y": "c1", "z": "c1"}  # A: all together
    b = {"w": "u", "x": "u", "y": "u", "z": "v"}  # B: split z out
    metrics = _pair_counting_metrics(a, b)
    assert metrics["pair_precision"] == 1.0  # everything B groups, A also groups
    assert metrics["pair_recall"] < 1.0
    assert metrics["pair_f1"] < 1.0
    assert 0.0 <= metrics["adjusted_rand_index"] < 1.0  # ARI floors at 0 by construction


def test_dedup_build_report_classifies_high_when_ari_low() -> None:
    from scripts.dual_validate.extractors import DedupAuthorsV1Extractor

    extractor = DedupAuthorsV1Extractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "dedup" / "authors_v1"
    gold_a = json.loads((pack / "gold.json").read_text())
    report = extractor.build_report(pack, run=None, gold_a=gold_a)
    assert report.spot_check_priority == "high"
    assert report.summary["metrics"]["adjusted_rand_index"] == 0.0
    assert report.summary["b_total"] == 0


# ---------------------------------------------------------------------------
# Phase 6.C — retrieval extractors (workspace_scoped_live, hybrid_ablation_v2, multihop_v2)
# ---------------------------------------------------------------------------


def test_workspace_scoped_live_negative_case_is_low_when_b_empty() -> None:
    from scripts.dual_validate.extractors import WorkspaceScopedLiveExtractor

    extractor = WorkspaceScopedLiveExtractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    packs = extractor.discover_packs(fixtures)
    pack = next(p for p in packs if p.name == "ws_yolo_negative_mask_segmentation")
    gold_a = json.loads((pack / "gold.json").read_text())

    class _RunStub:
        structured_b = [
            {
                "expected_corpus_work_ids": [],
                "would_violate_workspace_with": [],
                "rationale": "abstain",
            }
        ]
        prompt_hash = "sha256:00"
        usage_tokens = {"prompt": 1, "completion": 1, "total": 2}
        latency_ms = 0.0

        class call_spec:  # noqa: N801 — dataclass-like stub
            model = "stub"
            base_url = "x"

    report = extractor.build_report(pack, run=_RunStub(), gold_a=gold_a)
    assert report.spot_check_priority == "low"


def test_workspace_scoped_live_high_when_boundary_violation() -> None:
    from scripts.dual_validate.extractors import WorkspaceScopedLiveExtractor

    extractor = WorkspaceScopedLiveExtractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    packs = extractor.discover_packs(fixtures)
    pack = next(p for p in packs if p.name == "ws_yolo_speed_question")
    gold_a = json.loads((pack / "gold.json").read_text())
    forbidden_id = gold_a["forbidden_corpus_work_ids"][0]

    class _RunStub:
        structured_b = [
            {
                "expected_corpus_work_ids": ["yolov1", forbidden_id],  # boundary leak
                "would_violate_workspace_with": [],
                "rationale": "leaked",
            }
        ]
        prompt_hash = "sha256:00"
        usage_tokens = None
        latency_ms = None

        class call_spec:  # noqa: N801
            model = "stub"
            base_url = "x"

    report = extractor.build_report(pack, run=_RunStub(), gold_a=gold_a)
    assert report.spot_check_priority == "high"
    assert "boundary leak" in report.spot_check_priority_rationale


def test_hybrid_ablation_v2_set_overlap_metrics() -> None:
    from scripts.dual_validate.extractors import HybridAblationV2Extractor

    extractor = HybridAblationV2Extractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "retrieval" / "hybrid_ablation_v2" / "ha_anchor_free"
    gold_a = json.loads((pack / "gold.json").read_text())

    class _RunStub:
        structured_b = [
            {
                "relevant": list(gold_a["relevant_corpus_work_ids"]),
                "irrelevant": list(gold_a["irrelevant_corpus_work_ids"]),
                "rationale": "agreed",
            }
        ]
        prompt_hash = "sha256:00"
        usage_tokens = None
        latency_ms = None

        class call_spec:  # noqa: N801
            model = "stub"
            base_url = "x"

    report = extractor.build_report(pack, run=_RunStub(), gold_a=gold_a)
    assert report.spot_check_priority == "low"
    assert report.summary["accuracy"] == 1.0


def test_multihop_v2_chain_order_correctness_via_kendall() -> None:
    from scripts.dual_validate.extractors.retrieval_v1 import _kendall_order

    a = ["yolov1", "yolov2", "yolov3", "yolox"]
    assert _kendall_order(a, a) == 1.0
    assert _kendall_order(a, list(reversed(a))) == 0.0
    # one swap → 5/6 correct (out of 6 ordered pairs)
    swapped = ["yolov1", "yolov3", "yolov2", "yolox"]
    assert 0.6 < _kendall_order(a, swapped) < 1.0


def test_multihop_v2_set_case_b_uses_slug_canonical_disagreement() -> None:
    from scripts.dual_validate.extractors import MultihopV2Extractor

    extractor = MultihopV2Extractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "retrieval" / "multihop_v2" / "mh_authors_yolo_intersect_rcnn_family"
    gold_a = json.loads((pack / "gold.json").read_text())

    class _RunStub:
        structured_b = [
            {
                "expected_chain_corpus_work_ids": [],
                "expected_node_canonical_names": ["ross_girshick", "ali_farhadi"],  # slug-form
                "rationale": "guessed slugs",
            }
        ]
        prompt_hash = "sha256:00"
        usage_tokens = None
        latency_ms = None

        class call_spec:  # noqa: N801
            model = "stub"
            base_url = "x"

    report = extractor.build_report(pack, run=_RunStub(), gold_a=gold_a)
    assert report.spot_check_priority == "high"
    assert report.summary["metrics"]["jaccard"] == 0.0


# ---------------------------------------------------------------------------
# Phase 6.C — agent_tools_live extractor
# ---------------------------------------------------------------------------


def test_agent_tools_live_discovers_only_live_packs() -> None:
    from scripts.dual_validate.extractors import AgentToolsLiveExtractor

    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    extractor = AgentToolsLiveExtractor()
    packs = extractor.discover_packs(fixtures)
    assert all(p.name.startswith("live_") for p in packs)
    assert len(packs) == 6


def test_agent_tools_live_negative_case_is_low_when_b_abstains() -> None:
    from scripts.dual_validate.extractors import AgentToolsLiveExtractor

    extractor = AgentToolsLiveExtractor()
    fixtures = Path(__file__).resolve().parents[1] / "tests/fixtures/benchmarks"
    pack = fixtures / "agent_tools_v1" / "live_06_negative_blockchain_unanswerable"
    gold_a = json.loads((pack / "gold.json").read_text())

    class _RunStub:
        structured_b = [
            {
                "tool_sequence": ["vector_search", "final_answer"],
                "expected_works_corpus_ids": [],
                "expected_methods_canonical": [],
                "answer_reference_text": "No paper in the corpus introduces blockchain detection.",
                "expected_behavior": "abstain_or_empty",
            }
        ]
        prompt_hash = "sha256:00"
        usage_tokens = None
        latency_ms = None

        class call_spec:  # noqa: N801
            model = "stub"
            base_url = "x"

    report = extractor.build_report(pack, run=_RunStub(), gold_a=gold_a)
    assert report.spot_check_priority == "low"
    assert report.summary["is_negative_case"] is True


def test_agent_tools_live_parse_response_normalises_tool_dicts_and_strings() -> None:
    from scripts.dual_validate.extractors import AgentToolsLiveExtractor

    raw = json.dumps(
        {
            "expected_tool_sequence": [
                {"tool_name": "vector_search"},
                "cypher_query",
                {"tool_name": "cite_works"},
            ],
            "expected_works_corpus_ids": ["yolov1"],
            "expected_methods_canonical": ["focal_loss"],
            "answer_reference_text": "ok",
            "expected_behavior": "answer",
        }
    )
    parsed = AgentToolsLiveExtractor().parse_response(raw)
    assert parsed[0]["tool_sequence"] == ["vector_search", "cypher_query", "cite_works"]
    assert parsed[0]["expected_methods_canonical"] == ["focal_loss"]
