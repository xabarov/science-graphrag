"""Persist :CONTRADICTS edges between :Work nodes (BT12 / Wave 9)."""

from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def merge_work_contradicts(
    client: _Neo4jClient,
    work_id_a: str,
    work_id_b: str,
    *,
    subtype: str = "unspecified",
) -> None:
    """Create a single directed CONTRADICTS edge (canonical order by id). Idempotent MERGE."""

    a = str(work_id_a or "").strip()
    b = str(work_id_b or "").strip()
    if not a or not b or a == b:
        return
    lo, hi = (a, b) if a < b else (b, a)
    q = """
    MATCH (x:Work {id: $lo}), (y:Work {id: $hi})
    MERGE (x)-[r:CONTRADICTS]->(y)
    SET r.subtype = $subtype,
        r.schema_version = coalesce(r.schema_version, 1)
    """
    with client.session() as session:
        session.run(q, lo=lo, hi=hi, subtype=str(subtype or "unspecified")[:120])
