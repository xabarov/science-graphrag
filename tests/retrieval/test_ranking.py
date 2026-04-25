"""Unit tests for retrieval/ranking.py."""

from science_graphrag.retrieval.ranking import (
    _body_section_bonus,
    _hit_fingerprint_key,
    _is_likely_back_matter_section,
    _rank_hits_for_answer,
    _reciprocal_rank_fusion,
)


def _make_hit(
    score: float,
    work_id: str = "w1",
    chunk_id: str = "c1",
    section: str | None = None,
) -> dict:
    return {
        "id": chunk_id,
        "score": score,
        "work_id": work_id,
        "chunk_id": chunk_id,
        "section_path": section,
        "text": "test chunk",
        "title": "Test Work",
        "chunk_fingerprint": f"fp-{chunk_id}",
    }


def test_back_matter_section() -> None:
    assert _is_likely_back_matter_section("references") is True
    assert _is_likely_back_matter_section("introduction") is False
    assert _is_likely_back_matter_section(None) is False


def test_body_section_bonus() -> None:
    assert _body_section_bonus("abstract") > 0
    assert _body_section_bonus("references") <= 0


def test_rank_hits_returns_top_k() -> None:
    hits = [_make_hit(0.9 - idx * 0.1, chunk_id=f"c{idx}") for idx in range(10)]
    ranked = _rank_hits_for_answer(hits, top_k=3)
    assert len(ranked) == 3


def test_reciprocal_rank_fusion_deduplicates() -> None:
    hits_a = [_make_hit(0.9, work_id="w1", chunk_id="c1")]
    hits_b = [_make_hit(0.8, work_id="w1", chunk_id="c1")]
    merged = _reciprocal_rank_fusion([hits_a, hits_b])
    keys = [_hit_fingerprint_key(hit) for hit in merged]
    assert len(keys) == len(set(keys)), "duplicates present after RRF"
