from __future__ import annotations

"""Facade module for ingestion pipeline orchestration.

Heavy implementation lives in `_pipeline_impl.py` to keep this module small and
navigable; public API remains backward-compatible.
"""

from science_graphrag.ingestion._pipeline_impl import (
    CORPUS_SUPPORTED_SUFFIXES,
    IngestResult,
    IngestSource,
    SkippedDuplicateIngestError,
    _article_slug,
    _canonical_article_rel,
    _canonical_diagnostics_rel,
    _markdown_from_path,
    _normalize_arxiv_id,
    _normalized_title_for_fingerprint,
    _openalex_lookup_with_retry,
    _persist_reference_citation,
    _read_cached_markdown,
    _resolve_document_id_for_sha,
    _resolve_work_id,
    _retry_call,
    _slug,
    _strip_artifact_header,
    _venue_id,
    _write_extraction_diagnostics_json,
    _write_markdown_artifact,
    discover_corpus_files,
    fetch_work_by_doi,
    ingest_document,
    run_ingest_batch_cli,
    run_ingest_cli,
    run_ingest_embed_qdrant_phase,
    run_ingest_from_file,
    run_ingest_from_job,
    run_ingest_pipeline,
    uuid,
)
from science_graphrag.ingestion.resume_ingest import resume_document_embed_phase

__all__ = [
    "CORPUS_SUPPORTED_SUFFIXES",
    "IngestResult",
    "IngestSource",
    "SkippedDuplicateIngestError",
    "discover_corpus_files",
    "ingest_document",
    "resume_document_embed_phase",
    "run_ingest_batch_cli",
    "run_ingest_cli",
    "run_ingest_embed_qdrant_phase",
    "run_ingest_from_file",
    "run_ingest_from_job",
    "run_ingest_pipeline",
]
