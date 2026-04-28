from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from science_graphrag.agent.idea_workflow import IdeaOrchestrator
from science_graphrag.agent.tools import (
    CypherQueryTool,
    EdgeSearchTool,
    FinalAnswerTool,
    IdeaSearchTool,
)
from science_graphrag.agent.tools.workspace_catalog_tools import WorkspaceInspectTool
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.storage.db import get_engine, session_factory
from science_graphrag.storage.models_orm import WorkspaceHypothesisRecord

router = APIRouter()
logger = logging.getLogger(__name__)

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
    stores: StoreRegistry = Depends(get_stores),
) -> IdeaAssistResponse:
    if not settings.hypothesis_enabled:
        raise HTTPException(status_code=503, detail="hypothesis_disabled")
    started = perf_counter()
    if not settings.idea_assist_live_runtime:
        duration_ms = int((perf_counter() - started) * 1000)
        return IdeaAssistResponse(
            hypotheses=[],
            contradictions=[],
            tool_trace=[],
            duration_ms=duration_ms,
            run_metadata={
                "advisory_only": True,
                "live_runtime": False,
                "wave": "S",
                "mode": body.mode,
                "max_candidates": body.max_candidates,
                "note": "idea_assist_live_runtime disabled; skipped orchestrator",
            },
        )
    orchestrator = IdeaOrchestrator(
        settings=settings,
        idea_search=IdeaSearchTool(
            stores.qdrant_chunks,
            work_store=stores.qdrant_works,
            settings=settings,
        ),
        cypher_query=CypherQueryTool(stores.neo4j),
        edge_search=EdgeSearchTool(stores.neo4j),
        workspace_inspect=WorkspaceInspectTool(stores.neo4j),
        final_answer=FinalAnswerTool(),
    )
    out = orchestrator.run(
        workspace_id=body.workspace_id.strip(),
        seed_topic=(body.seed_topic or "").strip() or None,
        mode=body.mode,
        max_candidates=body.max_candidates,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    try:
        engine = get_engine(settings.database_url)
        sess_maker = session_factory(engine)
        with sess_maker() as session:
            for row in out.hypotheses:
                session.add(
                    WorkspaceHypothesisRecord(
                        workspace_id=body.workspace_id.strip(),
                        text=row.text,
                        payload_json=json.dumps(
                            {
                                "supporting_claim_ids": row.supporting_claim_ids,
                                "novelty_hint": row.novelty_hint,
                                "evidence_quotes": row.evidence_quotes,
                            },
                            ensure_ascii=False,
                        ),
                    )
                )
            session.commit()
    except SQLAlchemyError as exc:
        logger.warning("idea_assist hypothesis persist skipped: %s", exc)

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
            "live_runtime": True,
            "wave": "S",
            "mode": body.mode,
            "max_candidates": body.max_candidates,
        },
    )
