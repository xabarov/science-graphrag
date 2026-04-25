from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from science_graphrag.agent.runtime import build_agent
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings

router = APIRouter()


class AgentQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    workspace_id: str | None = None
    max_tool_calls: int | None = Field(default=None, ge=1, le=30)


class AgentQueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    run_metadata: dict[str, Any]


@router.post("/agent/query", response_model=AgentQueryResponse)
def post_agent_query(
    body: AgentQueryRequest,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> AgentQueryResponse:
    if not settings.agent_enabled:
        raise HTTPException(status_code=503, detail="agent_disabled")
    started = perf_counter()
    agent = build_agent(
        settings=settings,
        stores=stores,
    )
    out = agent.run(
        question=body.question,
        workspace_id=(body.workspace_id or "").strip() or None,
        max_tool_calls=body.max_tool_calls or settings.agent_max_tool_calls,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    return AgentQueryResponse(
        answer=out.answer,
        citations=out.citations,
        tool_trace=list(out.tool_trace),
        duration_ms=duration_ms,
        run_metadata={
            "agent_runtime": settings.agent_runtime,
            "agent_enabled": settings.agent_enabled,
            "agent_max_tool_calls": body.max_tool_calls or settings.agent_max_tool_calls,
            "extraction_llm_model": settings.extraction_llm_model,
            "extraction_llm_base_url": settings.extraction_llm_base_url,
        },
    )
