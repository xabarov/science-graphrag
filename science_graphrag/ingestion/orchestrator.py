"""Batch ingest orchestration seams used by CLI entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from pathlib import Path
from typing import Any, Callable

from science_graphrag.ingestion.document_runtime import file_timeout
from science_graphrag.ingestion.progress_store import append_progress, load_progress
from science_graphrag.utils.project_logging import get_logger

logger = get_logger("ingestion.orchestrator")


@dataclass(slots=True)
class BatchDeps:
    """Injectable dependencies for batch ingest flow."""

    discover_corpus_files: Callable[[Path], list[Path]]
    ingest_document: Callable[..., tuple[str, str]]
    session_factory: Callable[[Any], Any]


def run_batch_ingest(
    directory: Path,
    *,
    deps: BatchDeps,
    settings: Any,
    engine: Any,
    progress_file: Path,
    continue_on_error: bool,
    skip_existing_sha: bool,
    force_new_document: bool,
    per_file_timeout_s: int,
    resume: bool,
    duplicate_error_type: type[Exception] | None = None,
    bypass_markdown_cache: bool = False,
) -> list[dict[str, Any]]:
    """Run ingest-corpus batch with resume/timeout/progress semantics."""
    paths = deps.discover_corpus_files(directory)
    if not paths:
        logger.warning("No ingestible files under %s", directory)
        logger.info("No .pdf/.md/.txt files found.")
        return []

    progress_by_path = load_progress(progress_file) if resume else {}
    rows: list[dict[str, Any]] = []
    ingest_one = deps.ingest_document
    if bypass_markdown_cache:
        ingest_one = partial(deps.ingest_document, bypass_markdown_cache=True)

    factory = deps.session_factory(engine)
    for path in paths:
        resolved_path = str(path.resolve())
        if resume and progress_by_path.get(resolved_path) == "ok":
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": None,
                    "skipped_duplicate": False,
                    "status": "skip",
                },
            )
            logger.info("SKIP resumed=ok path=%s", path)
            continue

        started_at = datetime.now(UTC)
        try:
            with factory() as db_session:
                with file_timeout(per_file_timeout_s):
                    doc_id, work_id = ingest_one(
                        path,
                        settings=settings,
                        session=db_session,
                        skip_existing_sha=skip_existing_sha,
                        force_new_document=force_new_document,
                    )
            finished_at = datetime.now(UTC)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": doc_id,
                    "work_id": work_id,
                    "error": None,
                    "skipped_duplicate": False,
                    "status": "ok",
                },
            )
            append_progress(
                progress_file,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "ok",
                    "document_id": doc_id,
                    "work_id": work_id,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": None,
                },
            )
            logger.info("OK path=%s document_id=%s work_id=%s", path, doc_id, work_id)
        except TimeoutError as exc:
            finished_at = datetime.now(UTC)
            logger.exception("Ingest timeout for %s", path)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": str(exc),
                    "skipped_duplicate": False,
                    "status": "timeout",
                },
            )
            append_progress(
                progress_file,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "timeout",
                    "document_id": None,
                    "work_id": None,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": str(exc),
                },
            )
            logger.info("FAIL_TIMEOUT path=%s error=%s", path, exc)
            if not continue_on_error:
                break
        except Exception as exc:  # pylint: disable=broad-exception-caught  # batch ingest boundary
            if duplicate_error_type is not None and isinstance(exc, duplicate_error_type):
                finished_at = datetime.now(UTC)
                document_id = str(getattr(exc, "document_id", ""))
                sha256 = str(getattr(exc, "sha256", "")) or None
                rows.append(
                    {
                        "path": resolved_path,
                        "document_id": document_id or None,
                        "work_id": None,
                        "error": None,
                        "skipped_duplicate": True,
                        "status": "skip",
                    },
                )
                append_progress(
                    progress_file,
                    {
                        "path": resolved_path,
                        "sha256": sha256,
                        "status": "skip",
                        "document_id": document_id or None,
                        "work_id": None,
                        "started_at": started_at.isoformat(),
                        "finished_at": finished_at.isoformat(),
                        "error": None,
                    },
                )
                logger.info(
                    "SKIP duplicate-sha path=%s document_id=%s",
                    path,
                    document_id,
                )
                continue

            finished_at = datetime.now(UTC)
            logger.exception("Ingest failed for %s", path)
            rows.append(
                {
                    "path": resolved_path,
                    "document_id": None,
                    "work_id": None,
                    "error": str(exc),
                    "skipped_duplicate": False,
                    "status": "fail",
                },
            )
            append_progress(
                progress_file,
                {
                    "path": resolved_path,
                    "sha256": None,
                    "status": "fail",
                    "document_id": None,
                    "work_id": None,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "error": str(exc),
                },
            )
            logger.info("FAIL path=%s error=%s", path, exc)
            if not continue_on_error:
                break

    return rows
