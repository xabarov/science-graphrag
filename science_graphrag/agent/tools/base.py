from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from science_graphrag.agent.trace import ToolCallTrace


@dataclass
class ToolResult:
    payload: dict[str, Any]
    row_count: int | None = None
    truncated: bool = False


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
            res = self.run(**kwargs)
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
