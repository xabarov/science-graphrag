from __future__ import annotations

from typing import TYPE_CHECKING

from science_graphrag.agent.tools import (
    CypherQueryTool,
    EdgeSearchTool,
    EntitySearchTool,
    FinalAnswerTool,
    IdeaSearchTool,
    SummarizeWorkspaceTool,
)
from science_graphrag.agent.trace import ToolCallTrace

if TYPE_CHECKING:
    from science_graphrag.agent.runtime import AgentRunOutput
    from science_graphrag.config import Settings
    from science_graphrag.storage.neo4j_store import Neo4jGraphStore
    from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


class LegacyRetrievalAgent:
    """Legacy deterministic retrieval runtime retained for compatibility."""

    def __init__(
        self,
        *,
        settings: Settings,
        neo4j: Neo4jGraphStore,
        chunks: QdrantChunkStore,
        works: QdrantWorkEmbeddingStore | None,
    ) -> None:
        self.settings = settings
        self.entity_search = EntitySearchTool(neo4j)
        self.edge_search = EdgeSearchTool(neo4j)
        self.cypher_query = CypherQueryTool(neo4j)
        self.idea_search = IdeaSearchTool(chunks, work_store=works, settings=settings)
        self.summarize_workspace = SummarizeWorkspaceTool(neo4j)
        self.final_answer = FinalAnswerTool()

    def run(
        self,
        *,
        question: str,
        workspace_id: str | None,
        max_tool_calls: int,
    ) -> AgentRunOutput:
        from science_graphrag.agent.runtime import AgentRunOutput

        trace: list[ToolCallTrace] = []
        step = 1
        idea = self.idea_search.run_with_trace(
            step=step,
            trace=trace,
            args_summary={"q": question[:120], "workspace_id": workspace_id, "top_k": 5},
            q=question,
            kinds=["chunk", "work"],
            workspace_id=workspace_id,
            top_k=5,
        )
        step += 1
        summary_text = ""
        if workspace_id and step <= max_tool_calls:
            ws = self.summarize_workspace.run_with_trace(
                step=step,
                trace=trace,
                args_summary={"workspace_id": workspace_id, "top_n_works": 8},
                workspace_id=workspace_id,
                top_n_works=8,
            )
            summary_text = str(ws.payload.get("summary") or "")
            step += 1

        hits = idea.payload.get("items") or []
        citations = [
            {"work_id": i.get("work_id"), "snippet": i.get("snippet", "")} for i in hits[:3]
        ]
        answer_lines = [
            "Agent retrieval summary:",
            f"- Question: {question}",
            f"- Retrieved items: {len(hits)}",
        ]
        if summary_text:
            answer_lines.append(f"- Workspace: {summary_text}")
        if citations:
            answer_lines.append(
                "- Supporting works: " + ", ".join(str(c.get("work_id") or "") for c in citations)
            )
        answer = "\n".join(answer_lines)
        final = self.final_answer.run_with_trace(
            step=step,
            trace=trace,
            args_summary={"answer_chars": len(answer), "citations": len(citations)},
            answer=answer,
            citations=citations,
        )
        return AgentRunOutput(
            answer=str(final.payload.get("answer") or ""),
            citations=list(final.payload.get("citations") or []),
            tool_trace=trace,
            routing_log=None,
        )
