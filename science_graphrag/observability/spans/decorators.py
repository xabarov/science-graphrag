from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
from typing import Any, Iterator

from opentelemetry import trace as trace_api
from opentelemetry.trace import SpanKind, Status, StatusCode, Tracer

from science_graphrag.observability.init import init_tracer_provider
from science_graphrag.observability.scope import (
    _EXTRACTION_LLM_CHAIN_NAMES,
    _EXTRACTION_LLM_MANUAL_LLM_NAMES,
    is_extraction_llm_scope,
)

MIME_TYPE_TEXT = "text/plain"
MIME_TYPE_JSON = "application/json"
DEFAULT_SPAN_PAYLOAD_LIMIT = 4000


def _runtime_tracer(name: str = "science-graphrag") -> Tracer:
    # Keep monkeypatch compatibility for tests patching package-level get_tracer.
    from science_graphrag.observability import spans as spans_module

    return spans_module.get_tracer(name)


class SpanKindOI:
    """OpenInference span kinds for Phoenix UI."""

    LLM = "LLM"
    CHAIN = "CHAIN"
    RETRIEVER = "RETRIEVER"
    TOOL = "TOOL"
    EMBEDDING = "EMBEDDING"


class OpenInferenceAttributes:
    """OpenInference semantic convention attribute keys used by this project."""

    SPAN_KIND = "openinference.span.kind"
    INPUT_VALUE = "input.value"
    INPUT_MIME_TYPE = "input.mime_type"
    OUTPUT_VALUE = "output.value"
    OUTPUT_MIME_TYPE = "output.mime_type"
    SESSION_ID = "session.id"
    USER_ID = "user.id"


@contextmanager
def _noop_span_context() -> Iterator[None]:
    yield None


def add_span_event(name: str, attributes: dict[str, Any] | None = None) -> None:
    span = trace_api.get_current_span()
    if span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_attribute(key: str, value: Any) -> None:
    span = trace_api.get_current_span()
    if span.is_recording() and value is not None and value != "":
        span.set_attribute(key, value)


def set_span_attributes(attributes: dict[str, Any]) -> None:
    for key, value in attributes.items():
        set_span_attribute(key, value)


def set_span_error(exception: BaseException) -> None:
    span = trace_api.get_current_span()
    if span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(exception)))
        span.record_exception(exception)


@lru_cache(maxsize=8)
def get_tracer(name: str = "science-graphrag") -> Tracer:
    init_tracer_provider()
    return trace_api.get_tracer(name)


@contextmanager
def chain_span(name: str, attributes: dict[str, Any] | None = None):
    if is_extraction_llm_scope() and name not in _EXTRACTION_LLM_CHAIN_NAMES:
        with _noop_span_context():
            yield None
        return
    with _runtime_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.CHAIN)
        if attributes:
            set_span_attributes(attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def llm_span(name: str, attributes: dict[str, Any] | None = None):
    if is_extraction_llm_scope() and name not in _EXTRACTION_LLM_MANUAL_LLM_NAMES:
        with _noop_span_context():
            yield None
        return
    with _runtime_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.LLM)
        if attributes:
            set_span_attributes(attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def embeddings_span(name: str, attributes: dict[str, Any] | None = None):
    with _runtime_tracer().start_as_current_span(name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.EMBEDDING)
        if attributes:
            set_span_attributes(attributes)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def traced_tool_span(
    name: str,
    *,
    tool_name: str,
    tool_type: str = "tool",
    tool_parameters: dict[str, Any] | list[Any] | str | None = None,
    tool_description: str | None = None,
):
    from science_graphrag.observability.spans.attributes import SpanAttributes

    with _runtime_tracer().start_as_current_span(name) as span:
        span.set_attribute(OpenInferenceAttributes.SPAN_KIND, SpanKindOI.TOOL)
        SpanAttributes.set_tool_attrs(
            tool_name,
            tool_type=tool_type,
            tool_description=tool_description,
        )
        if tool_parameters is not None:
            SpanAttributes.set_tool_parameters(tool_parameters)
            SpanAttributes.set_input(tool_parameters, mime_type=MIME_TYPE_JSON)
        try:
            yield span
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise
