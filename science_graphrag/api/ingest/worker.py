"""In-process ingest worker — thin facade over ingestion.jobs execution."""

from __future__ import annotations

from science_graphrag.ingestion.jobs import batch_parent_ingest as _batch
from science_graphrag.ingestion.jobs import single_document_ingest as _jobs

SUPPORTED_SUFFIXES = _jobs.SUPPORTED_SUFFIXES
_append_log = _jobs.append_ingest_job_log
_execute_single_ingest = _jobs.execute_single_ingest
_refresh_parent_job = _batch.refresh_parent_job
_run_batch_thread = _batch.run_batch_thread
_run_ingest_thread = _batch.run_ingest_thread
_sse_progress_canonical_fields = _jobs.sse_progress_canonical_fields

__all__ = [
    "SUPPORTED_SUFFIXES",
    "_append_log",
    "_execute_single_ingest",
    "_refresh_parent_job",
    "_run_batch_thread",
    "_run_ingest_thread",
    "_sse_progress_canonical_fields",
]
