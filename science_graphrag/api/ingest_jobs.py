"""Backward-compatible shim for ingest API split."""

from science_graphrag.api.ingest.dispatcher import (
    BATCH_MAX_FILES,
    SUPPORTED_SUFFIXES,
    _append_log,
    job_to_dict,
    start_batch_ingest_job,
    start_ingest_job,
)
from science_graphrag.api.ingest.dto import IngestJobEvent, IngestJobRecord, IngestJobView, IngestStageView
from science_graphrag.api.ingest.registry import IngestJobRegistry, _registry
from science_graphrag.api.ingest.router import router
from science_graphrag.api.ingest_event_bus import BUS

__all__ = [
    "BATCH_MAX_FILES",
    "BUS",
    "IngestJobEvent",
    "IngestJobRecord",
    "IngestJobRegistry",
    "IngestJobView",
    "IngestStageView",
    "SUPPORTED_SUFFIXES",
    "_append_log",
    "_registry",
    "job_to_dict",
    "router",
    "start_batch_ingest_job",
    "start_ingest_job",
]
