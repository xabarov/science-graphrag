"""OpenTelemetry trace context for Dramatiq message options (producer-side inject)."""

from __future__ import annotations

import logging
from typing import Any

from opentelemetry import propagate

logger = logging.getLogger(__name__)


def dramatiq_otel_options() -> dict[str, Any]:
    """Build Dramatiq ``options`` entries carrying W3C trace context for the worker."""
    carrier: dict[str, str] = {}
    try:
        propagate.inject(carrier)
    except Exception:  # pylint: disable=broad-exception-caught
        logger.debug("dramatiq_otel_options: inject failed", exc_info=True)
        return {}
    return {k: v for k, v in carrier.items() if v}
