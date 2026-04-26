"""Optional live API checks; skipped unless ``AGENT_LIVE_BASE`` is set.

Run (API must be up, keys in server env)::

    AGENT_LIVE_BASE=http://127.0.0.1:8000 \\
    AGENT_LIVE_WORKSPACE_ID=<uuid> \\
    .venv/bin/pytest tests/live/test_agent_v2_http_optional.py -v
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
import pytest

_REPO = Path(__file__).resolve().parents[2]
_LIVE_PKG = _REPO / "scripts" / "live_check"
if str(_LIVE_PKG) not in sys.path:
    sys.path.insert(0, str(_LIVE_PKG))

from http_suite import (  # noqa: E402  pylint: disable=wrong-import-position,import-error
    check_agent_v2_sse,
    check_agent_v2_sync_json,
    check_health,
    check_multi_turn_digest,
)

pytestmark = pytest.mark.live_api


def _base() -> str:
    return (os.environ.get("AGENT_LIVE_BASE") or "").strip().rstrip("/")


def _workspace() -> str | None:
    w = (os.environ.get("AGENT_LIVE_WORKSPACE_ID") or "").strip()
    return w or None


def _timeout() -> float:
    return float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))


@pytest.mark.skipif(not _base(), reason="AGENT_LIVE_BASE unset")
def test_live_health() -> None:
    """GET /health on AGENT_LIVE_BASE."""
    with httpx.Client(timeout=_timeout()) as client:
        res = check_health(client, _base())
    assert res.ok, res.detail


@pytest.mark.skipif(not _base(), reason="AGENT_LIVE_BASE unset")
def test_live_agent_v2_sync_minimal() -> None:
    """Minimal JSON agent query."""
    with httpx.Client(timeout=_timeout()) as client:
        res = check_agent_v2_sync_json(
            client,
            _base(),
            workspace_id=_workspace(),
            question=os.environ.get("AGENT_LIVE_QUESTION", "Say hello in one short sentence."),
        )
    assert res.ok, res.detail


@pytest.mark.skipif(not _base(), reason="AGENT_LIVE_BASE unset")
@pytest.mark.skipif(
    os.environ.get("AGENT_LIVE_SKIP_MULTI_TURN") == "1",
    reason="AGENT_LIVE_SKIP_MULTI_TURN=1",
)
def test_live_agent_v2_multi_turn() -> None:
    """Two JSON turns with thread_id + history_digest."""
    with httpx.Client(timeout=_timeout()) as client:
        res = check_multi_turn_digest(
            client, _base(), workspace_id=_workspace(), timeout=_timeout()
        )
    assert res.ok, res.detail


@pytest.mark.skipif(not _base(), reason="AGENT_LIVE_BASE unset")
@pytest.mark.skipif(
    (os.environ.get("AGENT_LIVE_GATE_CH4") or "").strip().lower() not in ("1", "true", "yes"),
    reason="AGENT_LIVE_GATE_CH4 not enabled (set to 1 for CH4 strict gate)",
)
def test_live_agent_v2_gate_ch4_sse() -> None:
    """Strict CH4: SSE stream must include context_compacted and session_init in final trace."""
    import uuid

    tid = f"pytest_ch4_{uuid.uuid4().hex[:10]}"
    with httpx.Client(timeout=_timeout()) as client:
        res = check_agent_v2_sse(
            client,
            _base(),
            workspace_id=_workspace(),
            question=os.environ.get(
                "AGENT_LIVE_QUESTION_SSE",
                "One-sentence summary of what an academic GraphRAG system does.",
            ),
            thread_id=tid,
            timeout=_timeout(),
        )
    assert res.ok, res.detail


@pytest.mark.skipif(not _base(), reason="AGENT_LIVE_BASE unset")
@pytest.mark.skipif(
    (os.environ.get("AGENT_LIVE_GATE_CH4") or "").strip().lower() not in ("1", "true", "yes"),
    reason="AGENT_LIVE_GATE_CH4 not enabled (set to 1 for CH4 strict gate)",
)
def test_live_agent_v2_gate_ch4_sync_json_with_thread() -> None:
    """Strict CH4: sync JSON with thread_id must include session_init in tool_trace (parity with SSE gate)."""
    import uuid

    tid = f"pytest_ch4_sync_{uuid.uuid4().hex[:10]}"
    with httpx.Client(timeout=_timeout()) as client:
        res = check_agent_v2_sync_json(
            client,
            _base(),
            workspace_id=_workspace(),
            question=os.environ.get("AGENT_LIVE_QUESTION", "Say hello in one short sentence."),
            thread_id=tid,
        )
    assert res.ok, res.detail
