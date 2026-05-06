"""Ingest-related CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.pipeline import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.ingestion.resume_ingest import (
    resume_document_embed_phase,
    resume_document_ingest_stages,
)
from science_graphrag.storage.db import get_engine, init_db, session_factory


def register(app: typer.Typer) -> None:
    """Register ingest commands on root app."""

    @app.command("ingest-resume-embed")
    def ingest_resume_embed_cmd(
        document_id: str = typer.Argument(..., help="documents.id (UUID) with artifacts + work_id"),
    ) -> None:
        """Re-run Qdrant embedding stage only (recovery after OpenRouter/embed failures)."""
        s = get_settings()
        engine = get_engine(s.database_url)
        init_db(engine)
        factory = session_factory(engine)
        with factory() as session:
            work_id = resume_document_embed_phase(
                document_id=document_id.strip(),
                settings=s,
                session=session,
                ingest_workspace_ids=None,
                job_id=None,
                stage_session_factory=None,
                stage_event_publisher=None,
            )
        typer.echo(f"OK document_id={document_id} work_id={work_id}")

    @app.command("ingest-resume")
    def ingest_resume_cmd(
        document_id: str = typer.Argument(..., help="documents.id (UUID) with artifacts + work_id"),
        stages: str = typer.Option(
            "embed",
            "--stages",
            help=(
                "Comma-separated late-stage resume set. "
                "Supported: embed, claims, references (order is normalized automatically)."
            ),
        ),
    ) -> None:
        """Resume selected late ingest stages (recovery after partial failures)."""
        s = get_settings()
        engine = get_engine(s.database_url)
        init_db(engine)
        factory = session_factory(engine)
        with factory() as session:
            work_id = resume_document_ingest_stages(
                document_id=document_id.strip(),
                stages_csv=stages,
                settings=s,
                session=session,
                ingest_workspace_ids=None,
                job_id=None,
                stage_session_factory=None,
                stage_event_publisher=None,
            )
        typer.echo(f"OK document_id={document_id} work_id={work_id}")

    @app.command("ingest")
    def ingest_cmd(
        path: Path = typer.Argument(
            ...,
            exists=True,
            readable=True,
            help="PDF, .txt, or .md (markdown read as article text)",
        ),
        skip_existing_sha: bool = typer.Option(
            False,
            "--skip-existing-sha",
            help="If file bytes already in Postgres (sha256), exit without re-ingesting.",
        ),
        force_new_document: bool = typer.Option(
            False,
            "--force-new-document",
            help="Always allocate a new document_id (no sha256 reuse in SQL).",
        ),
        embeddings_preflight: bool = typer.Option(
            False,
            "--embeddings-preflight/--no-embeddings-preflight",
            help="Probe embeddings API once before ingest (OpenRouter when configured).",
        ),
        no_cache: bool = typer.Option(
            False,
            "--no-cache",
            help="Bypass disk markdown cache for PDFs even when reuse_cached_markdown=true.",
        ),
    ) -> None:
        """Run Phase 1 ingestion pipeline for one document."""
        run_ingest_cli(
            path,
            skip_existing_sha=skip_existing_sha,
            force_new_document=force_new_document,
            embeddings_preflight=embeddings_preflight,
            bypass_markdown_cache=no_cache,
        )

    @app.command("ingest-corpus")
    def ingest_corpus_cmd(
        directory: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            help="Directory tree to scan for .pdf, .md, and .txt files",
        ),
        continue_on_error: bool = typer.Option(
            False,
            "--continue-on-error",
            help="Log failures and continue with remaining files",
        ),
        skip_existing_sha: bool = typer.Option(
            False,
            "--skip-existing-sha",
            help="Skip files whose sha256 is already in documents table.",
        ),
        force_new_document: bool = typer.Option(
            False,
            "--force-new-document",
            help="Never reuse document_id by sha256 (new row per file run).",
        ),
        per_file_timeout_s: int = typer.Option(
            900,
            "--per-file-timeout-s",
            min=0,
            help="Hard wall timeout (seconds) per file; 0 disables timeout.",
        ),
        resume: bool = typer.Option(
            False,
            "--resume/--no-resume",
            help="Skip files with status=ok in progress JSONL.",
        ),
        progress_file: Path | None = typer.Option(
            None,
            "--progress-file",
            help="Path to ingest progress JSONL checkpoint file.",
        ),
        embeddings_preflight: bool = typer.Option(
            False,
            "--embeddings-preflight/--no-embeddings-preflight",
            help="Call embeddings API once before scanning files (OpenRouter channel only).",
        ),
        no_cache: bool = typer.Option(
            False,
            "--no-cache",
            help="Bypass disk markdown cache for PDFs even when reuse_cached_markdown=true.",
        ),
    ) -> None:
        """Batch-ingest a corpus directory and print Work-level dedup audit for Neo4j."""
        run_ingest_batch_cli(
            directory,
            continue_on_error=continue_on_error,
            skip_existing_sha=skip_existing_sha,
            force_new_document=force_new_document,
            per_file_timeout_s=per_file_timeout_s,
            resume=resume,
            progress_file=progress_file,
            embeddings_preflight=embeddings_preflight,
            bypass_markdown_cache=no_cache,
        )
