from __future__ import annotations

import json
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from science_graphrag.agent.tools import (
    CypherQueryTool,
    EdgeSearchTool,
    FinalAnswerTool,
    IdeaSearchTool,
    SummarizeWorkspaceTool,
)
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.config import Settings
from science_graphrag.ingestion.llm.extractor import (
    EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
    SyncInstructorExtractor,
)
from science_graphrag.observability.phoenix_tracer import SpanAttributes, llm_span
from science_graphrag.utils.llm_deadline import MonotonicDeadline

IdeaAssistMode = Literal["hypotheses", "contradictions", "both"]


@dataclass
class HypothesisCandidate:
    text: str
    supporting_claim_ids: list[str]
    novelty_hint: str
    evidence_quotes: list[str]


@dataclass
class ContradictionPair:
    claim_a_id: str
    claim_b_id: str
    description: str


@dataclass
class IdeaWorkflowOutput:
    hypotheses: list[HypothesisCandidate]
    contradictions: list[ContradictionPair]
    tool_trace: list[ToolCallTrace]
    duration_ms: int


class _HypothesisLLM(BaseModel):
    text: str = Field(default="", max_length=1000)
    supporting_claim_ids: list[str] = Field(default_factory=list)
    novelty_hint: str = Field(default="", max_length=600)
    evidence_quotes: list[str] = Field(default_factory=list)


class _ContradictionLLM(BaseModel):
    claim_a_id: str = Field(default="", max_length=200)
    claim_b_id: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=600)


class _IdeaAssistLLMResponse(BaseModel):
    hypotheses: list[_HypothesisLLM] = Field(default_factory=list)
    contradictions: list[_ContradictionLLM] = Field(default_factory=list)


_IDEA_ASSIST_SYSTEM = """You are an idea-assist engine for scientific workspaces.

Generate up to 3 hypothesis candidates and/or contradiction pairs from grounded claim evidence.

Rules:
1) Return strict JSON only.
2) Every hypothesis must cite claim IDs and include at least one verbatim evidence quote.
3) Avoid plagiarizing titles/abstracts; provide a novelty hint.
4) For contradictions, only emit pairs with explicit polarity or claim-text conflict evidence.
5) If evidence is insufficient, return empty arrays.
"""


class IdeaOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        idea_search: IdeaSearchTool,
        cypher_query: CypherQueryTool,
        edge_search: EdgeSearchTool,
        summarize_workspace: SummarizeWorkspaceTool,
        final_answer: FinalAnswerTool,
    ) -> None:
        self._settings = settings
        self._idea_search = idea_search
        self._cypher_query = cypher_query
        self._edge_search = edge_search
        self._summarize_workspace = summarize_workspace
        self._final_answer = final_answer

    def run(
        self,
        *,
        workspace_id: str,
        seed_topic: str | None,
        mode: IdeaAssistMode = "both",
        max_candidates: int = 3,
    ) -> IdeaWorkflowOutput:
        started = perf_counter()
        trace: list[ToolCallTrace] = []
        step = 1
        candidate_cap = max(1, min(int(max_candidates), 5))

        seed = str(seed_topic or "").strip()
        if not seed:
            ws = self._summarize_workspace.run_with_trace(
                step=step,
                trace=trace,
                args_summary={"workspace_id": workspace_id, "top_n_works": 8},
                workspace_id=workspace_id,
                top_n_works=8,
            )
            step += 1
            seed = str(ws.payload.get("summary") or "").strip()

        idea = self._idea_search.run_with_trace(
            step=step,
            trace=trace,
            args_summary={
                "q": seed[:120],
                "workspace_id": workspace_id,
                "kinds": ["chunk", "work"],
                "top_k": 10,
            },
            q=seed,
            workspace_id=workspace_id,
            kinds=["chunk", "work"],
            top_k=10,
        )
        step += 1
        work_ids = [
            str(item.get("work_id"))
            for item in (idea.payload.get("items") or [])
            if item.get("work_id")
        ]
        unique_work_ids = sorted({wid for wid in work_ids if wid})

        claim_rows: list[dict[str, Any]] = []
        if unique_work_ids:
            claims_query = """
            MATCH (ws:Workspace {id: $workspace_id})-[:CONTAINS]->(w:Work)
            WHERE w.id IN $work_ids
            MATCH (w)<-[:ANCHORED_IN]-(e:Evidence)<-[:SUPPORTED_BY]-(c:Claim)
            RETURN w.id AS work_id,
                   c.id AS claim_id,
                   coalesce(c.normalized_text, c.text, '') AS claim_text,
                   coalesce(c.polarity, 'neutral') AS polarity,
                   coalesce(c.claim_type, '') AS claim_type,
                   coalesce(c.confidence, 0.0) AS confidence,
                   e.chunk_fingerprint AS chunk_fingerprint,
                   coalesce(e.quote, '') AS quote
            ORDER BY work_id, claim_id
            LIMIT 400
            """
            claims_res = self._cypher_query.run_with_trace(
                step=step,
                trace=trace,
                args_summary={"workspace_id": workspace_id, "work_ids": len(unique_work_ids)},
                query=claims_query,
                params={"workspace_id": workspace_id, "work_ids": unique_work_ids},
            )
            step += 1
            claim_rows = [
                row for row in (claims_res.payload.get("rows") or []) if isinstance(row, dict)
            ]

        contradiction_rows: list[dict[str, Any]] = []
        if mode in ("contradictions", "both"):
            anchor_work = unique_work_ids[0] if unique_work_ids else ""
            if anchor_work:
                rels = self._edge_search.run_with_trace(
                    step=step,
                    trace=trace,
                    args_summary={
                        "node_id": anchor_work,
                        "rel_types": ["CONTRADICTS"],
                        "direction": "both",
                        "limit": 50,
                    },
                    node_id=anchor_work,
                    rel_types=["CONTRADICTS"],
                    direction="both",
                    limit=50,
                )
                step += 1
                contradiction_rows = [
                    row for row in (rels.payload.get("items") or []) if isinstance(row, dict)
                ]

        llm_response = self._run_llm(
            workspace_id=workspace_id,
            seed_topic=seed,
            mode=mode,
            max_candidates=candidate_cap,
            claims=claim_rows,
            contradictions=contradiction_rows,
        )

        hypotheses: list[HypothesisCandidate] = []
        if mode in ("hypotheses", "both"):
            for row in llm_response.hypotheses[:candidate_cap]:
                text = str(row.text or "").strip()
                evidence_quotes = [str(x).strip() for x in row.evidence_quotes if str(x).strip()]
                if not text or not evidence_quotes:
                    continue
                hypotheses.append(
                    HypothesisCandidate(
                        text=text,
                        supporting_claim_ids=[
                            str(x).strip() for x in row.supporting_claim_ids if str(x).strip()
                        ],
                        novelty_hint=str(row.novelty_hint or "").strip(),
                        evidence_quotes=evidence_quotes,
                    )
                )

        contradictions: list[ContradictionPair] = []
        if mode in ("contradictions", "both"):
            for row in llm_response.contradictions[:candidate_cap]:
                a = str(row.claim_a_id or "").strip()
                b = str(row.claim_b_id or "").strip()
                if not a or not b:
                    continue
                contradictions.append(
                    ContradictionPair(
                        claim_a_id=a,
                        claim_b_id=b,
                        description=str(row.description or "").strip(),
                    )
                )

        self._final_answer.run_with_trace(
            step=step,
            trace=trace,
            args_summary={"hypotheses": len(hypotheses), "contradictions": len(contradictions)},
            answer=f"Idea-assist generated {len(hypotheses)} hypotheses and {len(contradictions)} contradictions.",
            citations=[],
        )
        duration_ms = int((perf_counter() - started) * 1000)
        return IdeaWorkflowOutput(
            hypotheses=hypotheses,
            contradictions=contradictions,
            tool_trace=trace,
            duration_ms=duration_ms,
        )

    def _run_llm(
        self,
        *,
        workspace_id: str,
        seed_topic: str,
        mode: IdeaAssistMode,
        max_candidates: int,
        claims: list[dict[str, Any]],
        contradictions: list[dict[str, Any]],
    ) -> _IdeaAssistLLMResponse:
        if not self._settings.extraction_llm_api_key:
            return _IdeaAssistLLMResponse()
        extractor = SyncInstructorExtractor(
            api_key=self._settings.extraction_llm_api_key,
            base_url=self._settings.extraction_llm_base_url,
            model=self._settings.extraction_llm_model,
            temperature=0.0,
            max_tokens=min(4096, self._settings.extraction_llm_max_tokens_references),
            timeout_seconds=self._settings.extraction_llm_timeout_seconds,
            mode=self._settings.extraction_llm_mode,
        )
        transport_s = float(self._settings.extraction_llm_timeout_seconds)
        op_budget = min(900.0, transport_s * float(EXTRACT_MAYBE_MAX_INNER_ATTEMPTS))
        op_deadline = MonotonicDeadline.from_budget_seconds(op_budget)
        claims_preview = claims[:80]
        user = json.dumps(
            {
                "workspace_id": workspace_id,
                "seed_topic": seed_topic,
                "mode": mode,
                "max_candidates": max_candidates,
                "claims": claims_preview,
                "existing_contradictions": contradictions[:40],
            },
            ensure_ascii=False,
        )
        with llm_span(
            "llm.idea_assist",
            {
                **SpanAttributes.llm_runtime_policy_attributes(
                    pool_name="idea_assist",
                    transport_timeout_seconds=transport_s,
                    timeout_contract="transport_with_operation_deadline",
                    retry_extra_budget=0,
                    operation_deadline_seconds=op_budget,
                    transport_max_attempts=EXTRACT_MAYBE_MAX_INNER_ATTEMPTS,
                ),
            },
        ):
            parsed, err = extractor.extract_maybe(
                _IdeaAssistLLMResponse,
                system=_IDEA_ASSIST_SYSTEM,
                user=user,
                per_attempt_timeout_seconds=transport_s,
                operation_deadline=op_deadline,
            )
        if err or parsed is None:
            return _IdeaAssistLLMResponse()
        return parsed
