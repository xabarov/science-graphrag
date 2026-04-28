"""Tests for throttled non-VL pipeline stage logging."""

from __future__ import annotations

import logging

import pytest

from science_graphrag.utils.ingest_pipeline_log_heartbeat import (
    maybe_log_ingest_pipeline_progress_throttled,
    maybe_log_ingest_pipeline_stage_entry,
    pipeline_log_heartbeat_run,
)


def test_stage_entry_logs_each_new_stage_only_once(caplog: pytest.LogCaptureFixture) -> None:
    log = logging.getLogger("science_graphrag.test_pipe")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_pipe"):
        with pipeline_log_heartbeat_run():
            maybe_log_ingest_pipeline_stage_entry(log, stage_name="parse_pdf")
            maybe_log_ingest_pipeline_stage_entry(log, stage_name="parse_pdf")
            maybe_log_ingest_pipeline_stage_entry(log, stage_name="embed")
    msgs = [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]
    assert msgs.count("Ingest pipeline stage=parse_pdf") == 1
    assert "Ingest pipeline stage=embed" in msgs


def test_progress_throttled_by_interval(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("SCIENCE_GRAPHRAG_INGEST_PIPELINE_LOG_HEARTBEAT_SECONDS", "60")
    log = logging.getLogger("science_graphrag.test_pipe_prog")
    with caplog.at_level(logging.INFO, logger="science_graphrag.test_pipe_prog"):
        with pipeline_log_heartbeat_run():
            maybe_log_ingest_pipeline_progress_throttled(log, stage_name="embed")
            maybe_log_ingest_pipeline_progress_throttled(log, stage_name="embed")
    assert len([r for r in caplog.records if "progress" in r.getMessage()]) == 1
