"""FastAPI entrypoint: retrieval, citations, minimal researcher UI."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from science_graphrag.api import works as works_api
from science_graphrag.api.admin_access import require_admin_if_configured
from science_graphrag.api.ask_sessions import router as ask_sessions_router
from science_graphrag.api.benchmark import router as benchmark_router
from science_graphrag.api.settings import router as settings_router
from science_graphrag.api.retrieval import GroundedAnswer, answer_query
from science_graphrag.config import get_settings

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


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=24)


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    graph_context: dict
    retrieval_trace: dict


class WorksListResponse(BaseModel):
    items: list[dict]
    total: int


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/query", response_model=QueryResponse)
def post_query(body: QueryRequest) -> QueryResponse:
    result: GroundedAnswer = answer_query(
        body.query,
        settings=get_settings(),
        work_id=body.work_id,
        top_k=body.top_k,
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
) -> WorksListResponse:
    items, total = works_api.list_works(
        get_settings(),
        q=q,
        limit=limit,
        offset=offset,
        year_min=year_min,
        year_max=year_max,
        has_semantic=has_semantic,
    )
    return WorksListResponse(items=items, total=total)


@app.get("/v1/works/{work_id}")
def get_work_by_id(work_id: str) -> dict:
    detail = works_api.get_work_detail(get_settings(), work_id)
    if not detail:
        raise HTTPException(status_code=404, detail="work_not_found")
    chunks = works_api.work_chunks(get_settings(), work_id, limit=1, offset=0)
    if "error" not in chunks:
        detail["ingestion"]["has_chunks"] = int(chunks.get("total", 0)) > 0
    return detail


@app.get("/v1/works/{work_id}/graph")
def get_work_graph(
    work_id: str,
    neighbor_limit: int = Query(default=200, ge=1, le=2000),
    depth: int = Query(default=1, ge=1, le=3),
) -> dict:
    g = works_api.work_graph_neighborhood(
        get_settings(),
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
) -> dict:
    exists = works_api.get_work_detail(get_settings(), work_id)
    if not exists:
        raise HTTPException(status_code=404, detail="work_not_found")
    return works_api.work_chunks(get_settings(), work_id, limit=limit, offset=offset)


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
