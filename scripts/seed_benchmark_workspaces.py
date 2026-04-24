#!/usr/bin/env python3
"""Idempotent: MERGE pilot workspaces ``ws-pilot-od`` / ``ws-pilot-pdf`` and CONTAINS edges to pilot Work nodes.

Reads membership from ``tests/fixtures/benchmarks/retrieval/workspace_scoped/_workspaces.json``.
Then run ``scripts/backfill_workspace_payloads.py`` (subprocess) to tag Qdrant chunk payloads.

Uses the Neo4j driver directly to avoid importing ``science_graphrag.storage`` package ``__init__``
(circular import with ingestion during some entrypoints).

Usage::

    python scripts/seed_benchmark_workspaces.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from neo4j import GraphDatabase

from science_graphrag.config import get_settings


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    manifest = repo / "tests/fixtures/benchmarks/retrieval/workspace_scoped/_workspaces.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    workspaces = data.get("workspaces") or {}
    if not isinstance(workspaces, dict) or not workspaces:
        print("no workspaces in manifest", file=sys.stderr)
        return 1

    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        for ws_id, meta in workspaces.items():
            wid = str(ws_id).strip()
            name = str((meta or {}).get("name") or wid).strip()
            work_ids = [str(x).strip() for x in ((meta or {}).get("work_ids") or []) if str(x).strip()]
            q_merge = (
                "MERGE (ws:Workspace {id: $id}) "
                "ON CREATE SET ws.created_at = datetime() "
                "SET ws.name = $name "
                "RETURN ws.id AS id"
            )
            with driver.session() as session:
                session.run(q_merge, id=wid, name=name)
            for work in work_ids:
                with driver.session() as session:
                    ex = session.run(
                        "MATCH (w:Work {id: $id}) RETURN 1 AS ok LIMIT 1",
                        id=work,
                    ).single()
                    if not ex:
                        print(f"skip_missing_work workspace={wid} work_id={work}", file=sys.stderr)
                        continue
                    session.run(
                        """
                        MATCH (ws:Workspace {id: $wid})
                        MATCH (w:Work {id: $work})
                        MERGE (ws)-[:CONTAINS]->(w)
                        RETURN 1 AS ok
                        """,
                        wid=wid,
                        work=work,
                    )
            print(f"workspace_ok id={wid} work_count={len(work_ids)}")
    finally:
        driver.close()

    rc = subprocess.call(
        [sys.executable, str(repo / "scripts/backfill_workspace_payloads.py")],
        cwd=str(repo),
    )
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())
