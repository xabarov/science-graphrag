"""Tests for R3 compaction policy helpers."""

from __future__ import annotations

from science_graphrag.agent.context.compaction import build_context_compacted_payload
from science_graphrag.agent.context import compaction_policy as compaction_policy_mod
from science_graphrag.agent.context.compaction_policy import (
    attach_l4_eligibility_to_compaction_audit,
    evaluate_l4_full_history_compact_eligibility,
)
from science_graphrag.config import Settings


def test_l4_eligibility_disabled() -> None:
    s = Settings(agent_llm_full_history_compact_enabled=False)
    out = evaluate_l4_full_history_compact_eligibility(s, "tid", digest_count=99, digest_cap=10)
    assert out["eligible"] is False
    assert out["skip_reason"] == "disabled"


def test_l4_eligibility_below_cap() -> None:
    s = Settings(agent_llm_full_history_compact_enabled=True)
    out = evaluate_l4_full_history_compact_eligibility(s, "tid", digest_count=3, digest_cap=10)
    assert out["eligible"] is False
    assert out["skip_reason"] == "below_digest_cap"


def test_attach_l4_eligibility_merges_audit() -> None:
    s = Settings(agent_llm_full_history_compact_enabled=False)
    cp = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="",
        latest_full_state={"x": 1},
        digest_count=2,
        digest_cap=10,
    )
    merged = attach_l4_eligibility_to_compaction_audit(
        cp,
        settings=s,
        thread_id="t1",
        digest_count=2,
        digest_cap=10,
    )
    aud = merged.get("audit") or {}
    assert "l4_eligibility" in aud
    assert aud["l4_eligibility"]["skip_reason"] == "disabled"


def test_attach_llm_compact_applied_ignored_when_not_eligible(monkeypatch) -> None:
    s = Settings(agent_llm_full_history_compact_enabled=True)
    monkeypatch.setattr(
        compaction_policy_mod,
        "evaluate_l4_full_history_compact_eligibility",
        lambda *_a, **_kw: {"eligible": False, "skip_reason": "below_digest_cap"},
    )
    cp = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="",
        latest_full_state={"x": 1},
        digest_count=2,
        digest_cap=10,
    )
    merged = attach_l4_eligibility_to_compaction_audit(
        cp,
        settings=s,
        thread_id="t1",
        digest_count=2,
        digest_cap=10,
        llm_compact_applied=True,
    )
    elig = (merged.get("audit") or {}).get("l4_eligibility") or {}
    assert elig.get("eligible") is False
    assert "llm_compact_applied" not in elig


def test_attach_llm_compact_applied_merged_when_eligible(monkeypatch) -> None:
    s = Settings(agent_llm_full_history_compact_enabled=True)
    monkeypatch.setattr(
        compaction_policy_mod,
        "evaluate_l4_full_history_compact_eligibility",
        lambda *_a, **_kw: {
            "schema_version": "l4_eligibility_v1",
            "eligible": True,
            "skip_reason": None,
        },
    )
    cp = build_context_compacted_payload(
        thread_id="t1",
        session_summary_excerpt="",
        latest_full_state={"x": 1},
        digest_count=10,
        digest_cap=10,
    )
    merged_false = attach_l4_eligibility_to_compaction_audit(
        cp,
        settings=s,
        thread_id="t1",
        digest_count=10,
        digest_cap=10,
        llm_compact_applied=False,
    )
    elig_f = (merged_false.get("audit") or {}).get("l4_eligibility") or {}
    assert elig_f.get("eligible") is True
    assert elig_f.get("llm_compact_applied") is False

    merged_none = attach_l4_eligibility_to_compaction_audit(
        cp,
        settings=s,
        thread_id="t1",
        digest_count=10,
        digest_cap=10,
        llm_compact_applied=None,
    )
    elig_n = (merged_none.get("audit") or {}).get("l4_eligibility") or {}
    assert elig_n.get("eligible") is True
    assert "llm_compact_applied" not in elig_n
