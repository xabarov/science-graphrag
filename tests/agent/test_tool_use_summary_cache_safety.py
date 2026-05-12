"""Regression: tool_use_summary uses cache-safe side-LLM seam (Wave E / §10.9)."""

from __future__ import annotations

from unittest.mock import patch

from science_graphrag.agent.forked_runtime import SideLlmRunResult
from science_graphrag.agent.tool_use_summary import summarize_tool_result_payload_dict
from science_graphrag.config import Settings


def test_summarize_uses_stable_system_and_fork_prompt_for_cache_key() -> None:
    """Side-LLM receives fixed system string and tool JSON only in fork_prompt (§10.2)."""
    settings = Settings(
        agent_tool_use_summary_enabled=True,
        extraction_llm_model="test/model",
        extraction_llm_base_url="http://example.invalid",
        extraction_llm_api_key="dummy",
    )
    payload = {"ok": True, "row_count": 99, "workspace_id": "ws1"}

    def _fake_side_llm(**kwargs: object) -> SideLlmRunResult:
        assert str(kwargs.get("parent_system") or "").startswith(
            "You compress one JSON tool result"
        )
        assert "Tool JSON:" in str(kwargs.get("fork_prompt") or "")
        return SideLlmRunResult(
            text=(
                '{"schema_version":"tool_use_summary_v1","tool":"find_works",'
                '"bullets":["a"],"work_ids":[],"numeric_facts":{},"warnings":[]}'
            ),
            forked=True,
            latency_ms=0,
            side_llm_cache_read_tokens=400,
            side_llm_cache_creation_tokens=100,
            side_llm_cache_read_ratio=0.8,
        )

    with patch(
        "science_graphrag.agent.tool_use_summary.run_side_llm_chat",
        side_effect=_fake_side_llm,
    ):
        merged, meta = summarize_tool_result_payload_dict(
            settings=settings, tool_name="find_works", payload=payload
        )

    assert merged.get("_tool_use_summary", {}).get("schema_version") == "tool_use_summary_v1"
    assert meta.get("side_llm_cache_read_ratio") == 0.8
    assert meta.get("forked") is True


def test_summarize_surfaces_cache_ratio_for_trace_review_gate() -> None:
    """Telemetry is passed through; Wave E ratio floor is enforced by trace compare, not here."""
    settings = Settings(
        agent_tool_use_summary_enabled=True,
        extraction_llm_model="test/model",
        extraction_llm_base_url="http://example.invalid",
        extraction_llm_api_key="dummy",
    )
    payload = {"ok": True, "rows": [{"work_id": "w1"}] * 20}
    result = SideLlmRunResult(
        text=(
            '{"schema_version":"tool_use_summary_v1","tool":"find_works",'
            '"bullets":["x"],"work_ids":["w1"],"numeric_facts":{},"warnings":[]}'
        ),
        forked=True,
        latency_ms=0,
        side_llm_cache_read_tokens=45,
        side_llm_cache_creation_tokens=55,
        side_llm_cache_read_ratio=0.45,
    )
    with patch(
        "science_graphrag.agent.tool_use_summary.run_side_llm_chat",
        return_value=result,
    ):
        _merged, meta = summarize_tool_result_payload_dict(
            settings=settings, tool_name="find_works", payload=payload
        )

    assert meta.get("side_llm_cache_read_ratio") == 0.45


def test_summarize_preserves_low_cache_ratio_without_inline_clamp() -> None:
    """Low ratios stay in meta; acceptance gate uses trace_regression_compare min-side option."""
    settings = Settings(
        agent_tool_use_summary_enabled=True,
        extraction_llm_model="test/model",
        extraction_llm_base_url="http://example.invalid",
        extraction_llm_api_key="dummy",
    )
    payload = {"ok": True, "rows": [{"work_id": "w1"}] * 5}
    result = SideLlmRunResult(
        text=(
            '{"schema_version":"tool_use_summary_v1","tool":"find_works",'
            '"bullets":["y"],"work_ids":["w1"],"numeric_facts":{},"warnings":[]}'
        ),
        forked=True,
        latency_ms=0,
        side_llm_cache_read_tokens=10,
        side_llm_cache_creation_tokens=90,
        side_llm_cache_read_ratio=0.1,
    )
    with patch(
        "science_graphrag.agent.tool_use_summary.run_side_llm_chat",
        return_value=result,
    ):
        _merged, meta = summarize_tool_result_payload_dict(
            settings=settings, tool_name="find_works", payload=payload
        )

    assert meta.get("side_llm_cache_read_ratio") == 0.1
