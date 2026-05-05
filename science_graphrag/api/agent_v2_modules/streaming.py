"""Streaming primitives for Agent API v2."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncIterator
from typing import Any

from opentelemetry import context as otel_context

from science_graphrag.agent.graph.errors import AgentGraphDeadlineExceeded


async def iter_graph_chunks(
    graph: Any,
    initial_state: dict[str, Any],
    config: dict[str, Any],
    *,
    deadline_seconds: float | None = None,
) -> AsyncIterator[Any]:
    """Yield graph stream chunks (updates dict, or (mode, payload) tuples)."""
    if hasattr(graph, "astream") and callable(graph.astream):
        sig = inspect.signature(graph.astream)
        kwargs: dict[str, Any] = {}
        if "stream_mode" in sig.parameters:
            kwargs["stream_mode"] = ["updates", "values"]

        async def _astream_body() -> AsyncIterator[Any]:
            async for chunk in graph.astream(initial_state, config=config, **kwargs):
                yield chunk

        if deadline_seconds and deadline_seconds > 0:
            try:
                async with asyncio.timeout(float(deadline_seconds)):
                    async for item in _astream_body():
                        yield item
            except TimeoutError as exc:
                raise AgentGraphDeadlineExceeded(
                    timeout_seconds=float(deadline_seconds),
                ) from exc
            return

        async for chunk in _astream_body():
            yield chunk
        return

    parent_ctx = otel_context.get_current()

    def _collect_sync_chunks() -> list[Any]:
        token = otel_context.attach(parent_ctx)
        try:
            out: list[Any] = []
            for chunk in graph.stream(initial_state, config=config):
                out.append(chunk)
            return out
        finally:
            otel_context.detach(token)

    if deadline_seconds and deadline_seconds > 0:
        try:
            chunks = await asyncio.wait_for(
                asyncio.to_thread(_collect_sync_chunks),
                timeout=float(deadline_seconds),
            )
        except TimeoutError as exc:
            raise AgentGraphDeadlineExceeded(
                timeout_seconds=float(deadline_seconds),
            ) from exc
    else:
        chunks = await asyncio.to_thread(_collect_sync_chunks)
    for chunk in chunks:
        yield chunk


def iter_update_node_states(chunk: Any) -> list[Any]:
    """Normalize stream chunk to a list of per-node state dicts."""
    if isinstance(chunk, tuple) and len(chunk) == 2:
        _mode, payload = chunk
        if isinstance(payload, dict):
            return list(payload.values())
        return []
    if isinstance(chunk, dict):
        return list(chunk.values())
    return []
