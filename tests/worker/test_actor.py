"""Tests for Wave W Dramatiq ingest actor."""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from science_graphrag.worker.actor import ingest_document_actor


def test_ingest_document_actor_skips_completed_job() -> None:
    mock_job = MagicMock()
    mock_job.kind = "single"
    mock_job.status = "completed"
    mock_job.queued_source_object_key = None

    with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
        with patch("science_graphrag.worker.actor.get_ingest_job_registry") as mock_registry:
            reg = mock_registry.return_value
            reg.get_job.return_value = mock_job
            with patch("science_graphrag.worker.actor.execute_single_ingest") as mock_execute:
                ingest_document_actor.fn("job-123")
                mock_execute.assert_not_called()


def test_ingest_document_actor_skips_missing_job() -> None:
    with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
        with patch("science_graphrag.worker.actor.get_ingest_job_registry") as mock_registry:
            reg = mock_registry.return_value
            reg.get_job.return_value = None
            with patch("science_graphrag.worker.actor.execute_single_ingest") as mock_execute:
                ingest_document_actor.fn("job-missing")
                mock_execute.assert_not_called()


def test_ingest_document_actor_runs_batch_child_queued_job() -> None:
    """Batch uploads enqueue ``batch_child`` rows; actor must not skip them."""
    mock_job = MagicMock()
    mock_job.kind = "batch_child"
    mock_job.status = "queued"
    mock_job.filename = "paper.pdf"
    mock_job.parent_job_id = "parent-1"
    mock_job.queued_source_object_key = "s3://fake/key"

    with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
        with patch("science_graphrag.worker.actor.get_ingest_job_registry") as mock_registry:
            with patch("science_graphrag.worker.actor.build_ingest_queue_store") as mock_store:
                with patch("science_graphrag.worker.actor.tempfile.mkstemp") as mock_mkstemp:
                    mock_mkstemp.return_value = (3, "/tmp/fake-ingest.pdf")
                    with patch("science_graphrag.worker.actor.os.close"):
                        exec_patch = patch("science_graphrag.worker.actor.execute_single_ingest")
                        with exec_patch as mock_execute:
                            reg = mock_registry.return_value
                            reg.get_job.return_value = mock_job
                            reg.claim_queued_job.return_value = True
                            mock_store.return_value.get_to_path = MagicMock()
                            ingest_document_actor.fn("job-child-1")
                            reg.claim_queued_job.assert_called_once_with("job-child-1")
                            mock_execute.assert_called_once()


def test_ingest_document_actor_logs_terminal_status_after_pipeline(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """After pipeline, actor logs INFO with DB status (completed/failed, etc.)."""
    mock_job = MagicMock()
    mock_job.kind = "batch_child"
    mock_job.status = "queued"
    mock_job.filename = "paper.pdf"
    mock_job.workspace_id = "ws-1"
    mock_job.queued_source_object_key = "s3://fake/key"

    refreshed = MagicMock()
    refreshed.status = "completed"

    with caplog.at_level(logging.INFO, logger="science_graphrag.worker.actor"):
        with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
            mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
            with patch("science_graphrag.worker.actor.get_ingest_job_registry") as mock_registry:
                with patch("science_graphrag.worker.actor.build_ingest_queue_store") as mock_store:
                    with patch("science_graphrag.worker.actor.tempfile.mkstemp") as mock_mkstemp:
                        mock_mkstemp.return_value = (3, "/tmp/fake-ingest.pdf")
                        with patch("science_graphrag.worker.actor.os.close"):
                            with patch(
                                "science_graphrag.worker.actor.execute_single_ingest"
                            ) as mock_execute:
                                reg = mock_registry.return_value
                                reg.get_job.side_effect = [mock_job, refreshed]
                                reg.claim_queued_job.return_value = True
                                mock_store.return_value.get_to_path = MagicMock()
                                ingest_document_actor.fn("job-child-1")

    assert reg.get_job.call_count == 2
    terminal_msgs = [
        r.getMessage()
        for r in caplog.records
        if r.message and "Ingest actor: terminal job_id=job-child-1" in r.getMessage()
    ]
    assert terminal_msgs, "expected terminal INFO line"
    assert any("status=completed" in m for m in terminal_msgs)
    assert any("kind=batch_child" in m for m in terminal_msgs)
