"""FastAPI entrypoint: retrieval, citations, minimal researcher UI."""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from typing import Any, Literal

from pydantic import BaseModel, Field

from science_graphrag.api import works as works_api
from science_graphrag.api.admin_access import require_admin_if_configured
from science_graphrag.api.ask_sessions import router as ask_sessions_router
from science_graphrag.api.benchmark import router as benchmark_router
from science_graphrag.api.ingest_jobs import router as ingest_router
from science_graphrag.api.retrieval import GroundedAnswer, answer_query
from science_graphrag.api.settings import router as settings_router
from science_graphrag.api.workspace_dedup import router as workspace_dedup_router
from science_graphrag.api.workspaces import router as workspaces_router
from science_graphrag.config import Settings, get_settings

app = FastAPI(title="science-graphrag", version="0.1.0")
_STATIC_DIR = Path(__file__).resolve().parent / "static"
# React/Vite build: `science_graphrag/api/static/ui/` → served at `/ui` (includes `/ui/assets/*`).
# Do not mount `/ui/assets` to `_STATIC_DIR`: hashed bundles live under `static/ui/assets/`.
_UI_DIR = _STATIC_DIR / "ui"
if _UI_DIR.is_dir():
    app.mount("/ui", StaticFiles(directory=_UI_DIR, html=True), name="ui")

# Benchmark endpoints (UI-driven runs + fixtures).
app.include_router(
    benchmark_router,
    prefix="/v1",
    dependencies=[Depends(require_admin_if_configured)],
)
app.include_router(
    settings_router,
    prefix="/v1",
    dependencies=[Depends(require_admin_if_configured)],
)
app.include_router(ask_sessions_router, prefix="/v1")
app.include_router(workspaces_router, prefix="/v1")
app.include_router(workspace_dedup_router, prefix="/v1/workspaces")
app.include_router(ingest_router, prefix="/v1")


def _parse_single_byte_range(range_header: str, file_size: int) -> tuple[int, int] | None:
    """Parse one ``bytes=`` range; return inclusive (start, end) or None if unsatisfiable."""

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
        start = int(a)
        end = file_size - 1
    elif b != "":
        suffix = int(b)
        if suffix <= 0:
            return None
        start = max(0, file_size - suffix)
        end = file_size - 1
    else:
        return None
    if start < 0 or start >= file_size:
        return None
    end = min(end, file_size - 1)
    if end < start:
        return None
    return start, end


def _iter_pdf_slice(path: Path, start: int, length: int) -> Iterator[bytes]:
    chunk = 64 * 1024
    with path.open("rb") as handle:
        handle.seek(start)
        remaining = length
        while remaining > 0:
            n = min(chunk, remaining)
            block = handle.read(n)
            if not block:
                break
            remaining -= len(block)
            yield block


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    work_id: str | None = None
    workspace_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=24)
    mode: Literal["vector", "hybrid"] = Field(
        default="vector",
        description="Retrieval path: dense vector only, or hybrid (RRF + Neo4j fulltext + CITES expand).",
    )


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    graph_context: dict
    retrieval_trace: dict


class WorksListResponse(BaseModel):
    items: list[dict]
    total: int


class ClaimEvidenceOut(BaseModel):
    chunk_fingerprint: str
    quote: str
    section_path: str | None = None


class ClaimOut(BaseModel):
    claim_id: str
    normalized_text: str
    claim_type: str
    polarity: str
    confidence: float
    evidence: list[ClaimEvidenceOut]


class WorkClaimsResponse(BaseModel):
    work_id: str
    items: list[ClaimOut]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/idea-search")
def idea_search_stub(
    q: str = Query("", min_length=0),
    kinds: str = Query("work,chunk", description="Comma-separated kinds (stub ignores)."),
    top_k: int = Query(5, ge=1, le=24),
    workspace_id: str | None = Query(default=None),
) -> dict[str, Any]:
    """Stub for Wave R ``idea_search`` tool; returns empty hits until agent stack ships."""

    kind_list = [k.strip() for k in (kinds or "").split(",") if k.strip()]
    return {
        "items": [],
        "query": q,
        "kinds": kind_list,
        "top_k": top_k,
        "workspace_id": (workspace_id or "").strip() or None,
        "status": "stub_wave_r",
    }


