"""Thread insight snapshot (Epic A1)."""

from unittest.mock import patch

import science_graphrag.agent.context.thread_insights as thread_insights_mod
from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.context.thread_insights import (
    _maybe_llm_synthesize_thread_insight,
    maybe_refresh_thread_insight_after_turn,
)
from science_graphrag.agent.forked_runtime import SideLlmRunResult
from science_graphrag.config import Settings


def test_maybe_refresh_thread_insight_writes_session_meta_and_audit() -> None:
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=2,
        agent_thread_insights_max_chunks=2,
        agent_thread_insights_max_workers=2,
    )
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-a",
        turn_digest={
            "user_intent": "q1",
            "answer_excerpt": "a1",
            "answer_class": "inventory",
            "tools_used": ["find_works"],
        },
    )
    be.update_after_turn(
        "tid-a",
        turn_digest={
            "user_intent": "q2",
            "answer_excerpt": "a2",
            "answer_class": "fact_lookup",
            "tools_used": [],
        },
    )
    maybe_refresh_thread_insight_after_turn("tid-a", settings=st)
    ent = be.get_session_copy("tid-a")
    tip = (ent.get("session_meta") or {}).get("thread_insight")
    assert isinstance(tip, dict)
    assert tip.get("version") == 1
    assert "chunk=c0" in str(tip.get("current") or "")
    aud = tip.get("audit")
    assert isinstance(aud, dict)
    assert aud.get("schema_version") == "thread_insight_audit_v1"
    assert int(aud.get("chunk_count") or 0) >= 1
    assert aud.get("mode") == "deterministic_stub"
    assert aud.get("built_at_turn_counter") == 2
    assert aud.get("forked") is False
    cb = tip.get("compaction_boundary")
    assert isinstance(cb, dict)
    assert cb.get("schema_version") == "thread_insight_compaction_boundary_v1"
    assert "pre_tokens" in cb and int(cb["pre_tokens"]) >= 0
    assert isinstance(cb.get("source_range"), dict)
    assert isinstance(cb.get("preserved_segment"), str)


def test_thread_insight_skipped_when_disabled() -> None:
    clear_session_store_for_tests()
    st = Settings(agent_thread_insights_enabled=False, agent_thread_insights_min_digests=1)
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-b",
        turn_digest={"user_intent": "x", "answer_excerpt": "y", "tools_used": []},
    )
    maybe_refresh_thread_insight_after_turn("tid-b", settings=st)
    ent = be.get_session_copy("tid-b")
    assert (ent.get("session_meta") or {}).get("thread_insight") is None


def test_thread_insight_skip_fresh_when_turn_delta_high() -> None:
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=2,
        agent_thread_insights_stale_after_turn_delta=5,
    )
    be = get_session_memory_backend()
    for i in range(2):
        be.update_after_turn(
            "tid-fresh",
            turn_digest={
                "user_intent": f"q{i}",
                "answer_excerpt": f"a{i}",
                "answer_class": "inventory",
                "tools_used": [],
            },
        )
    maybe_refresh_thread_insight_after_turn("tid-fresh", settings=st)
    ent = be.get_session_copy("tid-fresh")
    assert (ent.get("session_meta") or {}).get("thread_insight", {}).get("version") == 1
    be.update_after_turn(
        "tid-fresh",
        turn_digest={
            "user_intent": "q2",
            "answer_excerpt": "a2",
            "answer_class": "inventory",
            "tools_used": [],
        },
    )
    maybe_refresh_thread_insight_after_turn("tid-fresh", settings=st)
    ent2 = be.get_session_copy("tid-fresh")
    assert (ent2.get("session_meta") or {}).get("thread_insight", {}).get("version") == 1
    ctrl = (ent2.get("session_meta") or {}).get("thread_insight_control")
    assert isinstance(ctrl, dict)
    assert ctrl.get("refresh_decision") == "skip_fresh"


def test_thread_insight_high_churn_forces_refresh() -> None:
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=2,
        agent_thread_insights_stale_after_turn_delta=10,
        agent_thread_insights_high_churn_window_digests=2,
        agent_thread_insights_high_churn_min_tool_events=3,
    )
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-churn",
        turn_digest={"user_intent": "a", "answer_excerpt": "x", "tools_used": ["t1", "t2"]},
    )
    be.update_after_turn(
        "tid-churn",
        turn_digest={"user_intent": "b", "answer_excerpt": "y", "tools_used": ["t3"]},
    )
    maybe_refresh_thread_insight_after_turn("tid-churn", settings=st)
    v1 = (
        (be.get_session_copy("tid-churn").get("session_meta") or {})
        .get("thread_insight", {})
        .get("version")
    )
    assert v1 == 1
    be.update_after_turn(
        "tid-churn",
        turn_digest={
            "user_intent": "c",
            "answer_excerpt": "z",
            "tools_used": ["t4", "t5", "t6"],
        },
    )
    maybe_refresh_thread_insight_after_turn("tid-churn", settings=st)
    tip = (be.get_session_copy("tid-churn").get("session_meta") or {}).get("thread_insight")
    assert tip.get("version") == 2
    assert tip.get("audit", {}).get("stale_reason") == "high_churn"


