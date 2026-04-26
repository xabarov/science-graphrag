#!/usr/bin/env python3
"""Idempotent: MERGE pilot workspaces and CONTAINS edges to pilot Work nodes.

Reads membership from:
- ``tests/fixtures/benchmarks/retrieval/workspace_scoped/_workspaces.json``
  (uses ``work_ids`` — direct Neo4j UUIDs)
- ``tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json``
  (uses ``corpus_work_ids`` — fixture slugs resolved to UUIDs via paper title lookup)

Then runs ``scripts/backfill_workspace_payloads.py`` (subprocess) to tag Qdrant chunk payloads.

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

from eval.retrieval.work_id_resolve import is_uuid_like
from science_graphrag.config import get_settings


def _resolve_corpus_slug_to_uuid(
    slug: str, repo: Path, driver: GraphDatabase.driver  # type: ignore[type-arg]
) -> str | None:
    """Look up the Neo4j Work UUID for a corpus fixture slug via paper title."""
    fixture = repo / "tests" / "fixtures" / "benchmarks" / "layer1" / slug / "gold.json"
    if not fixture.is_file():
        return None
    try:
        g = json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    title = str((g.get("work_metadata") or {}).get("title") or "").strip()
    if not title:
        return None
    with driver.session() as sess:
        result = sess.run(
            "MATCH (w:Work) WHERE toLower(w.title) = toLower($t) RETURN w.id AS id LIMIT 1",
            t=title,
        )
        rec = result.single()
        return str(rec["id"]) if rec else None


def _seed_manifest(
    manifest: Path,
    driver: GraphDatabase.driver,  # type: ignore[type-arg]
    repo: Path,
    *,
    use_corpus_ids: bool = False,
) -> None:
    """MERGE workspaces and CONTAINS edges from one manifest file."""
    data = json.loads(manifest.read_text(encoding="utf-8"))
    workspaces = data.get("workspaces") or {}
    if not isinstance(workspaces, dict) or not workspaces:
        print(f"no workspaces in {manifest}", file=sys.stderr)
        return

    for ws_id, meta in workspaces.items():
        wid = str(ws_id).strip()
        name = str((meta or {}).get("name") or wid).strip()
        q_merge = (
            "MERGE (ws:Workspace {id: $id}) "
            "ON CREATE SET ws.created_at = datetime() "
            "SET ws.name = $name "
            "RETURN ws.id AS id"
        )
        with driver.session() as session:
            session.run(q_merge, id=wid, name=name)

        if use_corpus_ids:
            raw_ids = list((meta or {}).get("corpus_work_ids") or [])
            if raw_ids == ["*"] or raw_ids == "*":
                print(f"workspace_ok id={wid} corpus=* (unbounded; no CONTAINS edges)")
                continue
            work_uuids: list[str] = []
            for slug in raw_ids:
                slug_s = str(slug).strip()
                if not slug_s:
                    continue
                uuid = _resolve_corpus_slug_to_uuid(slug_s, repo, driver)
                if uuid:
                    work_uuids.append(uuid)
                else:
                    print(
                        f"skip_missing_work workspace={wid} corpus_slug={slug_s}", file=sys.stderr
                    )
        else:
            work_uuids = []
            for ref in (meta or {}).get("work_ids") or []:
                ref_s = str(ref).strip()
                if not ref_s:
                    continue
                if is_uuid_like(ref_s):
                    work_uuids.append(ref_s)
                else:
                    resolved = _resolve_corpus_slug_to_uuid(ref_s, repo, driver)
                    if resolved:
                        work_uuids.append(resolved)
                    else:
                        print(
                            f"skip_unresolved_slug workspace={wid} slug={ref_s}",
                            file=sys.stderr,
                        )

        for work_uuid in work_uuids:
            with driver.session() as session:
                ex = session.run(
                    "MATCH (w:Work {id: $id}) RETURN 1 AS ok LIMIT 1",
                    id=work_uuid,
                ).single()
                if not ex:
                    print(f"skip_missing_work workspace={wid} work_id={work_uuid}", file=sys.stderr)
                    continue
                session.run(
                    """
                    MATCH (ws:Workspace {id: $wid})
                    MATCH (w:Work {id: $work})
                    MERGE (ws)-[:CONTAINS]->(w)
                    RETURN 1 AS ok
                    """,
                    wid=wid,
                    work=work_uuid,
                )
        print(f"workspace_ok id={wid} work_count={len(work_uuids)}")


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    settings = get_settings()
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        pilot_manifest = (
            repo / "tests/fixtures/benchmarks/retrieval/workspace_scoped/_workspaces.json"
        )
        _seed_manifest(pilot_manifest, driver, repo, use_corpus_ids=False)

        live_manifest = (
            repo / "tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json"
        )
        _seed_manifest(live_manifest, driver, repo, use_corpus_ids=True)
    finally:
        driver.close()

    rc = subprocess.call(
        [sys.executable, str(repo / "scripts/backfill_workspace_payloads.py")],
        cwd=str(repo),
    )
    return int(rc)


if __name__ == "__main__":
    sys.exit(main())
