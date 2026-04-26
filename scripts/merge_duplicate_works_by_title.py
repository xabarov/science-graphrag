#!/usr/bin/env python3
"""Audit Neo4j :Work nodes with duplicate titles; optionally merge into canonical (most Qdrant chunks).

Operator flow (see plan Phase 1):
  .venv/bin/python scripts/merge_duplicate_works_by_title.py --dry-run
  .venv/bin/python scripts/merge_duplicate_works_by_title.py --apply

Each merge runs ``science-graphrag merge-work <keep> <drop>`` (Neo4j + Qdrant in one step).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from neo4j import GraphDatabase

# Repo root (parent of scripts/)
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from science_graphrag.config import get_settings
from science_graphrag.ingestion.embeddings import resolve_embedding_dim
from science_graphrag.storage.qdrant_store import QdrantChunkStore


def _chunk_counts_for_ids(
    q: QdrantChunkStore,
    ids: list[str],
) -> dict[str, int]:
    return {wid: q.count_chunks_for_work(work_id=wid) for wid in ids}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned merges only (default if neither flag).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Execute ``science-graphrag merge-work`` for each drop into canonical keep.",
    )
    parser.add_argument(
        "--audit-json",
        type=Path,
        default=None,
        help="Write merge plan JSON (default: eval/results/work-dedup-by-title.json).",
    )
    args = parser.parse_args()
    apply_merges = bool(args.apply) and not bool(args.dry_run)

    s = get_settings()
    dim = resolve_embedding_dim(settings=s)
    q = QdrantChunkStore(s.qdrant_url, s.qdrant_collection, vector_dim=dim)
    driver = GraphDatabase.driver(
        s.neo4j_uri,
        auth=(s.neo4j_user, s.neo4j_password),
    )
    clusters: list[dict[str, object]] = []
    try:
        with driver.session() as sess:
            rows = sess.run(
                """
                MATCH (w:Work)
                WHERE trim(coalesce(w.title, '')) <> ''
                WITH toLower(trim(w.title)) AS t, collect(w.id) AS ids
                WHERE size(ids) > 1 AND size(ids) <= 25
                RETURN t AS title_key, ids AS work_ids
                ORDER BY size(ids) DESC, t
                """
            ).data()
    finally:
        driver.close()

    cli = _REPO / ".venv" / "bin" / "science-graphrag"
    if not cli.is_file():
        cli = Path("science-graphrag")

    merge_ops: list[tuple[str, str]] = []
    for row in rows:
        ids = [str(x) for x in (row.get("work_ids") or []) if x]
        if len(ids) < 2:
            continue
        counts = _chunk_counts_for_ids(q, ids)
        ordered = sorted(ids, key=lambda w: (-counts.get(w, 0), w))
        keep = ordered[0]
        drops = ordered[1:]
        clusters.append(
            {
                "title_key": row.get("title_key"),
                "work_ids": ids,
                "chunk_counts": counts,
                "keep_id": keep,
                "drop_ids": drops,
            },
        )
        for d in drops:
            merge_ops.append((keep, d))

    audit_path = args.audit_json or (_REPO / "eval" / "results" / "work-dedup-by-title.json")
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(
        json.dumps({"clusters": clusters, "merge_pairs": [{"keep": k, "drop": d} for k, d in merge_ops]}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote audit: {audit_path}", flush=True)
    print(f"Duplicate-title clusters: {len(clusters)}; merge pairs: {len(merge_ops)}", flush=True)

    for keep, drop in merge_ops:
        print(f"  merge-work {keep}  (drop {drop})", flush=True)

    if not apply_merges:
        print("Dry run only. Re-run with --apply to execute merges.", flush=True)
        return 0

    exe = str(cli.resolve()) if cli.is_file() else "science-graphrag"
    for keep, drop in merge_ops:
        print(f"Running: {exe} merge-work {keep} {drop}", flush=True)
        r = subprocess.run(
            [exe, "merge-work", keep, drop],
            cwd=str(_REPO),
            check=False,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(r.stdout, file=sys.stderr)
            print(r.stderr, file=sys.stderr)
            print(f"FAIL merge-work keep={keep} drop={drop} exit={r.returncode}", file=sys.stderr)
            return r.returncode or 1
        print(r.stdout, end="", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
