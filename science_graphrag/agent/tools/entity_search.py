from __future__ import annotations

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
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
