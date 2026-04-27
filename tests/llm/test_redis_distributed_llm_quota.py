"""Phase 5: Redis-backed global LLM quota (ADR 025)."""

from __future__ import annotations

import pytest

pytest.importorskip("fakeredis")
from fakeredis import FakeRedis  # noqa: E402

from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import (
    llm_pool_slot,
    reset_llm_pool_registry_for_tests,
)
from science_graphrag.llm.redis_quota import (
    DistributedQuotaAcquireTimeout,
    acquire_slot_blocking,
    release_token,
    reset_quota_redis_client_for_tests,
    set_quota_redis_client_override,
    try_acquire_once,
)


@pytest.fixture(autouse=True)
def _cleanup_quota() -> None:
    yield
    set_quota_redis_client_override(None)
    reset_quota_redis_client_for_tests()
    reset_llm_pool_registry_for_tests()


@pytest.fixture
def fake_redis() -> FakeRedis:
    r = FakeRedis(decode_responses=True)
    set_quota_redis_client_override(r)
    return r


def _quota_settings(**kwargs: object) -> Settings:
    base = dict(
        llm_distributed_quota_enabled=True,
        llm_distributed_quota_key_prefix="test:llm_quota",
        llm_distributed_quota_acquire_timeout_seconds=10.0,
        llm_distributed_quota_lease_seconds=120,
        llm_concurrency_claims=2,
        redis_url="redis://127.0.0.1:9/0",
    )
    base.update(kwargs)
    return Settings.model_validate(base)


def test_try_acquire_respects_cap(fake_redis: FakeRedis) -> None:
    s = _quota_settings()
    assert try_acquire_once(s, "claims", "tok-a") is True
    assert try_acquire_once(s, "claims", "tok-b") is True
    assert try_acquire_once(s, "claims", "tok-c") is False
    release_token(s, "claims", "tok-a")
    assert try_acquire_once(s, "claims", "tok-c") is True


def test_acquire_blocking_then_release(fake_redis: FakeRedis) -> None:
    s = _quota_settings()
    tok = acquire_slot_blocking(s, "claims")
    assert tok is not None
    release_token(s, "claims", tok)


def test_acquire_blocking_timeout(fake_redis: FakeRedis) -> None:
    s = _quota_settings(llm_distributed_quota_acquire_timeout_seconds=1.0, llm_concurrency_claims=1)
    t1 = acquire_slot_blocking(s, "claims")
    assert t1 is not None
    try:
        with pytest.raises(DistributedQuotaAcquireTimeout):
            acquire_slot_blocking(s, "claims")
    finally:
        release_token(s, "claims", t1)


def test_llm_pool_slot_holds_distributed_lease(fake_redis: FakeRedis) -> None:
    """Smoke: nested local + distributed acquire/release without error."""

    s = _quota_settings(llm_concurrency_claims=2)
    with llm_pool_slot("claims", s):
        pass


def test_distributed_disabled_no_redis_used() -> None:
    set_quota_redis_client_override(None)
    reset_quota_redis_client_for_tests()
    s = Settings.model_validate(
        {
            "llm_distributed_quota_enabled": False,
            "llm_concurrency_claims": 1,
        }
    )
    with llm_pool_slot("claims", s):
        pass
