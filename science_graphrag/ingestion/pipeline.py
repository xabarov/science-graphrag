"""Stable public façade for ingestion entrypoints."""

from __future__ import annotations

import uuid

from science_graphrag.ingestion._pipeline_impl import (
    IngestResult,
    IngestSource,
    SkippedDuplicateIngestError,
    ingest_document,
    run_ingest_from_file,
    run_ingest_from_job,
    run_ingest_pipeline,
)
from science_graphrag.ingestion.corpus_discovery import (
    CORPUS_SUPPORTED_SUFFIXES,
    discover_corpus_files,
)
from science_graphrag.ingestion.embed_phase import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.enrichment.openalex import fetch_work_by_doi
from science_graphrag.ingestion.pipeline_cli_entrypoints import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.ingestion.reference_citations import persist_reference_citation
from science_graphrag.ingestion.resume_ingest import (
    resume_document_embed_phase,
    resume_document_ingest_stages,
)

# Backward-compat alias retained while external scripts migrate imports.
_persist_reference_citation = persist_reference_citation

__all__ = [
    "CORPUS_SUPPORTED_SUFFIXES",
    "IngestResult",
    "IngestSource",
    "SkippedDuplicateIngestError",
    "fetch_work_by_doi",
    "uuid",
    "discover_corpus_files",
    "ingest_document",
    "resume_document_embed_phase",
    "resume_document_ingest_stages",
    "run_ingest_batch_cli",
    "run_ingest_cli",
    "run_ingest_embed_qdrant_phase",
    "run_ingest_from_file",
    "run_ingest_from_job",
    "run_ingest_pipeline",
    # Backward-compat (prefer `persist_reference_citation` import path).
    "persist_reference_citation",
    "_persist_reference_citation",
]
