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


def test_score_retrieval_answer_rouge_reported_when_reference_set() -> None:
    ga = GroundedAnswer(
        answer="the cat sat on mat",
        citations=[{"chunk_fingerprint": "stub-fp-1"}],
        graph_context={},
        retrieval_trace={"hit_count": 2},
    )
    gold = {
        "required_chunk_fingerprints": ["stub-fp-1"],
        "min_hit_count": 1,
        "answer_reference_text": "the cat sat on the mat",
    }
    m = score_retrieval_answer(ga, gold)
    assert m["passed"] is True
    assert m.get("answer_rouge_l") is not None
    assert float(m["answer_rouge_l"]) > 0.5


def test_score_retrieval_answer_rouge_can_fail_contract() -> None:
    ga = GroundedAnswer(
        answer="unrelated text about dogs",
        citations=[{"chunk_fingerprint": "stub-fp-1"}],
        graph_context={},
        retrieval_trace={"hit_count": 2},
    )
    gold = {
        "required_chunk_fingerprints": ["stub-fp-1"],
        "min_hit_count": 1,
        "answer_reference_text": "the cat sat on the mat",
        "min_answer_rouge_l": 0.99,
    }
    m = score_retrieval_answer(ga, gold)
    assert m["passed"] is False
    assert float(m.get("answer_rouge_l") or 0.0) < 0.99


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


def test_discover_retrieval_workspace_scoped_six_cases() -> None:
    root = RETRIEVAL_FIXTURES / "workspace_scoped"
    cases = discover_retrieval_case_dirs(root, tier="workspace_scoped")
    ids = {c.name for c in cases}
    assert len(ids) == 6
    assert ids == {
        "ws_pilot_od_methods_overview",
        "ws_pilot_od_chunk_anchor",
        "ws_pilot_od_scoped_negative",
        "ws_pilot_pdf_methods_overview",
        "ws_pilot_pdf_chunk_anchor",
        "ws_pilot_pdf_scoped_negative",
    }


def test_score_retrieval_workspace_scope_ok_when_trace_and_citations_match() -> None:
    member = "work-a"
    ga = GroundedAnswer(
        answer="scoped",
        citations=[{"chunk_fingerprint": "fp1", "work_id": member}],
        graph_context={},
        retrieval_trace={
            "hit_count": 1,
            "workspace_id": "ws-pilot-od",
            "embedding": {"embedding_model": "hash-deterministic"},
        },
    )
    gold = {
        "workspace_id": "ws-pilot-od",
        "expected_workspace_scope": True,
        "workspace_member_work_ids": [member],
        "forbidden_work_ids": ["external-work"],
        "min_hit_count": 1,
        "required_chunk_fingerprints": ["fp1"],
    }
    m = score_retrieval_answer(ga, gold)
    assert m["workspace_scope_ok"] is True
    assert m["trace_workspace_matches"] is True
    assert m.get("out_of_scope_citation_work_ids") == []
    assert m.get("forbidden_work_ids_leaked") == []
    assert m["passed"] is True


def test_score_retrieval_workspace_scope_fails_on_trace_workspace_mismatch() -> None:
    ga = GroundedAnswer(
        answer="x",
        citations=[{"work_id": "work-a"}],
        graph_context={},
        retrieval_trace={"hit_count": 1, "workspace_id": "ws-other"},
    )
    gold = {
        "workspace_id": "ws-pilot-od",
        "expected_workspace_scope": True,
        "workspace_member_work_ids": ["work-a"],
    }
    m = score_retrieval_answer(ga, gold)
    assert m["trace_workspace_matches"] is False
    assert m["workspace_scope_ok"] is False
    assert m["passed"] is False


def test_score_retrieval_workspace_scope_fails_on_forbidden_work_id() -> None:
    forbidden = "external-uuid"
    ga = GroundedAnswer(
        answer="leak",
        citations=[{"chunk_fingerprint": "fp1", "work_id": forbidden}],
        graph_context={},
        retrieval_trace={"hit_count": 1, "workspace_id": "ws-pilot-od"},
    )
    gold = {
        "workspace_id": "ws-pilot-od",
        "expected_workspace_scope": True,
        "workspace_member_work_ids": ["work-a"],
        "forbidden_work_ids": [forbidden],
        "min_hit_count": 1,
        "required_chunk_fingerprints": ["fp1"],
    }
    m = score_retrieval_answer(ga, gold)
    assert forbidden in (m.get("forbidden_work_ids_leaked") or [])
    assert m["workspace_scope_ok"] is False
    assert m["passed"] is False


def test_score_retrieval_contract_only_respects_workspace_scope() -> None:
    ga = GroundedAnswer(
        answer="x",
        citations=[{"work_id": "outsider"}],
        graph_context={},
        retrieval_trace={"hit_count": 0, "embedding": {"x": 1}, "workspace_id": "ws-1"},
    )
    gold = {
        "contract_only": True,
        "expected_workspace_scope": True,
        "workspace_id": "ws-1",
        "workspace_member_work_ids": ["member-only"],
        "forbidden_work_ids": ["outsider"],
    }
    m = score_retrieval_answer(ga, gold)
    assert m["contract_only"] is True
    assert m["workspace_scope_ok"] is False
    assert m["passed"] is False
