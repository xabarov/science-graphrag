"""Unified entity dedup API (Wave T)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, select

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.dedup.dataset_pipeline import run_dataset_dedup
from science_graphrag.dedup.institution_pipeline import run_institution_dedup
from science_graphrag.dedup.method_pipeline import run_method_dedup
from science_graphrag.dedup.venue_pipeline import run_venue_dedup
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import EntityDedupConflict

router = APIRouter(tags=["entity-dedup"])
EntityType = Literal["institution", "venue", "method", "dataset"]


class EntityDedupDecideBody(BaseModel):
    decision: Literal["merge", "skip"]
    keep_entity_id: str | None = None


def _session_factory(settings: Settings):
    engine = get_engine(settings.database_url)
    init_db(engine)
    return session_factory(engine)


@router.post("/dedup/entity/run")
def run_entity_dedup(
    entity_type: EntityType,
    workspace_id: str | None = None,
    limit: int = Query(default=500, ge=2, le=5000),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, int | str]:
    factory = _session_factory(settings)
    with factory() as session:
        if entity_type == "institution":
            res = run_institution_dedup(
                neo4j=stores.neo4j,
                db_session=session,
                workspace_id=workspace_id,
                limit=limit,
            )
        elif entity_type == "venue":
            res = run_venue_dedup(
                neo4j=stores.neo4j,
                db_session=session,
                workspace_id=workspace_id,
                limit=limit,
            )
        elif entity_type == "method":
            res = run_method_dedup(
                neo4j=stores.neo4j,
                db_session=session,
                workspace_id=workspace_id,
                limit=limit,
            )
        else:
            res = run_dataset_dedup(
                neo4j=stores.neo4j,
                db_session=session,
                workspace_id=workspace_id,
                limit=limit,
            )
    return {"entity_type": entity_type, **res}


@router.get("/dedup/entity")
def list_entity_conflicts(
    entity_type: EntityType,
    status: str = Query(default="pending"),
    workspace_id: str | None = Query(
        default=None, description="Filter conflicts scoped to this workspace"
    ),
    origin: str | None = Query(default=None, description="Filter by origin (e.g. ingest | scan)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, object]:
    factory = _session_factory(settings)
    with factory() as session:
        q = select(EntityDedupConflict).where(EntityDedupConflict.entity_type == entity_type)
        if status != "all":
            q = q.where(EntityDedupConflict.status == status)
        wsv = (workspace_id or "").strip()
        if wsv:
            q = q.where(EntityDedupConflict.workspace_id == wsv)
        if origin and str(origin).strip():
            q = q.where(EntityDedupConflict.origin == str(origin).strip())
        q = q.order_by(desc(EntityDedupConflict.created_at)).offset(offset).limit(limit)
        rows = list(session.scalars(q).all())
        items = [
            {
                "id": r.id,
                "entity_type": r.entity_type,
                "entity_id_a": r.entity_id_a,
                "entity_id_b": r.entity_id_b,
                "entity_label_a": stores.neo4j.fetch_entity_display_label(
                    r.entity_type, r.entity_id_a
                ),
                "entity_label_b": stores.neo4j.fetch_entity_display_label(
                    r.entity_type, r.entity_id_b
                ),
                "similarity_score": r.similarity_score,
                "status": r.status,
                "decision": r.decision,
                "keep_entity_id": r.keep_entity_id,
                "workspace_id": r.workspace_id,
                "origin": r.origin,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            }
            for r in rows
        ]
        return {"items": items, "total": len(items)}


@router.post("/dedup/entity/{conflict_id}/decide")
def decide_entity_conflict(
    conflict_id: str,
    body: EntityDedupDecideBody,
    workspace_id: str | None = Query(
        default=None,
        description="When the conflict row has workspace_id set, must match for safety",
    ),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, object]:
    factory = _session_factory(settings)
    with factory() as session:
        row = session.get(EntityDedupConflict, conflict_id)
        if not row:
            raise HTTPException(status_code=404, detail="conflict_not_found")
        if row.status != "pending":
            raise HTTPException(status_code=400, detail="conflict_already_resolved")

        row_ws = (row.workspace_id or "").strip()
        req_ws = (workspace_id or "").strip()
        if row_ws and req_ws and row_ws != req_ws:
            raise HTTPException(status_code=400, detail="workspace_mismatch")

        if body.decision == "skip":
            row.status = "skipped"
            row.decision = "skip"
            row.decided_at = datetime.now(UTC)
            session.commit()
            return {"ok": True, "merged": False}

        keep = (body.keep_entity_id or "").strip() or row.entity_id_a
        if keep not in (row.entity_id_a, row.entity_id_b):
            raise HTTPException(status_code=400, detail="keep_entity_id_not_in_pair")
        drop = row.entity_id_b if keep == row.entity_id_a else row.entity_id_a

        merged = False
        if row.entity_type == "institution":
            merged = stores.neo4j.merge_institution_into_canonical(keep, drop)
        elif row.entity_type == "venue":
            merged = stores.neo4j.merge_venue_into_canonical(keep, drop)
        elif row.entity_type == "method":
            merged = stores.neo4j.merge_method_into_canonical(keep, drop)
        elif row.entity_type == "dataset":
            merged = stores.neo4j.add_dataset_alias(keep, drop)

        row.status = "approved" if merged else "failed"
        row.decision = "merge"
        row.keep_entity_id = keep
        row.decided_at = datetime.now(UTC)
        session.commit()
        return {"ok": True, "merged": merged, "keep_entity_id": keep, "drop_entity_id": drop}
