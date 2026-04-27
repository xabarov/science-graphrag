"""Unit tests for OD claims gap classification (no live DB)."""

from __future__ import annotations

from eval.chat_agent.od_claims_gap_audit import classify_od_claims_gap


def _base_row(**kwargs):
    """Minimal work row for classifier tests."""
    row = {
        "work_id": "w1",
        "neo4j_claim_count": 0,
        "qdrant_claim_vector_count": 0,
        "qdrant_chunk_points_total": 10,
        "neo4j_method_count": 2,
        "documents": [],
    }
    row.update(kwargs)
    return row


def test_classify_ok_when_neo_has_claims_and_vectors():
    """Works with Neo4j + Qdrant claims are not in the missing-claims bucket."""
    cls, _reason, _ev = classify_od_claims_gap(
        row=_base_row(neo4j_claim_count=3, qdrant_claim_vector_count=3),
        manifest_claims_extraction_enabled=True,
        path_to_progress={},
        doc_id_to_progress={},
    )
    assert cls == "ok"


def test_classify_claims_embed_missing():
    """Neo4j claims without vectors maps to claims_embed_missing."""
    cls, reason, ev = classify_od_claims_gap(
        row=_base_row(neo4j_claim_count=2, qdrant_claim_vector_count=0),
        manifest_claims_extraction_enabled=True,
        path_to_progress={},
        doc_id_to_progress={},
    )
    assert cls == "claims_embed_missing"
    assert ev.get("neo4j_claim_count") == 2
    assert "qdrant" in reason.lower()


def test_classify_stage_not_run_from_progress_skip():
    """Duplicate-sha skip in ingest progress implies claims stage not re-run."""
    cls, reason, _ev = classify_od_claims_gap(
        row=_base_row(
            documents=[
                {
                    "document_id": "doc-1",
                    "source_path": "/data/papers/foo.pdf",
                    "checkpoint": {"version": 1, "last_completed": None, "stages": {}},
                },
            ],
        ),
        manifest_claims_extraction_enabled=True,
        path_to_progress={"/data/papers/foo.pdf": {"status": "skip", "document_id": "doc-1"}},
        doc_id_to_progress={},
    )
    assert cls == "claims_stage_not_run"
    assert "skip" in reason.lower()


def test_classify_extraction_failed_from_checkpoint():
    """Failed extract_claims stage in checkpoint is claims_extraction_failed."""
    cls, reason, _ev = classify_od_claims_gap(
        row=_base_row(
            documents=[
                {
                    "document_id": "d1",
                    "source_path": "/x.md",
                    "checkpoint": {
                        "version": 1,
                        "stages": {
                            "extract_claims": {
                                "status": "failed_terminal",
                                "error": "boom",
                            },
                        },
                    },
                },
            ],
        ),
        manifest_claims_extraction_enabled=True,
        path_to_progress={},
        doc_id_to_progress={},
    )
    assert cls == "claims_extraction_failed"
    assert "extract_claims" in reason


def test_classify_unknown_when_no_signals():
    """No progress/checkpoints => unknown with explicit fact summary."""
    cls, reason, ev = classify_od_claims_gap(
        row=_base_row(documents=[]),
        manifest_claims_extraction_enabled=True,
        path_to_progress={},
        doc_id_to_progress={},
    )
    assert cls == "unknown"
    assert "neo4j_claim_count=0" in reason
    assert ev.get("neo4j_claim_count") == 0


def test_classify_stage_not_run_chunk_without_extract():
    """Chunk completed in checkpoint but no extract_claims entry."""
    cls, reason, _ev = classify_od_claims_gap(
        row=_base_row(
            qdrant_chunk_points_total=5,
            documents=[
                {
                    "document_id": "d1",
                    "source_path": "/a.pdf",
                    "checkpoint": {
                        "version": 1,
                        "stages": {"chunk": {"status": "completed"}},
                    },
                },
            ],
        ),
        manifest_claims_extraction_enabled=True,
        path_to_progress={},
        doc_id_to_progress={},
    )
    assert cls == "claims_stage_not_run"
    assert "extract_claims" in reason.lower()
