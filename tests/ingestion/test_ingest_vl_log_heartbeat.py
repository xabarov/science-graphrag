"""Tests for rate-limited VL ingest INFO heartbeats."""

from __future__ import annotations

import logging

import pytest

from science_graphrag.utils import ingest_vl_log_heartbeat as hb
from science_graphrag.utils import project_logging
from science_graphrag.utils.log_context import ingest_log_context
from science_graphrag.utils.project_logging import reset_project_logging_for_tests


@pytest.fixture(autouse=True)
def _reset_project_logging() -> None:
    reset_project_logging_for_tests()
    root_sg = logging.getLogger("science_graphrag")
    root_sg.setLevel(logging.NOTSET)
    yield
    reset_project_logging_for_tests()


def test_page_heartbeat_throttles_by_monotonic_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second progress emit within interval is skipped; next after interval updates state."""
    monkeypatch.setenv("SCIENCE_GRAPHRAG_INGEST_VL_LOG_HEARTBEAT_SECONDS", "60")
    log = logging.getLogger("science_graphrag.test_vl_hb")
    state = hb.VlLogHeartbeatState()
    t0 = 1_000_000.0
    hb.maybe_log_vl_page_heartbeat(log, state, pages_done=1, pages_total=10, now_monotonic=t0)
    hb.maybe_log_vl_page_heartbeat(
        log, state, pages_done=2, pages_total=10, now_monotonic=t0 + 30.0
    )
    hb.maybe_log_vl_page_heartbeat(
        log, state, pages_done=3, pages_total=10, now_monotonic=t0 + 61.0
    )
    assert state.last_emit_monotonic == t0 + 61.0


def test_parse_started_logs_once(caplog: pytest.LogCaptureFixture) -> None:
    """VL start line is emitted once even if batches_ready fires twice."""
    log = logging.getLogger("science_graphrag.test_vl_start")
    state = hb.VlLogHeartbeatState()
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_vl_start"):
        hb.maybe_log_vl_parse_started(log, state, batch_count=3, page_total=12, batch_size=2)
        hb.maybe_log_vl_parse_started(log, state, batch_count=9, page_total=99, batch_size=1)
    assert state.started_logged is True
    assert len(caplog.records) == 1
    assert "batches=3" in caplog.records[0].getMessage()


def test_heartbeat_message_contains_job_id_with_context(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Correlation filter fills job_id on heartbeat lines under ingest_log_context."""
    project_logging.configure_logging()
    log = logging.getLogger("science_graphrag.ingestion.pipeline")
    state = hb.VlLogHeartbeatState()
    with caplog.at_level(logging.INFO, logger="science_graphrag.ingestion.pipeline"):
        with ingest_log_context(job_id="job-vl-hb", workspace_id="ws-1"):
            hb.maybe_log_vl_parse_started(log, state, batch_count=1, page_total=5, batch_size=5)
            hb.maybe_log_vl_page_heartbeat(
                log, state, pages_done=5, pages_total=5, now_monotonic=0.0
            )
            hb.maybe_log_vl_page_heartbeat(
                log, state, pages_done=5, pages_total=5, now_monotonic=100.0
            )
    assert len(caplog.records) >= 2
    for rec in caplog.records:
        assert getattr(rec, "job_id", None) == "job-vl-hb"
        assert getattr(rec, "workspace_id", None) == "ws-1"


def test_vl_page_heartbeat_regression_budget_over_simulated_duration(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Regression: INFO page heartbeats stay bounded vs simulated wall time (default 60s interval)."""
    monkeypatch.setenv("SCIENCE_GRAPHRAG_INGEST_VL_LOG_HEARTBEAT_SECONDS", "60")
    log = logging.getLogger("science_graphrag.test_vl_budget")
    state = hb.VlLogHeartbeatState()
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_vl_budget"):
        for step in range(0, 601, 5):
            hb.maybe_log_vl_page_heartbeat(
                log, state, pages_done=step, pages_total=900, now_monotonic=float(step)
            )
    infos = [r for r in caplog.records if r.levelno == logging.INFO]
    assert len(infos) <= 12
