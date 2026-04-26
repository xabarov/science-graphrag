"""Helpers for ingest job payloads (pending dedup conflicts)."""

from __future__ import annotations

from sqlalchemy import func, or_, select

from science_graphrag.config import Settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import WorkDedupConflict


def count_pending_ingest_work_dedup_conflicts(settings: Settings, workspace_id: str, work_id: str) -> int:
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
