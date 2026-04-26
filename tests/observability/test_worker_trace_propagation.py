from __future__ import annotations

from types import SimpleNamespace

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

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
