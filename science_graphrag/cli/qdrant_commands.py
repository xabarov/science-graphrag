"""Qdrant-related CLI commands."""

from __future__ import annotations

import typer

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.qdrant_store import (
    QdrantChunkStore,
    recreate_all_embedding_collections,
    recreate_qdrant_chunk_collection,
)
from science_graphrag.storage.qdrant_store.recreate_embedding_collections import (
    describe_embedding_collections_cutover,
)


def register(app: typer.Typer) -> None:
    """Register Qdrant commands on the root typer app."""

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
        from science_graphrag.storage.neo4j_store import Neo4jGraphStore

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
                    if not wid or not isinstance(wid, str) or wid in seen:
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
        typer.echo("Repair: science-graphrag repoint-qdrant-work-ids <keep_work_id> <orphan_work_id>")

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
        from science_graphrag.storage.neo4j_store import Neo4jGraphStore

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
