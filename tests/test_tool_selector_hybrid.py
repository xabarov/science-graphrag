"""Tests for optional LLM rerank shortlist (Epic C1) guardrails."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from science_graphrag.agent.tool_selector_hybrid import maybe_llm_rerank_shortlist
from science_graphrag.config import Settings


def _fake_tool(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def test_pre_denied_tools_not_restored_after_successful_rerank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Denied names must not reappear via merge tail after LLM rerank."""
    picked = [
        _fake_tool("workspace_inspect"),
        _fake_tool("idea_search"),
        _fake_tool("final_answer"),
    ]
    settings = MagicMock(spec=Settings)
    settings.agent_tool_search_llm_rerank_enabled = True
    settings.extraction_llm_api_key = "k"
    settings.agent_tool_search_llm_pre_denylist = ["idea_search"]
    settings.agent_tool_search_llm_rerank_max_candidates = 12
    settings.agent_tool_search_llm_rerank_timeout_seconds = 8.0
    settings.agent_tool_search_llm_rerank_max_tokens = 256

    class _Resp:
        content = '{"ranked_tools": ["final_answer", "workspace_inspect"], "confidence": 0.9, "reason_codes": ["ok"]}'

    monkeypatch.setattr(
        "science_graphrag.agent.tool_selector_hybrid.invoke_chat_gated",
        lambda *_a, **_k: _Resp(),
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tool_selector_hybrid.build_chat_model",
        lambda *_a, **_k: MagicMock(),
    )

    out, meta = maybe_llm_rerank_shortlist(
        picked,
        question="test",
        specialist="single_agent_react",
        settings=settings,
        rules_matched_tools=["workspace_inspect", "idea_search", "final_answer"],
        message_discovery_merged=[],
        carryover_merged=[],
    )
    names = [getattr(t, "name", "") for t in out]
    assert "idea_search" not in names
    assert names == ["final_answer", "workspace_inspect"]
    assert meta.get("selector_stage") == "hybrid_llm"
    assert "idea_search" in (meta.get("pre_llm_denied_tools") or [])


def test_llm_rerank_failure_returns_candidate_subset_not_full_picked(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """On LLM failure, return pre-filtered candidates in picked order, not original picked."""
    picked = [
        _fake_tool("workspace_inspect"),
        _fake_tool("idea_search"),
        _fake_tool("final_answer"),
    ]
    settings = MagicMock(spec=Settings)
    settings.agent_tool_search_llm_rerank_enabled = True
    settings.extraction_llm_api_key = "k"
    settings.agent_tool_search_llm_pre_denylist = ["idea_search"]
    settings.agent_tool_search_llm_rerank_max_candidates = 12
    settings.agent_tool_search_llm_rerank_timeout_seconds = 8.0
    settings.agent_tool_search_llm_rerank_max_tokens = 256

    def _boom(*_a, **_k):
        raise RuntimeError("llm_down")

    monkeypatch.setattr(
        "science_graphrag.agent.tool_selector_hybrid.invoke_chat_gated",
        _boom,
    )
    monkeypatch.setattr(
        "science_graphrag.agent.tool_selector_hybrid.build_chat_model",
        lambda *_a, **_k: MagicMock(),
    )

    out, meta = maybe_llm_rerank_shortlist(
        picked,
        question="test",
        specialist="single_agent_react",
        settings=settings,
        rules_matched_tools=["workspace_inspect", "idea_search", "final_answer"],
        message_discovery_merged=[],
        carryover_merged=[],
    )
    names = [getattr(t, "name", "") for t in out]
    assert names == ["workspace_inspect", "final_answer"]
    assert "idea_search" not in names
    assert meta.get("selector_stage") == "rules_fallback"


def test_empty_candidates_returns_empty_without_final_answer() -> None:
    """When every picked tool is pre-denylisted and there is no final_answer, return []."""
    picked = [_fake_tool("idea_search")]
    settings = MagicMock(spec=Settings)
    settings.agent_tool_search_llm_rerank_enabled = True
    settings.extraction_llm_api_key = "k"
    settings.agent_tool_search_llm_pre_denylist = ["idea_search"]
    settings.agent_tool_search_llm_rerank_max_candidates = 12
    settings.agent_tool_search_llm_rerank_timeout_seconds = 8.0
    settings.agent_tool_search_llm_rerank_max_tokens = 256

    out, meta = maybe_llm_rerank_shortlist(
        picked,
        question="q",
        specialist="single_agent_react",
        settings=settings,
        rules_matched_tools=["idea_search"],
        message_discovery_merged=[],
        carryover_merged=[],
    )
    assert out == []
    assert meta.get("selector_reason_codes") == ["llm_rerank_skipped_empty_candidates"]


def test_empty_candidates_keeps_final_answer_escape_hatch() -> None:
    """If every tool is pre-denylisted, still return final_answer from picked when present."""
    picked = [_fake_tool("idea_search"), _fake_tool("final_answer")]
    settings = MagicMock(spec=Settings)
    settings.agent_tool_search_llm_rerank_enabled = True
    settings.extraction_llm_api_key = "k"
    settings.agent_tool_search_llm_pre_denylist = ["idea_search", "final_answer"]
    settings.agent_tool_search_llm_rerank_max_candidates = 12
    settings.agent_tool_search_llm_rerank_timeout_seconds = 8.0
    settings.agent_tool_search_llm_rerank_max_tokens = 256

    out, meta = maybe_llm_rerank_shortlist(
        picked,
        question="q",
        specialist="single_agent_react",
        settings=settings,
        rules_matched_tools=["idea_search", "final_answer"],
        message_discovery_merged=[],
        carryover_merged=[],
    )
    assert [getattr(t, "name", "") for t in out] == ["final_answer"]
    assert meta.get("selector_reason_codes") == ["llm_rerank_skipped_empty_candidates"]


def test_no_api_key_still_applies_pre_deny_filter() -> None:
    """No API key should skip LLM but still return pre-filtered candidates."""
    picked = [
        _fake_tool("workspace_inspect"),
        _fake_tool("idea_search"),
        _fake_tool("final_answer"),
    ]
    settings = MagicMock(spec=Settings)
    settings.agent_tool_search_llm_rerank_enabled = True
    settings.extraction_llm_api_key = ""
    settings.agent_tool_search_llm_pre_denylist = ["idea_search"]
    settings.agent_tool_search_llm_rerank_max_candidates = 12
    settings.agent_tool_search_llm_rerank_timeout_seconds = 8.0
    settings.agent_tool_search_llm_rerank_max_tokens = 256

    out, meta = maybe_llm_rerank_shortlist(
        picked,
        question="q",
        specialist="single_agent_react",
        settings=settings,
        rules_matched_tools=["workspace_inspect", "idea_search", "final_answer"],
        message_discovery_merged=[],
        carryover_merged=[],
    )
    assert [getattr(t, "name", "") for t in out] == ["workspace_inspect", "final_answer"]
    assert meta.get("selector_reason_codes") == ["llm_rerank_skipped_no_api_key"]
    assert "idea_search" in (meta.get("pre_llm_denied_tools") or [])
