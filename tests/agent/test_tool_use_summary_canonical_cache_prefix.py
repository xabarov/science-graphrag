"""Wave E2 PR1/PR2: canonical side-LLM fork_prompt for prompt-cache stability."""

from __future__ import annotations

from unittest.mock import patch

from science_graphrag.agent.forked_runtime import SideLlmRunResult
from science_graphrag.agent.tool_use_summary import (
    canonical_tool_json_for_side_llm,
    summarize_tool_result_payload_dict,
)
from science_graphrag.config import Settings

_VALID_SUMMARY = (
    '{"schema_version":"tool_use_summary_v1","tool":"find_works",'
    '"bullets":["x"],"work_ids":[],"numeric_facts":{},"warnings":[]}'
)


def test_canonical_json_stable_across_dict_key_order() -> None:
    a = {"z": 1, "m": {"b": 2, "a": 3}, "rows": [{"work_id": "w1"}]}
    b = {"m": {"a": 3, "b": 2}, "rows": [{"work_id": "w1"}], "z": 1}
    assert canonical_tool_json_for_side_llm(a) == canonical_tool_json_for_side_llm(b)


def test_canonical_json_uses_compact_separators() -> None:
    s = canonical_tool_json_for_side_llm({"ok": True, "n": 1})
    assert ", " not in s
    assert ": " not in s


def test_summarize_identical_fork_prompt_for_equivalent_payloads() -> None:
    """PR2: repeated batches with same logical payload must hit identical HumanMessage text."""
    settings = Settings(
        agent_tool_use_summary_enabled=True,
        extraction_llm_model="test/model",
        extraction_llm_base_url="http://example.invalid",
        extraction_llm_api_key="dummy",
    )
    prompts: list[str] = []

    def _capture(**kwargs: object) -> SideLlmRunResult:
        prompts.append(str(kwargs.get("fork_prompt") or ""))
        return SideLlmRunResult(
            text=_VALID_SUMMARY,
            forked=True,
            latency_ms=0,
            side_llm_cache_read_tokens=100,
            side_llm_cache_creation_tokens=0,
            side_llm_cache_read_ratio=1.0,
        )

    p1 = {"ok": True, "row_count": 5, "extra": {"z": 9, "a": 1}}
    p2 = {"extra": {"a": 1, "z": 9}, "row_count": 5, "ok": True}

    with patch(
        "science_graphrag.agent.tool_use_summary.run_side_llm_chat",
        side_effect=_capture,
    ):
        summarize_tool_result_payload_dict(settings=settings, tool_name="find_works", payload=p1)
        summarize_tool_result_payload_dict(settings=settings, tool_name="find_works", payload=p2)

    assert len(prompts) == 2
    assert prompts[0] == prompts[1]
    assert prompts[0].startswith("Tool JSON:\n")
