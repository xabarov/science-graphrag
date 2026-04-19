"""Retrieval benchmark scoring (Wave F)."""

from __future__ import annotations

from pathlib import Path

from eval.retrieval.metrics import score_retrieval_answer
from eval.retrieval.runner import discover_retrieval_case_dirs, run_retrieval_case
from science_graphrag.api.retrieval import GroundedAnswer

RETRIEVAL_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "benchmarks" / "retrieval"


def test_score_retrieval_contract_only_passes_minimal_trace() -> None:
    ga = GroundedAnswer(
        answer="x",
        citations=[],
        graph_context={},
        retrieval_trace={"hit_count": 0, "embedding": {"embedding_model": "hash-deterministic"}},
    )
    gold = {"contract_only": True}
    m = score_retrieval_answer(ga, gold)
    assert m["passed"] is True


def test_score_retrieval_requires_fingerprints() -> None:
    ga = GroundedAnswer(
        answer="x",
        citations=[{"chunk_fingerprint": "stub-fp-1"}],
        graph_context={},
        retrieval_trace={"hit_count": 2},
    )
    gold = {"required_chunk_fingerprints": ["stub-fp-1", "stub-fp-2"], "min_hit_count": 1}
    m = score_retrieval_answer(ga, gold)
    assert m["passed"] is False
    assert "stub-fp-2" in (m.get("missing_chunk_fingerprints") or [])


def test_run_retrieval_case_with_mock_answer_fn(tmp_path: Path) -> None:
    root = tmp_path / "case_z"
    root.mkdir()
    (root / "question.txt").write_text("hello world", encoding="utf-8")
    (root / "gold.json").write_text(
        '{"required_chunk_fingerprints": ["stub-fp-1", "stub-fp-2"], "min_hit_count": 1}',
        encoding="utf-8",
    )

    def _fake_answer(_q: str, **_kwargs) -> GroundedAnswer:
        return GroundedAnswer(
            answer="mock",
            citations=[
                {"chunk_fingerprint": "stub-fp-1"},
                {"chunk_fingerprint": "stub-fp-2"},
            ],
            graph_context={},
            retrieval_trace={"hit_count": 3},
        )

    report = run_retrieval_case(root, settings=None, answer_fn=_fake_answer)
    assert report["case_id"] == "case_z"
    assert report["metrics"]["passed"] is True


def test_discover_retrieval_merge_safe_contract_three_cases() -> None:
    cases = discover_retrieval_case_dirs(RETRIEVAL_FIXTURES, tier="merge_safe_contract")
    ids = {c.name for c in cases}
    assert ids == {"cv_corpus_methods_overview", "single_stage_detectors", "yolo_family_keywords"}


def test_discover_retrieval_strict_pilot_excluded_from_merge_safe() -> None:
    merge_ids = {
        c.name for c in discover_retrieval_case_dirs(RETRIEVAL_FIXTURES, tier="merge_safe_contract")
    }
    assert "strict_pilot_methods" not in merge_ids


def test_discover_retrieval_strict_pilot_three_cases() -> None:
    cases = discover_retrieval_case_dirs(RETRIEVAL_FIXTURES, tier="strict_pilot")
    ids = {c.name for c in cases}
    assert ids == {"strict_pilot_methods", "strict_pilot_work_scoped", "strict_pilot_corpus_wide"}
