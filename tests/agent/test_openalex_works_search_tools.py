"""Tests for OpenAlex works search tool."""

from __future__ import annotations

import pytest

from science_graphrag.agent.tools.external.openalex_works_search_tools import (
    _openalex_works_search_impl,
)
from science_graphrag.config import Settings


@pytest.fixture(name="settings")
def fixture_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "test-key")
    return Settings(openalex_mailto="test@example.com")


def test_openalex_works_search_success_maps_results(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample = {
        "results": [
            {
                "id": "https://openalex.org/W123",
                "display_name": "Example Paper",
                "publication_year": 2021,
                "doi": "https://doi.org/10.1234/ex",
                "abstract_inverted_index": {"Hello": [0], "world": [1]},
            }
        ],
        "meta": {"count": 1},
    }

    class _Resp:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return sample

    class _Client:
        def __init__(self, *_a, **_k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def get(self, _url, **_kwargs):
            return _Resp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.external.openalex_works_search_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _openalex_works_search_impl(
        "machine learning",
        settings=settings,
        from_year=2020,
        to_year=2022,
        max_results=5,
    )
    assert out["ok"] is True
    assert out["row_count"] == 1
    assert len(out["web_sources"]) == 1
    assert out["web_sources"][0]["source_tool"] == "openalex_works_search"
    assert out["web_sources"][0]["provenance_kind"] == "openalex_metadata"
    assert out["items"][0]["doi"] == "10.1234/ex"


def test_openalex_works_search_http_error(
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
        "science_graphrag.agent.tools.external.openalex_works_search_tools.httpx.Client",
        lambda *_a, **_k: _Client(),
    )
    out = _openalex_works_search_impl(
        "q", settings=settings, from_year=None, to_year=None, max_results=3
    )
    assert out["ok"] is False
    assert out["error"] == "openalex_works_search_failed"
    assert out["row_count"] == 0


def test_build_openalex_tools_returns_named_tool(settings: Settings) -> None:
    from science_graphrag.agent.tools.external.openalex_works_search_tools import (
        build_openalex_works_search_tools,
    )

    tools = build_openalex_works_search_tools(settings)
    assert len(tools) == 1
    assert getattr(tools[0], "name", "") == "openalex_works_search"
