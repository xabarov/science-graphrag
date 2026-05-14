"""Compatibility shim: ingest registry moved to ingestion.jobs."""

from science_graphrag.ingestion.jobs.registry import (
    IngestJobRegistry,
    _registry,
    get_ingest_job_registry,
    reset_ingest_job_registry_for_tests,
)

__all__ = [
    "IngestJobRegistry",
    "_registry",
    "get_ingest_job_registry",
    "reset_ingest_job_registry_for_tests",
]
