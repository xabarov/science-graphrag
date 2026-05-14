from __future__ import annotations

from time import perf_counter
from typing import Any

from science_graphrag.agent.idea_assist import (
    IdeaAssistLLMResponse,
    IdeaAssistMode,
    IdeaWorkflowOutput,
    collect_idea_assist_context,
    normalize_idea_assist_output,
    run_idea_assist_llm,
)
from science_graphrag.agent.tools import (
    CypherQueryTool,
    EdgeSearchTool,
    FinalAnswerTool,
    IdeaSearchTool,
)
from science_graphrag.agent.tools.workspace_catalog_tools import WorkspaceInspectTool
from science_graphrag.agent.trace import ToolCallTrace
from science_graphrag.config import Settings


class IdeaOrchestrator:
    def __init__(
        self,
        *,
        settings: Settings,
        idea_search: IdeaSearchTool,
        cypher_query: CypherQueryTool,
        edge_search: EdgeSearchTool,
        workspace_inspect: WorkspaceInspectTool,
        final_answer: FinalAnswerTool,
    ) -> None:
        self._settings = settings
        self._idea_search = idea_search
        self._cypher_query = cypher_query
        self._edge_search = edge_search
        self._workspace_inspect = workspace_inspect
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
        candidate_cap = max(1, min(int(max_candidates), 5))
        seed, claim_rows, contradiction_rows = collect_idea_assist_context(
            workspace_id=workspace_id,
            seed_topic=seed_topic,
            mode=mode,
            idea_search=self._idea_search,
            cypher_query=self._cypher_query,
            edge_search=self._edge_search,
            workspace_inspect=self._workspace_inspect,
            trace=trace,
        )

        llm_response = self._run_llm(
            workspace_id=workspace_id,
            seed_topic=seed,
            mode=mode,
            max_candidates=candidate_cap,
            claims=claim_rows,
            contradictions=contradiction_rows,
        )
        hypotheses, contradictions = normalize_idea_assist_output(
            llm_response=llm_response,
            mode=mode,
            max_candidates=candidate_cap,
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
    ) -> IdeaAssistLLMResponse:
        return run_idea_assist_llm(
            settings=self._settings,
            workspace_id=workspace_id,
            seed_topic=seed_topic,
            mode=mode,
            max_candidates=max_candidates,
            claims=claims,
            contradictions=contradictions,
        )
