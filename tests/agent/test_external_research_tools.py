"""Unit tests for web research + DOI resolver helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest

from science_graphrag.agent.tools import web_research_tools as web_research_tools_mod
from science_graphrag.agent.tools.doi_resolver_tool import _doi_resolve_body
from science_graphrag.agent.tools.web_research_tools import _web_fetch_impl
from science_graphrag.config import Settings


@pytest.fixture(name="settings")
def fixture_settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_EXTRACTION_LLM_API_KEY", "test-key")
    return Settings()


def test_web_fetch_rejects_unsupported_scheme(settings: Settings) -> None:
    out = _web_fetch_impl(
        "ftp://arxiv.org/abs/1234.5678",
        "summarize",
        settings=settings,
        allowed_domains=None,
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] == "unsupported_scheme"


def test_web_fetch_cache_miss_on_different_prompt(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    """Composite cache key must not reuse summary built for another prompt."""

    class _FakeResp:
        status_code = 200
        url = "https://arxiv.org/abs/1234.5678"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"<html><body>paper</body></html>"

    class _FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def stream(self, *_args, **_kwargs):
            return _FakeResp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.web_research_tools.httpx.Client",
        _FakeClient,
    )
    calls: list[str] = []

    def _fake_invoke(_llm, msgs, **_k):
        body = str(getattr(msgs[0], "content", "") or "")
        calls.append(body)
        if "PromptA" in body:
            return SimpleNamespace(content="SummaryA")
        return SimpleNamespace(content="SummaryB")

    monkeypatch.setattr(
        "science_graphrag.agent.tools.web_research_tools.invoke_chat_gated",
        _fake_invoke,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.web_research_tools.build_chat_model",
        lambda *_a, **_k: MagicMock(),
    )
    with web_research_tools_mod._FETCH_CACHE_LOCK:
        web_research_tools_mod._FETCH_CACHE.clear()

    url = "https://arxiv.org/abs/1234.5678"
    out1 = _web_fetch_impl(
        url,
        "PromptA",
        settings=settings,
        allowed_domains=["arxiv.org"],
        blocked_domains=[],
    )
    out2 = _web_fetch_impl(
        url,
        "PromptB",
        settings=settings,
        allowed_domains=["arxiv.org"],
        blocked_domains=[],
    )
    assert out1["ok"] is True
    assert out2["ok"] is True
    assert out1.get("summary") == "SummaryA"
    assert out2.get("summary") == "SummaryB"
    assert out2.get("cache_hit") is not True
    with web_research_tools_mod._FETCH_CACHE_LOCK:
        web_research_tools_mod._FETCH_CACHE.clear()


def test_web_fetch_rejects_disallowed_redirect_host(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    class _FakeResp:
        status_code = 200
        url = "https://evil.example/paper"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def raise_for_status(self) -> None:
            return None

        def iter_bytes(self):
            yield b"hello"

    class _FakeClient:
        def __init__(self, **_kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def stream(self, *_args, **_kwargs):
            return _FakeResp()

    monkeypatch.setattr(
        "science_graphrag.agent.tools.web_research_tools.httpx.Client",
        _FakeClient,
    )
    out = _web_fetch_impl(
        "https://arxiv.org/abs/1234.5678",
        "summarize",
        settings=settings,
        allowed_domains=["arxiv.org"],
        blocked_domains=[],
    )
    assert out["ok"] is False
    assert out["error"] == "redirect_host_not_allowed"
    assert out["detail"] == "evil.example"


def test_doi_resolver_graph_match_when_workspace_misses_global_hit(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    """Global graph hit with explicit workspace must not be labeled workspace_match."""
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool.fetch_work_by_doi",
        lambda _doi, _mailto: None,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool._crossref_fallback",
        lambda _doi, _mailto, **_kw: {"doi": "10.1000/xyz", "title": "X"},
    )
    store = SimpleNamespace(
        find_work_id_by_doi_in_workspace=lambda _ws, _doi: None,
        find_work_id_by_doi=lambda _doi: "W-global",
        fetch_work_bibliography_card=lambda _wid: {
            "title": "T",
            "year": 2024,
            "doi": "10.1000/xyz",
        },
    )
    out = _doi_resolve_body(store, settings, "10.1000/xyz", "ws-missing").payload
    assert out["ok"] is True
    assert out["paper_id_in_workspace"] is None
    assert out.get("graph_work_id") == "W-global"
    assert out["metadata_source"] == "graph_match"
    assert out.get("matched_in_workspace") is False
    assert out["evidence_origin"] == "corpus_graph"


def test_doi_resolver_workspace_match_overrides_metadata_source(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool.fetch_work_by_doi",
        lambda _doi, _mailto: None,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool._crossref_fallback",
        lambda _doi, _mailto, **_kw: {"doi": "10.1000/xyz", "title": "X"},
    )
    store = SimpleNamespace(
        find_work_id_by_doi_in_workspace=lambda _ws, _doi: "W-1",
        find_work_id_by_doi=lambda _doi: None,
        fetch_work_bibliography_card=lambda _wid: {
            "title": "T",
            "year": 2024,
            "doi": "10.1000/xyz",
        },
    )
    out = _doi_resolve_body(store, settings, "https://doi.org/10.1000/xyz", "ws-1").payload
    assert out["ok"] is True
    assert out["paper_id_in_workspace"] == "W-1"
    assert out.get("graph_work_id") == "W-1"
    assert out["metadata_source"] == "workspace_match"
    assert out.get("matched_in_workspace") is True
    assert out["evidence_origin"] == "workspace_graph"


def test_doi_resolver_crossref_fallback_source_name(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool.fetch_work_by_doi",
        lambda _doi, _mailto: None,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool._crossref_fallback",
        lambda _doi, _mailto, **_kw: {"doi": "10.1000/abc", "title": "Crossref title"},
    )
    store = SimpleNamespace(
        find_work_id_by_doi_in_workspace=lambda _ws, _doi: None,
        find_work_id_by_doi=lambda _doi: None,
        fetch_work_bibliography_card=lambda _wid: None,
    )
    out = _doi_resolve_body(store, settings, "10.1000/abc", None).payload
    assert out["ok"] is True
    assert out["metadata_source"] == "crossref_fallback"


def test_doi_resolver_preserves_openalex_error_detail(
    monkeypatch: pytest.MonkeyPatch,
    settings: Settings,
) -> None:
    def _boom(_doi: str, _mailto: str):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr("science_graphrag.agent.tools.doi_resolver_tool.fetch_work_by_doi", _boom)
    monkeypatch.setattr(
        "science_graphrag.agent.tools.doi_resolver_tool._crossref_fallback",
        lambda _doi, _mailto, **_kw: None,
    )
    store = SimpleNamespace(
        find_work_id_by_doi_in_workspace=lambda _ws, _doi: None,
        find_work_id_by_doi=lambda _doi: None,
        fetch_work_bibliography_card=lambda _wid: None,
    )
    out = _doi_resolve_body(store, settings, "10.1000/def", None).payload
    assert out["ok"] is True
    assert out["metadata_source"] == "none"
    assert str(out.get("metadata_source_detail") or "").startswith("openalex_error:")
