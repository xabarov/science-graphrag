"""Neo4j-backed resolution predictions for references_resolution benchmark (Wave M)."""

from __future__ import annotations

from typing import Any

from science_graphrag.ingestion.dedup import normalize_doi
from science_graphrag.storage.neo4j_store import Neo4jGraphStore


def _norm_ck(key: str) -> str:
    return str(key or "").strip().lower()


def _parse_canonical_key(canonical_key: str) -> tuple[str, str]:
    t = _norm_ck(canonical_key)
    if t.startswith("arxiv:"):
        return "arxiv", t[6:].strip()
    if t.startswith("doi:"):
        rest = t[4:].strip()
        return "doi", normalize_doi(rest) or rest
    if t.startswith("work_id:"):
        return "work_id", t[8:].strip()
    return "unknown", canonical_key


def _canonical_from_graph_keys(keys: dict[str, str], *, work_id: str) -> str | None:
    arx = (keys.get("arxiv_id") or "").strip()
    if arx:
        return f"arxiv:{arx.lower()}"
    doi = normalize_doi(keys.get("doi") or "")
    if doi:
        return f"doi:{doi.lower()}"
    if work_id:
        return f"work_id:{work_id}"
    return None


def graph_resolve_predictions(gold: dict[str, Any], store: Neo4jGraphStore) -> list[dict[str, Any]]:
    """
    Build predictions by resolving ``expected_resolutions`` against Neo4j :Work nodes.

    For ``arxiv:`` / ``doi:`` keys, lookup is by indexed identifiers; predicted ``canonical_key``
    matches gold when normalized graph-derived key equals normalized expected key.
    For ``work_id:`` keys, lookup is ``MATCH (w:Work {id: $id})`` existence only.
    """

    out: list[dict[str, Any]] = []
    rows = gold.get("expected_resolutions") or []
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        sid = row.get("raw_citation_span_id")
        ck = row.get("canonical_key")
        if not sid or not ck:
            continue
        kind, val = _parse_canonical_key(str(ck))
        wid: str | None = None
        if kind == "arxiv":
            wid = store.find_work_id_by_arxiv(val)
        elif kind == "doi":
            d = normalize_doi(val)
            wid = store.find_work_id_by_doi(d) if d else None
        elif kind == "work_id":
            wid = val if store.work_exists(val) else None
        else:
            wid = None
        if not wid:
            continue
        if kind == "work_id":
            out.append({"raw_citation_span_id": str(sid), "canonical_key": str(ck)})
            continue
        gkeys = store.get_work_external_keys(wid)
        if not gkeys:
            continue
        computed = _canonical_from_graph_keys(gkeys, work_id=str(wid))
        if computed and _norm_ck(computed) == _norm_ck(str(ck)):
            out.append({"raw_citation_span_id": str(sid), "canonical_key": str(ck)})
    return out
