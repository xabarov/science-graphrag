from __future__ import annotations

from typing import Any

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class EdgeSearchTool(BaseAgentTool):
    name = "edge_search"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(
        self,
        *,
        node_id: str,
        rel_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> ToolResult:
        rel_types = [r for r in (rel_types or []) if r]
        lim = max(1, min(int(limit), 200))
        rel_filter = ""
        if rel_types:
            rel_filter = " AND type(r) IN $rel_types"
        if direction == "in":
            pattern = "(src)-[r]->(n:Work {id: $node_id})"
        elif direction == "out":
            pattern = "(n:Work {id: $node_id})-[r]->(tgt)"
        else:
            pattern = "(n:Work {id: $node_id})-[r]-(other)"
        if direction == "in":
            cypher = f"MATCH {pattern} WHERE 1=1{rel_filter} RETURN src.id AS src, type(r) AS rel, n.id AS tgt LIMIT $lim"
        elif direction == "out":
            cypher = f"MATCH {pattern} WHERE 1=1{rel_filter} RETURN n.id AS src, type(r) AS rel, tgt.id AS tgt LIMIT $lim"
        else:
            cypher = f"MATCH {pattern} WHERE 1=1{rel_filter} RETURN n.id AS src, type(r) AS rel, other.id AS tgt LIMIT $lim"
        rows: list[dict[str, Any]] = []
        with self._store.session() as session:
            for row in session.run(cypher, node_id=node_id, rel_types=rel_types, lim=lim):
                rows.append(dict(row.items()))
        return ToolResult(payload={"items": rows}, row_count=len(rows), truncated=len(rows) >= lim)


class EdgeSearchArgs(BaseModel):
    node_id: str = Field(..., description="Work node id.")
    rel_types: list[str] = Field(default_factory=list, description="Optional relation type filter.")
    direction: str = Field(default="both", description="in, out, or both.")
    limit: int = Field(default=50, ge=1, le=200, description="Max edges to return.")


def _make_edge_search_tool(store: Neo4jGraphStore) -> BaseTool:
    runtime_tool = EdgeSearchTool(store)

    @tool("edge_search", args_schema=EdgeSearchArgs, return_direct=False)
    def edge_search_tool(
        node_id: str,
        rel_types: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search neighboring graph edges for a work node."""
        result = run_tool_result_with_span(
            tool_name="edge_search",
            tool_parameters={
                "node_id": node_id,
                "rel_types": list(rel_types or [])[:12],
                "direction": direction,
                "limit": limit,
            },
            fn=lambda: runtime_tool.run(
                node_id=node_id,
                rel_types=rel_types,
                direction=direction,
                limit=limit,
            ),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return edge_search_tool
