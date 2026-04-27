"""Deterministic Phoenix span shape checks for agent tooling (no live Phoenix)."""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from science_graphrag.agent.tools.base import ToolResult, run_tool_result_with_span
from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability import spans as observability_spans
from science_graphrag.observability.spans import SpanAttributes, chain_span
from science_graphrag.observability.spans.decorators import embeddings_span, retriever_span


def _span_fixture(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    monkeypatch.setenv("PHOENIX_TRACE_SCOPE", "full")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-agent-spans")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    monkeypatch.setattr(observability_spans, "get_tracer", lambda name="science-graphrag": tracer)
    return exporter


def test_agent_query_tree_tool_embedding_retriever(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter = _span_fixture(monkeypatch)
    with chain_span("agent.query", {"user.id": "ws-1"}):
        with embeddings_span("embedding.agent.idea_search"):
            SpanAttributes.set_embedding_agent_attrs("test-model", dim=4, input_count=1)
        with retriever_span("retrieval.qdrant.idea_search"):
            SpanAttributes.set_retrieval_qdrant_context(
                collection_name="chunks", top_k=3, workspace_id="ws-1"
            )
        run_tool_result_with_span(
            tool_name="idea_search",
            tool_parameters={"query": "q", "top_k": 3},
            fn=lambda: ToolResult(payload={"items": []}, row_count=0),
        )

    names = [s.name for s in exporter.get_finished_spans()]
    assert "agent.query" in names
    assert "embedding.agent.idea_search" in names
    assert "retrieval.qdrant.idea_search" in names
    assert "tool.idea_search" in names


def test_chain_span_has_no_llm_token_attrs(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter = _span_fixture(monkeypatch)
    with chain_span("agent.query", {}):
        SpanAttributes.set_output({"ok": True})

    spans = exporter.get_finished_spans()
    root = [s for s in spans if s.name == "agent.query"][0]
    llm_keys = [k for k in root.attributes.keys() if str(k).startswith("llm.")]
    assert llm_keys == []


def test_tool_span_error_on_failed_body(monkeypatch: pytest.MonkeyPatch) -> None:
    exporter = _span_fixture(monkeypatch)

    def boom() -> ToolResult:
        raise ValueError("tool_failed")

    with pytest.raises(ValueError, match="tool_failed"):
        run_tool_result_with_span(
            tool_name="cypher_query",
            tool_parameters={"query": "RETURN 1"},
            fn=boom,
        )

    tool_spans = [s for s in exporter.get_finished_spans() if s.name == "tool.cypher_query"]
    assert len(tool_spans) == 1
    assert str(tool_spans[0].status.status_code.name) == "ERROR"
