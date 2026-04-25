from __future__ import annotations

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


class SummarizeWorkspaceTool(BaseAgentTool):
    name = "summarize_workspace"

    def __init__(self, store: Neo4jGraphStore) -> None:
        self._store = store

    def run(self, *, workspace_id: str, top_n_works: int = 8) -> ToolResult:
        ws = self._store.workspace_get(workspace_id)
        if not ws:
            return ToolResult(
                payload={"summary": "Workspace not found.", "cited_work_ids": []}, row_count=0
            )
        work_ids = [str(x) for x in (ws.get("work_ids") or []) if x][
            : max(1, min(int(top_n_works), 15))
        ]
        summary = (
            f"Workspace {ws.get('name') or workspace_id} currently contains {len(ws.get('work_ids') or [])} works. "
            f"Top sampled works: {', '.join(work_ids) if work_ids else 'none'}."
        )
        return ToolResult(
            payload={"summary": summary, "cited_work_ids": work_ids}, row_count=len(work_ids)
        )
