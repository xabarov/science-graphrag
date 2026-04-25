"""HTTP API for user workspaces (collections of :Work) and combined graph view."""

from __future__ import annotations

import io
import uuid
import zipfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, Field

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.api.ingest_jobs import (
    SUPPORTED_SUFFIXES,
    job_to_dict,
    start_batch_ingest_job,
    start_ingest_job,
)
from science_graphrag.config import Settings, get_settings

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
def list_workspaces(stores: StoreRegistry = Depends(get_stores)) -> dict[str, Any]:
    items = stores.neo4j.workspace_list()
    return {"items": items, "total": len(items)}


@router.post("")
def create_workspace(
    body: WorkspaceCreateBody,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    return stores.neo4j.workspace_create(body.name)


@router.post("/merge")
def merge_workspaces(
    body: WorkspaceMergeBody,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    if not neo.workspace_get(body.keep_workspace_id) or not neo.workspace_get(
        body.drop_workspace_id
    ):
        raise HTTPException(status_code=404, detail="workspace_not_found")
    if not neo.workspace_merge_into(body.keep_workspace_id, body.drop_workspace_id):
        raise HTTPException(status_code=400, detail="workspace_merge_failed")
    ws = neo.workspace_get(body.keep_workspace_id)
    assert ws is not None
    return ws


@router.get("/{workspace_id}")
def get_workspace(workspace_id: str, stores: StoreRegistry = Depends(get_stores)) -> dict[str, Any]:
    ws = stores.neo4j.workspace_get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return ws


@router.patch("/{workspace_id}")
def rename_workspace(
    workspace_id: str,
    body: WorkspaceRenameBody,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    if not neo.workspace_rename(workspace_id, body.name):
        raise HTTPException(status_code=404, detail="workspace_not_found")
    ws = neo.workspace_get(workspace_id)
    assert ws is not None
    return ws


@router.delete("/{workspace_id}")
def delete_workspace(
    workspace_id: str,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    if not stores.neo4j.workspace_delete(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")
    return {"deleted": True, "id": workspace_id}


@router.post("/{workspace_id}/works")
def add_work_to_workspace(
    workspace_id: str,
    body: WorkspaceAddWorkBody,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    if not neo.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")
    wid = body.work_id.strip()
    if not neo.workspace_add_work(workspace_id, wid):
        raise HTTPException(status_code=400, detail="work_add_failed")
    try:
        stores.qdrant_chunks.add_workspace_to_chunks(work_id=wid, workspace_id=workspace_id)
    except Exception:  # noqa: BLE001
        pass
    ws = neo.workspace_get(workspace_id)
    assert ws is not None
    return ws


@router.delete("/{workspace_id}/works/{work_id}")
def remove_work_from_workspace(
    workspace_id: str,
    work_id: str,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    if not neo.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")
    neo.workspace_remove_work(workspace_id, work_id)
    ws = neo.workspace_get(workspace_id)
    assert ws is not None
    return ws


@router.get("/{workspace_id}/deduplication-candidates")
def get_workspace_dedup_candidates(
    workspace_id: str,
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    ws = neo.workspace_get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    allowed = set(ws.get("work_ids") or [])
    violations = neo.find_work_dedup_violations()
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


@router.post("/{workspace_id}/ingest/document")
async def ingest_document_to_workspace(
    workspace_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """Upload PDF/MD/TXT; ingest runs in background — poll ``GET /v1/ingest/jobs/{job_id}``."""

    if not stores.neo4j.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")

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
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    """Multipart: repeated ``files`` entries and/or ``archive`` ``.zip`` (PDF/MD/TXT inside)."""

    if not stores.neo4j.workspace_get(workspace_id):
        raise HTTPException(status_code=404, detail="workspace_not_found")

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
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    neo = stores.neo4j
    ws = neo.workspace_get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="workspace_not_found")
    allowed = set(ws.get("work_ids") or [])
    if body.keep_work_id not in allowed or body.drop_work_id not in allowed:
        raise HTTPException(status_code=400, detail="works_must_belong_to_workspace")
    keep = body.keep_work_id.strip()
    drop = body.drop_work_id.strip()
    merged = neo.merge_work_into_canonical(keep, drop)
    qdrant_repointed = 0
    work_embed_deleted = 0
    if merged:
        qdrant_repointed = stores.qdrant_chunks.repoint_work_id_payload(
            from_work_id=drop,
            to_work_id=keep,
        )
        work_embed_deleted = stores.qdrant_works.delete_by_work_id(work_id=drop)
        neo.workspace_remove_work(workspace_id, drop)
    return {
        "merged": bool(merged),
        "keep_work_id": keep,
        "drop_work_id": drop,
        "qdrant_repointed": qdrant_repointed,
        "work_embedding_deleted": int(work_embed_deleted),
    }
