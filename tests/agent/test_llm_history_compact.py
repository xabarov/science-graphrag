"""Tests for L4 LLM session consolidation."""

from __future__ import annotations

from science_graphrag.agent.context.llm_history_compact import maybe_llm_compact_session_after_turn
from science_graphrag.agent.context.session_store import (
    clear_session_store_for_tests,
    get_session_for_thread,
    update_session_after_turn,
)
from science_graphrag.config import Settings


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
        mod, "_invoke_summary_llm", lambda settings, user_blob: "COMPACT_LLM_SUMMARY"
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
        return "PTL_OK_SUMMARY"

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
    assert get_session_for_thread(tid)["session_summary"] == "PTL_OK_SUMMARY"
