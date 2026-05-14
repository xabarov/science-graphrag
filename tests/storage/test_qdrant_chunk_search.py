"""Unit tests for split Qdrant chunk similarity helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from qdrant_client.models import FieldCondition, Filter

from science_graphrag.storage.qdrant_store.chunk_search import (
    build_chunk_similarity_filter,
    map_chunk_query_hit,
    query_similar_chunks,
)


def test_build_chunk_similarity_filter_workspace_plus_work_id() -> None:
    flt = build_chunk_similarity_filter(
        work_id="work-1",
        work_ids=None,
        workspace_id="ws-a",
    )
    assert isinstance(flt, Filter)
    must = list(flt.must or [])
    assert len(must) == 2
    assert isinstance(must[0], FieldCondition)
    assert must[0].key == "workspace_ids"
    assert isinstance(must[1], FieldCondition)
    assert must[1].key == "work_id"


def test_map_chunk_query_hit_falls_back_to_id_when_fingerprint_missing() -> None:
    hit = SimpleNamespace(
        id="pid-1",
        score=0.81,
        payload={
            "text": "chunk text",
            "work_id": "w",
            "document_id": "d",
            "section_path": "## Intro",
            "chunk_kind": "paragraph",
            "language": "en",
        },
    )
    row = map_chunk_query_hit(hit)
    assert row["id"] == "pid-1"
    assert row["chunk_fingerprint"] == "pid-1"
    assert row["score"] == 0.81
    assert row["text"] == "chunk text"


def test_query_similar_chunks_delegates_query_points_and_maps_hits() -> None:
    client = MagicMock()
    client.query_points.return_value = SimpleNamespace(
        points=[
            SimpleNamespace(
                id="pid-2",
                score=0.77,
                payload={"text": "a", "work_id": "w", "chunk_fingerprint": "fp-2"},
            )
        ]
    )
    out = query_similar_chunks(
        client,
        "chunks",
        vector=[0.1, 0.2],
        limit=3,
        workspace_id="ws-1",
    )
    client.query_points.assert_called_once()
    assert out == [
        {
            "id": "pid-2",
            "score": 0.77,
            "text": "a",
            "work_id": "w",
            "document_id": None,
            "chunk_fingerprint": "fp-2",
            "section_path": None,
            "chunk_kind": None,
            "language": None,
        }
    ]
