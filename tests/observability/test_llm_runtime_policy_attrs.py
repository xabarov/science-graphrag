"""Phase 0: LLM runtime policy span attributes."""

from __future__ import annotations

from typing import Any

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel

from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability import spans as observability_spans
from science_graphrag.observability.spans.attributes import SpanAttributes


def test_llm_runtime_policy_attributes() -> None:
    attrs = SpanAttributes.llm_runtime_policy_attributes(
        pool_name="metadata",
        transport_timeout_seconds=180.0,
        timeout_contract="transport_only",
        retry_extra_budget=2,
        operation_deadline_seconds=300.0,
        response_deadline_seconds=60.0,
        transport_max_attempts=3,
    )
    assert attrs["llm.pool_name"] == "metadata"
    assert attrs["llm.transport_timeout_seconds"] == 180.0
    assert attrs["llm.timeout_contract"] == "transport_only"
    assert attrs["llm.retry_budget"] == 2
    assert attrs["llm.operation_deadline_seconds"] == 300.0
    assert attrs["llm.response_deadline_seconds"] == 60.0
    assert attrs["llm.transport_max_attempts"] == 3


class _DummySchema(BaseModel):
    x: int = 1


class _FakeExtractor:
    """Minimal stand-in for ``SyncInstructorExtractor`` in span attribute tests."""

    transport_timeout_seconds = 200.0
    model = "test/model"
    temperature = 0.0
    max_tokens = 16
    base_url = "https://example.test/v1"

    def extract_maybe(
        self,
        response_model: type[BaseModel],
        *,
        system: str,
        user: str,
    ) -> tuple[Any, str | None]:
        return _DummySchema(), None


def test_run_extraction_span_uses_extractor_transport_timeout(monkeypatch) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-runtime-policy")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    monkeypatch.setattr(observability_spans, "get_tracer", lambda name="science-graphrag": tracer)

    ext = _FakeExtractor()
    parsed, err = run_extraction(
        ext,
        "hi",
        _DummySchema,
        stage_name="metadata_extraction",
        document_id="doc-1",
        pool_name="metadata",
        timeout_seconds=60.0,
        retries=0,
    )
    assert parsed is not None and err is None
    spans = exporter.get_finished_spans()
    llm_spans = [s for s in spans if s.name == "llm.metadata_extraction"]
    assert len(llm_spans) == 1
    attrs = dict(llm_spans[0].attributes or {})
    assert attrs.get("extraction.timeout_seconds") == 200.0
    assert attrs.get("llm.transport_timeout_seconds") == 200.0
    assert attrs.get("llm.pool_name") == "metadata"
    assert attrs.get("llm.timeout_contract") == "transport_only"
    assert attrs.get("llm.retry_budget") == 0
