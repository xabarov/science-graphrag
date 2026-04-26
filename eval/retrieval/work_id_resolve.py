"""Resolve benchmark layer1 fixture slugs to Neo4j ``Work.id`` (portable gold across DB re-ingests)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from science_graphrag.config import Settings

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


def is_uuid_like(value: str) -> bool:
    """Return True if *value* looks like a standard UUID."""
    return bool(_UUID_RE.match(str(value).strip()))


def resolve_work_id_from_layer1_slug(
    repo: Path,
    slug: str,
    *,
    settings: Settings,
) -> str | None:
    """Neo4j lookup of :Work id by title from ``tests/fixtures/benchmarks/layer1/<slug>/gold.json``."""

    sid = str(slug).strip()
    if not sid:
        return None
    fixture = repo / "tests" / "fixtures" / "benchmarks" / "layer1" / sid / "gold.json"
    if not fixture.is_file():
        return None
    try:
        g = json.loads(fixture.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    title = str((g.get("work_metadata") or {}).get("title") or "").strip()
    if not title:
        return None
    try:
        from neo4j import GraphDatabase
    except ImportError:
        return None
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    try:
        with driver.session() as sess:
            rows = sess.run(
                "MATCH (w:Work) WHERE toLower(w.title) = toLower($t) RETURN w.id AS id ORDER BY w.id",
                t=title,
            ).data()
            ids = [str(r["id"]) for r in rows if r.get("id")]
        if not ids:
            return None
        if len(ids) == 1:
            return ids[0]
        # Prefer the :Work that actually has indexed chunks in Qdrant (duplicate-title guard).
        try:
            from science_graphrag.ingestion.embeddings import resolve_embedding_dim
            from science_graphrag.storage.qdrant_store import QdrantChunkStore

            dim = resolve_embedding_dim(settings=settings)
            q = QdrantChunkStore(
                settings.qdrant_url,
                settings.qdrant_collection,
                vector_dim=dim,
            )
            best: str | None = None
            best_cnt = -1
            for wid in ids:
                cnt = q.count_chunks_for_work(work_id=wid)
                if cnt > best_cnt or (cnt == best_cnt and (best is None or wid < best)):
                    best_cnt = cnt
                    best = wid
            return best or ids[0]
        except Exception:  # noqa: BLE001 — resolver must not break benchmarks on Qdrant hiccup
            return ids[0]
    finally:
        driver.close()


def expand_workspace_member_work_ids(
    raw: list[object] | None,
    *,
    repo: Path,
    settings: Settings,
) -> set[str]:
    """Expand ``workspace_member_work_ids`` entries: UUIDs as-is; layer1 slugs → Neo4j ids."""

    out: set[str] = set()
    for x in raw or []:
        s0 = str(x).strip()
        if not s0:
            continue
        if is_uuid_like(s0):
            out.add(s0)
            continue
        fixture = repo / "tests" / "fixtures" / "benchmarks" / "layer1" / s0 / "gold.json"
        if fixture.is_file():
            uid = resolve_work_id_from_layer1_slug(repo, s0, settings=settings)
            if uid:
                out.add(uid)
                continue
        out.add(s0)
    return out
