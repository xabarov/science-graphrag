from __future__ import annotations

from typing import TypedDict


class ToolCallTrace(TypedDict):
    step: int
    tool: str
    args_summary: dict
    row_count: int | None
    duration_ms: int
    truncated: bool
    error: str | None
