from __future__ import annotations

from time import perf_counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from science_graphrag.agent.runtime import build_agent
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore

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
) -> AgentQueryResponse:
    if not settings.agent_enabled:
        raise HTTPException(status_code=503, detail="agent_disabled")
    started = perf_counter()
    dim = resolve_embedding_dim(embedding_model=settings.embedding_model)
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    chunks = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
    works = QdrantWorkEmbeddingStore(
        settings.qdrant_url,
        settings.qdrant_work_embeddings_collection,
        vector_dim=dim,
    )
    try:
        agent = build_agent(settings=settings, neo4j=neo, chunks=chunks, works=works)
        out = agent.run(
            question=body.question,
            workspace_id=(body.workspace_id or "").strip() or None,
            max_tool_calls=body.max_tool_calls or settings.agent_max_tool_calls,
        )
    finally:
        neo.close()
    duration_ms = int((perf_counter() - started) * 1000)
    return AgentQueryResponse(
        answer=out.answer,
        citations=out.citations,
        tool_trace=list(out.tool_trace),
        duration_ms=duration_ms,
        run_metadata={
            "agent_runtime": "langgraph_like_v1",
            "agent_enabled": settings.agent_enabled,
            "agent_max_tool_calls": body.max_tool_calls or settings.agent_max_tool_calls,
            "extraction_llm_model": settings.extraction_llm_model,
            "extraction_llm_base_url": settings.extraction_llm_base_url,
        },
    )
