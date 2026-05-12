"""Tests for L4 LLM session consolidation."""

from __future__ import annotations

from science_graphrag.agent.context.llm_history_compact import (
    L4SummaryResult,
    maybe_llm_compact_session_after_turn,
)
from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.agent.forked_runtime import SideLlmRunResult
from science_graphrag.config import Settings


def _fake_summary_result(
    text: str, *, cache_read: int = 800, cache_creation: int = 200
) -> L4SummaryResult:
    """Build a fake side-LLM completion with cache telemetry for unit tests."""
    denom = float(cache_read + cache_creation)
    ratio = round(cache_read / denom, 4) if denom > 0 else 0.0
    return L4SummaryResult(
        text=text,
        fork=SideLlmRunResult(
            text=text,
            forked=True,
            latency_ms=42,
            side_llm_cache_read_tokens=cache_read,
            side_llm_cache_creation_tokens=cache_creation,
            side_llm_cache_read_ratio=ratio,
        ),
    )


def test_llm_compact_skipped_when_disabled() -> None:
    clear_session_store_for_tests()
    tid = "t_skip_l4"
    update_session_after_turn(
        tid,
        turn_digest={
            "user_intent": "u",
            "answer_excerpt": "a",
            "answer_class": "grounded_explanation",
            "tools_used": ["idea_search"],
        },
    )
    settings = Settings.model_construct(
        agent_llm_full_history_compact_enabled=False,
        agent_compaction_digest_cap=1,
        extraction_llm_api_key="x",
    )
    assert (
        maybe_llm_compact_session_after_turn(
            settings,
            tid,
            digest_count=1,
            digest_cap=1,
        )
        is None
    )


def test_llm_compact_rewrites_summary(monkeypatch) -> None:
    clear_session_store_for_tests()
    tid = "t_apply_l4"
    for i in range(3):
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": f"intent-{i}",
                "answer_excerpt": f"answer-{i}",
                "answer_class": "grounded_explanation",
                "tools_used": ["idea_search"],
            },
        )

    import science_graphrag.agent.context.llm_history_compact as mod

    monkeypatch.setattr(
        mod,
        "_invoke_summary_llm",
        lambda settings, user_blob: _fake_summary_result("COMPACT_LLM_SUMMARY"),
    )

    settings = Settings.model_construct(
        agent_llm_full_history_compact_enabled=True,
        agent_llm_full_history_compact_cooldown_turns=1,
        agent_compaction_digest_cap=3,
        extraction_llm_api_key="sk-test-key",
        extraction_llm_base_url="https://example.invalid/v1",
        extraction_llm_model="unused-for-test",
        extraction_llm_timeout_seconds=30,
        chat_llm_model="",
        agent_llm_full_history_compact_max_out_tokens=512,
        agent_llm_full_history_compact_max_digest_chars=8000,
    )
    audit = maybe_llm_compact_session_after_turn(
        settings,
        tid,
        digest_count=3,
        digest_cap=3,
    )
    assert audit is not None
    assert get_session_for_thread(tid)["session_summary"] == "COMPACT_LLM_SUMMARY"
    meta = get_session_for_thread(tid)["session_meta"]
    assert meta.get("last_llm_compact_turn") == meta.get("turn_counter")
    # Wave H §H2: cache telemetry from ``run_side_llm_chat`` must reach the audit dict.
    assert audit["forked"] is True
    assert audit["side_llm_cache_read_tokens"] == 800
    assert audit["side_llm_cache_creation_tokens"] == 200
    assert audit["side_llm_cache_read_ratio"] == 0.8
    assert "side_llm_latency_ms" in audit


