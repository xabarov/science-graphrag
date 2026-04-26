"""Tests for ingest-time work dedup conflict enqueue."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import Settings
from science_graphrag.dedup.ingest_conflict_check import enqueue_work_near_duplicate_conflicts_on_ingest
from science_graphrag.domain.models import AuthorshipDraft, WorkDraft
from science_graphrag.storage.models_orm import Base, WorkDedupConflict


@pytest.fixture()
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def test_enqueue_inserts_ingest_origin_on_high_similarity(sqlite_session):
    draft = WorkDraft(title="New paper", abstract="Abstract here")
    authorships = [AuthorshipDraft(author_position=1, author_raw_name="Doe")]
    neo = MagicMock()
    neo.workspace_get.return_value = {"work_ids": ["w-old", "w-new"]}
    neo.fetch_work_bibliography_card.return_value = {
        "title": "Old paper",
        "year": 2020,
        "first_author": "Doe",
        "abstract": "Other abstract",
    }
    settings = Settings()

    with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedder") as me:
        ev = MagicMock()
        ev.dim = 4
        ev.embed.return_value = [[0.1, 0.2, 0.3, 0.4]]
        me.return_value = ev
        with patch("science_graphrag.dedup.ingest_conflict_check.QdrantWorkEmbeddingStore") as qc:
            qi = MagicMock()
            qi.search_similar_works.return_value = [{"work_id": "w-old", "score": 0.96}]
            qc.return_value = qi
            with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedding_dim", return_value=4):
                n = enqueue_work_near_duplicate_conflicts_on_ingest(
                    settings=settings,
                    session=sqlite_session,
                    neo=neo,
                    workspace_id="ws1",
                    new_work_id="w-new",
                    draft=draft,
                    authorships=authorships,
                )
    assert n == 1
    rows = list(sqlite_session.scalars(select(WorkDedupConflict)).all())
    assert len(rows) == 1
    assert rows[0].origin == "ingest"
    assert rows[0].status == "pending"
    assert {rows[0].work_id_a, rows[0].work_id_b} == {"w-old", "w-new"}


def test_enqueue_idempotent_same_fingerprint(sqlite_session):
    draft = WorkDraft(title="New paper", abstract="Abstract here")
    authorships = [AuthorshipDraft(author_position=1, author_raw_name="Doe")]
    neo = MagicMock()
    neo.workspace_get.return_value = {"work_ids": ["w-old", "w-new"]}
    neo.fetch_work_bibliography_card.return_value = {
        "title": "Old paper",
        "year": 2020,
        "first_author": "Doe",
        "abstract": "Other abstract",
    }
    settings = Settings()

    with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedder") as me:
        ev = MagicMock()
        ev.dim = 4
        ev.embed.return_value = [[0.1, 0.2, 0.3, 0.4]]
        me.return_value = ev
        with patch("science_graphrag.dedup.ingest_conflict_check.QdrantWorkEmbeddingStore") as qc:
            qi = MagicMock()
            qi.search_similar_works.return_value = [{"work_id": "w-old", "score": 0.96}]
            qc.return_value = qi
            with patch("science_graphrag.dedup.ingest_conflict_check.resolve_embedding_dim", return_value=4):
                n1 = enqueue_work_near_duplicate_conflicts_on_ingest(
                    settings=settings,
                    session=sqlite_session,
                    neo=neo,
                    workspace_id="ws1",
                    new_work_id="w-new",
                    draft=draft,
                    authorships=authorships,
                )
                sqlite_session.commit()
                n2 = enqueue_work_near_duplicate_conflicts_on_ingest(
                    settings=settings,
                    session=sqlite_session,
                    neo=neo,
                    workspace_id="ws1",
                    new_work_id="w-new",
                    draft=draft,
                    authorships=authorships,
                )
    assert n1 == 1
    assert n2 == 0
