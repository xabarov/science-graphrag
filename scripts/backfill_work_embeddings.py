#!/usr/bin/env python3
"""Backfill work summary embeddings for all workspace works.

Targets:
- ``qdrant``: upsert into Qdrant work_embeddings collection (default).
- ``neo4j``: write vectors to ``(:Work {id}).title_embedding``.
"""

from __future__ import annotations

import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import get_settings
from science_graphrag.embeddings import resolve_embedder, resolve_embedding_model_label
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.db import init_db
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantWorkEmbeddingStore


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace_id", help="Workspace id whose member works get summary vectors")
    p.add_argument(
        "--target",
        choices=("qdrant", "neo4j"),
        default="qdrant",
        help="Where to write vectors (default: qdrant).",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Without this flag, run in dry-run mode.",
    )
    args = p.parse_args()
    ws_id = str(args.workspace_id).strip()
    if not ws_id:
        raise SystemExit("workspace_id required")
    target = str(args.target).strip().lower()
    dry_run = not bool(args.apply)

    settings = get_settings()
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        ws = neo.workspace_get(ws_id)
        if not ws:
            raise SystemExit("workspace_not_found")
        work_ids = [str(x).strip() for x in (ws.get("work_ids") or []) if str(x).strip()]
    finally:
        neo.close()

    embedder = resolve_embedder(settings)
    dim = resolve_embedding_dim(settings=settings)
    emb_label = resolve_embedding_model_label(settings)
    qw = None
    if target == "qdrant":
        qw = QdrantWorkEmbeddingStore(
            settings.qdrant_url,
            settings.qdrant_work_embeddings_collection,
            vector_dim=dim,
        )

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    init_db(engine)
    sessionmaker(bind=engine)  # ensure tables

    neo2 = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        n = 0
        for wid in work_ids:
            card = neo2.fetch_work_bibliography_card(wid)
            if not card:
                continue
            text = f"{card.get('title') or ''}\n{card.get('abstract') or ''}\n{card.get('first_author') or ''}"[
                :8000
            ]
            vec = embedder.embed([text])[0]
            if dry_run:
                n += 1
                continue
            if target == "qdrant":
                assert qw is not None
                qw.upsert_work_summary(
                    work_id=wid,
                    vector=vec,
                    embedding_model=emb_label,
                    workspace_ids=[ws_id],
                    title=str(card.get("title") or ""),
                    publication_year=card.get("year"),
                    doi=str(card.get("doi") or "") or None,
                    arxiv_id=str(card.get("arxiv_id") or "") or None,
                    first_author_normalized=str(card.get("first_author") or ""),
                    embedding_kind="work_summary_v1",
                )
            else:
                with neo2.session() as session:
                    session.run(
                        """
                        MATCH (w:Work {id: $work_id})
                        SET w.title_embedding = $vec
                        """,
                        work_id=wid,
                        vec=[float(x) for x in vec],
                    )
            n += 1
        mode = "DRY-RUN planned" if dry_run else "Applied"
        print(f"{mode} {n} work summary vector update(s) for workspace={ws_id} target={target}")
    finally:
        neo2.close()


if __name__ == "__main__":
    main()
