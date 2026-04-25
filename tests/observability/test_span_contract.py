from __future__ import annotations

from pathlib import Path

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from science_graphrag.config import Settings
from science_graphrag.ingestion.vl_pdf import VLPDFProcessor
from science_graphrag.observability import phoenix_tracer
from science_graphrag.observability.phoenix_tracer import SpanAttributes, chain_span


class _FakeResponse:
    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return {
            "choices": [{"message": {"content": "# Title\n\nBody"}}],
            "usage": {"prompt_tokens": 13, "completion_tokens": 21, "total_tokens": 34},
        }


class _FakeClient:
    def __init__(self, *_args, **_kwargs) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        return None

    def post(self, *_args, **_kwargs) -> _FakeResponse:
        return _FakeResponse()


def _span_fixture(monkeypatch):
    monkeypatch.setenv("PHOENIX_TRACE_SCOPE", "full")
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test-phoenix")
    monkeypatch.setattr(phoenix_tracer, "get_tracer", lambda name="science-graphrag": tracer)
    return exporter


def test_vl_llm_span_has_model_and_token_contract(monkeypatch) -> None:
    exporter = _span_fixture(monkeypatch)
    monkeypatch.setattr("science_graphrag.ingestion.vl_pdf.httpx.Client", _FakeClient)
    monkeypatch.setattr(
        VLPDFProcessor, "_pdf_pages", lambda self, _p: [object(), object()]
    )  # noqa: ARG005
    monkeypatch.setattr(
        VLPDFProcessor, "_image_to_data_url", lambda *_a, **_k: "data:image/png;base64,xx"
    )

    settings = Settings(vl_api_key="k", use_vl_for_pdf=True)
    markdown = VLPDFProcessor(settings).pdf_to_markdown(Path("dummy.pdf"))

    assert markdown.startswith("# Title")
    spans = exporter.get_finished_spans()
    llm_spans = [s for s in spans if s.name == "llm.vl_pdf"]
    assert len(llm_spans) == 1
    attrs = llm_spans[0].attributes
    assert attrs["llm.model_name"] == settings.vl_model
    assert attrs["llm.token_count.prompt"] == 13
    assert attrs["llm.token_count.completion"] == 21
    assert attrs["llm.token_count.total"] == 34


def test_chain_span_does_not_receive_llm_attrs(monkeypatch) -> None:
    exporter = _span_fixture(monkeypatch)
    with chain_span("ingest.test.chain"):
        SpanAttributes.set_input({"ok": True})
        SpanAttributes.set_output({"ok": True})

    spans = exporter.get_finished_spans()
    chain = [s for s in spans if s.name == "ingest.test.chain"][0]
    llm_keys = [k for k in chain.attributes.keys() if str(k).startswith("llm.")]
    assert llm_keys == []
