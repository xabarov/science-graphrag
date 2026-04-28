from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from sqlalchemy import desc, select

from science_graphrag.config import Settings, get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.ingestion.pipeline import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.ingestion.resume_ingest import resume_document_embed_phase
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import WorkDedupMergeLog
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import (
    QdrantChunkStore,
    QdrantWorkEmbeddingStore,
    recreate_all_embedding_collections,
    recreate_qdrant_chunk_collection,
)
from science_graphrag.storage.qdrant_store.recreate_embedding_collections import (
    describe_embedding_collections_cutover,
)
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
) -> None:
    """Run Phase 1 ingestion pipeline for one document."""
    run_ingest_cli(
        path,
        skip_existing_sha=skip_existing_sha,
        force_new_document=force_new_document,
        embeddings_preflight=embeddings_preflight,
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


@app.command("repoint-qdrant-work-ids")
def repoint_qdrant_work_ids_cmd(
    keep_id: str = typer.Argument(
        ...,
        help="Canonical Work.id (payload.work_id after repair)",
    ),
    drop_id: str = typer.Argument(
        ...,
        help="Stale Work.id still stored in Qdrant payloads",
    ),
) -> None:
    """Rewrite Qdrant payloads: drop_id → keep_id (repair old merge without Qdrant sync)."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.repoint_work_id_payload(from_work_id=drop_id, to_work_id=keep_id)
    typer.echo(f"Qdrant: repointed {n} chunk(s) from work_id={drop_id} to work_id={keep_id}.")


@app.command("diagnose-qdrant-work-ids")
def diagnose_qdrant_work_ids_cmd(
    max_points: int = typer.Option(
        50_000,
        "--max-points",
        help="Stop scrolling after this many points (safety on large collections).",
    ),
) -> None:
    """List Qdrant payload work_id values with no matching :Work in Neo4j."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    seen: set[str] = set()
    orphans: set[str] = set()
    scanned = 0
    offset = None
    try:
        while scanned < max_points:
            batch, offset = q.scroll_points_payload_only(
                limit=min(256, max_points - scanned),
                offset=offset,
            )
            if not batch:
                break
            for rec in batch:
                scanned += 1
                if scanned > max_points:
                    break
                wid = (rec.payload or {}).get("work_id")
                if not wid or not isinstance(wid, str):
                    continue
                if wid in seen:
                    continue
                seen.add(wid)
                if not neo.work_exists(wid):
                    orphans.add(wid)
            if offset is None:
                break
    finally:
        neo.close()

    if not orphans:
        typer.echo(
            f"No orphan work_id in Qdrant among {scanned} point(s) scanned "
            f"({len(seen)} distinct work_id)."
        )
        return
    typer.echo(
        f"Scanned {scanned} point(s), {len(seen)} distinct work_id. "
        f"Orphan payload work_id (not in Neo4j):"
    )
    for wid in sorted(orphans):
        n = q.count_chunks_for_work(work_id=wid)
        typer.echo(f"  {wid}  ({n} chunk(s) in Qdrant)")
    typer.echo(
        "Repair: science-graphrag repoint-qdrant-work-ids " "<keep_work_id> <orphan_work_id>"
    )


@app.command("delete-qdrant-by-document-id")
def delete_qdrant_by_document_id_cmd(
    document_id: str = typer.Argument(..., help="Payload document_id to delete"),
) -> None:
    """Delete all Qdrant points with this payload document_id."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.delete_points_by_document_id(document_id=document_id)
    typer.echo(f"Qdrant: deleted {n} point(s) for document_id={document_id}.")


@app.command("delete-qdrant-by-work-id")
def delete_qdrant_by_work_id_cmd(
    work_id: str = typer.Argument(..., help="Payload work_id to delete"),
) -> None:
    """Delete all Qdrant points with this payload work_id (destructive)."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.delete_points_by_work_id(work_id=work_id)
    typer.echo(f"Qdrant: deleted {n} point(s) for work_id={work_id}.")


@app.command("qdrant-recreate-collection")
def qdrant_recreate_collection_cmd() -> None:
    """Delete and recreate the configured Qdrant collection (empty). Dev reset."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    recreate_qdrant_chunk_collection(
        url=s.qdrant_url,
        collection=s.qdrant_collection,
        vector_dim=dim,
    )
    typer.echo(f"Qdrant: recreated empty collection {s.qdrant_collection!r}.")


@app.command("qdrant-recreate-embedding-collections")
def qdrant_recreate_embedding_collections_cmd(
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Resolve vector_dim and print target collection names; do not delete or create.",
    ),
) -> None:
    """Drop and recreate dense-vector Qdrant collections (chunks, work/claim/author/entity)."""

    s = get_settings()
    if dry_run:
        dim, targets, existing = describe_embedding_collections_cutover(s)
        typer.echo(f"Qdrant dry-run: vector_dim={dim} url={s.qdrant_url!r}")
        for name in sorted(targets):
            typer.echo(f"  - {name}  (exists_now={name in existing})")
        typer.echo("No collections were modified. Omit --dry-run to drop+recreate.")
        return

    dim = recreate_all_embedding_collections(s)
    typer.echo(
        f"Qdrant: recreated embedding collections with vector_dim={dim} "
        f"(chunks, work_embeddings, claims, author_embeddings, entity dedup)."
    )


@app.command("purge-work")
def purge_work_cmd(
    work_id: str = typer.Argument(..., help="Work.id to purge from Qdrant"),
    detach_neo4j: bool = typer.Option(
        False,
        "--detach-neo4j",
        help="DETACH DELETE :Work if it exists and has no incoming CITES",
    ),
) -> None:
    """Remove retrieval chunks for a work; optionally remove isolated :Work in Neo4j."""

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.delete_points_by_work_id(work_id=work_id)
    typer.echo(f"Qdrant: deleted {n} point(s) for work_id={work_id}.")
    if detach_neo4j:
        neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
        try:
            removed = neo.detach_delete_work_if_no_incoming_cites(work_id)
        finally:
            neo.close()
        if not removed:
            typer.echo(
                "Neo4j: work not removed (missing, or another Work cites it via CITES).",
                err=True,
            )
            raise typer.Exit(code=1)
        typer.echo(f"Neo4j: DETACH DELETE work_id={work_id}")


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
        return
    if not rows:
        typer.echo("No duplicate Work clusters reported by find_work_dedup_violations().")
        return
    typer.echo(f"Clusters: {len(rows)}")
    for row in rows[:200]:
        typer.echo(f"- {row.get('dedup_key')}: {row.get('work_ids')}")
    if len(rows) > 200:
        typer.echo(f"... truncated ({len(rows)} total); use --json for full dump.")


def _mask_url(url: str) -> str:
    u = str(url or "").strip()
    if "@" in u and "://" in u:
        head, tail = u.split("://", 1)
        if "@" in tail:
            creds, host = tail.rsplit("@", 1)
            if creds:
                return f"{head}://***@{host}"
    return u


@app.command("config-check")
def config_check_cmd(
    strict: bool = typer.Option(
        True,
        "--strict/--no-strict",
        help="Exit 1 if extraction_llm_api_key is unset (recommended before long ingest).",
    ),
    embeddings_preflight: bool = typer.Option(
        False,
        "--embeddings-preflight/--no-embeddings-preflight",
        help="After printing settings, call embeddings once (fails fast on OpenRouter outages).",
    ),
    object_storage_preflight: bool = typer.Option(
        False,
        "--object-storage-preflight/--no-object-storage-preflight",
        help="When object_storage_enabled, verify S3/MinIO bucket access (head + list).",
    ),
) -> None:
    """Print non-secret diagnostics for Settings (operator pre-flight)."""

    s: Settings = get_settings()

    def _line(label: str, value: str) -> None:
        typer.echo(f"[config-check] {label:40} {value}")

    ex_ok = bool(s.extraction_llm_api_key)
    vl_ok = bool(s.vl_api_key)
    _line("extraction_llm_api_key", "SET" if ex_ok else "UNSET")
    _line("vl_api_key", "SET" if vl_ok else "UNSET")
    if s.openrouter_embedding_model:
        _line(
            "embeddings channel",
            f"openrouter (model={s.openrouter_embedding_model}, dim={s.openrouter_embedding_dim})",
        )
    elif s.embedding_model:
        _line("embeddings channel", f"local_sentence_transformers ({s.embedding_model})")
    else:
        _line(
            "embeddings channel", "hash_fallback (no embedding_model / openrouter_embedding_model)"
        )
    _line("database_url", _mask_url(s.database_url))
    _line("neo4j_uri", str(s.neo4j_uri))
    _line("qdrant_url", str(s.qdrant_url))
    _line("redis_url", _mask_url(s.redis_url))
    _line("agent_session_memory_backend", str(s.agent_session_memory_backend))
    skip = os.getenv("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV", "")
    _line("SCIENCE_GRAPHRAG_SKIP_HOST_DOTENV", skip or "(unset)")
    app_log = os.getenv("SCIENCE_GRAPHRAG_LOG_LEVEL", "INFO")
    _line("SCIENCE_GRAPHRAG_LOG_LEVEL", app_log)
    _line("SCIENCE_GRAPHRAG_LOG_LEVEL_INGEST", describe_ingest_log_level_env())
    _line("SCIENCE_GRAPHRAG_HTTP_LOG_LEVEL", describe_http_log_level_env())
    _line("SCIENCE_GRAPHRAG_DRAMATIQ_LOG_LEVEL", describe_dramatiq_log_level_env())
    _line("SCIENCE_GRAPHRAG_LOG_FORMAT", describe_log_format_env())
    _line("SCIENCE_GRAPHRAG_METRICS_ENABLED", str(bool(s.metrics_enabled)))
    _line("extraction_llm_enabled", str(bool(s.extraction_llm_enabled)))
    br = s.blob_root
    try:
        exists = br.exists()
    except OSError:
        exists = False
    _line("blob_root", f"{br} (exists={exists})")
    _line("object_storage_enabled", str(bool(s.object_storage_enabled)))
    if s.object_storage_enabled:
        _line(
            "s3_endpoint_url",
            (s.s3_endpoint_url or "").strip() or "(default virtual-hosted AWS / moto)",
        )
        _line("s3_bucket", (s.s3_bucket or "").strip())
        _line("s3_access_key_id", "SET" if (s.s3_access_key_id or "").strip() else "UNSET")
        _line("s3_secret_access_key", "SET" if (s.s3_secret_access_key or "").strip() else "UNSET")
        _line("s3_use_ssl", str(bool(s.s3_use_ssl)))
    if strict and not ex_ok:
        typer.echo("[config-check] FAILED: extraction_llm_api_key UNSET", err=True)
        raise typer.Exit(code=1)
    if embeddings_preflight:
        from science_graphrag.embeddings.preflight import probe_embeddings

        try:
            probe_embeddings(s)
            typer.echo("[config-check] embeddings preflight: OK")
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"[config-check] embeddings preflight: FAILED ({exc!s})", err=True)
            raise typer.Exit(code=1) from exc
    if object_storage_preflight:
        from science_graphrag.storage.object_storage_preflight import probe_object_storage

        if not s.object_storage_enabled:
            typer.echo(
                "[config-check] object storage preflight: skipped (object_storage_enabled=false)"
            )
        else:
            try:
                probe_object_storage(s)
                typer.echo("[config-check] object storage preflight: OK")
            except Exception as exc:  # noqa: BLE001
                typer.echo(f"[config-check] object storage preflight: FAILED ({exc!s})", err=True)
                raise typer.Exit(code=1) from exc


def main() -> None:
    app()


if __name__ == "__main__":
    main()
