from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from science_graphrag.agent.trace import ToolCallTrace


@dataclass
class ToolResult:
    payload: dict[str, Any]
    row_count: int | None = None
    truncated: bool = False


def _tool_span_payload_preview(payload: dict[str, Any]) -> dict[str, Any]:
    """Small subset of tool payload for Phoenix TOOL span output."""

    if "answer" in payload and isinstance(payload.get("answer"), str):
        ans = str(payload["answer"])
        return {
            "answer_chars": len(ans),
            "citations_count": (
                len(payload["citations"]) if isinstance(payload.get("citations"), list) else 0
            ),
        }

    preview: dict[str, Any] = {}
    for key in (
        "error",
        "summary",
        "format",
        "row_count",
        "truncated",
        "truncated_at",
        "work_ids",
        "cited_work_ids",
    ):
        if key in payload:
            val = payload[key]
            if isinstance(val, str) and len(val) > 200:
                preview[key] = val[:200] + "...[truncated]"
            else:
                preview[key] = val
    if "items" in payload and isinstance(payload["items"], list):
        preview["items_count"] = len(payload["items"])
    if "rows" in payload and isinstance(payload["rows"], list):
        preview["rows_count"] = len(payload["rows"])
    if "quote_candidates" in payload and isinstance(payload["quote_candidates"], list):
        preview["quote_candidates_count"] = len(payload["quote_candidates"])
    if "entries" in payload and isinstance(payload["entries"], list):
        preview["entries_count"] = len(payload["entries"])
    return preview


def run_tool_result_with_span(
    *,
    tool_name: str,
    tool_parameters: dict[str, Any],
    fn: Callable[[], ToolResult],
) -> ToolResult:
    """Run a tool body under a Phoenix TOOL span with safe output (LangChain + legacy paths)."""

    from science_graphrag.observability.spans import SpanAttributes, traced_tool_span
    from science_graphrag.observability.spans.decorators import MIME_TYPE_JSON

    with traced_tool_span(
        f"tool.{tool_name}",
        tool_name=tool_name,
        tool_parameters=tool_parameters,
    ):
        res = fn()
        SpanAttributes.set_output(
            SpanAttributes.tool_result_preview(
                row_count=res.row_count,
                truncated=res.truncated,
                preview=_tool_span_payload_preview(dict(res.payload)),
            ),
            mime_type=MIME_TYPE_JSON,
        )
        return res


class BaseAgentTool:
    name: str = "tool"

    def run(self, **kwargs: Any) -> ToolResult:  # pragma: no cover - interface
        raise NotImplementedError

    def run_with_trace(
        self,
        *,
        step: int,
        args_summary: dict[str, Any],
        trace: list[ToolCallTrace],
        **kwargs: Any,
    ) -> ToolResult:
        started = perf_counter()
        try:
            res = run_tool_result_with_span(
                tool_name=self.name,
                tool_parameters=args_summary,
                fn=lambda: self.run(**kwargs),
            )
            trace.append(
                ToolCallTrace(
                    step=step,
                    tool=self.name,
                    args_summary=args_summary,
                    row_count=res.row_count,
                    duration_ms=int((perf_counter() - started) * 1000),
                    truncated=res.truncated,
                    error=None,
                )
            )
            return res
        except Exception as exc:  # noqa: BLE001
            trace.append(
                ToolCallTrace(
                    step=step,
                    tool=self.name,
                    args_summary=args_summary,
                    row_count=None,
                    duration_ms=int((perf_counter() - started) * 1000),
                    truncated=False,
                    error=str(exc),
                )
            )
            raise


__all__ = ["BaseAgentTool", "ToolResult", "run_tool_result_with_span"]
