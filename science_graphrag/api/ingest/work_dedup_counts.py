"""Helpers for ingest job payloads (pending dedup conflicts by kind)."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from science_graphrag.config import Settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import (
    AuthorDedupConflict,
    EntityDedupConflict,
    WorkDedupConflict,
)
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def count_pending_ingest_work_dedup_conflicts(
    settings: Settings, workspace_id: str, work_id: str
) -> int:
    """Count pending ``WorkDedupConflict`` rows created during ingest for this work."""

    ws = str(workspace_id or "").strip()
    wid = str(work_id or "").strip()
    if not ws or not wid:
        return 0
    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        stmt = (
            select(func.count())
            .select_from(WorkDedupConflict)
            .where(
                WorkDedupConflict.workspace_id == ws,
                WorkDedupConflict.status == "pending",
                WorkDedupConflict.origin == "ingest",
                or_(
                    WorkDedupConflict.work_id_a == wid,
                    WorkDedupConflict.work_id_b == wid,
                ),
            )
        )
        val = session.scalar(stmt)
        return int(val or 0)


def count_pending_ingest_author_dedup_conflicts(
    settings: Settings, workspace_id: str, work_id: str
) -> int:
    """Count pending author dedup rows (ingest) involving an author on this work."""

    ws = str(workspace_id or "").strip()
    wid = str(work_id or "").strip()
    if not ws or not wid:
        return 0

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        author_rows = neo.list_work_authors(wid)
    finally:
        neo.close()

    aids = {str(r.get("id") or "").strip() for r in author_rows if str(r.get("id") or "").strip()}
    if not aids:
        return 0

    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        stmt = (
            select(func.count())
            .select_from(AuthorDedupConflict)
            .where(
                AuthorDedupConflict.workspace_id == ws,
                AuthorDedupConflict.status == "pending",
                AuthorDedupConflict.origin == "ingest",
                or_(
                    AuthorDedupConflict.author_id_a.in_(aids),
                    AuthorDedupConflict.author_id_b.in_(aids),
                ),
            )
        )
        val = session.scalar(stmt)
        return int(val or 0)


def count_pending_ingest_entity_dedup_conflicts(
    settings: Settings, workspace_id: str, work_id: str
) -> int:
    """Count pending entity dedup rows (ingest) involving an entity attached to this work."""

    ws = str(workspace_id or "").strip()
    wid = str(work_id or "").strip()
    if not ws or not wid:
        return 0

    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        eids: set[str] = set()
        for fn in (
            neo.list_work_institutions,
            neo.list_work_venues,
            neo.list_work_methods,
            neo.list_work_datasets,
        ):
            for row in fn(wid):
                eid = str(row.get("id") or "").strip()
                if eid:
                    eids.add(eid)
    finally:
        neo.close()

    if not eids:
        return 0

    engine = get_engine(settings.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        stmt = (
            select(func.count())
            .select_from(EntityDedupConflict)
            .where(
                EntityDedupConflict.workspace_id == ws,
                EntityDedupConflict.status == "pending",
                EntityDedupConflict.origin == "ingest",
                or_(
                    EntityDedupConflict.entity_id_a.in_(eids),
                    EntityDedupConflict.entity_id_b.in_(eids),
                ),
            )
        )
        val = session.scalar(stmt)
        return int(val or 0)


def count_pending_ingest_conflicts(
    settings: Settings, workspace_id: str, work_id: str
) -> dict[str, int]:
    """Breakdown of pending ingest-origin dedup queue rows for this job's work."""

    ws = str(workspace_id or "").strip()
    wid = str(work_id or "").strip()
    if not ws or not wid:
        return {"works": 0, "authors": 0, "entities": 0}
    return {
        "works": count_pending_ingest_work_dedup_conflicts(settings, ws, wid),
        "authors": count_pending_ingest_author_dedup_conflicts(settings, ws, wid),
        "entities": count_pending_ingest_entity_dedup_conflicts(settings, ws, wid),
    }
