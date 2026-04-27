from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
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


class SummarizeWorkspaceArgs(BaseModel):
    workspace_id: str = Field(..., description="Workspace id.")
    top_n_works: int = Field(default=8, ge=1, le=15, description="How many work ids to include.")


def _make_summarize_workspace_tool(store: Neo4jGraphStore) -> BaseTool:
    runtime_tool = SummarizeWorkspaceTool(store)

    @tool("summarize_workspace", args_schema=SummarizeWorkspaceArgs, return_direct=False)
    def summarize_workspace_tool(
        workspace_id: str, top_n_works: int = 8
    ) -> dict[str, str | list[str] | int]:
        """Summarize workspace composition and sample work ids."""
        result = run_tool_result_with_span(
            tool_name="summarize_workspace",
            tool_parameters={"workspace_id": workspace_id, "top_n_works": top_n_works},
            fn=lambda: runtime_tool.run(workspace_id=workspace_id, top_n_works=top_n_works),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return summarize_workspace_tool
