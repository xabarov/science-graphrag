"""Wave X3: attach OpenTelemetry context before Dramatiq message processing."""

from __future__ import annotations

import logging
import threading
from typing import Any

from dramatiq.middleware import Middleware
from opentelemetry import context, propagate

logger = logging.getLogger(__name__)

_tls = threading.local()


class OtelTraceMiddleware(Middleware):
    """Extract W3C trace context from ``message.options`` (if present) and attach it."""

    def before_process_message(self, broker: Any, message: Any) -> None:
        opts = getattr(message, "options", None) or {}
        carrier: dict[str, str] = {}
        if isinstance(opts, dict):
            for key, val in opts.items():
                if not isinstance(key, str) or val is None:
                    continue
                lk = key.lower()
                if lk.startswith("trace") or key == "traceparent":
                    carrier[key] = str(val)
        try:
            ctx = propagate.extract(carrier)
            token = context.attach(ctx)
            setattr(_tls, "otel_token", token)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.debug("otel_middleware: extract/attach failed", exc_info=True)

    def after_process_message(
        self, broker: Any, message: Any, *, result=None, exception=None
    ) -> None:
        token = getattr(_tls, "otel_token", None)
        if token is not None:
            try:
                context.detach(token)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.debug("otel_middleware: detach failed", exc_info=True)
            delattr(_tls, "otel_token")
