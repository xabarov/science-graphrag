"""Remove a :Work from a :Workspace with Qdrant payload sync and optional safe global purge."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import delete, or_, select

from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import (
    DocumentRecord,
    IngestionRunRecord,
    IngestJobEventOrm,
    IngestJobRecordOrm,
    IngestJobStageOrm,
    WorkDedupConflict,
    WorkDedupMergeLog,
    WorkTranslationRecord,
)

log = logging.getLogger(__name__)

WORK_NOT_IN_WORKSPACE = "work_not_in_workspace"
WORKSPACE_NOT_FOUND = "workspace_not_found"


def _qdrant_detach_workspace(stores: StoreRegistry, *, work_id: str, workspace_id: str) -> None:
    try:
        stores.qdrant_chunks.remove_workspace_from_chunks(
            work_id=work_id,
            workspace_id=workspace_id,
        )
    except Exception:  # noqa: BLE001
        log.debug("remove_workspace_from_chunks failed", exc_info=True)
    try:
        stores.qdrant_works.remove_workspace_from_work_point(
            work_id=work_id,
            workspace_id=workspace_id,
        )
    except Exception:  # noqa: BLE001
        log.debug("remove_workspace_from_work_point failed", exc_info=True)


def _purge_postgres_for_work(settings: Settings, work_id: str) -> None:
    wid = str(work_id or "").strip()
    if not wid:
        return
    eng = get_engine(settings.database_url)
    init_db(eng)
    fac = session_factory(eng)
    with fac() as session:
        session.execute(delete(WorkTranslationRecord).where(WorkTranslationRecord.work_id == wid))
        session.execute(
            delete(WorkDedupConflict).where(
                or_(
                    WorkDedupConflict.work_id_a == wid,
                    WorkDedupConflict.work_id_b == wid,
                ),
            ),
        )
        session.execute(
            delete(WorkDedupMergeLog).where(
                or_(
                    WorkDedupMergeLog.keep_work_id == wid,
                    WorkDedupMergeLog.drop_work_id == wid,
                ),
            ),
        )
        doc_ids = list(
            session.scalars(select(DocumentRecord.id).where(DocumentRecord.work_id == wid)).all(),
        )
        for did in doc_ids:
            did_s = str(did or "").strip()
            if did_s:
                session.execute(
                    delete(IngestionRunRecord).where(IngestionRunRecord.document_id == did_s),
                )
        session.execute(delete(DocumentRecord).where(DocumentRecord.work_id == wid))
        jobs = list(
            session.scalars(
                select(IngestJobRecordOrm).where(IngestJobRecordOrm.work_id == wid)
            ).all(),
        )
        for j in jobs:
            jid = str(j.job_id or "").strip()
            if jid:
                session.execute(delete(IngestJobStageOrm).where(IngestJobStageOrm.job_id == jid))
                session.execute(delete(IngestJobEventOrm).where(IngestJobEventOrm.job_id == jid))
        session.execute(delete(IngestJobRecordOrm).where(IngestJobRecordOrm.work_id == wid))
        session.commit()


def _purge_vectors_and_neo4j_work(stores: StoreRegistry, *, work_id: str) -> bool:
    try:
        stores.qdrant_claims.delete_points_by_work_id(work_id=work_id)
    except Exception:  # noqa: BLE001
        log.warning("qdrant_claims delete_points_by_work_id failed", exc_info=True)
    try:
        stores.qdrant_chunks.delete_points_by_work_id(work_id=work_id)
    except Exception:  # noqa: BLE001
        log.warning("qdrant_chunks delete_points_by_work_id failed", exc_info=True)
    try:
        stores.qdrant_works.delete_by_work_id(work_id=work_id)
    except Exception:  # noqa: BLE001
        log.warning("qdrant_works delete_by_work_id failed", exc_info=True)
    stores.neo4j.detach_delete_claims_for_work(work_id)
    return bool(stores.neo4j.detach_delete_work_if_no_incoming_cites(work_id))


def remove_work_from_workspace_result(
    stores: StoreRegistry,
    *,
    settings: Settings,
    workspace_id: str,
    work_id: str,
) -> dict[str, Any]:
    """
    Remove ``work_id`` from ``workspace_id``.

    Returns ``workspace`` (post-removal), ``removal_status``, and diagnostic flags.
    """

    neo = stores.neo4j
    wid = str(work_id or "").strip()
    wsv = str(workspace_id or "").strip()
    if not wid or not wsv:
        raise ValueError(WORK_NOT_IN_WORKSPACE)

    ws = neo.workspace_get(wsv)
    if not ws:
        raise KeyError(WORKSPACE_NOT_FOUND)

    is_unbounded = bool(ws.get("unbounded"))
    work_ids = {str(x) for x in (ws.get("work_ids") or []) if x}
    if not is_unbounded and wid not in work_ids:
        raise ValueError(WORK_NOT_IN_WORKSPACE)

    removed_neo = neo.workspace_remove_work(wsv, wid)
    if not is_unbounded and not removed_neo:
        raise ValueError(WORK_NOT_IN_WORKSPACE)

    _qdrant_detach_workspace(stores, work_id=wid, workspace_id=wsv)

    updated_ws = neo.workspace_get(wsv)
    if updated_ws is None:
        raise KeyError(WORKSPACE_NOT_FOUND)

    if is_unbounded:
        return {
            "workspace": updated_ws,
            "removal_status": "detached_only",
            "has_other_workspace_memberships": True,
            "has_incoming_cites": bool(neo.work_has_incoming_cites(wid)),
            "removed_neo_contains": removed_neo,
        }

    remaining_memberships = neo.count_work_workspace_memberships(wid)
    has_other = remaining_memberships > 0
    incoming = bool(neo.work_has_incoming_cites(wid))

    if has_other:
        return {
            "workspace": updated_ws,
            "removal_status": "detached_only",
            "has_other_workspace_memberships": True,
            "has_incoming_cites": incoming,
            "removed_neo_contains": removed_neo,
        }

    if incoming:
        return {
            "workspace": updated_ws,
            "removal_status": "purge_blocked_by_incoming_cites",
            "has_other_workspace_memberships": False,
            "has_incoming_cites": True,
            "removed_neo_contains": removed_neo,
        }

    if neo.work_exists(wid):
        try:
            _purge_postgres_for_work(settings, wid)
        except Exception:  # noqa: BLE001
            log.warning(
                "postgres purge for work_id=%s failed; continuing vector+neo purge",
                wid,
                exc_info=True,
            )
        deleted = _purge_vectors_and_neo4j_work(stores, work_id=wid)
        if not deleted:
            log.warning(
                "neo4j detach_delete_work_if_no_incoming_cites returned false after checks work_id=%s",
                wid,
            )

    final_ws = neo.workspace_get(wsv) or updated_ws
    return {
        "workspace": final_ws,
        "removal_status": "purged",
        "has_other_workspace_memberships": False,
        "has_incoming_cites": False,
        "removed_neo_contains": removed_neo,
    }
