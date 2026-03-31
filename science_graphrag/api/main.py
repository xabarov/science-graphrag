"""FastAPI entrypoint: retrieval, citations, minimal researcher UI."""

from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from science_graphrag.api.retrieval import GroundedAnswer, answer_query
from science_graphrag.config import get_settings

app = FastAPI(title="science-graphrag", version="0.1.0")
_STATIC_DIR = Path(__file__).resolve().parent / "static"
if _STATIC_DIR.is_dir():
    app.mount("/ui/assets", StaticFiles(directory=_STATIC_DIR), name="ui_assets")


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=24)


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict]
    graph_context: dict
    retrieval_trace: dict


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


@app.get("/", response_class=HTMLResponse, response_model=None)
def root_page() -> FileResponse | HTMLResponse:
    index = _STATIC_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(
        content="<p>UI missing; open science_graphrag/api/static/index.html in repo.</p>",
        status_code=200,
    )


def main() -> None:
    uvicorn.run(
        "science_graphrag.api.main:app",
        host="0.0.0.0",
        port=8787,
        reload=False,
    )
