from __future__ import annotations

from langchain_core.tools import BaseTool, tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import BaseAgentTool, ToolResult
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span


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
    answer: str = Field(
        ...,
        description=(
            "User-facing markdown; must reflect retrieved evidence when tools were used. "
            "This tool call must be the last in the turn."
        ),
    )
    citations: list[dict] = Field(
        default_factory=list,
        description=(
            "Structured citations (e.g. work_id, chunk id, snippet refs). May be empty only when "
            "no corpus tools ran or the reply is explicitly non-factual."
        ),
    )


def _make_final_answer_tool() -> BaseTool:
    runtime_tool = FinalAnswerTool()

    @tool("final_answer", args_schema=FinalAnswerArgs, return_direct=True)
    def final_answer_tool(answer: str, citations: list[dict] | None = None) -> dict:
        """Single closing hop: payload keys follow ``FinalAnswerArgs`` (see schema); must be last."""
        result = run_tool_result_with_span(
            tool_name="final_answer",
            tool_parameters={
                "answer_chars": len(answer or ""),
                "citations_count": len(citations or []),
            },
            fn=lambda: runtime_tool.run(answer=answer, citations=citations),
        )
        payload = dict(result.payload)
        payload.setdefault("row_count", result.row_count)
        payload.setdefault("truncated", result.truncated)
        return payload

    return final_answer_tool
