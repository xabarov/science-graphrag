from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from science_graphrag.agent.idea_workflow import IdeaOrchestrator
from science_graphrag.agent.tools import (
    CypherQueryTool,
    EdgeSearchTool,
    FinalAnswerTool,
    IdeaSearchTool,
    SummarizeWorkspaceTool,
)
from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore

router = APIRouter()

IdeaAssistMode = Literal["hypotheses", "contradictions", "both"]


class IdeaAssistRequest(BaseModel):
    workspace_id: str = Field(..., min_length=1)
    seed_topic: str | None = None
    mode: IdeaAssistMode = "both"
    max_candidates: int = Field(default=3, ge=1, le=5)


class HypothesisCandidateOut(BaseModel):
    text: str
    supporting_claim_ids: list[str]
    novelty_hint: str
    evidence_quotes: list[str]


class ContradictionPairOut(BaseModel):
    claim_a_id: str
    claim_b_id: str
    description: str


class IdeaAssistResponse(BaseModel):
    hypotheses: list[HypothesisCandidateOut]
    contradictions: list[ContradictionPairOut]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    run_metadata: dict[str, Any]


@router.post("/agent/idea-assist", response_model=IdeaAssistResponse)
def post_idea_assist(
    body: IdeaAssistRequest,
    settings: Settings = Depends(get_settings),
) -> IdeaAssistResponse:
    if not settings.hypothesis_enabled:
        raise HTTPException(status_code=503, detail="hypothesis_disabled")
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
        orchestrator = IdeaOrchestrator(
            settings=settings,
            idea_search=IdeaSearchTool(chunks, work_store=works, embedding_model=settings.embedding_model),
            cypher_query=CypherQueryTool(neo),
            edge_search=EdgeSearchTool(neo),
            summarize_workspace=SummarizeWorkspaceTool(neo),
            final_answer=FinalAnswerTool(),
        )
        out = orchestrator.run(
            workspace_id=body.workspace_id.strip(),
            seed_topic=(body.seed_topic or "").strip() or None,
            mode=body.mode,
            max_candidates=body.max_candidates,
        )
    finally:
        neo.close()
    duration_ms = int((perf_counter() - started) * 1000)
    return IdeaAssistResponse(
        hypotheses=[
            HypothesisCandidateOut(
                text=row.text,
                supporting_claim_ids=row.supporting_claim_ids,
                novelty_hint=row.novelty_hint,
                evidence_quotes=row.evidence_quotes,
            )
            for row in out.hypotheses
        ],
        contradictions=[
            ContradictionPairOut(
                claim_a_id=row.claim_a_id,
                claim_b_id=row.claim_b_id,
                description=row.description,
            )
            for row in out.contradictions
        ],
        tool_trace=[dict(step) for step in out.tool_trace],
        duration_ms=duration_ms,
        run_metadata={
            "advisory_only": True,
            "wave": "S",
            "mode": body.mode,
            "max_candidates": body.max_candidates,
        },
    )
