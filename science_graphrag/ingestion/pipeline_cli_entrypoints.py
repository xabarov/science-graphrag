"""CLI-oriented ingestion entrypoints (batch + single-file)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from science_graphrag.config import Settings, get_settings
from science_graphrag.embeddings.preflight import probe_embeddings
from science_graphrag.ingestion import _pipeline_impl as _pimpl
from science_graphrag.ingestion.corpus_discovery import discover_corpus_files
from science_graphrag.ingestion.orchestrator import BatchDeps, run_batch_ingest
from science_graphrag.ingestion.progress_store import default_progress_file
from science_graphrag.observability.phoenix_tracer import init_tracer_provider
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.pipeline")


def _run_dedup_audit(settings: Settings) -> None:
    """Run post-batch Neo4j Work dedup audit and log clusters (used by batch CLI)."""
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        violations = neo.find_work_dedup_violations()
    finally:
        neo.close()

    logger.info("--- Work dedup audit (Neo4j) ---")
    if not violations:
        logger.info(
            "OK: no duplicate Work clusters by doi / openalex_id / fingerprint / arxiv_id",
        )
        return
    logger.info("Found %s duplicate cluster(s):", len(violations))
    for item in violations:
        logger.info(
            "  [%s] key=%r work_ids=%s",
            item["kind"],
            item["dedup_key"],
            item["work_ids"],
        )


def run_ingest_batch_cli(
    directory: Path,
    *,
    continue_on_error: bool = False,
    settings: Settings | None = None,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    per_file_timeout_s: int = 900,
    resume: bool = False,
    progress_file: Path | None = None,
    embeddings_preflight: bool = False,
    bypass_markdown_cache: bool = False,
) -> list[dict[str, Any]]:
    """
    Ingest every ``.pdf`` / ``.md`` / ``.txt`` under ``directory`` (recursive).

    Prints a per-file summary and a post-hoc Neo4j :Work dedup audit
    (duplicate clusters by DOI, OpenAlex id, fingerprint, arXiv id).
    """

    init_tracer_provider()
    s = settings or get_settings()
    if embeddings_preflight:
        probe_embeddings(s)
    engine = get_engine(s.database_url)
    init_db(engine)
    progress_path = progress_file or default_progress_file()
    rows = run_batch_ingest(
        directory,
        deps=BatchDeps(
            discover_corpus_files=discover_corpus_files,
            ingest_document=_pimpl.ingest_document,
            session_factory=session_factory,
        ),
        settings=s,
        engine=engine,
        progress_file=progress_path,
        continue_on_error=continue_on_error,
        skip_existing_sha=skip_existing_sha,
        force_new_document=force_new_document,
        per_file_timeout_s=per_file_timeout_s,
        resume=resume,
        duplicate_error_type=_pimpl.SkippedDuplicateIngestError,
        bypass_markdown_cache=bypass_markdown_cache,
    )

    _run_dedup_audit(s)
    return rows


def run_ingest_cli(
    path: Path,
    *,
    skip_existing_sha: bool = False,
    force_new_document: bool = False,
    embeddings_preflight: bool = False,
    bypass_markdown_cache: bool = False,
) -> None:
    """CLI helper for single-file ingest."""
    init_tracer_provider()
    s = get_settings()
    if embeddings_preflight:
        probe_embeddings(s)
    engine = get_engine(s.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        try:
            doc_id, work_id = _pimpl.ingest_document(
                path,
                settings=s,
                session=session,
                skip_existing_sha=skip_existing_sha,
                force_new_document=force_new_document,
                bypass_markdown_cache=bypass_markdown_cache,
            )
            logger.info("document_id=%s work_id=%s", doc_id, work_id)
        except _pimpl.SkippedDuplicateIngestError as dup:
            logger.info(
                "SKIP duplicate sha256=%s document_id=%s",
                dup.sha256,
                dup.document_id,
            )


__all__ = ["run_ingest_batch_cli", "run_ingest_cli"]
