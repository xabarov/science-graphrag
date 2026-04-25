"""BT2: workspace_scoped_live scoring (forbidden work ids + abstain_keywords)."""

from __future__ import annotations

from eval.retrieval.metrics import score_workspace_scoped_live_answer
from science_graphrag.retrieval import GroundedAnswer


def test_forbidden_corpus_work_id_in_citations_fails() -> None:
    """Citing a forbidden corpus work id increments violation count and fails the case."""
    gold = {
        "schema_version": 1,
        "workspace_id": "ws",
        "forbidden_corpus_work_ids": ["leaked_work"],
        "forbidden_violation_gate": 0,
        "expected_citations": [],
        "min_hit_count": 0,
    }
    ga = GroundedAnswer(
        answer="answer",
        citations=[{"work_id": "leaked_work", "chunk_fingerprint": "fp1"}],
        graph_context={},
        retrieval_trace={"hit_count": 1, "workspace_id": "ws"},
    )
    m = score_workspace_scoped_live_answer(ga, gold, workspace_catalog=None)
    assert m["forbidden_work_id_violation_count"] >= 1
    assert m["passed"] is False


def test_abstain_keywords_must_contain_any_requires_phrase_or_empty() -> None:
    """``abstain_keywords`` + ``must_contain_any`` requires a keyword hit (or empty abstain)."""
    gold = {
        "schema_version": 1,
        "workspace_id": "ws",
        "forbidden_corpus_work_ids": [],
        "forbidden_violation_gate": 0,
        "expected_citations": [],
        "min_hit_count": 0,
        "answer_metric": {
            "type": "abstain_keywords",
            "must_contain_any": ["not enough information"],
        },
    }
    ga_bad = GroundedAnswer(
        answer="I will guess wildly.",
        citations=[],
        graph_context={},
        retrieval_trace={"hit_count": 0, "workspace_id": "ws"},
    )
    m_bad = score_workspace_scoped_live_answer(ga_bad, gold, workspace_catalog=None)
    assert m_bad["answer_metric_type"] == "abstain_keywords"
    assert m_bad["passed"] is False

    ga_ok = GroundedAnswer(
        answer="Not enough information in the corpus.",
        citations=[],
        graph_context={},
        retrieval_trace={"hit_count": 0, "workspace_id": "ws"},
    )
    m_ok = score_workspace_scoped_live_answer(ga_ok, gold, workspace_catalog=None)
    assert m_ok["abstain_keyword_hit"] is True
    assert m_ok["passed"] is True
