"""Unit tests for external PDF read tool (bounded fetch/extract/cache)."""

from __future__ import annotations

from io import BytesIO

import pytest
from pypdf import PdfWriter

from science_graphrag.agent.tools.external.pdf_read_orchestrator import execute_pdf_read
from science_graphrag.agent.tools.external.pdf_read_tools import build_pdf_read_tools
from science_graphrag.config import Settings


def _build_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.fixture(name="settings")
def fixture_settings() -> Settings:
    return Settings.model_construct(
        agent_external_http_timeout_seconds=5.0,
        agent_pdf_read_max_bytes=8_000_000,
        agent_pdf_read_max_pages=30,
        agent_pdf_read_cache_ttl_seconds=60,
        agent_pdf_read_cache_max_entries=256,
        agent_pdf_read_backend_mode="pypdf",
    )


def test_build_pdf_read_tools_registers_name(settings: Settings) -> None:
    tools = build_pdf_read_tools(settings=settings)
    assert [getattr(t, "name", "") for t in tools] == ["read_external_pdf"]


def test_read_external_pdf_rejects_non_https(settings: Settings) -> None:
    out = execute_pdf_read(
        "http://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] == "unsupported_scheme"
    assert str(out.get("artifact_id") or "").startswith("sg-pdf-")


def test_read_external_pdf_fetch_failure(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            raise OSError("network down")

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] == "fetch_failed"


def test_read_external_pdf_too_large(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    class _Resp:
        status_code = 200
        url = "https://example.org/paper.pdf"
        content = b"x" * 9_000_000

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] == "pdf_too_large"


def test_read_external_pdf_parse_failed(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Resp:
        status_code = 200
        url = "https://example.org/paper.pdf"
        content = b"not-a-pdf"

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] == "pdf_parse_failed"


def test_read_external_pdf_page_limit(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    pdf_bytes = _build_pdf_bytes()
    limited = settings.model_copy(update={"agent_pdf_read_max_pages": 1})

    class _Resp:
        status_code = 200
        url = "https://example.org/paper.pdf"
        content = pdf_bytes

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=limited,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] in {"pdf_page_limit", "pdf_parse_failed"}


def test_read_external_pdf_private_host_not_allowed(settings: Settings) -> None:
    out = execute_pdf_read(
        "https://localhost/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is False
    assert out["error"] == "private_host_not_allowed"


def test_read_external_pdf_success_includes_read_backend(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_bytes = _build_pdf_bytes()

    class _Resp:
        status_code = 200
        url = "https://example.org/paper.pdf"
        content = pdf_bytes

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_orchestrator.extract_pdf_text",
        lambda *_a, **_k: ("Introduction. " * 40, 1, 1),
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is True
    assert out["read_backend"] == "pypdf"
    assert out["fallback_used"] is False


def test_hybrid_falls_back_to_vl_on_short_pypdf(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    pdf_bytes = _build_pdf_bytes()
    st = Settings.model_construct(
        agent_external_http_timeout_seconds=5.0,
        agent_pdf_read_max_bytes=8_000_000,
        agent_pdf_read_max_pages=30,
        agent_pdf_read_cache_ttl_seconds=60,
        agent_pdf_read_cache_max_entries=256,
        agent_pdf_read_backend_mode="hybrid",
        vl_api_key="sk-vl-test",
    )

    class _Resp:
        status_code = 200
        url = "https://example.org/paper.pdf"
        content = pdf_bytes

        def raise_for_status(self) -> None:
            return None

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, *_a, **_k):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_pipeline.httpx.Client",
        lambda *_a, **_k: _Client(),
    )

    def _short_pypdf(
        _content: bytes,
        *,
        max_pages: int,
        max_excerpt_chars: int,
    ) -> tuple[str, int, int]:
        return ("short", 1, 1)

    def _vl_ok(
        _content: bytes,
        *,
        settings: Settings,
        max_pages: int,
        max_excerpt_chars: int,
        total_pages_hint: int,
    ) -> tuple[str, int, int]:
        _ = settings
        text = "x" * 400
        return text[:max_excerpt_chars], 1, total_pages_hint

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_orchestrator._pypdf_extract",
        _short_pypdf,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.pdf_read_orchestrator._vl_markdown_excerpt",
        _vl_ok,
    )
    out = execute_pdf_read(
        "https://example.org/paper.pdf",
        settings=st,
        max_excerpt_chars=2000,
    )
    assert out["ok"] is True
    assert out["read_backend"] == "vl"
    assert out["fallback_used"] is True
