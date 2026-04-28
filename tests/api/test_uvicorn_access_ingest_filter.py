"""Uvicorn access log filter for ingest job polling noise."""

from __future__ import annotations

import logging

import pytest

from science_graphrag.api.main import _uvicorn_access_allow_record


def _record(msg: str, level: int = logging.INFO) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


@pytest.mark.parametrize(
    ("msg", "expected_allow"),
    [
        ('127.0.0.1 - "GET /v1/ingest/jobs/j1 HTTP/1.1" 200', False),
        ('127.0.0.1 - "GET /v1/ingest/jobs/j1?debug=1 HTTP/1.1" 200', True),
        ('127.0.0.1 - "GET /v1/ingest/jobs/j1?x=1&debug=true HTTP/1.1" 200', True),
        ('127.0.0.1 - "GET /v1/health HTTP/1.1" 200', True),
        ('127.0.0.1 - "GET /v1/ingest/jobs/j1 HTTP/1.1" 500', True),
    ],
)
def test_uvicorn_ingest_poll_suppression(msg: str, expected_allow: bool) -> None:
    assert _uvicorn_access_allow_record(_record(msg)) is expected_allow
