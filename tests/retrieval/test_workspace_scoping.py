"""Workspace scope: unbounded (full-corpus) vs bounded Neo4j membership."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.retrieval.answer import answer_query
from science_graphrag.retrieval.neo4j_context import _workspace_scope_work_ids


def test_unbounded_workspace_scope_returns_none_work_ids() -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = {
        "id": "ws_full_corpus",
        "name": "Full",
        "work_ids": [],
        "unbounded": True,
    }
    work_ids, meta = _workspace_scope_work_ids(neo, "ws_full_corpus")
    assert work_ids is None
    assert meta.get("workspace_unbounded") is True
    assert meta.get("workspace_id") == "ws_full_corpus"


def test_bounded_workspace_scope_returns_member_work_ids() -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = {
        "id": "ws_yolo_family",
        "name": "YOLO",
        "work_ids": ["uuid-a", "uuid-b"],
        "unbounded": False,
    }
    work_ids, meta = _workspace_scope_work_ids(neo, "ws_yolo_family")
    assert work_ids == ["uuid-a", "uuid-b"]
    assert "workspace_unbounded" not in meta
    assert meta.get("workspace_scope_work_count") == 2


def test_missing_workspace_still_empty_scope() -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = None
    work_ids, meta = _workspace_scope_work_ids(neo, "ws_missing")
    assert work_ids == []
    assert meta.get("workspace_missing") is True


@pytest.mark.parametrize(
    "row_extra",
    [
        {"unbounded": False},
        {},
    ],
)
def test_workspace_without_unbounded_true_treated_as_bounded(row_extra: dict) -> None:
    neo = MagicMock()
    neo.workspace_get.return_value = {"id": "ws_x", "name": "X", "work_ids": [], **row_extra}
    work_ids, meta = _workspace_scope_work_ids(neo, "ws_x")
    assert work_ids == []
    assert meta.get("workspace_unbounded") is None


def test_unbounded_workspace_returns_full_corpus() -> None:
    """Unbounded scope must not zero hits before Qdrant; trace shows ``workspace_unbounded``."""
    neo = MagicMock()
    neo.workspace_get.return_value = {
        "id": "ws_full_corpus",
        "work_ids": [],
        "unbounded": True,
    }
    stores = StoreRegistry(
        neo4j=neo,
        qdrant_chunks=MagicMock(),
        qdrant_works=MagicMock(),
        qdrant_claims=MagicMock(),
        blob=MagicMock(),
        artifacts=MagicMock(),
    )
    hits = [
        {
            "id": "pt-1",
            "score": 0.91,
            "text": "anchor-free object detectors",
            "work_id": "11111111-1111-1111-1111-111111111111",
            "document_id": "doc-1",
            "chunk_fingerprint": "fp-1",
            "section_path": None,
            "chunk_kind": None,
            "language": None,
        },
    ]
    with patch(
        "science_graphrag.retrieval.answer._qdrant_hits_for_answer", return_value=([], {}, hits)
    ):
        with patch(
            "science_graphrag.retrieval.answer._graph_context_for_hits",
            return_value=(
                {"methods": [], "semantic_available": False},
                "11111111-1111-1111-1111-111111111111",
            ),
        ):
            with patch(
                "science_graphrag.retrieval.answer._try_query_answer_llm", return_value=(None, {})
            ):
                ga = answer_query(
                    "What are anchor-free detectors?",
                    stores=stores,
                    workspace_id="ws_full_corpus",
                    top_k=3,
                    mode="vector",
                )
    assert ga.retrieval_trace.get("hit_count") == 1
    assert ga.retrieval_trace.get("workspace_unbounded") is True
    assert "no_retrieval_hits" not in (ga.retrieval_trace.get("degraded") or [])
