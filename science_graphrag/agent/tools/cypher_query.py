from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.cypher_safety import validate_readonly_cypher
from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class CypherQueryTool(BaseAgentTool):
    name = "cypher_query"

    def __init__(self, store: Neo4jGraphStore, *, max_rows: int = 200) -> None:
        self._store = store
        self._max_rows = max_rows

    def run(self, *, query: str, params: dict[str, Any] | None = None) -> ToolResult:
        validate_readonly_cypher(query, max_limit=self._max_rows)
        rows: list[dict[str, Any]] = []
        with self._store.session() as session:
            result = session.run(query, **(params or {}))
            for idx, row in enumerate(result):
                if idx >= self._max_rows:
                    break
                rows.append(dict(row.items()))
        return ToolResult(
            payload={
                "rows": rows,
                "row_count": len(rows),
                "truncated_at": self._max_rows if len(rows) >= self._max_rows else None,
            },
            row_count=len(rows),
            truncated=len(rows) >= self._max_rows,
        )


class CypherQueryArgs(BaseModel):
    query: str = Field(
        ...,
        description="Read-only Cypher query. No write clauses. LIMIT must be <= 200.",
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Optional Cypher parameters.")


def _make_cypher_query_tool(store: Neo4jGraphStore, *, max_rows: int = 200) -> BaseTool:
    runtime_tool = CypherQueryTool(store, max_rows=max_rows)

    @tool("cypher_query", args_schema=CypherQueryArgs, return_direct=False)
    def cypher_query_tool(query: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Execute a read-only Cypher query against the knowledge graph."""
        result = run_tool_result_with_span(
            tool_name="cypher_query",
            tool_parameters={
                "query": query[:400],
                "params_keys": sorted(list((params or {}).keys()))[:20],
            },
            fn=lambda: runtime_tool.run(query=query, params=params),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return cypher_query_tool
