"""Dramatiq actor for ingest execution."""

from __future__ import annotations

import logging
import os
import tempfile
import time
from pathlib import Path

import dramatiq

from science_graphrag.config import get_settings
from science_graphrag.ingestion.jobs.registry import get_ingest_job_registry
from science_graphrag.ingestion.jobs.single_document_ingest import execute_single_ingest
from science_graphrag.observability.ingest_metrics import (
    observe_ingest_job_started,
    observe_ingest_job_terminal,
)
from science_graphrag.storage.ingest_queue_store import build_ingest_queue_store
from science_graphrag.utils.log_context import ingest_log_context
from science_graphrag.utils.project_logging import configure_logging

configure_logging()

logger = logging.getLogger(__name__)


def _queued_blob_path(job_id: str, filename: str, settings) -> Path:
    suffix = Path(filename or "upload").suffix.lower()
    return Path(settings.blob_root) / "_ingest_queue" / f"{job_id}{suffix}"


@dramatiq.actor(queue_name="ingest", max_retries=0)
def ingest_document_actor(job_id: str) -> None:
    """Run ingest for a queued job id."""
    t_entry = time.perf_counter()

    def _duration_ms(since: float) -> int:
        return int((time.perf_counter() - since) * 1000)

    settings = get_settings()
    registry = get_ingest_job_registry(settings)
    registry.bootstrap()
    job = registry.get_job(job_id)
    if job is None:
        logger.error(
            "Ingest actor: missing job_id=%s duration_ms=%s",
            job_id,
            _duration_ms(t_entry),
        )
        return
    if job.kind not in ("single", "batch_child"):
        logger.info(
            "Ingest actor: skipping unsupported kind job_id=%s kind=%s duration_ms=%s",
            job_id,
            job.kind,
            _duration_ms(t_entry),
            extra={"stage": "actor_terminal"},
        )
        return
    if job.status in {"completed", "failed", "running"}:
        logger.info(
            "Ingest actor: skip (job not actionable) job_id=%s status=%s duration_ms=%s",
            job_id,
            job.status,
            _duration_ms(t_entry),
            extra={"stage": "actor_terminal"},
        )
        return

    if not registry.claim_queued_job(job_id):
        logger.info(
            "Ingest actor: job_id=%s already claimed by another worker, skipping duration_ms=%s",
            job_id,
            _duration_ms(t_entry),
            extra={"stage": "actor_terminal"},
        )
        return

    ws_id = (job.workspace_id or "").strip() or None
    downloaded: Path | None = None
    t_claimed = time.perf_counter()
    with ingest_log_context(job_id=job_id, workspace_id=ws_id):
        try:
            logger.info(
                "Ingest actor: claimed job; running pipeline",
                extra={"stage": "actor_pipeline"},
            )
            observe_ingest_job_started(settings, getattr(job, "kind", "") or "unknown")
            if job.queued_source_object_key:
                suffix = Path(job.filename or "upload").suffix.lower() or ".bin"
                fd, name = tempfile.mkstemp(prefix=f"ingest-{job_id}-", suffix=suffix)
                try:
                    os.close(fd)
                except OSError:
                    pass
                downloaded = Path(name)
                build_ingest_queue_store(settings).get_to_path(
                    job.queued_source_object_key, downloaded
                )
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
                        "Ingest actor: missing source path for job_id=%s path=%s duration_ms=%s",
                        job_id,
                        source_path,
                        _duration_ms(t_claimed),
                    )
                    return

            execute_single_ingest(job_id, source_path, settings)
        finally:
            refreshed = registry.get_job(job_id)
            term_status = (
                (getattr(refreshed, "status", "") or "unknown").strip()
                if refreshed is not None
                else "unknown"
            )
            logger.info(
                "Ingest actor: terminal job_id=%s kind=%s status=%s duration_ms=%s",
                job_id,
                getattr(job, "kind", ""),
                term_status,
                _duration_ms(t_claimed),
                extra={"stage": "actor_terminal"},
            )
            observe_ingest_job_terminal(
                settings,
                kind=getattr(job, "kind", "") or "unknown",
                status=term_status,
                duration_seconds=_duration_ms(t_claimed) / 1000.0,
            )
            if downloaded is not None:
                try:
                    downloaded.unlink(missing_ok=True)
                except OSError:
                    pass
