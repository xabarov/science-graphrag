"""Tests for worker startup compensation (stale ingest jobs)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import science_graphrag.worker as worker_mod


def test_run_compensation_sweep_resets_stale_running_then_enqueues() -> None:
    """Reset orphan ``running`` rows, then re-send Dramatiq for stale ``queued`` jobs."""
    mock_reg = MagicMock()
    mock_reg.reset_stale_running_jobs_to_queued.return_value = ["orphan-1"]
    mock_job = MagicMock()
    mock_job.job_id = "stale-queued-1"
    mock_reg.list_stale_queued_jobs.return_value = [mock_job]

    with patch("science_graphrag.worker.get_ingest_job_registry", return_value=mock_reg):
        with patch("science_graphrag.worker.ingest_document_actor") as mock_actor:
            with patch("science_graphrag.worker.dramatiq_otel_options", return_value={}):
                worker_mod.run_compensation_sweep()

    mock_reg.bootstrap.assert_called_once()
    mock_reg.reset_stale_running_jobs_to_queued.assert_called_once()
    mock_reg.list_stale_queued_jobs.assert_called_once()
    mock_actor.send.assert_called_once_with("stale-queued-1")
