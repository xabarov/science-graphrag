from __future__ import annotations

from types import SimpleNamespace

from science_graphrag.worker.otel_middleware import OtelTraceMiddleware


def test_otel_middleware_before_after_no_crash() -> None:
    mw = OtelTraceMiddleware()
    msg = SimpleNamespace(
        options={"traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"}
    )
    mw.before_process_message(None, msg)
    mw.after_process_message(None, msg, result=None, exception=None)