@app.post("/v1/query", response_model=QueryResponse)
def post_query(body: QueryRequest, settings: Settings = Depends(get_settings)) -> QueryResponse:
    result: GroundedAnswer = answer_query(
        body.query,
        settings=settings,
        work_id=body.work_id,
        workspace_id=body.workspace_id,
        top_k=body.top_k,
        mode=body.mode,
    )
    return QueryResponse(
        answer=result.answer,
        citations=result.citations,
        graph_context=result.graph_context,
        retrieval_trace=result.retrieval_trace,
    )


@app.get("/v1/works", response_model=WorksListResponse)
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
    settings: Settings = Depends(get_settings),
) -> WorksListResponse:
    items, total = works_api.list_works(
        settings,
        q=q,
        limit=limit,
        offset=offset,
        year_min=year_min,
        year_max=year_max,
        has_semantic=has_semantic,
    )
    return WorksListResponse(items=items, total=total)


@app.get("/v1/works/{work_id}")
def get_work_by_id(work_id: str, settings: Settings = Depends(get_settings)) -> dict:
    detail = works_api.get_work_detail(settings, work_id)
    if not detail:
        raise HTTPException(status_code=404, detail="work_not_found")
    chunks = works_api.work_chunks(settings, work_id, limit=1, offset=0)
    if "error" not in chunks:
        detail["ingestion"]["has_chunks"] = int(chunks.get("total", 0)) > 0
    return detail


@app.get("/v1/works/{work_id}/graph")
def get_work_graph(
    work_id: str,
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    depth: int = Query(default=1, ge=1, le=3),
    settings: Settings = Depends(get_settings),
) -> dict:
    g = works_api.work_graph_neighborhood(
        settings,
        work_id,
        neighbor_limit=neighbor_limit,
        depth=depth,
    )
    if not g:
        raise HTTPException(status_code=404, detail="work_not_found")
    return g


@app.get("/v1/works/{work_id}/chunks")
def get_work_chunks(
    work_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    settings: Settings = Depends(get_settings),
) -> dict:
    exists = works_api.get_work_detail(settings, work_id)
    if not exists:
        raise HTTPException(status_code=404, detail="work_not_found")
    return works_api.work_chunks(settings, work_id, limit=limit, offset=offset)


@app.get("/v1/works/{work_id}/claims", response_model=WorkClaimsResponse)
def get_work_claims(work_id: str, settings: Settings = Depends(get_settings)) -> WorkClaimsResponse:
    """Claims + verbatim evidence for Reader / Evidence UI (Wave O)."""

    items = works_api.list_work_claims(settings, work_id)
    if items is None:
        raise HTTPException(status_code=404, detail="work_not_found")
    return WorkClaimsResponse(work_id=work_id, items=items)


@app.get("/v1/works/{work_id}/sources")
def get_work_sources(work_id: str, settings: Settings = Depends(get_settings)) -> dict:
    body = works_api.work_sources_payload(settings, work_id)
    if not body:
        raise HTTPException(status_code=404, detail="work_not_found")
    return body


@app.get("/v1/works/{work_id}/pdf", response_model=None)
def get_work_pdf(request: Request, work_id: str, settings: Settings = Depends(get_settings)) -> Response:
    p = works_api.work_pdf_blob_path(settings, work_id)
    if not p:
        raise HTTPException(status_code=404, detail="pdf_not_found")
    size = int(p.stat().st_size)
    etag = f'W/"{p.name}"'
    common = {
        "Accept-Ranges": "bytes",
        "ETag": etag,
        "Cache-Control": "private, max-age=0",
    }
    inm = request.headers.get("if-none-match")
    if inm:
        tokens = {t.strip() for t in inm.split(",") if t.strip()}
        if etag in tokens:
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
        return Response(
            status_code=416,
            headers={**common, "Content-Range": f"bytes */{size}"},
        )
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


@app.get("/", response_model=None)
def root_page() -> RedirectResponse | HTMLResponse:
    if _UI_DIR.is_dir():
        return RedirectResponse(url="/ui/", status_code=307)
    return HTMLResponse(
        content="<p>UI missing; open science_graphrag/api/static/ui/index.html after building the frontend.</p>",
        status_code=200,
    )


@app.get("/legacy/retrieval-mvp", response_class=HTMLResponse, response_model=None)
def legacy_retrieval_mvp_page() -> FileResponse | HTMLResponse:
    index = _STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(
        content="<p>Legacy retrieval MVP missing; open science_graphrag/api/static/index.html in repo.</p>",
        status_code=200,
    )


def main() -> None:
    uvicorn.run(
        "science_graphrag.api.main:app",
        host="0.0.0.0",
        port=8787,
        reload=False,
    )
