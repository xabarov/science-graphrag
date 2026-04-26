"""CH5 foundation smoke: ``context_compacted`` fixture contract (CI-friendly, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.agent.context.compaction import build_context_compacted_payload

FIXTURE = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "benchmarks"
    / "chat_wave_c"
    / "chat_context_compaction_v1_smoke_gold.json"
)


def test_build_context_compacted_payload_shape() -> None:
    """Happy path: full graph state → ``post_answer`` trigger."""
    p = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="hello",
        latest_full_state={"messages": []},
    )
    assert p["type"] == "context_compacted"
    assert p["thread_id"] == "t1"
    assert p["session_summary_excerpt"] == "hello"
    assert p["compaction"]["kind"] == "turn_digest"
    assert p["compaction"]["trigger"] == "post_answer"


def test_build_context_compacted_degraded_trigger() -> None:
    """Missing ``values`` chunk → degraded_stream trigger."""
    p = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="x",
        latest_full_state=None,
    )
    assert p["compaction"]["trigger"] == "post_answer_degraded_stream"


def test_chat_context_compaction_fixture_valid() -> None:
    """Gold JSON lists expected field names for eval runners."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw.get("case_id") == "chat_context_compaction_v1_smoke"
    fields = raw.get("expected_context_compacted_fields") or []
    assert "compaction" in fields
    assert raw.get("expected_compaction_kind") == "turn_digest"
    triggers = raw.get("valid_triggers") or []
    assert "post_answer" in triggers
