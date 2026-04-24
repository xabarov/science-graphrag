#!/usr/bin/env python3
"""Backfill Qdrant ``work_embeddings`` from Neo4j for all works in a workspace (idempotent upsert)."""

from __future__ import annotations

import argparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import HashEmbeddingProvider, resolve_embedding_dim, try_sentence_transformer
from science_graphrag.storage.db import init_db
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantWorkEmbeddingStore


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("workspace_id", help="Workspace id whose member works get summary vectors")
    args = p.parse_args()
    ws_id = str(args.workspace_id).strip()
    if not ws_id:
        raise SystemExit("workspace_id required")

    settings = get_settings()
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    try:
        ws = neo.workspace_get(ws_id)
        if not ws:
            raise SystemExit("workspace_not_found")
        work_ids = [str(x).strip() for x in (ws.get("work_ids") or []) if str(x).strip()]
    finally:
        neo.close()

    embedder = (
        try_sentence_transformer(settings.embedding_model)
        if settings.embedding_model
        else HashEmbeddingProvider()
    )
    dim = resolve_embedding_dim(embedding_model=settings.embedding_model)
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
            text = f"{card.get('title') or ''}\n{card.get('abstract') or ''}\n{card.get('first_author') or ''}"[:8000]
            vec = embedder.embed([text])[0]
            qw.upsert_work_summary(
                work_id=wid,
                vector=vec,
                embedding_model=settings.embedding_model or "hash-deterministic",
                workspace_ids=[ws_id],
            )
            n += 1
        print(f"Upserted {n} work summary vector(s) for workspace={ws_id}")
    finally:
        neo2.close()


if __name__ == "__main__":
    main()
