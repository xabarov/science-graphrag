from __future__ import annotations

from pathlib import Path

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.ingestion.pipeline import run_ingest_batch_cli, run_ingest_cli
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, recreate_qdrant_chunk_collection

app = typer.Typer(no_args_is_help=True, help="science-graphrag CLI")


@app.callback()
def _root() -> None:
    """Scholarly GraphRAG — ingestion and graph backbone."""


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
) -> None:
    """Run Phase 1 ingestion pipeline for one document."""
    run_ingest_cli(
        path,
        skip_existing_sha=skip_existing_sha,
        force_new_document=force_new_document,
    )


@app.command("merge-work")
def merge_work_cmd(
    keep_id: str = typer.Argument(..., help="Canonical Work.id to keep"),
    drop_id: str = typer.Argument(..., help="Duplicate Work.id to re-point and delete"),
) -> None:
    """Re-point citations / semantic edges onto keep_id; delete drop_id if it has no authorships."""

    s = get_settings()
    neo = Neo4jGraphStore(s.neo4j_uri, s.neo4j_user, s.neo4j_password)
    try:
        dropped = neo.merge_work_into_canonical(keep_id, drop_id)
    finally:
        neo.close()
    if dropped:
        dim = resolve_embedding_dim(embedding_model=s.embedding_model)
        q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
        n = q.repoint_work_id_payload(from_work_id=drop_id, to_work_id=keep_id)
        typer.echo(
            f"Neo4j: merged into keep={keep_id}, removed drop={drop_id}. "
            f"Qdrant: repointed {n} chunk(s)."
        )
    else:
        typer.echo(
            f"Neo4j: merge did not remove drop={drop_id} (e.g. HAS_AUTHORSHIP present). "
            f"Qdrant unchanged. keep={keep_id}"
        )


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
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
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
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
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
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.delete_points_by_document_id(document_id=document_id)
    typer.echo(f"Qdrant: deleted {n} point(s) for document_id={document_id}.")


@app.command("delete-qdrant-by-work-id")
def delete_qdrant_by_work_id_cmd(
    work_id: str = typer.Argument(..., help="Payload work_id to delete"),
) -> None:
    """Delete all Qdrant points with this payload work_id (destructive)."""

    s = get_settings()
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    n = q.delete_points_by_work_id(work_id=work_id)
    typer.echo(f"Qdrant: deleted {n} point(s) for work_id={work_id}.")


@app.command("qdrant-recreate-collection")
def qdrant_recreate_collection_cmd() -> None:
    """Delete and recreate the configured Qdrant collection (empty). Dev reset."""

    s = get_settings()
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
    recreate_qdrant_chunk_collection(
        url=s.qdrant_url,
        collection=s.qdrant_collection,
        vector_dim=dim,
    )
    typer.echo(f"Qdrant: recreated empty collection {s.qdrant_collection!r}.")


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
    dim = resolve_embedding_dim(embedding_model=s.embedding_model)
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
) -> None:
    """Batch-ingest a corpus directory and print Work-level dedup audit for Neo4j."""

    run_ingest_batch_cli(
        directory,
        continue_on_error=continue_on_error,
        skip_existing_sha=skip_existing_sha,
        force_new_document=force_new_document,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
