from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult


class FinalAnswerTool(BaseAgentTool):
    name = "final_answer"

    def run(self, *, answer: str, citations: list[dict] | None = None) -> ToolResult:
        return ToolResult(
            payload={
                "answer": str(answer or "").strip(),
                "citations": list(citations or []),
            },
            row_count=len(citations or []),
        )


class FinalAnswerArgs(BaseModel):
    answer: str = Field(..., description="Final answer text.")
    citations: list[dict] = Field(default_factory=list, description="Citation list.")


def _make_final_answer_tool() -> BaseTool:
    runtime_tool = FinalAnswerTool()

    @tool("final_answer", args_schema=FinalAnswerArgs, return_direct=True)
    def final_answer_tool(answer: str, citations: list[dict] | None = None) -> dict:
        """Finalize answer payload for API response."""
        result = runtime_tool.run(answer=answer, citations=citations)
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return final_answer_tool
