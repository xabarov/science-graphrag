"""Redis-backed durable cache for PDF read (cross-process)."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from science_graphrag.agent.tools.external.pdf_read_durable_cache import (
    durable_pdf_read_get,
    durable_pdf_read_put,
    pdf_read_durable_cache_active,
)
from science_graphrag.config import Settings


def test_pdf_read_durable_cache_active_requires_redis_and_flag() -> None:
    st = Settings(redis_url="redis://localhost:6379/0", agent_pdf_read_durable_cache_enabled=True)
    assert pdf_read_durable_cache_active(st) is True
    st2 = Settings(redis_url="", agent_pdf_read_durable_cache_enabled=True)
    assert pdf_read_durable_cache_active(st2) is False
    st3 = Settings(redis_url="redis://localhost:6379/0", agent_pdf_read_durable_cache_enabled=False)
    assert pdf_read_durable_cache_active(st3) is False


def test_durable_pdf_roundtrip_with_fakeredis() -> None:
    pytest.importorskip("redis")
    import fakeredis  # type: ignore[import-untyped]

    server = fakeredis.FakeServer()
    fake = fakeredis.FakeStrictRedis(server=server, decode_responses=True)
    st = Settings(
        redis_url="redis://unused:6379/0",
        agent_pdf_read_durable_cache_enabled=True,
    )
    key = '{"url":"https://example.com/a.pdf","max_excerpt_chars":512,"max_pages":2,"read_backend":"pypdf"}'
    payload = {"ok": True, "row_count": 1, "summary": "hello", "web_sources": []}

    with patch(
        "science_graphrag.agent.tools.external.pdf_read_durable_cache.redis.Redis.from_url",
        return_value=fake,
    ):
        assert durable_pdf_read_get(st, key) is None
        durable_pdf_read_put(st, key, payload, ttl_seconds=120)
        got = durable_pdf_read_get(st, key)
    assert isinstance(got, dict)
    assert got.get("ok") is True
    assert got.get("summary") == "hello"


def test_durable_get_swallows_redis_errors() -> None:
    st = Settings(redis_url="redis://localhost:6379/0", agent_pdf_read_durable_cache_enabled=True)
    with patch(
        "science_graphrag.agent.tools.external.pdf_read_durable_cache.redis.Redis.from_url",
        side_effect=OSError("boom"),
    ):
        assert durable_pdf_read_get(st, "k") is None
