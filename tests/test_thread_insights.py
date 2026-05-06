"""Thread insight snapshot (Epic A Train T1 skeleton)."""

from science_graphrag.agent.context.session_backend import get_session_memory_backend
from science_graphrag.agent.context.session_store import clear_session_store_for_tests
from science_graphrag.agent.context.thread_insights import maybe_refresh_thread_insight_after_turn
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
