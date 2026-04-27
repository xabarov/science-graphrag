"""Regression: extraction_llm scope keeps ingest LLM/VL/claims, drops agent spans."""

from __future__ import annotations

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability import spans as observability_spans
from science_graphrag.observability.spans.decorators import chain_span, llm_span


def test_extraction_llm_scope_allows_ingest_llm_and_vl(monkeypatch) -> None:
    monkeypatch.setenv("PHOENIX_TRACE_SCOPE", "extraction_llm")
    # Reload scope cache behavior: decorators read env at call time via is_extraction_llm_scope
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-extraction-scope")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    monkeypatch.setattr(observability_spans, "get_tracer", lambda name="science-graphrag": tracer)

    with chain_span("agent.query"):
        pass
    with chain_span("ingest_document"):
        pass
    with llm_span("llm.vl_pdf"):
        pass
    with llm_span("llm.claims_extraction"):
        pass
    with llm_span("llm.metadata_extraction"):
        pass
    with llm_span("llm.semantic_method_dataset"):
        pass
    with chain_span("ingest.extract_claims.llm"):
        pass
    with llm_span("llm.agent.writer"):
        pass

    names = {s.name for s in exporter.get_finished_spans()}
    assert "agent.query" not in names
    assert "ingest_document" in names
    assert "ingest.extract_claims.llm" in names
    assert "llm.vl_pdf" in names
    assert "llm.claims_extraction" in names
    assert "llm.metadata_extraction" in names
    assert "llm.semantic_method_dataset" in names
    assert "llm.agent.writer" not in names
