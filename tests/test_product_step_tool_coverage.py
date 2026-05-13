"""Every LangChain tool in ``TOOL_MANIFEST`` maps to a localized product_step code."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.agent.tool_manifest import TOOL_MANIFEST
from science_graphrag.api.agent_v2_modules.stream_lifecycle import (
    GENERIC_PRODUCT_STEP_TOOLS,
    META_TOOL_NAMES,
    degraded_mode_event_from_warnings,
    product_step_code_for_tool,
    product_step_event_for_tool,
)


def test_manifest_tools_have_product_step_codes() -> None:
    missing: list[str] = []
    for entry in TOOL_MANIFEST:
        if entry.name in META_TOOL_NAMES:
            continue
        if entry.name in GENERIC_PRODUCT_STEP_TOOLS:
            continue
        if product_step_code_for_tool(entry.name) is None:
            missing.append(entry.name)
    assert not missing, f"Add mapping for tools: {missing}"


def test_unmapped_tool_uses_explicit_generic_product_step_payload() -> None:
    payload = product_step_event_for_tool("tool_from_future_runtime")
    assert payload["code"] == "using_tool"
    assert payload["generic"] is True
    assert payload["generic_reason"] == "unmapped_tool_name"


def test_manifest_unmapped_tools_must_be_explicitly_generic() -> None:
    for entry in TOOL_MANIFEST:
        if entry.name in META_TOOL_NAMES:
            continue
        if product_step_code_for_tool(entry.name) is not None:
            continue
        assert entry.name in GENERIC_PRODUCT_STEP_TOOLS


def test_mcp_tools_emit_intentionally_generic_product_step() -> None:
    for name in GENERIC_PRODUCT_STEP_TOOLS:
        payload = product_step_event_for_tool(name)
        assert payload["code"] == "using_tool"
        assert payload["generic"] is True
        assert payload["generic_reason"] == "intentionally_generic_tool"


def test_committed_trace_reviews_have_no_accidental_using_tool() -> None:
    repo = Path(__file__).resolve().parents[1]
    traces = sorted((repo / "eval" / "results").glob("trace-review-*.json"))
    if not traces:
        return
    known_manifest_tools = {entry.name for entry in TOOL_MANIFEST}
    for path in traces:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for case in payload.get("trace_timeline") or []:
            for step in case.get("tool_steps") or []:
                tool_name = str(step.get("tool") or "").strip()
                if not tool_name or tool_name not in known_manifest_tools:
                    continue
                if tool_name in GENERIC_PRODUCT_STEP_TOOLS:
                    continue
                code = str(step.get("product_step_code") or "").strip()
                assert (
                    code != "using_tool"
                ), f"{path.name}: tool {tool_name} unexpectedly uses generic product_step"


def test_degraded_mode_event_from_warnings_empty() -> None:
    assert degraded_mode_event_from_warnings([]) is None
    assert degraded_mode_event_from_warnings(["weak_evidence"]) is None


def test_degraded_mode_event_from_warnings_maps_recursion_partial() -> None:
    out = degraded_mode_event_from_warnings(
        ["agent_partial_graph_recursion_limit", "partial_after_recursion_limit"]
    )
    assert out is not None
    assert out["type"] == "degraded_mode"
    assert out["schema_version"] == 1
    assert out["reasons"] == ["recursion_limit_partial", "partial_after_recursion_limit"]
