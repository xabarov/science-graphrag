"""Route LangGraph stream chunks to values vs updates phase handlers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from science_graphrag.api.agent_v2_modules.stream_lifecycle_state import (
    StreamAgentLifecycleState,
    StreamLifecycleRequestContext,
)
from science_graphrag.api.agent_v2_modules.stream_phase_subagent_events import (
    iter_values_mode_stream_events,
)
from science_graphrag.api.agent_v2_modules.stream_phase_tool_events import (
    iter_updates_mode_tool_events,
)


async def iter_stream_chunk_phase_events(
    *,
    ctx: StreamLifecycleRequestContext,
    state: StreamAgentLifecycleState,
    chunk: Any,
) -> AsyncIterator[dict[str, str]]:
    """Dispatch one graph stream chunk to the appropriate phase emitters."""
    if isinstance(chunk, tuple) and len(chunk) == 2:
        mode, payload = chunk
        if mode == "values" and isinstance(payload, dict):
            async for ev in iter_values_mode_stream_events(ctx=ctx, state=state, payload=payload):
                yield ev
        if mode != "updates":
            return
        chunk = payload

    async for ev in iter_updates_mode_tool_events(ctx=ctx, state=state, chunk=chunk):
        yield ev


__all__ = ["iter_stream_chunk_phase_events"]
