"""Facade module for ingestion pipeline orchestration.

Heavy implementation lives in `_pipeline_impl.py` to keep this module small and
navigable; public API remains backward-compatible.

Compatibility note:
- Private `_...` exports are transitional and subject to sunset.
- Prefer stable public entrypoints listed in `__all__`.
"""

from __future__ import annotations

from science_graphrag.ingestion._pipeline_impl import (
    CORPUS_SUPPORTED_SUFFIXES,
    IngestResult,
    IngestSource,
    SkippedDuplicateIngestError,
    _markdown_from_path,
    _normalize_arxiv_id,
    _normalized_title_for_fingerprint,
    _openalex_lookup_with_retry,
    _persist_reference_citation,
    _resolve_document_id_for_sha,
    _resolve_work_id,
    _retry_call,
    _venue_id,
    _write_extraction_diagnostics_json,
    _write_markdown_artifact,
    discover_corpus_files,
    fetch_work_by_doi,
    ingest_document,
    run_ingest_batch_cli,
    run_ingest_cli,
    run_ingest_from_file,
    run_ingest_from_job,
    run_ingest_pipeline,
    uuid,
)
from science_graphrag.ingestion.artifact_layout import strip_ingest_artifact_header
from science_graphrag.ingestion.cache_policy import (
    article_slug,
    canonical_article_rel,
    canonical_diagnostics_rel,
    read_cached_markdown,
    slug,
)
from science_graphrag.ingestion.embed_phase import run_ingest_embed_qdrant_phase
from science_graphrag.ingestion.resume_ingest import resume_document_embed_phase

_slug = slug
_article_slug = article_slug
_canonical_article_rel = canonical_article_rel
_canonical_diagnostics_rel = canonical_diagnostics_rel
_read_cached_markdown = read_cached_markdown
_strip_artifact_header = strip_ingest_artifact_header

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
    "run_ingest_batch_cli",
    "run_ingest_cli",
    "run_ingest_embed_qdrant_phase",
    "run_ingest_from_file",
    "run_ingest_from_job",
    "run_ingest_pipeline",
    # Transitional compatibility exports; scheduled for sunset.
    "_slug",
    "_article_slug",
    "_canonical_article_rel",
    "_canonical_diagnostics_rel",
    "_read_cached_markdown",
    "_strip_artifact_header",
    "_markdown_from_path",
    "_normalize_arxiv_id",
    "_normalized_title_for_fingerprint",
    "_openalex_lookup_with_retry",
    "_persist_reference_citation",
    "_resolve_document_id_for_sha",
    "_resolve_work_id",
    "_retry_call",
    "_venue_id",
    "_write_extraction_diagnostics_json",
    "_write_markdown_artifact",
]
