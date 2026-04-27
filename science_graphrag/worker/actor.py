"""Dramatiq actor for ingest execution."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import dramatiq

from science_graphrag.api.ingest.registry import _registry
from science_graphrag.api.ingest.worker import _execute_single_ingest
from science_graphrag.config import get_settings
from science_graphrag.storage.ingest_queue_store import build_ingest_queue_store

logger = logging.getLogger(__name__)


def _queued_blob_path(job_id: str, filename: str, settings) -> Path:
    suffix = Path(filename or "upload").suffix.lower()
    return Path(settings.blob_root) / "_ingest_queue" / f"{job_id}{suffix}"


@dramatiq.actor(queue_name="ingest", max_retries=0)
def ingest_document_actor(job_id: str) -> None:
    """Run ingest for a queued job id."""
    settings = get_settings()
    registry = _registry(settings)
    registry.bootstrap()
    job = registry.get_job(job_id)
    if job is None:
        logger.error("Ingest actor: missing job_id=%s", job_id)
        return
    if job.kind != "single":
        logger.info("Ingest actor: skipping non-single job_id=%s kind=%s", job_id, job.kind)
        return
    if job.status in {"completed", "failed", "running"}:
        logger.info("Ingest actor: terminal/claimed job_id=%s status=%s", job_id, job.status)
        return

    if not registry.claim_queued_job(job_id):
        logger.info("Ingest actor: job_id=%s already claimed by another worker, skipping", job_id)
        return

    downloaded: Path | None = None
    try:
        if job.queued_source_object_key:
            suffix = Path(job.filename or "upload").suffix.lower() or ".bin"
            fd, name = tempfile.mkstemp(prefix=f"ingest-{job_id}-", suffix=suffix)
            try:
                os.close(fd)
            except OSError:
                pass
            downloaded = Path(name)
            build_ingest_queue_store(settings).get_to_path(job.queued_source_object_key, downloaded)
            source_path = downloaded
        else:
            source_path = _queued_blob_path(job_id, job.filename, settings)
            if not source_path.exists():
                registry.mark_failed(
                    job_id,
                    error="ingest_input_missing",
                    message=f"Missing queued source file for job: {source_path.name}",
                )
                logger.error(
                    "Ingest actor: missing source path for job_id=%s path=%s", job_id, source_path
                )
                return

        _execute_single_ingest(job_id, source_path, settings)
    finally:
        if downloaded is not None:
            try:
                downloaded.unlink(missing_ok=True)
            except OSError:
                pass
