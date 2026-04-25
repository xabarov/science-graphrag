from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.api.settings import get_settings
from science_graphrag.api.works.chunks import work_chunks
from science_graphrag.api.works.detail import (
    get_work_detail,
    list_work_claims,
    list_works,
    work_pdf_blob_path,
    work_sources_payload,
)
from science_graphrag.api.works.dto import WorkClaimsResponse, WorkListResponse
from science_graphrag.api.works.graph_neighborhood import work_graph_neighborhood
from science_graphrag.config import Settings

router = APIRouter(prefix="/v1/works", tags=["works"])


def _parse_single_byte_range(range_header: str, file_size: int) -> tuple[int, int] | None:
    if file_size <= 0:
        return None
    rh = range_header.strip()
    if not rh.lower().startswith("bytes="):
        return None
    spec = rh[6:].strip().split(",", maxsplit=1)[0].strip()
    m = re.match(r"^(\d*)-(\d*)$", spec)
    if not m:
        return None
    a, b = m.group(1), m.group(2)
    if a != "" and b != "":
        start, end = int(a), int(b)
    elif a != "":
        start, end = int(a), file_size - 1
    elif b != "":
        suffix = int(b)
        if suffix <= 0:
            return None
        start, end = max(0, file_size - suffix), file_size - 1
    else:
        return None
    if start < 0 or start >= file_size:
        return None
    end = min(end, file_size - 1)
    if end < start:
        return None
    return start, end


def _iter_pdf_slice(path: Path, start: int, length: int) -> Iterator[bytes]:
    with path.open("rb") as handle:
        handle.seek(start)
        remaining = length
        while remaining > 0:
            n = min(64 * 1024, remaining)
            block = handle.read(n)
            if not block:
                break
            remaining -= len(block)
            yield block


@router.get("", response_model=WorkListResponse)
def get_works_list(
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    year_min: int | None = Query(default=None),
    year_max: int | None = Query(default=None),
    has_semantic: bool | None = Query(
        default=None,
        description="If true, only works with Method/Dataset edges; if false, only without.",
    ),
    stores: StoreRegistry = Depends(get_stores),
) -> WorkListResponse:
    items, total = list_works(
        stores,
        q=q,
        limit=limit,
        offset=offset,
        year_min=year_min,
        year_max=year_max,
        has_semantic=has_semantic,
    )
    return WorkListResponse(items=items, total=total)


@router.get("/{work_id}")
def get_work_by_id(
    work_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    detail = get_work_detail(settings, stores, work_id)
    if not detail:
        raise HTTPException(status_code=404, detail="work_not_found")
    chunks = work_chunks(stores, work_id, limit=1, offset=0)
    if "error" not in chunks:
        detail["ingestion"]["has_chunks"] = int(chunks.get("total", 0)) > 0
    return detail


@router.get("/{work_id}/graph")
def get_work_graph(
    work_id: str,
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    depth: int = Query(default=1, ge=1, le=3),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    g = work_graph_neighborhood(
        stores,
        work_id,
        neighbor_limit=neighbor_limit,
        depth=depth,
        prioritize=prioritize,
    )
    if not g:
        raise HTTPException(status_code=404, detail="work_not_found")
    return g


@router.get("/{work_id}/chunks")
def get_work_chunks(
    work_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    if not get_work_detail(settings, stores, work_id):
        raise HTTPException(status_code=404, detail="work_not_found")
    return work_chunks(stores, work_id, limit=limit, offset=offset)


@router.get("/{work_id}/claims", response_model=WorkClaimsResponse)
def get_work_claims(
    work_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> WorkClaimsResponse:
    if not get_work_detail(settings, stores, work_id):
        raise HTTPException(status_code=404, detail="work_not_found")
    return WorkClaimsResponse(work_id=work_id, items=list_work_claims(stores, work_id))


@router.get("/{work_id}/sources")
def get_work_sources(
    work_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    body = work_sources_payload(settings, stores, work_id)
    if not body:
        raise HTTPException(status_code=404, detail="work_not_found")
    return body


@router.get("/{work_id}/pdf", response_model=None)
def get_work_pdf(
    request: Request,
    work_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> Response:
    p = work_pdf_blob_path(settings, stores, work_id)
    if not p:
        raise HTTPException(status_code=404, detail="pdf_not_found")
    size = int(p.stat().st_size)
    etag = f'W/"{p.name}"'
    common = {"Accept-Ranges": "bytes", "ETag": etag, "Cache-Control": "private, max-age=0"}
    inm = request.headers.get("if-none-match")
    if inm and etag in {t.strip() for t in inm.split(",") if t.strip()}:
        return Response(status_code=304, headers=common)
    range_hdr = request.headers.get("range")
    if not range_hdr:
        return StreamingResponse(
            _iter_pdf_slice(p, 0, size),
            media_type="application/pdf",
            headers={
                **common,
                "Content-Length": str(size),
                "Content-Disposition": 'inline; filename="document.pdf"',
            },
        )
    parsed = _parse_single_byte_range(range_hdr, size)
    if parsed is None:
        return Response(status_code=416, headers={**common, "Content-Range": f"bytes */{size}"})
    start, end = parsed
    length = end - start + 1
    return StreamingResponse(
        _iter_pdf_slice(p, start, length),
        status_code=206,
        media_type="application/pdf",
        headers={
            **common,
            "Content-Range": f"bytes {start}-{end}/{size}",
            "Content-Length": str(length),
            "Content-Disposition": 'inline; filename="document.pdf"',
        },
    )
