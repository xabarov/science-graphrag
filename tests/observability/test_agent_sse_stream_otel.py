"""OTel context survives sync ``graph.stream`` inside ``asyncio.to_thread`` (SSE fallback)."""

from __future__ import annotations

import asyncio

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from science_graphrag.api.agent_v2 import _iter_graph_chunks
from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability import spans as observability_spans
from science_graphrag.observability.spans import chain_span


def test_iter_graph_chunks_sync_stream_preserves_otel_parent(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_TRACE_SCOPE", "full")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-sse-stream-otel")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    monkeypatch.setattr(observability_spans, "get_tracer", lambda name="science-graphrag": tracer)

    class _GraphNoAstream:
        def stream(self, state, config=None):  # noqa: ARG002
            current = trace.get_current_span().get_span_context()
            assert current.is_valid is True
            with chain_span("from_sync_stream"):
                yield {"n": 1}

    async def _consume() -> None:
        with chain_span("agent.query"):
            async for _ in _iter_graph_chunks(
                _GraphNoAstream(),
                {},
                {},
                deadline_seconds=None,
            ):
                pass

    asyncio.run(_consume())

    spans = exporter.get_finished_spans()
    parent = next(s for s in spans if s.name == "agent.query")
    child = next(s for s in spans if s.name == "from_sync_stream")
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id
    assert child.context.trace_id == parent.context.trace_id
