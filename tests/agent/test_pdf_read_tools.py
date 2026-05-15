"""Unit tests for external PDF read tool (bounded fetch/extract/cache)."""

from __future__ import annotations

from io import BytesIO

import httpx
import pytest
from pypdf import PdfWriter

from science_graphrag.agent.tools.external.pdf_read_tools import (
    _read_external_pdf_impl,
    build_pdf_read_tools,
)
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
    )


def test_build_pdf_read_tools_registers_name(settings: Settings) -> None:
    tools = build_pdf_read_tools(settings=settings)
    assert [getattr(t, "name", "") for t in tools] == ["read_external_pdf"]


def test_read_external_pdf_rejects_non_https(settings: Settings) -> None:
    out = _read_external_pdf_impl(
        "http://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] == "unsupported_scheme"


def test_read_external_pdf_respects_blocked_domains(settings: Settings) -> None:
    out = _read_external_pdf_impl(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=["example.org"],
    )
    assert out["ok"] is False
    assert out["error"] == "host_not_allowed"


def test_read_external_pdf_fetch_failure(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "science_graphrag.agent.tools.external.pdf_read_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _read_external_pdf_impl(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
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
        "science_graphrag.agent.tools.external.pdf_read_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _read_external_pdf_impl(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] == "pdf_too_large"


def test_read_external_pdf_parse_failed(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
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
        "science_graphrag.agent.tools.external.pdf_read_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _read_external_pdf_impl(
        "https://example.org/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
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
        "science_graphrag.agent.tools.external.pdf_read_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _read_external_pdf_impl(
        "https://example.org/paper.pdf",
        settings=limited,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] in {"pdf_page_limit", "pdf_parse_failed"}


def test_read_external_pdf_private_host_not_allowed(settings: Settings) -> None:
    out = _read_external_pdf_impl(
        "https://localhost/paper.pdf",
        settings=settings,
        max_excerpt_chars=2000,
        allowed_domains=None,
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] == "private_host_not_allowed"