def test_thread_insight_circuit_opens_after_failures(monkeypatch) -> None:
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=1,
        agent_thread_insights_max_consecutive_failures=2,
        agent_thread_insights_circuit_open_skip_turns=99,
    )
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-cb",
        turn_digest={"user_intent": "x", "answer_excerpt": "y", "tools_used": []},
    )

    def boom(*_a, **_k):
        raise RuntimeError("simulated insight failure")

    monkeypatch.setattr(thread_insights_mod, "build_thread_insight_snapshot", boom)
    maybe_refresh_thread_insight_after_turn("tid-cb", settings=st)
    maybe_refresh_thread_insight_after_turn("tid-cb", settings=st)
    meta = be.get_session_copy("tid-cb").get("session_meta") or {}
    circ = meta.get("insight_circuit")
    assert isinstance(circ, dict)
    assert int(circ.get("consecutive_failures") or 0) >= 2
    assert int(circ.get("open_until_turn") or 0) > 0


def test_decide_refresh_uses_legacy_audit_turn_counter() -> None:
    """Snapshots without built_at_turn_counter still use audit.turn_counter for freshness."""
    clear_session_store_for_tests()
    st = Settings(
        agent_thread_insights_enabled=True,
        agent_thread_insights_min_digests=2,
        agent_thread_insights_stale_after_turn_delta=5,
    )
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-legacy",
        turn_digest={"user_intent": "a", "answer_excerpt": "x", "tools_used": []},
    )
    be.update_after_turn(
        "tid-legacy",
        turn_digest={"user_intent": "b", "answer_excerpt": "y", "tools_used": []},
    )
    maybe_refresh_thread_insight_after_turn("tid-legacy", settings=st)
    ent = be.get_session_copy("tid-legacy")
    tip = (ent.get("session_meta") or {}).get("thread_insight")
    assert isinstance(tip, dict)
    aud = dict(tip.get("audit") or {})
    aud.pop("built_at_turn_counter", None)
    tip["audit"] = aud
    be.apply_thread_insight_snapshot("tid-legacy", snapshot=tip)
    be.update_after_turn(
        "tid-legacy",
        turn_digest={"user_intent": "c", "answer_excerpt": "z", "tools_used": []},
    )
    maybe_refresh_thread_insight_after_turn("tid-legacy", settings=st)
    tip2 = (be.get_session_copy("tid-legacy").get("session_meta") or {}).get("thread_insight")
    assert tip2.get("version") == 1
    ctrl = (be.get_session_copy("tid-legacy").get("session_meta") or {}).get(
        "thread_insight_control"
    )
    assert ctrl.get("refresh_decision") == "skip_fresh"


def test_patch_session_meta_roundtrip() -> None:
    clear_session_store_for_tests()
    be = get_session_memory_backend()
    be.update_after_turn(
        "tid-patch",
        turn_digest={"user_intent": "u", "answer_excerpt": "a", "tools_used": []},
    )
    be.patch_session_meta("tid-patch", patch={"foo": "bar"})
    meta = be.get_session_copy("tid-patch").get("session_meta") or {}
    assert meta.get("foo") == "bar"


def test_llm_synthesis_empty_body_keeps_stub_and_side_telemetry() -> None:
    st = Settings(
        agent_thread_insights_llm_synthesis_enabled=True,
        extraction_llm_api_key="sk-test-empty-body",
    )
    fake = SideLlmRunResult(
        text="   ",
        forked=True,
        latency_ms=42,
        side_llm_cache_read_tokens=80,
        side_llm_cache_creation_tokens=20,
        side_llm_cache_read_ratio=0.8,
    )
    with patch(
        "science_graphrag.agent.context.thread_insights.synthesize_thread_insight_markdown",
        return_value=fake,
    ):
        body, mode, fork_meta, side_ms, err = _maybe_llm_synthesize_thread_insight(
            ["line-a", "line-b"], "{}", settings=st
        )
    assert err is None
    assert mode == "llm_forked_empty_body_fallback"
    assert "## thread_insight (skeleton)" in body
    assert fork_meta["forked"] is True
    assert fork_meta["side_llm_cache_read_tokens"] == 80
    assert side_ms == 42
