"""Phase 2: process-local LLM pool registry."""

from __future__ import annotations

import threading
import time

import pytest

from science_graphrag.config import Settings
from science_graphrag.llm.concurrency import (
    LlmPoolRegistry,
    llm_pool_slot,
    pool_concurrency_limit,
    reset_llm_pool_registry_for_tests,
    settings_llm_concurrency_signature,
)
from science_graphrag.utils.llm_semaphore import (
    get_llm_async_semaphore_map,
    reset_llm_async_semaphore_map_for_tests,
)


def test_pool_concurrency_limit_maps_claims() -> None:
    s = Settings.model_validate({"llm_concurrency_claims": 3})
    assert pool_concurrency_limit(s, "claims") == 3
    assert pool_concurrency_limit(s, "unknown_pool_uses_default") == max(
        1,
        int(s.llm_concurrency_default),
    )


def test_llm_pool_slot_enforces_max_concurrent_claims() -> None:
    reset_llm_pool_registry_for_tests()
    try:
        s = Settings.model_validate({"llm_concurrency_claims": 2})
        concurrent = {"n": 0, "max": 0}
        lock = threading.Lock()

        def worker() -> None:
            with llm_pool_slot("claims", s):
                with lock:
                    concurrent["n"] += 1
                    concurrent["max"] = max(concurrent["max"], concurrent["n"])
                time.sleep(0.06)
                with lock:
                    concurrent["n"] -= 1

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert concurrent["max"] <= 2
    finally:
        reset_llm_pool_registry_for_tests()


def test_llm_pool_slot_releases_on_exception() -> None:
    reset_llm_pool_registry_for_tests()
    try:
        s = Settings.model_validate({"llm_concurrency_claims": 1})
        with pytest.raises(RuntimeError):
            with llm_pool_slot("claims", s):
                raise RuntimeError("boom")
        with llm_pool_slot("claims", s):
            pass
    finally:
        reset_llm_pool_registry_for_tests()


def test_llm_pool_registry_shares_cap_for_same_settings_field() -> None:
    s = Settings.model_validate({"llm_concurrency_default": 1})
    reg = LlmPoolRegistry(s)
    assert reg.slot("metadata") is reg.slot("vl_pdf")


def test_get_llm_async_semaphore_map_cached() -> None:
    reset_llm_async_semaphore_map_for_tests()
    try:
        s = Settings.model_validate({"llm_concurrency_translation": 2})
        m1 = get_llm_async_semaphore_map(s)
        m2 = get_llm_async_semaphore_map(s)
        assert m1["translation"] is m2["translation"]
    finally:
        reset_llm_async_semaphore_map_for_tests()


def test_settings_llm_concurrency_signature_changes_with_semantic_cap() -> None:
    a = Settings.model_validate({"llm_concurrency_semantic": 4})
    b = Settings.model_validate({"llm_concurrency_semantic": 5})
    assert settings_llm_concurrency_signature(a) != settings_llm_concurrency_signature(b)


def test_async_semaphore_map_rebuilt_when_semantic_limit_changes() -> None:
    """Async cache must track full pool signature (shared with threading registry)."""

    reset_llm_async_semaphore_map_for_tests()
    try:
        base = {"llm_concurrency_translation": 2, "llm_concurrency_semantic": 4}
        s1 = Settings.model_validate(base)
        s2 = Settings.model_validate({**base, "llm_concurrency_semantic": 5})
        m1 = get_llm_async_semaphore_map(s1)
        m2 = get_llm_async_semaphore_map(s2)
        assert m1["translation"] is not m2["translation"]
    finally:
        reset_llm_async_semaphore_map_for_tests()
