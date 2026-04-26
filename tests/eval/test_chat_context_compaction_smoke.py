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
        digest_count=2,
        rolling_threshold=3,
        digest_cap=10,
        workspace_id=None,
        workspace_capsule_present=False,
    )
    assert p["type"] == "context_compacted"
    assert p["thread_id"] == "t1"
    assert p["session_summary_excerpt"] == "hello"
    assert p["compaction"]["kind"] == "turn_digest"
    assert p["compaction"]["trigger"] == "post_answer"
    assert p["compaction"]["kinds"] == ["turn_digest"]
    assert p["compaction"]["digest_count"] == 2
    assert p["compaction"]["boundary"]["status"] == "idle"


def test_build_context_compacted_degraded_trigger() -> None:
    """Missing ``values`` chunk → degraded_stream trigger."""
    p = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="x",
        latest_full_state=None,
        digest_count=1,
    )
    assert p["compaction"]["trigger"] == "post_answer_degraded_stream"


def test_build_context_compacted_rolling_and_capsule_kinds() -> None:
    """CH5: kinds include rolling_memory and workspace_capsule when thresholds met."""
    p = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="s",
        latest_full_state={"ok": True},
        digest_count=4,
        rolling_threshold=3,
        digest_cap=10,
        workspace_id="ws-1",
        workspace_capsule_present=True,
    )
    kinds = p["compaction"]["kinds"]
    assert "turn_digest" in kinds
    assert "rolling_memory" in kinds
    assert "workspace_capsule" in kinds


def test_build_context_compacted_boundary_candidate_at_cap() -> None:
    p = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="s",
        latest_full_state={"ok": True},
        digest_count=10,
        rolling_threshold=3,
        digest_cap=10,
    )
    assert p["compaction"]["boundary"]["status"] == "candidate"


def test_chat_context_compaction_fixture_valid() -> None:
    """Gold JSON lists expected field names for eval runners."""
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw.get("case_id") == "chat_context_compaction_v1_smoke"
    fields = raw.get("expected_context_compacted_fields") or []
    assert "compaction" in fields
    assert raw.get("expected_compaction_kind") == "turn_digest"
    triggers = raw.get("valid_triggers") or []
    assert "post_answer" in triggers
    sample = build_context_compacted_payload(
        thread_id="t_gold",
        session_summary_excerpt="x",
        latest_full_state={"ok": True},
        digest_count=1,
    )
    for k in raw.get("expected_compaction_keys") or []:
        assert k in sample["compaction"]
