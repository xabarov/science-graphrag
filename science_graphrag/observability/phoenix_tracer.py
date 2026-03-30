"""
Minimal Phoenix / OpenTelemetry init for science-graphrag (aligned with osint-gr patterns).
"""

from __future__ import annotations

import os
import socket
from contextlib import contextmanager
from functools import lru_cache
from typing import Any

from opentelemetry import trace as trace_api
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer
from phoenix.otel import register


class SpanKindOI:
    """OpenInference span kinds for Phoenix UI."""

    LLM = "LLM"
    CHAIN = "CHAIN"
    RETRIEVER = "RETRIEVER"
    TOOL = "TOOL"


class OpenInferenceAttributes:
    SPAN_KIND = "openinference.span.kind"
    INPUT_VALUE = "input.value"
    OUTPUT_VALUE = "output.value"


@lru_cache(maxsize=1)
def init_tracer_provider() -> None:
    """Initialize Phoenix tracer provider once per process."""
    endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    project_name = os.getenv("PHOENIX_PROJECT_NAME", "science-graphrag")
    api_key = os.getenv("PHOENIX_API_KEY") or None

    if endpoint:
        if "phoenix" in endpoint:
            try:
                socket.getaddrinfo("phoenix", 6006)
            except OSError:
                endpoint = endpoint.replace("phoenix", "localhost")

        normalized = endpoint.rstrip("/")
        if normalized.endswith(":6006"):
            endpoint = f"{normalized}/v1/traces"

    batch = os.getenv("ENV", "dev").lower() not in {"dev", "local", "test"}

    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    register(
        project_name=project_name,
        endpoint=endpoint,
        batch=batch,
        headers=headers or None,
    )
    _register_optional_openai_instrumentation()


@lru_cache(maxsize=1)
def _register_optional_openai_instrumentation() -> None:
    if os.getenv("PHOENIX_OPENAI_AUTO_INSTRUMENTATION", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return
    try:
        from openinference.instrumentation.openai import OpenAIInstrumentor
    except Exception:
        return
    try:
        OpenAIInstrumentor().instrument()
    except Exception:
        return


@lru_cache(maxsize=8)
def get_tracer(name: str = "science-graphrag") -> Tracer:
    """OpenTelemetry tracer bound to Phoenix exporter."""
    init_tracer_provider()
    return trace_api.get_tracer(name)


@contextmanager
def chain_span(name: str, attributes: dict[str, Any] | None = None):
    """CHAIN-style span for phase grouping in Phoenix."""
    with get_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.CHAIN)
        if attributes:
            for key, value in attributes.items():
                if value is not None and value != "":
                    span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def llm_span(name: str, attributes: dict[str, Any] | None = None):
    """LLM-style span (VL / chat completions)."""
    with get_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.LLM)
        if attributes:
            for key, value in attributes.items():
                if value is not None and value != "":
                    span.set_attribute(key, value)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
