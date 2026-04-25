"""HTTP API for user workspaces (collections of :Work) and combined graph view."""

from __future__ import annotations

import io
import uuid
import zipfile
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from science_graphrag.api.ingest_jobs import (
    SUPPORTED_SUFFIXES,
    job_to_dict,
    start_batch_ingest_job,
    start_ingest_job,
)
from science_graphrag.api.workspace_graph import (
    legacy_workspace_graph_union as workspace_graph_union,
)
from science_graphrag.api.workspace_graph import (
    project_workspace_graph,
    workspace_graph_neighbors,
    workspace_graph_stats,
)
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


def _files_from_zip(data: bytes) -> list[tuple[str, bytes]]:
    """Extract ``.pdf`` / ``.md`` / ``.txt`` from a zip (basename only, no path traversal)."""

    out: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                if not name or name.startswith("."):
                    continue
                if Path(name).suffix.lower() not in SUPPORTED_SUFFIXES:
                    continue
                try:
                    raw = zf.read(info)
                except Exception:  # noqa: BLE001
                    continue
                out.append((name, raw))
    except zipfile.BadZipFile:
        return []
    return out


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
def rename_workspace(
    workspace_id: str,
    body: WorkspaceRenameBody,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_rename(workspace_id, body.name):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        ws = store.workspace_get(workspace_id)
        assert ws is not None
        return ws
    finally:
        store.close()


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str, settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    store = _store(settings)
    try:
        if not store.workspace_delete(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
        return {"deleted": True, "id": workspace_id}
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
        wid = body.work_id.strip()
        if not store.workspace_add_work(workspace_id, wid):
            raise HTTPException(status_code=400, detail="work_add_failed")
        dim = resolve_embedding_dim(embedding_model=settings.embedding_model)
        qdrant = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
        try:
            qdrant.add_workspace_to_chunks(work_id=wid, workspace_id=workspace_id)
        except Exception:  # noqa: BLE001
            pass
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
    mode: str = Query(
        default="inner_only",
        description="inner_only | union_1hop | semantic_layer | full",
    ),
    depth: int = Query(default=1, ge=1, le=2),
    include_external: bool = Query(default=False),
    external_min_internal_citers: int = Query(default=0, ge=0, le=50),
    node_types: str | None = Query(
        default=None,
        description="Comma-separated: Work,Author,Method,Dataset,Venue,Institution,Authorship",
    ),
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    g = project_workspace_graph(
        settings,
        workspace_id,
        mode=mode,
        depth=depth,
        include_external=include_external,
        node_types=node_types,
        neighbor_limit=neighbor_limit,
        external_min_internal_citers=external_min_internal_citers,
    )
    if g is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return g


@router.get("/{workspace_id}/graph/stats")
def get_workspace_graph_stats(
    workspace_id: str,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    s = workspace_graph_stats(settings, workspace_id)
    if s is None:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return s


@router.get("/{workspace_id}/graph/neighbors")
def get_workspace_graph_neighbors(
    workspace_id: str,
    node_id: str = Query(..., min_length=1, description="Neo4j node id (e.g. Work.id)"),
    depth: int = Query(default=1, ge=1, le=2),
    limit: int = Query(default=80, ge=1, le=200),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    g = workspace_graph_neighbors(
        settings,
        workspace_id,
        node_id,
        depth=depth,
        limit=limit,
    )
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
    max_bytes = int(settings.workspace_upload_max_file_size_mb) * 1024 * 1024
    if len(data) > max_bytes:
        size_mb = len(data) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail={
                "error": "workspace_upload_file_too_large",
                "max_file_size_mb": settings.workspace_upload_max_file_size_mb,
                "file_size_mb": round(size_mb, 2),
            },
        )
    rec = start_ingest_job(
        workspace_id=workspace_id, filename=raw_name, file_bytes=data, settings=settings
    )
    return job_to_dict(rec)


@router.post("/{workspace_id}/ingest/batch")
async def ingest_batch_to_workspace(
    workspace_id: str,
    request: Request,
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    """Multipart: repeated ``files`` entries and/or ``archive`` ``.zip`` (PDF/MD/TXT inside)."""

    store = _store(settings)
    try:
        if not store.workspace_get(workspace_id):
            raise HTTPException(status_code=404, detail="workspace_not_found")
    finally:
        store.close()

    form = await request.form()
    items: list[tuple[str, bytes]] = []
    arch = form.get("archive")
    if arch is not None and hasattr(arch, "read"):
        data = await arch.read()
        fn = (getattr(arch, "filename", "") or "").strip()
        if not fn.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="archive_must_be_zip")
        items.extend(_files_from_zip(data))
    max_bytes = int(settings.workspace_upload_max_file_size_mb) * 1024 * 1024
    for f in form.getlist("files"):
        if f is None or not hasattr(f, "read"):
            continue
        raw = await f.read()
        fn = (getattr(f, "filename", "") or "upload").strip() or "upload"
        if Path(fn).suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        if len(raw) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "workspace_upload_file_too_large",
                    "filename": fn,
                    "max_file_size_mb": settings.workspace_upload_max_file_size_mb,
                },
            )
        items.append((fn, raw))
    if not items:
        raise HTTPException(status_code=400, detail="no_supported_files_in_batch")
    rec = start_batch_ingest_job(workspace_id=workspace_id, files=items, settings=settings)
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
        work_embed_deleted = 0
        if merged:
            dim = resolve_embedding_dim(embedding_model=settings.embedding_model)
            qdrant = QdrantChunkStore(
                settings.qdrant_url, settings.qdrant_collection, vector_dim=dim
            )
            qdrant_repointed = qdrant.repoint_work_id_payload(from_work_id=drop, to_work_id=keep)
            qw = QdrantWorkEmbeddingStore(
                settings.qdrant_url,
                settings.qdrant_work_embeddings_collection,
                vector_dim=dim,
            )
            work_embed_deleted = qw.delete_by_work_id(work_id=drop)
            store.workspace_remove_work(workspace_id, drop)
        return {
            "merged": bool(merged),
            "keep_work_id": keep,
            "drop_work_id": drop,
            "qdrant_repointed": qdrant_repointed,
            "work_embedding_deleted": int(work_embed_deleted),
        }
    finally:
        store.close()