def test_llm_compact_ptl_retries_on_context_limit(monkeypatch) -> None:
    clear_session_store_for_tests()
    tid = "t_ptl_l4"
    for i in range(4):
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": f"intent-{i}",
                "answer_excerpt": f"answer-{i}",
                "answer_class": "grounded_explanation",
                "tools_used": ["idea_search"],
            },
        )

    import science_graphrag.agent.context.llm_history_compact as mod

    calls = {"n": 0}

    def flaky_llm(settings, user_blob):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ValueError("maximum context length exceeded")
        return _fake_summary_result("PTL_OK_SUMMARY")

    monkeypatch.setattr(mod, "_invoke_summary_llm", flaky_llm)

    settings = Settings.model_construct(
        agent_llm_full_history_compact_enabled=True,
        agent_llm_full_history_compact_cooldown_turns=1,
        agent_compaction_digest_cap=4,
        extraction_llm_api_key="sk-test-key",
        extraction_llm_base_url="https://example.invalid/v1",
        extraction_llm_model="unused-for-test",
        extraction_llm_timeout_seconds=30,
        chat_llm_model="",
        agent_llm_full_history_compact_max_out_tokens=512,
        agent_llm_full_history_compact_max_digest_chars=8000,
        agent_llm_full_history_compact_ptl_max_retries=2,
    )
    audit = maybe_llm_compact_session_after_turn(
        settings,
        tid,
        digest_count=4,
        digest_cap=4,
    )
    assert audit is not None
    assert audit.get("ptl_retry_count") == 1
    assert audit.get("ptl_retry_count_per_compaction") == 1
    assert get_session_for_thread(tid)["session_summary"] == "PTL_OK_SUMMARY"


def test_llm_compact_routes_through_run_side_llm_chat(monkeypatch) -> None:
    """Wave H §H2: L4 path must use the cache-safe shared helper, not raw build_chat_model."""
    clear_session_store_for_tests()
    tid = "t_cache_safe_l4"
    for i in range(3):
        update_session_after_turn(
            tid,
            turn_digest={
                "user_intent": f"intent-{i}",
                "answer_excerpt": f"answer-{i}",
                "answer_class": "grounded_explanation",
                "tools_used": ["idea_search"],
            },
        )

    captured: dict[str, object] = {}

    def fake_run_side_llm_chat(**kwargs):
        captured.update(kwargs)
        return SideLlmRunResult(
            text="WAVE_H_SUMMARY",
            forked=True,
            latency_ms=99,
            side_llm_cache_read_tokens=1200,
            side_llm_cache_creation_tokens=300,
            side_llm_cache_read_ratio=0.8,
        )

    import science_graphrag.agent.context.llm_history_compact as mod

    monkeypatch.setattr(mod, "run_side_llm_chat", fake_run_side_llm_chat)

    settings = Settings.model_construct(
        agent_llm_full_history_compact_enabled=True,
        agent_llm_full_history_compact_cooldown_turns=1,
        agent_compaction_digest_cap=3,
        extraction_llm_api_key="sk-test-key",
        extraction_llm_base_url="https://example.invalid/v1",
        extraction_llm_model="unused-for-test",
        extraction_llm_timeout_seconds=30,
        chat_llm_model="",
        agent_llm_full_history_compact_max_out_tokens=512,
        agent_llm_full_history_compact_max_digest_chars=8000,
        agent_pre_compact_sanitizers_enabled=True,
    )
    audit = maybe_llm_compact_session_after_turn(
        settings,
        tid,
        digest_count=3,
        digest_cap=3,
    )
    try:
        assert audit is not None
        assert get_session_for_thread(tid)["session_summary"] == "WAVE_H_SUMMARY"
        # System prompt is the cache-stable prefix; same string on every L4 call.
        assert captured["parent_system"] == mod._L4_SUMMARY_SYSTEM
        # Settings + temperature are forwarded; cache-prefix shape stays controlled.
        assert captured["settings"] is settings
        assert captured["temperature"] == 0.15
        # Audit must surface cache telemetry fields for trace-review aggregation.
        assert audit["forked"] is True
        assert audit["side_llm_cache_read_ratio"] == 0.8
        assert audit["side_llm_latency_ms"] == 99
    finally:
        clear_session_store_for_tests()
