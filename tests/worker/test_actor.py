"""Tests for Wave W Dramatiq ingest actor."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from science_graphrag.worker.actor import ingest_document_actor


def test_ingest_document_actor_skips_completed_job() -> None:
    mock_job = MagicMock()
    mock_job.kind = "single"
    mock_job.status = "completed"

    with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
        with patch("science_graphrag.worker.actor._registry") as mock_registry:
            reg = mock_registry.return_value
            reg.get_job.return_value = mock_job
            with patch("science_graphrag.worker.actor._execute_single_ingest") as mock_execute:
                ingest_document_actor.fn("job-123")
                mock_execute.assert_not_called()


def test_ingest_document_actor_skips_missing_job() -> None:
    with patch("science_graphrag.worker.actor.get_settings") as mock_settings:
        mock_settings.return_value = SimpleNamespace(blob_root=Path("/tmp"))
        with patch("science_graphrag.worker.actor._registry") as mock_registry:
            reg = mock_registry.return_value
            reg.get_job.return_value = None
            with patch("science_graphrag.worker.actor._execute_single_ingest") as mock_execute:
                ingest_document_actor.fn("job-missing")
                mock_execute.assert_not_called()
