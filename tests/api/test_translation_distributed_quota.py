"""Translation SSE path with optional distributed quota (Phase 5)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

pytest.importorskip("fakeredis")
from fakeredis import FakeRedis  # noqa: E402

from science_graphrag.api import main as api_main
from science_graphrag.config import Settings
from science_graphrag.llm import redis_quota


@pytest.fixture(autouse=True)
def _cleanup_fake_redis() -> None:
    yield
    redis_quota.set_quota_redis_client_override(None)
    redis_quota.reset_quota_redis_client_for_tests()


def test_translate_sse_ok_with_distributed_quota_enabled() -> None:
    r = FakeRedis(decode_responses=True)
    redis_quota.set_quota_redis_client_override(r)
    s = Settings.model_validate(
        {
            "llm_distributed_quota_enabled": True,
            "llm_distributed_quota_key_prefix": "test:tr_sse",
            "llm_distributed_quota_acquire_timeout_seconds": 5.0,
            "llm_distributed_quota_lease_seconds": 60,
            "llm_concurrency_translation": 2,
        }
    )
    with patch("science_graphrag.api.translation.get_settings", return_value=s):
        client = TestClient(api_main.app)
        res = client.post("/v1/works/ws-test/translate/abstract")
    assert res.status_code == 200
    body = res.text
    assert "queued" in body and "done" in body
