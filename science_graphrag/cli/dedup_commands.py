"""Dedup and merge-related CLI commands."""

from __future__ import annotations

import json

import typer
from sqlalchemy import desc, select

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.db import get_engine, init_db, session_factory
from science_graphrag.storage.models_orm import WorkDedupMergeLog
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore, QdrantWorkEmbeddingStore


def register(app: typer.Typer) -> None:
    """Register dedup/merge commands on root app."""

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
            query = select(WorkDedupMergeLog).order_by(desc(WorkDedupMergeLog.created_at)).limit(limit)
            if workspace_id:
                query = query.where(WorkDedupMergeLog.workspace_id == workspace_id.strip())
            rows = list(session.scalars(query).all())
        if not rows:
            typer.echo("No merge log rows.")
            return
        for row in rows:
            typer.echo(
                f"{row.created_at.isoformat() if row.created_at else ''} "
                f"ws={row.workspace_id} keep={row.keep_work_id} "
                f"drop={row.drop_work_id} conflict={row.conflict_id or '—'}",
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
