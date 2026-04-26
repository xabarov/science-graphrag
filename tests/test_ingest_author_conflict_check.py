"""Tests for ingest-time author dedup conflict enqueue."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import Settings
from science_graphrag.dedup.ingest_conflict_check import (
    enqueue_author_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.storage.models_orm import AuthorDedupConflict, Base


@pytest.fixture()
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def test_enqueue_author_inserts_ingest_origin_on_high_similarity(sqlite_session):
    neo = MagicMock()
    neo.workspace_get.return_value = {"id": "ws1"}
    neo.list_work_authors.return_value = [{"id": "a-new", "full_name": "Jane Doe"}]
    neo.list_workspace_authors.return_value = [
        {"id": "a-new", "full_name": "Jane Doe"},
        {"id": "a-old", "full_name": "Jane Doe"},
    ]
    neo.fetch_author_affiliation_hint.return_value = "MIT"
    settings = Settings()

    with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedder") as me:
        ev = MagicMock()
        ev.embed.return_value = [[0.1, 0.2, 0.3, 0.4]]
        me.return_value = ev
        with patch("science_graphrag.dedup.ingest_conflict_check.QdrantAuthorEmbeddingStore") as qc:
            qi = MagicMock()
            qi.search_similar_authors.return_value = [{"author_id": "a-old", "score": 0.96}]
            qc.return_value = qi
            with patch(
                "science_graphrag.dedup.ingest_conflict_check.resolve_embedding_dim", return_value=4
            ):
                with patch(
                    "science_graphrag.dedup.ingest_conflict_check.resolve_embedding_model_label",
                    return_value="test",
                ):
                    n = enqueue_author_near_duplicate_conflicts_on_ingest(
                        settings=settings,
                        session=sqlite_session,
                        neo=neo,
                        workspace_id="ws1",
                        new_work_id="w1",
                    )
    assert n == 1
    rows = list(sqlite_session.scalars(select(AuthorDedupConflict)).all())
    assert len(rows) == 1
    assert rows[0].origin == "ingest"
    assert rows[0].status == "pending"
    assert {rows[0].author_id_a, rows[0].author_id_b} == {"a-old", "a-new"}


def test_enqueue_author_idempotent_same_fingerprint(sqlite_session):
    neo = MagicMock()
    neo.workspace_get.return_value = {"id": "ws1"}
    neo.list_work_authors.return_value = [{"id": "a-new", "full_name": "Jane Doe"}]
    neo.list_workspace_authors.return_value = [
        {"id": "a-new", "full_name": "Jane Doe"},
        {"id": "a-old", "full_name": "Jane Doe"},
    ]
    neo.fetch_author_affiliation_hint.return_value = "MIT"
    settings = Settings()

    with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedder") as me:
        ev = MagicMock()
        ev.embed.return_value = [[0.1, 0.2, 0.3, 0.4]]
        me.return_value = ev
        with patch("science_graphrag.dedup.ingest_conflict_check.QdrantAuthorEmbeddingStore") as qc:
            qi = MagicMock()
            qi.search_similar_authors.return_value = [{"author_id": "a-old", "score": 0.96}]
            qc.return_value = qi
            with patch(
                "science_graphrag.dedup.ingest_conflict_check.resolve_embedding_dim", return_value=4
            ):
                with patch(
                    "science_graphrag.dedup.ingest_conflict_check.resolve_embedding_model_label",
                    return_value="test",
                ):
                    n1 = enqueue_author_near_duplicate_conflicts_on_ingest(
                        settings=settings,
                        session=sqlite_session,
                        neo=neo,
                        workspace_id="ws1",
                        new_work_id="w1",
                    )
                    sqlite_session.commit()
                    n2 = enqueue_author_near_duplicate_conflicts_on_ingest(
                        settings=settings,
                        session=sqlite_session,
                        neo=neo,
                        workspace_id="ws1",
                        new_work_id="w1",
                    )
    assert n1 == 1
    assert n2 == 0
