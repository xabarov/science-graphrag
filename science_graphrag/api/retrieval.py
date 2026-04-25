"""Thin retrieval router delegating to retrieval core package."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.retrieval import GroundedAnswer, answer_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    workspace_id: str | None = None
    retrieval_mode: str = Field(default="vector")
    mode: str | None = None


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    graph_context: dict[str, Any]
    retrieval_trace: dict[str, Any]


@router.post("/query", response_model=QueryResponse)
def post_query(
    body: QueryRequest,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> QueryResponse:
    mode = body.mode or body.retrieval_mode
    result: GroundedAnswer = answer_query(
        question=body.query,
        work_id=body.work_id,
        top_k=body.top_k,
        workspace_id=body.workspace_id,
        mode=mode,
        settings=settings,
        stores=stores,
    )
    return QueryResponse(
        answer=result.answer,
        citations=result.citations,
        graph_context=result.graph_context,
        retrieval_trace=result.retrieval_trace,
    )
