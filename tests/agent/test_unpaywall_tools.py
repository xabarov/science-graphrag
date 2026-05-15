"""Unit tests for Unpaywall OA lookup tool (no network by default)."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from science_graphrag.agent.tools.external import build_external_research_tools
from science_graphrag.agent.tools.external.unpaywall_tools import (
    _unpaywall_lookup_impl,
    build_unpaywall_tools,
)
from science_graphrag.config import Settings

_JSON_OA = (
    '{"doi":"10.1038/nature12373","title":"T","is_oa":true,"oa_status":"gold",'
    '"best_oa_location":{"url":"https://example.org/article","url_for_pdf":"https://example.org/a.pdf",'
    '"license":"cc-by"}}'
)


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def json(self) -> object:
        import json

        return json.loads(self.text)

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "err",
                request=MagicMock(),
                response=MagicMock(status_code=self.status_code),
            )


class _FakeClient:
    def __init__(self, body: str, status_code: int = 200) -> None:
        self._body = body
        self._status = status_code

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, *_a: object) -> None:
        return None

    def get(self, *_a: object, **_k: object) -> _FakeResponse:
        return _FakeResponse(self._body, status_code=self._status)


@pytest.fixture
def settings() -> Settings:
    return Settings.model_construct(
        agent_web_search_http_timeout_seconds=5.0,
        agent_unpaywall_http_timeout_seconds=5.0,
        openalex_mailto="ops@example.com",
    )


def test_unpaywall_lookup_invalid_doi(settings: Settings) -> None:
    out = _unpaywall_lookup_impl("not-a-doi", settings=settings)
    assert out["ok"] is False
    assert out["error"] == "invalid_doi"


def test_unpaywall_lookup_success(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    def _client(*_a: object, **_k: object) -> _FakeClient:
        return _FakeClient(_JSON_OA)

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.unpaywall_tools.httpx.Client",
        _client,
    )
    out = _unpaywall_lookup_impl("10.1038/nature12373", settings=settings)
    assert out["ok"] is True
    assert out["normalized_doi"] == "10.1038/nature12373"
    assert out["item"]["is_oa"] is True
    assert out["item"]["oa_pdf_url"] == "https://example.org/a.pdf"
    assert out["web_sources"][0]["source_tool"] == "unpaywall_lookup"
    assert out["evidence_origin"] == "external_web"


def test_build_unpaywall_tools_registers_name(settings: Settings) -> None:
    tools = build_unpaywall_tools(settings=settings)
    assert [getattr(t, "name", "") for t in tools] == ["unpaywall_lookup"]


def test_build_external_research_tools_respects_unpaywall_flag(settings: Settings) -> None:
    off = Settings.model_construct(
        agent_unpaywall_oa_tool_enabled=False,
        agent_web_search_http_timeout_seconds=5.0,
    )
    names_off = {getattr(t, "name", "") for t in build_external_research_tools(settings=off)}
    assert "unpaywall_lookup" not in names_off
    names_on = {getattr(t, "name", "") for t in build_external_research_tools(settings=settings)}
    assert "unpaywall_lookup" in names_on
