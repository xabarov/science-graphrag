"""Workspace dedup API: conflict queues and decision endpoints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import (
    AuthorDedupConflict,
    WorkDedupConflict,
    WorkDedupMergeLog,
)
from science_graphrag.storage.qdrant_store import QdrantAuthorEmbeddingStore

router = APIRouter(tags=["workspace-dedup"])


def _session_factory(settings: Settings):
    engine = get_engine(settings.database_url)
    init_db(engine)
    return session_factory(engine)


class DedupDecideBody(BaseModel):
    decision: Literal["merge_a", "merge_b", "merge", "keep_separate", "skip"] = Field(
        ...,
        description="merge_a/merge_b keep that side; merge + keep_work_id is an alias for the matching side",
    )
    keep_work_id: str | None = Field(
        default=None,
        description="When decision is merge, the canonical work id (must equal work_id_a or work_id_b).",
    )


class AuthorDedupDecideBody(BaseModel):
    decision: Literal["merge_a", "merge_b", "keep_separate", "skip"]


@router.get("/{workspace_id}/dedup/conflicts")
def get_dedup_conflicts(
    workspace_id: str,
    status: str = Query(default="pending", description="pending | all"),
    origin: str | None = Query(default=None, description="Filter by origin (e.g. ingest | scan)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    if not stores.neo4j.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")

    factory = _session_factory(settings)
    with factory() as session:
        q = select(WorkDedupConflict).where(WorkDedupConflict.workspace_id == workspace_id)
        if status == "pending":
            q = q.where(WorkDedupConflict.status == "pending")
        if origin and str(origin).strip():
            q = q.where(WorkDedupConflict.origin == str(origin).strip())
        q = q.order_by(desc(WorkDedupConflict.created_at)).offset(offset).limit(limit)
        rows = list(session.scalars(q).all())
        items = [
            {
                "id": r.id,
                "work_id_a": r.work_id_a,
                "work_id_b": r.work_id_b,
                "similarity_score": r.similarity_score,
                "check_mode": r.check_mode,
                "llm_same_work": r.llm_same_work,
                "llm_reason": r.llm_reason,
                "status": r.status,
                "decision": r.decision,
                "keep_work_id": r.keep_work_id,
                "fingerprint": r.fingerprint,
                "origin": getattr(r, "origin", None) or "scan",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "decided_at": r.decided_at.isoformat() if r.decided_at else None,
            }
            for r in rows
        ]
        return {"items": items, "total": len(items)}


@router.post("/{workspace_id}/dedup/conflicts/{conflict_id}/decide")
def post_dedup_conflict_decide(
    workspace_id: str,
    conflict_id: str,
    body: DedupDecideBody,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    ws = neo.workspace_get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    allowed = set(str(x) for x in (ws.get("work_ids") or []))

    factory = _session_factory(settings)
    with factory() as session:
        row = session.get(WorkDedupConflict, conflict_id)
        if not row or row.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="conflict_not_found")
        if row.status != "pending":
            raise HTTPException(status_code=400, detail="conflict_already_resolved")

        kid_raw = (body.keep_work_id or "").strip()
        if kid_raw and body.decision != "merge":
            raise HTTPException(status_code=400, detail="keep_work_id_only_with_decision_merge")

        now = datetime.now(UTC)
        if body.decision in ("keep_separate", "skip"):
            row.status = "skipped" if body.decision == "skip" else "rejected"
            row.decision = body.decision
            row.decided_at = now
            session.commit()
            return {"ok": True, "merged": False, "decision": body.decision}

        eff_decision = body.decision
        if eff_decision == "merge":
            kid = (body.keep_work_id or "").strip()
            if not kid:
                raise HTTPException(status_code=400, detail="keep_work_id_required_for_merge")
            if kid == row.work_id_a:
                eff_decision = "merge_a"
            elif kid == row.work_id_b:
                eff_decision = "merge_b"
            else:
                raise HTTPException(status_code=400, detail="keep_work_id_not_in_conflict_pair")

        keep = row.work_id_a if eff_decision == "merge_a" else row.work_id_b
        drop = row.work_id_b if eff_decision == "merge_a" else row.work_id_a
        if keep not in allowed or drop not in allowed:
            raise HTTPException(status_code=400, detail="works_must_belong_to_workspace")

        merged = neo.merge_work_into_canonical(keep, drop)
        if not merged:
            raise HTTPException(status_code=500, detail="merge_failed")

        stores.qdrant_chunks.repoint_work_id_payload(from_work_id=drop, to_work_id=keep)
        stores.qdrant_works.delete_by_work_id(work_id=drop)
        neo.workspace_remove_work(workspace_id, drop)

        row.status = "approved"
        row.decision = eff_decision
        row.keep_work_id = keep
        row.decided_at = now
        session.add(
            WorkDedupMergeLog(
                id=str(uuid.uuid4()),
                workspace_id=workspace_id,
                keep_work_id=keep,
                drop_work_id=drop,
                conflict_id=conflict_id,
            ),
        )
        session.commit()
        return {"ok": True, "merged": True, "keep_work_id": keep, "drop_work_id": drop}


# --- Author dedup (L2) ---


@router.get("/{workspace_id}/dedup/authors/conflicts")
def get_author_dedup_conflicts(
    workspace_id: str,
    status: str = Query(default="pending"),
    origin: str | None = Query(default=None, description="Filter by origin (e.g. ingest | scan)"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    if not stores.neo4j.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")

    factory = _session_factory(settings)
    with factory() as session:
        q = select(AuthorDedupConflict).where(AuthorDedupConflict.workspace_id == workspace_id)
        if status == "pending":
            q = q.where(AuthorDedupConflict.status == "pending")
        if origin and str(origin).strip():
            q = q.where(AuthorDedupConflict.origin == str(origin).strip())
        q = q.order_by(desc(AuthorDedupConflict.created_at)).offset(offset).limit(limit)
        rows = list(session.scalars(q).all())
        items = [
            {
                "id": r.id,
                "author_id_a": r.author_id_a,
                "author_id_b": r.author_id_b,
                "author_name_a": stores.neo4j.fetch_author_display_name(r.author_id_a),
                "author_name_b": stores.neo4j.fetch_author_display_name(r.author_id_b),
                "similarity_score": r.similarity_score,
                "check_mode": r.check_mode,
                "llm_same_author": r.llm_same_author,
                "llm_reason": r.llm_reason,
                "status": r.status,
                "decision": r.decision,
                "keep_author_id": r.keep_author_id,
                "origin": r.origin,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return {"items": items, "total": len(items)}


@router.post("/{workspace_id}/dedup/authors/conflicts/{conflict_id}/decide")
def post_author_dedup_decide(
    workspace_id: str,
    conflict_id: str,
    body: AuthorDedupDecideBody,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    if not stores.neo4j.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")

    factory = _session_factory(settings)
    with factory() as session:
        row = session.get(AuthorDedupConflict, conflict_id)
        if not row or row.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="conflict_not_found")
        if row.status != "pending":
            raise HTTPException(status_code=400, detail="conflict_already_resolved")

        now = datetime.now(UTC)
        if body.decision in ("keep_separate", "skip"):
            row.status = "skipped" if body.decision == "skip" else "rejected"
            row.decision = body.decision
            row.decided_at = now
            session.commit()
            return {"ok": True, "merged": False}

        keep = row.author_id_a if body.decision == "merge_a" else row.author_id_b
        drop = row.author_id_b if body.decision == "merge_a" else row.author_id_a

        merged = stores.neo4j.merge_author_into_canonical(keep, drop)

        if merged:
            dim = resolve_embedding_dim(settings=settings)
            ast = QdrantAuthorEmbeddingStore(
                settings.qdrant_url,
                settings.qdrant_author_embeddings_collection,
                vector_dim=dim,
            )
            ast.delete_by_author_id(author_id=drop)

        row.status = "approved"
        row.decision = body.decision
        row.keep_author_id = keep
        row.decided_at = now
        session.commit()
        return {"ok": True, "merged": bool(merged), "keep_author_id": keep, "drop_author_id": drop}

