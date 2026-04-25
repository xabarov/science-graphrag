from __future__ import annotations

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
