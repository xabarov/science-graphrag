from __future__ import annotations

from types import SimpleNamespace

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from science_graphrag.agent.graph.invoke_timeout import invoke_graph_with_deadline
from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability import spans as observability_spans
from science_graphrag.observability.spans import chain_span
from science_graphrag.worker.otel_middleware import OtelTraceMiddleware
from science_graphrag.worker.trace_options import dramatiq_otel_options


def test_otel_middleware_before_after_no_crash() -> None:
    mw = OtelTraceMiddleware()
    msg = SimpleNamespace(
        options={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
    )
    mw.before_process_message(None, msg)
    mw.after_process_message(None, msg, result=None, exception=None)


def test_dramatiq_otel_options_injects_traceparent_under_span() -> None:
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("enqueue"):
        opts = dramatiq_otel_options()
    assert "traceparent" in opts
    assert opts["traceparent"].count("-") >= 2


def test_invoke_graph_with_deadline_preserves_otel_parent_context(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_TRACE_SCOPE", "full")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-thread-propagation")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    monkeypatch.setattr(observability_spans, "get_tracer", lambda name="science-graphrag": tracer)

    class _FakeGraph:
        def invoke(self, state, config=None):  # noqa: ARG002
            current = trace.get_current_span().get_span_context()
            assert current.is_valid is True
            with chain_span("agent.worker.child"):
                return {"ok": True}

    with chain_span("agent.query"):
        result = invoke_graph_with_deadline(_FakeGraph(), {}, config={}, timeout_seconds=2)

    assert result == {"ok": True}
    spans = exporter.get_finished_spans()
    parent = next(s for s in spans if s.name == "agent.query")
    child = next(s for s in spans if s.name == "agent.worker.child")
    assert child.parent is not None
    assert child.parent.span_id == parent.context.span_id
    assert child.context.trace_id == parent.context.trace_id
