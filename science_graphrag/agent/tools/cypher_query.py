from __future__ import annotations

from typing import Any

from science_graphrag.agent.cypher_safety import validate_readonly_cypher
from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
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
