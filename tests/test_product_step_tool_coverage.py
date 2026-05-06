"""Every LangChain tool in ``TOOL_MANIFEST`` maps to a localized product_step code."""

from __future__ import annotations

from science_graphrag.agent.tool_manifest import TOOL_MANIFEST
from science_graphrag.api.agent_v2_modules.stream_lifecycle import (
    META_TOOL_NAMES,
    product_step_event_for_tool,
    product_step_code_for_tool,
)


def test_manifest_tools_have_product_step_codes() -> None:
    missing: list[str] = []
    for entry in TOOL_MANIFEST:
        if entry.name in META_TOOL_NAMES:
            continue
        if product_step_code_for_tool(entry.name) is None:
            missing.append(entry.name)
    assert not missing, f"Add mapping for tools: {missing}"


def test_unmapped_tool_uses_explicit_generic_product_step_payload() -> None:
    payload = product_step_event_for_tool("tool_from_future_runtime")
    assert payload["code"] == "using_tool"
    assert payload["generic"] is True
    assert payload["generic_reason"] == "unmapped_tool_name"
