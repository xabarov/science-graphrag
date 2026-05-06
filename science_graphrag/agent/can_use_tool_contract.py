"""Per-call tool gating callback contract (Train T3 §10.7).

Kept separate from ``tool_execution_pipeline`` so disk/registry code does not
depend on the full execution seam module graph.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from science_graphrag.agent.graph.state import AgentState

CanUseTool = Callable[[AgentState, str, dict[str, Any]], str | None]

__all__ = ["CanUseTool"]
