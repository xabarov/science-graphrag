"""HTTP API for user workspaces (collections of :Work) and combined graph view."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

from science_graphrag.api import works as works_api
from science_graphrag.api.ingest_jobs import job_to_dict, start_ingest_job
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _store(settings: Settings) -> Neo4jGraphStore:
    return Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)


class WorkspaceCreateBody(BaseModel):
    name: str = Field(default="Workspace", min_length=1, max_length=200)


class WorkspaceRenameBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)


class WorkspaceAddWorkBody(BaseModel):
    work_id: str = Field(..., min_length=1, max_length=512)


class WorkspaceMergeBody(BaseModel):
    keep_workspace_id: str = Field(..., min_length=1)
    drop_workspace_id: str = Field(..., min_length=1)


class MergeWorksBody(BaseModel):
    keep_work_id: str = Field(..., min_length=1)
    drop_work_id: str = Field(..., min_length=1)


def _merge_graph_payloads(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[str, dict[str, Any]] = {}
    semantic_any = False
    truncated_any = False
    for g in payloads:
        if not g:
            continue
        if g.get("meta", {}).get("semantic_available"):
            semantic_any = True
        if g.get("meta", {}).get("is_truncated"):
            truncated_any = True
        for n in g.get("nodes") or []:
            nid = str(n.get("id") or "")
            if nid:
                nodes_by_id[nid] = n
        for e in g.get("edges") or []:
            eid = str(e.get("id") or "")
            if eid:
                edges_by_key[eid] = e
                continue
            src = str(e.get("source_id") or e.get("source") or "")
            tgt = str(e.get("target_id") or e.get("target") or "")
            rt = str(e.get("rel_type") or e.get("type") or "")
            key = f"{src}|{rt}|{tgt}"
            edges_by_key[key] = e
    nodes = list(nodes_by_id.values())
    edges = list(edges_by_key.values())
    return {
        "work_id": "",
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "semantic_available": semantic_any,
            "graph_scope": "workspace_union_1hop",
            "graph_depth_effective": 1,
            "workspace_node_count": len(nodes),
            "workspace_edge_count": len(edges),
            "is_truncated": truncated_any,
            "available_expansions": [],
        },
    }


def workspace_graph_union(
    settings: Settings, workspace_id: str, *, neighbor_limit: int = 160
) -> dict[str, Any] | None:
    store = _store(settings)
    try:
        ws = store.workspace_get(workspace_id)
        if not ws:
            return None
        work_ids: list[str] = list(ws.get("work_ids") or [])
        if not work_ids:
            return {
                "work_id": "",
                "nodes": [],
                "edges": [],
                "meta": {
                    "semantic_available": False,
                    "graph_scope": "workspace_union_1hop",
                    "graph_depth_effective": 1,
                    "workspace_node_count": 0,
                    "workspace_edge_count": 0,
                    "is_truncated": False,
                    "available_expansions": [],
                },
            }
        per_lim = max(30, min(neighbor_limit, 800 // max(1, len(work_ids))))
        payloads: list[dict[str, Any]] = []
        for wid in work_ids:
            g = works_api.work_graph_neighborhood(
                settings,
                wid,
                neighbor_limit=per_lim,
                depth=1,
            )
            if g:
                payloads.append(g)
        merged = _merge_graph_payloads(payloads)
        merged["meta"]["workspace_id"] = workspace_id
        merged["meta"]["source_work_ids"] = work_ids
        return merged
    finally:
        store.close()


@router.get("")
def list_workspaces(settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    store = _store(settings)
    try:
        items = store.workspace_list()
        return {"items": items, "total": len(items)}
    finally:
        store.close()


@router.post("")
def create_workspace(
    body: WorkspaceCreateBody, settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    store = _store(settings)
    try:
        return store.workspace_create(body.name)
    finally:
        store.close()


@router.post("/merge")
def merge_workspaces(
    body: WorkspaceMergeBody, settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_get(body.keep_workspace_id) or not store.workspace_get(
            body.drop_workspace_id
        ):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        if not store.workspace_merge_into(body.keep_workspace_id, body.drop_workspace_id):
            raise HTTPException(status_code=400, detail="workspace_merge_failed")
        ws = store.workspace_get(body.keep_workspace_id)
        assert ws is not None
        return ws
    finally:
        store.close()


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, settings: Settings = Depends(get_settings)) -> dict[str, Any]:
    store = _store(settings)
    try:
        ws = store.workspace_get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="workspace_not_found")
        return ws
    finally:
        store.close()


@router.patch("/{workspace_id}")
def patch_workspace(
    workspace_id: str,
    body: WorkspaceRenameBody,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_rename(workspace_id, body.name):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        ws = store.workspace_get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="workspace_not_found")
        return ws
    finally:
        store.close()


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    store = _store(settings)
    try:
        if not store.workspace_delete(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        return {"status": "deleted", "id": workspace_id}
    finally:
        store.close()


@router.post("/{workspace_id}/works")
def add_work_to_workspace(
    workspace_id: str,
    body: WorkspaceAddWorkBody,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_get(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        if not store.workspace_add_work(workspace_id, body.work_id.strip()):
            raise HTTPException(status_code=400, detail="work_not_found_or_invalid")
        ws = store.workspace_get(workspace_id)
        assert ws is not None
        return ws
    finally:
        store.close()


@router.delete("/{workspace_id}/works/{work_id}")
def remove_work_from_workspace(
    workspace_id: str,
    work_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_get(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        store.workspace_remove_work(workspace_id, work_id)
        ws = store.workspace_get(workspace_id)
        assert ws is not None
        return ws
    finally:
        store.close()


@router.get("/{workspace_id}/graph")
def get_workspace_graph(
    workspace_id: str,
    neighbor_limit: int = 200,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    g = workspace_graph_union(settings, workspace_id, neighbor_limit=neighbor_limit)
    if g is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return g


@router.get("/{workspace_id}/deduplication-candidates")
def get_workspace_dedup_candidates(
    workspace_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        ws = store.workspace_get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="workspace_not_found")
        allowed = set(ws.get("work_ids") or [])
        violations = store.find_work_dedup_violations()
        out: list[dict[str, Any]] = []
        for row in violations:
            wids = [str(x) for x in row.get("work_ids") or []]
            if len(wids) < 2:
                continue
            if not allowed.intersection(wids):
                continue
            out.append(
                {
                    "kind": row.get("kind"),
                    "dedup_key": row.get("dedup_key"),
                    "work_ids": wids,
                    "id": str(uuid.uuid4()),
                },
            )
        return {"items": out, "total": len(out)}
    finally:
        store.close()


@router.post("/{workspace_id}/ingest/document")
async def ingest_document_to_workspace(
    workspace_id: str,
    settings: Settings = Depends(get_settings),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload PDF/MD/TXT; ingest runs in background — poll ``GET /v1/ingest/jobs/{job_id}``."""

    store = _store(settings)
    try:
        if not store.workspace_get(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
    finally:
        store.close()

    raw_name = (file.filename or "document.pdf").strip() or "document.pdf"
    data = await file.read()
    rec = start_ingest_job(
        workspace_id=workspace_id, filename=raw_name, file_bytes=data, settings=settings
    )
    return job_to_dict(rec)


@router.post("/{workspace_id}/merge-works")
def merge_workspace_works(
    workspace_id: str,
    body: MergeWorksBody,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        ws = store.workspace_get(workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="workspace_not_found")
        allowed = set(ws.get("work_ids") or [])
        if body.keep_work_id not in allowed or body.drop_work_id not in allowed:
            raise HTTPException(status_code=400, detail="works_must_belong_to_workspace")
        keep = body.keep_work_id.strip()
        drop = body.drop_work_id.strip()
        merged = store.merge_work_into_canonical(keep, drop)
        qdrant_repointed = 0
        if merged:
            dim = resolve_embedding_dim(embedding_model=settings.embedding_model)
            qdrant = QdrantChunkStore(
                settings.qdrant_url, settings.qdrant_collection, vector_dim=dim
            )
            qdrant_repointed = qdrant.repoint_work_id_payload(from_work_id=drop, to_work_id=keep)
            store.workspace_remove_work(workspace_id, drop)
        return {
            "merged": bool(merged),
            "keep_work_id": keep,
            "drop_work_id": drop,
            "qdrant_repointed": qdrant_repointed,
        }
    finally:
        store.close()
