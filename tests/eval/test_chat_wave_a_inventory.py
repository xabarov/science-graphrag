"""Chat wave A fixture smoke: schema + tool names exist in manifest (CI-friendly, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.agent.tool_manifest import manifest_by_name

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "benchmarks"
    / "chat_wave_a"
    / "inventory_smoke_gold.json"
)


def test_chat_wave_a_inventory_fixture_valid() -> None:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw.get("case_id")
    assert raw.get("question")
    expect = raw.get("expected_tool_sequence_any") or []
    assert isinstance(expect, list) and len(expect) >= 1
    m = manifest_by_name()
    for tool in expect:
        assert tool in m, f"unknown tool in gold: {tool}"
