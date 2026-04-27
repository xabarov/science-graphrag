"""Integration-style tests for distributed LLM quota (Phase 5 closure)."""

from __future__ import annotations

import os
import threading
import time
import uuid
from unittest.mock import patch

import pytest

pytest.importorskip("fakeredis")
from fakeredis import FakeRedis  # noqa: E402

from science_graphrag.config import Settings
from science_graphrag.llm import redis_quota
from science_graphrag.llm.concurrency import (
    get_llm_pool_registry,
    llm_pool_slot,
    reset_llm_pool_registry_for_tests,
)
from science_graphrag.llm.redis_quota import (
    DistributedQuotaAcquireTimeout,
    reset_quota_redis_client_for_tests,
    set_quota_redis_client_override,
)


@pytest.fixture(autouse=True)
def _cleanup() -> None:
    yield
    set_quota_redis_client_override(None)
    reset_quota_redis_client_for_tests()
    reset_llm_pool_registry_for_tests()


def _quota_settings(**kwargs: object) -> Settings:
    base = dict(
        llm_distributed_quota_enabled=True,
        llm_distributed_quota_key_prefix="test:integ",
        llm_distributed_quota_acquire_timeout_seconds=10.0,
        llm_distributed_quota_lease_seconds=120,
        llm_concurrency_claims=2,
        redis_url="redis://127.0.0.1:9/0",
    )
    base.update(kwargs)
    return Settings.model_validate(base)


def test_parallel_llm_pool_slot_never_exceeds_redis_cap() -> None:
    """Two threads hold slots concurrently; ZSET cardinality never exceeds pool cap."""

    r = FakeRedis(decode_responses=True)
    set_quota_redis_client_override(r)
    s = _quota_settings(llm_concurrency_claims=2)
    zkey = redis_quota._zset_key(s, "claims")  # noqa: SLF001
    start = threading.Barrier(2)
    peak = [0]

    def worker() -> None:
        start.wait()
        with llm_pool_slot("claims", s):
            n = int(r.zcard(zkey))
            peak[0] = max(peak[0], n)
            time.sleep(0.05)

    t1 = threading.Thread(target=worker)
    t2 = threading.Thread(target=worker)
    t1.start()
    t2.start()
    t1.join(timeout=10.0)
    t2.join(timeout=10.0)
    assert not t1.is_alive() and not t2.is_alive()
    assert peak[0] <= 2
    assert int(r.zcard(zkey)) == 0


def test_llm_pool_slot_releases_local_sem_on_distributed_timeout() -> None:
    r = FakeRedis(decode_responses=True)
    set_quota_redis_client_override(r)
    s = _quota_settings(llm_concurrency_claims=2, llm_distributed_quota_acquire_timeout_seconds=1.0)

    def _raise_timeout(*_a, **_k):
        raise DistributedQuotaAcquireTimeout("simulated")

    sem = get_llm_pool_registry(s).slot("claims")
    with patch.object(redis_quota, "acquire_slot_blocking", side_effect=_raise_timeout):
        with pytest.raises(DistributedQuotaAcquireTimeout):
            with llm_pool_slot("claims", s):
                pass
    assert sem.acquire(blocking=False) is True
    sem.release()


def test_acquire_slot_blocking_fail_open_returns_none() -> None:
    class _Bad:
        def register_script(self, *_args, **_kwargs):
            def _run(*_a, **_k):
                raise OSError("simulated_redis_down")

            return _run

    s = _quota_settings()
    with patch.object(redis_quota, "_redis_client", lambda *_: _Bad()):
        tok = redis_quota.acquire_slot_blocking(s, "claims")
    assert tok is None


def test_live_redis_second_acquire_times_out_when_cap_is_one() -> None:
    """Optional: real Redis enforces cap across sequential acquires (skip if Redis down)."""

    try:
        import redis as redis_mod  # pylint: disable=import-outside-toplevel
    except ImportError:
        pytest.skip("redis package not installed")

    url = (os.environ.get("SCIENCE_GRAPHRAG_REDIS_URL") or "redis://127.0.0.1:6379/0").strip()
    try:
        ping_client = redis_mod.Redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        ping_client.ping()
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Redis not available: {exc}")

    prefix = f"test_live_quota:{uuid.uuid4().hex}"
    s = Settings.model_validate(
        {
            "redis_url": url,
            "llm_distributed_quota_enabled": True,
            "llm_distributed_quota_key_prefix": prefix,
            "llm_distributed_quota_acquire_timeout_seconds": 1.5,
            "llm_distributed_quota_lease_seconds": 30,
            "llm_concurrency_claims": 1,
        }
    )
    zkey = redis_quota._zset_key(s, "claims")  # noqa: SLF001
    tok: str | None = None
    try:
        tok = redis_quota.acquire_slot_blocking(s, "claims")
        assert tok
        with pytest.raises(DistributedQuotaAcquireTimeout):
            redis_quota.acquire_slot_blocking(s, "claims")
    finally:
        if tok:
            redis_quota.release_token(s, "claims", tok)
        try:
            ping_client.delete(zkey)
        except Exception:  # noqa: BLE001
            pass
        try:
            ping_client.close()
        except Exception:  # noqa: BLE001
            pass
