from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class EntitySearchTool(BaseAgentTool):
    name = "entity_search"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, kind: str, q: str, limit: int = 10) -> ToolResult:
        if kind != "work":
            return ToolResult(payload={"items": []}, row_count=0)
        rows = self._store.fulltext_search_work_ids(q, limit=max(1, min(int(limit), 25)))
        items = [{"id": wid, "label": "Work", "score": score, "snippet": ""} for wid, score in rows]
        return ToolResult(payload={"items": items}, row_count=len(items))


class EntitySearchArgs(BaseModel):
    kind: str = Field(default="work", description="Entity kind, currently supports 'work'.")
    query: str = Field(..., description="Search query.")
    limit: int = Field(default=10, ge=1, le=25, description="Max entities to return.")


def _make_entity_search_tool(store: Neo4jGraphStore) -> BaseTool:
    runtime_tool = EntitySearchTool(store)

    @tool("entity_search", args_schema=EntitySearchArgs, return_direct=False)
    def entity_search_tool(kind: str = "work", query: str = "", limit: int = 10) -> dict:
        """Search knowledge-graph entities by fulltext index."""
        result = run_tool_result_with_span(
            tool_name="entity_search",
            tool_parameters={
                "kind": kind,
                "query": query[:240],
                "limit": limit,
            },
            fn=lambda: runtime_tool.run(kind=kind, q=query, limit=limit),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return entity_search_tool
