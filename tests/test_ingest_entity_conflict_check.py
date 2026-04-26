"""Tests for ingest-time entity dedup conflict enqueue."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from science_graphrag.dedup.entity_ingest_conflict_check import (
    enqueue_entity_near_duplicate_conflicts_on_ingest,
)
from science_graphrag.storage.models_orm import Base, EntityDedupConflict


@pytest.fixture()
def sqlite_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        yield session


def _inst_row(iid: str) -> dict:
    return {
        "id": iid,
        "name": "Same Org",
        "normalized_name": "Same Org",
        "country": "",
        "city": "",
    }


def test_enqueue_institution_pair_ingest_origin(sqlite_session):
    neo = MagicMock()
    neo.workspace_get.return_value = {"id": "ws1"}
    neo.list_work_institutions.return_value = [_inst_row("i-new")]
    neo.list_workspace_institutions.return_value = [_inst_row("i-new"), _inst_row("i-old")]
    for fn in (neo.list_work_venues, neo.list_work_methods, neo.list_work_datasets):
        fn.return_value = []

    counts = enqueue_entity_near_duplicate_conflicts_on_ingest(
        session=sqlite_session,
        neo=neo,
        workspace_id="ws1",
        new_work_id="w1",
    )
    assert counts["institution"] == 1
    assert counts["venue"] == 0
    rows = list(sqlite_session.scalars(select(EntityDedupConflict)).all())
    assert len(rows) == 1
    assert rows[0].entity_type == "institution"
    assert rows[0].origin == "ingest"
    assert rows[0].workspace_id == "ws1"
    assert {rows[0].entity_id_a, rows[0].entity_id_b} == {"i-new", "i-old"}
