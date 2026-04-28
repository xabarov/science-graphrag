from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.api.graph_reader_meta import normalize_workspace_id_query_param
from science_graphrag.api.settings import get_settings
from science_graphrag.api.works.chunks import work_chunks
from science_graphrag.api.works.detail import (
    get_work_detail,
    get_work_extracted_body_payload,
    list_work_claims,
    list_work_summaries_by_ids,
    list_works,
    work_pdf_blob_path,
    work_sources_payload,
)
from science_graphrag.api.works.dto import (
    WorkClaimsResponse,
    WorkIdsBatchBody,
    WorkListResponse,
    WorkSummaryBatchResponse,
)
from science_graphrag.api.works.graph_neighborhood import (
    expand_work_aggregator,
    load_work_graph_workspace_internal_ids,
    work_graph_neighborhood,
)
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


@router.post("/batch-summary", response_model=WorkSummaryBatchResponse)
def post_works_batch_summary(
    body: WorkIdsBatchBody,
    stores: StoreRegistry = Depends(get_stores),
) -> WorkSummaryBatchResponse:
    """Resolve title/year/doi/arxiv for many works in one Neo4j query (workspace list)."""

    seen: set[str] = set()
    deduped: list[str] = []
    for raw in body.work_ids:
        wid = str(raw or "").strip()
        if not wid or wid in seen:
            continue
        seen.add(wid)
        deduped.append(wid)
    items = list_work_summaries_by_ids(stores, deduped)
    return WorkSummaryBatchResponse(items=items)


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


@router.get("/{work_id}/extracted-body")
def get_work_extracted_body(
    work_id: str,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    """Full extracted markdown/text from ingest artifacts (not Qdrant chunk join)."""
    body = get_work_extracted_body_payload(settings, stores, work_id)
    if body is None:
        raise HTTPException(status_code=404, detail="work_not_found")
    return body


@router.get("/{work_id}/graph")
def get_work_graph(  # pylint: disable=R0917
    work_id: str,
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    depth: int = Query(default=1, ge=1, le=3),
    prioritize: str | None = Query(default="Method,Dataset,Work"),
    view: str = Query(default="reader", description="reader | raw"),
    aggregator_threshold: int | None = Query(
        default=None,
        ge=2,
        le=200,
        description="Optional global override for GR8 neighbor aggregation threshold.",
    ),
    aggregator_disabled_kinds: str | None = Query(
        default=None,
        description="CSV of neighbor kinds to skip aggregating (e.g. Author,Institution).",
    ),
    include_claims: bool = Query(
        default=False,
        description="Include capped Claim nodes linked from the center Work (HAS_CLAIM edges).",
    ),
    claims_limit: int = Query(default=24, ge=1, le=120),
    include_authorship_debug: bool = Query(
        default=False,
        description=(
            "If true, meta.authorship_projection classifies reader AUTHORED targets "
            "(native|synthesized|mixed|none)."
        ),
    ),
    workspace_id: str | None = Query(
        default=None,
        description=(
            "Optional workspace collection id: when set, neighbor Works include "
            "workspace_membership (internal|external) relative to this workspace. "
            "Center work must be contained in the workspace."
        ),
    ),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    ws_norm = normalize_workspace_id_query_param(workspace_id)
    workspace_internal_ids: set[str] | None = None
    with stores.neo4j.session() as session:
        if not session.run(
            "MATCH (w:Work {id: $id}) RETURN w.id AS wid", id=str(work_id).strip()
        ).single():
            raise HTTPException(status_code=404, detail="work_not_found")
        if ws_norm:
            workspace_internal_ids, err = load_work_graph_workspace_internal_ids(
                session, workspace_id=ws_norm, center_work_id=str(work_id).strip()
            )
            if err == "workspace_not_found":
                raise HTTPException(status_code=404, detail="workspace_not_found")
            if err == "work_not_in_workspace":
                raise HTTPException(status_code=422, detail="work_not_in_workspace")

    g = work_graph_neighborhood(
        stores,
        work_id,
        neighbor_limit=neighbor_limit,
        depth=depth,
        prioritize=prioritize,
        view=view,
        workspace_id=ws_norm,
        workspace_internal_work_ids=workspace_internal_ids,
        aggregator_threshold=aggregator_threshold,
        aggregator_disabled_kinds=aggregator_disabled_kinds,
        include_claims=include_claims,
        claims_limit=claims_limit,
        include_authorship_debug=include_authorship_debug,
    )
    if not g:
        raise HTTPException(status_code=404, detail="work_not_found")
    return g


@router.get("/{work_id}/graph/expand")
def expand_aggregator(
    work_id: str,
    aggregator_id: str = Query(..., min_length=6),
    limit: int = Query(default=50, ge=1, le=300),
    workspace_id: str | None = Query(
        default=None,
        description="Optional workspace id for membership fields (same rules as GET .../graph).",
    ),
    stores: StoreRegistry = Depends(get_stores),
) -> dict[str, Any]:
    ws_norm = normalize_workspace_id_query_param(workspace_id)
    workspace_internal_ids: set[str] | None = None
    with stores.neo4j.session() as session:
        if not session.run(
            "MATCH (w:Work {id: $id}) RETURN w.id AS wid", id=str(work_id).strip()
        ).single():
            raise HTTPException(status_code=404, detail="work_not_found")
        if ws_norm:
            workspace_internal_ids, err = load_work_graph_workspace_internal_ids(
                session, workspace_id=ws_norm, center_work_id=str(work_id).strip()
            )
            if err == "workspace_not_found":
                raise HTTPException(status_code=404, detail="workspace_not_found")
            if err == "work_not_in_workspace":
                raise HTTPException(status_code=422, detail="work_not_in_workspace")

    payload = expand_work_aggregator(
        stores,
        work_id,
        aggregator_id,
        limit=limit,
        workspace_id=ws_norm,
        workspace_internal_work_ids=workspace_internal_ids,
    )
    if payload is None:
        raise HTTPException(status_code=404, detail="work_not_found")
    return payload


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
