"""Optional Redis session backend continuity (skip if Redis unavailable)."""

from __future__ import annotations

import os
import uuid

import pytest

from science_graphrag.agent.context.session_backend import RedisSessionMemoryBackend
from science_graphrag.agent.context.session_store import clear_session_store_for_tests


def _redis_url() -> str:
    return (os.environ.get("SCIENCE_GRAPHRAG_REDIS_URL") or "redis://127.0.0.1:6379/0").strip()


@pytest.mark.skipif(
    os.environ.get("SCIENCE_GRAPHRAG_SKIP_REDIS_SESSION_TEST") == "1",
    reason="SCIENCE_GRAPHRAG_SKIP_REDIS_SESSION_TEST=1",
)
def test_redis_session_memory_survives_reconnect() -> None:
    """Two backend instances (simulating worker restart) share the same thread state."""
    prefix = f"test_sess_{uuid.uuid4().hex}:"
    url = _redis_url()
    be1: RedisSessionMemoryBackend | None = None
    try:
        be1 = RedisSessionMemoryBackend(redis_url=url, key_prefix=prefix, ttl_seconds=3600)
        be1._redis.ping()  # noqa: SLF001
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Redis not available: {exc}")

    try:
        tid = "thread_redis_continuity"
        be1.update_after_turn(
            tid,
            turn_digest={
                "user_intent": "first q",
                "answer_excerpt": "first a",
                "answer_class": "inventory",
                "tools_used": [],
            },
            workspace_id="ws-redis-1",
        )
        be1.update_after_turn(
            tid,
            turn_digest={
                "user_intent": "second q",
                "answer_excerpt": "second a",
                "answer_class": "inventory",
                "tools_used": [],
            },
            workspace_id="ws-redis-1",
        )

        be2 = RedisSessionMemoryBackend(redis_url=url, key_prefix=prefix, ttl_seconds=3600)
        snap = be2.get_session_copy(tid)
        assert len(snap.get("digests") or []) == 2
        assert "second q" in str(snap.get("session_summary") or "")
        wc = (snap.get("capsules") or {}).get("workspace")
        assert isinstance(wc, dict)
        assert wc.get("workspace_id") == "ws-redis-1"
    finally:
        if be1 is not None:
            be1.clear_all()


def test_configure_falls_back_to_memory_on_bad_redis(monkeypatch) -> None:
    """configure_session_memory_backend must not crash when Redis URL is invalid."""
    from science_graphrag.agent.context import session_backend as sb
    from science_graphrag.config import Settings

    monkeypatch.setattr(sb, "_backend", None)
    s = Settings(
        agent_session_memory_backend="redis",
        redis_url="redis://127.0.0.1:9/0",
    )
    sb.configure_session_memory_backend(s)
    be = sb.get_session_memory_backend()
    assert be.__class__.__name__ == "InMemorySessionMemoryBackend"
    clear_session_store_for_tests()
    sb.set_session_memory_backend(None)
