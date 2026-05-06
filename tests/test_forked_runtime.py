"""Tests for cache-side LLM fork telemetry (§10.2)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from science_graphrag.agent.forked_runtime import (
    _cache_read_ratio,
    _cache_tokens_from_ai_message,
    run_side_llm_chat,
    side_llm_fork_metadata,
)
from science_graphrag.config import Settings


def test_side_llm_fork_metadata_accepts_numeric_telemetry() -> None:
    meta = side_llm_fork_metadata(
        forked=True,
        side_llm_cache_read_tokens=600,
        side_llm_cache_creation_tokens=400,
        side_llm_cache_read_ratio=0.6,
    )
    assert meta["forked"] is True
    assert meta["side_llm_cache_read_tokens"] == 600
    assert meta["side_llm_cache_read_ratio"] == 0.6


def test_cache_tokens_from_openrouter_shaped_usage_metadata() -> None:
    msg = AIMessage(
        content="ok",
        usage_metadata={
            "input_tokens": 1000,
            "output_tokens": 50,
            "total_tokens": 1050,
            "cache_read_input_tokens": 700,
            "cache_creation_input_tokens": 200,
        },
    )
    cr, cc = _cache_tokens_from_ai_message(msg)
    assert cr == 700
    assert cc == 200
    assert _cache_read_ratio(cr, cc) == pytest.approx(0.7778, rel=1e-4)


def test_cache_read_ratio_none_when_no_cache_fields() -> None:
    msg = AIMessage(
        content="x",
        usage_metadata={"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
    )
    cr, cc = _cache_tokens_from_ai_message(msg)
    assert cr is None and cc is None
    assert _cache_read_ratio(cr, cc) is None


def test_run_side_llm_chat_non_ai_message_marks_not_forked() -> None:
    settings = Settings()
    with patch(
        "science_graphrag.agent.forked_runtime.invoke_chat_gated",
        return_value=HumanMessage(content="unexpected"),
    ):
        out = run_side_llm_chat(
            settings=settings,
            parent_system="sys",
            fork_prompt="hi",
        )
    assert out.forked is False
    assert out.text == "unexpected"
    assert out.side_llm_cache_read_ratio is None
