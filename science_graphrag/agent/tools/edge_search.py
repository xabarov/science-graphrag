from __future__ import annotations

from typing import Any

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
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
