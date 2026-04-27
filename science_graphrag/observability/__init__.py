"""Observability helpers (Phoenix / OpenTelemetry)."""

from science_graphrag.observability.init import init_tracer_provider
from science_graphrag.observability.scope import (
    _EXTRACTION_LLM_CHAIN_NAMES,
    PHOENIX_TRACE_SCOPE,
    phoenix_trace_scope,
)
from science_graphrag.observability.spans import (
    OpenInferenceAttributes,
    SpanAttributes,
    add_span_event,
    chain_span,
    embeddings_span,
    get_tracer,
    llm_span,
    retriever_span,
    set_span_attribute,
    set_span_attributes,
    set_span_error,
    traced_tool_span,
)

__all__ = [
    "PHOENIX_TRACE_SCOPE",
    "OpenInferenceAttributes",
    "SpanAttributes",
    "_EXTRACTION_LLM_CHAIN_NAMES",
    "add_span_event",
    "chain_span",
    "embeddings_span",
    "get_tracer",
    "init_tracer_provider",
    "llm_span",
    "phoenix_trace_scope",
    "retriever_span",
    "set_span_attribute",
    "set_span_attributes",
    "set_span_error",
    "traced_tool_span",
]
