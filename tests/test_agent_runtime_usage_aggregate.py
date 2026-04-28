"""Tests for aggregate_agent_llm_usage (agent run_metadata for UI)."""

from __future__ import annotations

from langchain_core.messages import AIMessage

from science_graphrag.agent.runtime import aggregate_agent_llm_usage


def _usage_meta(inp: int, out: int, total: int) -> dict[str, int]:
    return {"input_tokens": inp, "output_tokens": out, "total_tokens": total}


def test_aggregate_sums_usage_metadata() -> None:
    """Sums prompt/completion across multiple assistant messages."""
    m1 = AIMessage(content="a", usage_metadata=_usage_meta(3, 1, 4))
    m2 = AIMessage(content="b", usage_metadata=_usage_meta(2, 5, 7))
    out = aggregate_agent_llm_usage([m1, m2])
    assert out is not None
    assert out["prompt_tokens"] == 5
    assert out["completion_tokens"] == 6
    assert out["total_tokens"] == 11


def test_aggregate_total_only_message() -> None:
    """When per-part counts are zero, falls back to total_tokens."""
    m = AIMessage(content="x", usage_metadata=_usage_meta(0, 0, 100))
    out = aggregate_agent_llm_usage([m])
    assert out is not None
    assert out["total_tokens"] == 100
    assert out["prompt_tokens"] == 0
    assert out["completion_tokens"] == 0


def test_aggregate_empty_messages() -> None:
    """No messages yields no usage dict."""
    assert aggregate_agent_llm_usage([]) is None
