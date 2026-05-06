from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from sqlalchemy import desc, select

from science_graphrag.config import Settings, get_settings
from science_graphrag.cli.config_commands import register as register_config_commands
from science_graphrag.cli.qdrant_commands import register as register_qdrant_commands
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.ingestion.pipeline import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.ingestion.resume_ingest import (
    resume_document_embed_phase,
    resume_document_ingest_stages,
)
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import WorkDedupMergeLog
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore
from science_graphrag.utils.project_logging import (
    configure_logging,
    describe_dramatiq_log_level_env,
    describe_http_log_level_env,
    describe_ingest_log_level_env,
    describe_log_format_env,
)

app = typer.Typer(no_args_is_help=True, help="science-graphrag CLI")


@app.callback()
def _root() -> None:
    """Scholarly GraphRAG — ingestion and graph backbone."""
    configure_logging()


register_qdrant_commands(app)
register_config_commands(app)


@app.command("neo4j-wipe")
def neo4j_wipe_cmd() -> None:
    """Remove all nodes and relationships from the configured Neo4j database."""
    s = get_settings()
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        neo.wipe_all()
    finally:
        neo.close()
    typer.echo("Neo4j database wiped.")


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


@app.command("merge-work")
def merge_work_cmd(
    keep_id: str = typer.Argument(..., help="Canonical Work.id to keep"),
    drop_id: str = typer.Argument(..., help="Duplicate Work.id to re-point and delete"),
) -> None:
    """Re-point citations / semantic edges onto keep_id; re-bind authorships; delete drop_id."""

    s = get_settings()
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        dropped = neo.merge_work_into_canonical(keep_id, drop_id)
    finally:
        neo.close()
    if dropped:
        dim = resolve_embedding_dim(settings=s)
        q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
        n = q.repoint_work_id_payload(from_work_id=drop_id, to_work_id=keep_id)
        qw = QdrantWorkEmbeddingStore(
            s.qdrant_url,
            s.qdrant_work_embeddings_collection,
            vector_dim=dim,
        )
        we = qw.delete_by_work_id(work_id=drop_id)
        typer.echo(
            f"Neo4j: merged into keep={keep_id}, removed drop={drop_id}. "
            f"Qdrant: repointed {n} chunk(s); work_embeddings removed={we}."
        )
    else:
        typer.echo(f"Neo4j: merge did not complete for drop={drop_id}. keep={keep_id}")


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


@app.command("merge-catalog-audit")
def merge_catalog_audit_cmd() -> None:
    """Author/institution merge catalog — policy checklist (Wave H2 scaffold).

    Full clients (Crossref/ORCID/ROR) are not wired here yet; this command prints
    the canonical doc pointer for operators.
    """

    typer.echo(
        "merge-catalog-audit: no external API calls in this build.\n"
        "See docs/specs/merge-catalog-wave-h.md and docs/adr/009-author-institution-merge-catalog.md"
    )


@app.command("dedup-merge-audit")
def dedup_merge_audit_cmd(
    workspace_id: str | None = typer.Option(
        None,
        "--workspace-id",
        help="If set, only merge log rows for this workspace.",
    ),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
) -> None:
    """Print Postgres work_dedup_merge_log rows (Wave L audit; reverse merge not automated)."""

    s = get_settings()
    engine = get_engine(s.database_url)
    init_db(engine)
    factory = session_factory(engine)
    with factory() as session:
        q = select(WorkDedupMergeLog).order_by(desc(WorkDedupMergeLog.created_at)).limit(limit)
        if workspace_id:
            q = q.where(WorkDedupMergeLog.workspace_id == workspace_id.strip())
        rows = list(session.scalars(q).all())
    if not rows:
        typer.echo("No merge log rows.")
        return
    for r in rows:
        typer.echo(
            f"{r.created_at.isoformat() if r.created_at else ''} "
            f"ws={r.workspace_id} keep={r.keep_work_id} drop={r.drop_work_id} conflict={r.conflict_id or '—'}",
        )


@app.command("work-dedup-report")
def work_dedup_report_cmd(
    as_json: bool = typer.Option(False, "--json", help="Emit JSON instead of plain text rows."),
    fail_on_clusters: bool = typer.Option(
        False,
        "--fail-on-clusters",
        help="Exit 2 when duplicate clusters are present (for CI/nightly checks).",
    ),
) -> None:
    """List Work dedup clusters from Neo4j (read-only; Wave H3 prep)."""

    s = get_settings()
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        rows = neo.find_work_dedup_violations()
    finally:
        neo.close()
    if as_json:
        typer.echo(json.dumps(rows, indent=2, default=str))
        if fail_on_clusters and rows:
            raise typer.Exit(code=2)
        return
    if not rows:
        typer.echo("No duplicate Work clusters reported by find_work_dedup_violations().")
        return
    typer.echo(f"Clusters: {len(rows)}")
    for row in rows[:200]:
        typer.echo(f"- {row.get('dedup_key')}: {row.get('work_ids')}")
    if len(rows) > 200:
        typer.echo(f"... truncated ({len(rows)} total); use --json for full dump.")
    if fail_on_clusters:
        raise typer.Exit(code=2)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
