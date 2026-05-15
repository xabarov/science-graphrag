"""Unit tests for arXiv Atom API tools (no network by default)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from science_graphrag.agent.tools.arxiv_tools import (
    _arxiv_fetch_impl,
    _arxiv_search_impl,
    _build_search_query,
    _resolve_arxiv_id_from_user_input,
    build_arxiv_tools,
)
from science_graphrag.config import Settings

_ATOM_ONE_ENTRY = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2301.07012v1</id>
    <title>Example Paper Title</title>
    <summary>  This is the abstract.  </summary>
    <published>2023-01-17T00:00:00-05:00</published>
    <updated>2023-01-18T00:00:00-05:00</updated>
    <author><name>Alice Researcher</name></author>
    <author><name>Bob Scientist</name></author>
    <arxiv:doi>10.1234/example.doi</arxiv:doi>
    <category term="cs.CV" scheme="http://arxiv.org/schemas/atom"/>
    <link rel="alternate" type="text/html" href="https://arxiv.org/abs/2301.07012v1"/>
    <link rel="related" type="application/pdf" href="https://arxiv.org/pdf/2301.07012v1.pdf"/>
  </entry>
</feed>
"""


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code),
            )


class _FakeClient:
    def __init__(self, response_body: str, status_code: int = 200) -> None:
        self._body = response_body
        self._status = status_code

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def get(self, *_a: object, **_k: object) -> _FakeResponse:
        return _FakeResponse(self._body, status_code=self._status)


@pytest.fixture
def settings() -> Settings:
    return Settings.model_construct(agent_web_search_http_timeout_seconds=5.0)


def test_build_search_query_categories_and_dates() -> None:
    q, err = _build_search_query(
        "object detection",
        categories=["cs.CV", "cs.LG"],
        date_from="2020-01-01",
        date_to="2020-12-31",
    )
    assert err is None
    assert q is not None
    assert 'all:"object detection"' in q
    assert "+AND+(cat:cs.CV+OR+cat:cs.LG)" in q
    assert "+AND+submittedDate:[202001010000+TO+202012312359]" in q


def test_build_search_query_invalid_date() -> None:
    q, err = _build_search_query("x", categories=None, date_from="not-a-date", date_to=None)
    assert q is None
    assert err == "invalid_date_range"


def test_resolve_arxiv_id_variants() -> None:
    assert _resolve_arxiv_id_from_user_input("https://arxiv.org/abs/2301.07012")[0] == "2301.07012"
    assert (
        _resolve_arxiv_id_from_user_input("https://arxiv.org/pdf/2301.07012.pdf")[0] == "2301.07012"
    )
    assert _resolve_arxiv_id_from_user_input("arxiv: 2301.07012v2")[0] == "2301.07012v2"
    assert _resolve_arxiv_id_from_user_input("2301.07012")[0] == "2301.07012"
    assert _resolve_arxiv_id_from_user_input("nope")[0] is None


def test_arxiv_search_impl_parses_feed(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    def _client(*_a: object, **_k: object) -> _FakeClient:
        return _FakeClient(_ATOM_ONE_ENTRY)

    monkeypatch.setattr("science_graphrag.agent.tools.arxiv_tools.httpx.Client", _client)
    out = _arxiv_search_impl(
        "object detection",
        settings=settings,
        max_results=3,
        categories=None,
        date_from=None,
        date_to=None,
    )
    assert out["ok"] is True
    assert out["row_count"] == 1
    assert out["items"][0]["arxiv_id"] == "2301.07012v1"
    assert out["items"][0]["title"] == "Example Paper Title"
    assert out["items"][0]["doi"] == "10.1234/example.doi"
    assert out["evidence_origin"] == "external_web"
    assert len(out["web_sources"]) == 1
    assert out["web_sources"][0]["source_tool"] == "arxiv_search"
    assert "arxiv.org/abs" in out["web_sources"][0]["url"]


def test_arxiv_fetch_impl_unsupported_pdf(settings: Settings) -> None:
    out = _arxiv_fetch_impl(
        "2301.07012",
        settings=settings,
        include_pdf_text=True,
    )
    assert out["ok"] is False
    assert out["error"] == "unsupported_pdf_text"


def test_arxiv_fetch_impl_by_id(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    def _client(*_a: object, **_k: object) -> _FakeClient:
        return _FakeClient(_ATOM_ONE_ENTRY)

    monkeypatch.setattr("science_graphrag.agent.tools.arxiv_tools.httpx.Client", _client)
    out = _arxiv_fetch_impl("2301.07012", settings=settings, include_pdf_text=False)
    assert out["ok"] is True
    assert out["row_count"] == 1
    assert out["item"]["arxiv_id"] == "2301.07012v1"
    assert out["web_sources"][0]["source_tool"] == "arxiv_fetch"


def test_arxiv_fetch_empty_feed(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = """<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom"></feed>"""

    def _client(*_a: object, **_k: object) -> _FakeClient:
        return _FakeClient(empty)

    monkeypatch.setattr("science_graphrag.agent.tools.arxiv_tools.httpx.Client", _client)
    out = _arxiv_fetch_impl("2301.07012", settings=settings, include_pdf_text=False)
    assert out["ok"] is True
    assert out["row_count"] == 0
    assert out["item"] is None


def test_build_arxiv_tools_registers_names(settings: Settings) -> None:
    tools = build_arxiv_tools(settings=settings)
    names = [getattr(t, "name", "") for t in tools]
    assert names == ["arxiv_search", "arxiv_fetch"]
