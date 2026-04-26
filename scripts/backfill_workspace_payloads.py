#!/usr/bin/env python3
"""Idempotent: set Qdrant chunk ``workspace_ids`` from Neo4j workspace membership.

- Bounded workspaces: ``Workspace-[:CONTAINS]->Work`` → tag chunks per ``work_id``.
- Unbounded (``ws.unbounded``): tag **all** points in the chunks collection with that workspace id.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import create_engine

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.db import init_db
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-id", default="", help="Limit to one workspace id (optional)")
    args = p.parse_args()
    settings = get_settings()
    neo = Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password)
    dim = resolve_embedding_dim(settings=settings)
    qdrant = QdrantChunkStore(settings.qdrant_url, settings.qdrant_collection, vector_dim=dim)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    init_db(engine)
    wid_filter = (args.workspace_id or "").strip()
    try:
        pairs: list[tuple[str, str]] = []
        unbounded_ids: list[str] = []
        for ws in neo.workspace_list():
            ws_id = str(ws.get("id") or "").strip()
            if not ws_id or (wid_filter and ws_id != wid_filter):
                continue
            if bool(ws.get("unbounded")):
                unbounded_ids.append(ws_id)
                continue
            for work_id in ws.get("work_ids") or []:
                w = str(work_id).strip()
                if w:
                    pairs.append((w, ws_id))
        total = 0
        for work_id, ws_id in pairs:
            total += qdrant.add_workspace_to_chunks(work_id=work_id, workspace_id=ws_id)
        print(f"updated_payload_fields={total} pairs={len(pairs)}")
        for ws_id in unbounded_ids:
            n = qdrant.add_workspace_to_all_chunks(workspace_id=ws_id)
            print(f"unbounded_workspace={ws_id} updated_points={n}")
        return 0
    finally:
        neo.close()


if __name__ == "__main__":
    sys.exit(main())
