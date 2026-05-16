"""Tests for Semantic Scholar external tools."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from science_graphrag.agent.tools.external.semantic_scholar_tools import (
    _semantic_scholar_paper_impl,
    _semantic_scholar_search_impl,
    build_semantic_scholar_tools,
)
from science_graphrag.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        agent_external_http_timeout_seconds=15.0,
        openalex_mailto="test@example.org",
    )


def test_semantic_scholar_search_success_maps_results(settings: Settings) -> None:
    payload = {
        "data": [
            {
                "paperId": "abc123",
                "title": "Attention Is All You Need",
                "year": 2017,
                "citationCount": 90000,
                "referenceCount": 40,
                "externalIds": {"DOI": "10.5555/123"},
                "url": "https://arxiv.org/abs/1706.03762",
                "abstract": "We propose a new simple network architecture",
            }
        ]
    }
    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = payload
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.return_value = resp
        m_client.return_value = inst
        out = _semantic_scholar_search_impl("transformer", settings=settings, max_results=5)
    assert out["ok"] is True
    assert out["row_count"] == 1
    assert out["items"][0]["semantic_scholar_paper_id"] == "abc123"
    assert out["web_sources"][0]["source_tool"] == "semantic_scholar_search"


def test_semantic_scholar_search_rate_limit(settings: Settings) -> None:
    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        resp = MagicMock()
        resp.status_code = 429
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.return_value = resp
        m_client.return_value = inst
        out = _semantic_scholar_search_impl("q", settings=settings, max_results=3)
    assert out["ok"] is False
    assert out["error"] == "semantic_scholar_rate_limited"


def test_semantic_scholar_paper_not_found(settings: Settings) -> None:
    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        resp = MagicMock()
        resp.status_code = 404
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.return_value = resp
        m_client.return_value = inst
        out = _semantic_scholar_paper_impl("missing-id", settings=settings)
    assert out["ok"] is False
    assert out["detail"] == "paper_not_found"


def test_semantic_scholar_search_sends_optional_api_key_header() -> None:
    st = Settings(
        agent_external_http_timeout_seconds=15.0,
        openalex_mailto="test@example.org",
        semantic_scholar_api_key="s2-test-key",
    )
    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": []}
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.return_value = resp
        m_client.return_value = inst
        _semantic_scholar_search_impl("q", settings=st, max_results=1)
        _args, kwargs = inst.get.call_args
        headers = kwargs.get("headers") or {}
        assert headers.get("x-api-key") == "s2-test-key"


def test_semantic_scholar_search_omits_api_key_when_unset(settings: Settings) -> None:
    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"data": []}
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.return_value = resp
        m_client.return_value = inst
        _semantic_scholar_search_impl("q", settings=settings, max_results=1)
        _args, kwargs = inst.get.call_args
        headers = kwargs.get("headers") or {}
        assert "x-api-key" not in headers


def test_semantic_scholar_search_transport_failure(settings: Settings) -> None:
    import httpx

    with patch(
        "science_graphrag.agent.tools.external.semantic_scholar_tools.httpx.Client",
    ) as m_client:
        inst = MagicMock()
        inst.__enter__.return_value = inst
        inst.__exit__.return_value = False
        inst.get.side_effect = httpx.ConnectError("refused")
        m_client.return_value = inst
        out = _semantic_scholar_search_impl("q", settings=settings, max_results=3)
    assert out["ok"] is False
    assert out["error"] == "semantic_scholar_request_failed"
    assert "refused" in str(out.get("detail") or "")


def test_build_semantic_scholar_tools_registers_names(settings: Settings) -> None:
    tools = build_semantic_scholar_tools(settings)
    names = sorted({getattr(t, "name", "") for t in tools})
    assert names == ["semantic_scholar_paper", "semantic_scholar_search"]
