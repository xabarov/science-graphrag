"""Backward-compatible observability re-export module."""

# Backward-compat re-export. Do not add logic here.
from science_graphrag.observability import (  # noqa: F401
    _EXTRACTION_LLM_CHAIN_NAMES,
    PHOENIX_TRACE_SCOPE,
    OpenInferenceAttributes,
    SpanAttributes,
    add_span_event,
    chain_span,
    embeddings_span,
    get_tracer,
    init_tracer_provider,
    llm_span,
    phoenix_trace_scope,
    set_span_attribute,
    set_span_attributes,
    set_span_error,
    traced_tool_span,
)
