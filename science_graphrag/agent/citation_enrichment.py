"""Attach passage text to structured citations for Ask UI (excerpt/snippet fields)."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from science_graphrag.agent.tool_call_normalization import normalize_tool_call_name

_PASSAGE_KEYS = (
    "excerpt",
    "snippet",
    "text",
    "quote_text",
    "chunk_text",
    "passage",
    "body",
    "content",
)


def _citation_has_passage(c: dict[str, Any]) -> bool:
    for k in _PASSAGE_KEYS:
        v = c.get(k)
        if isinstance(v, str) and v.strip():
            return True
    return False


def _norm(value: object) -> str:
    return str(value or "").strip()


def _quote_body(row: dict[str, Any]) -> str:
    return str(
        row.get("quote_text") or row.get("text") or row.get("snippet") or "",
    ).strip()


def _quote_row_fingerprint(row: dict[str, Any]) -> str:
    """Chunk key from quote rows: ``chunk_id`` (paper_quote_search) or ``chunk_fingerprint``."""

    return _norm(
        row.get("chunk_fingerprint")
        or row.get("chunk_id")
        or row.get("fingerprint")
        or row.get("id")
    )


def _normalize_title(value: object) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _title_work_map_from_inventory(inventory: dict[str, Any]) -> dict[str, str]:
    """Map normalized paper titles from merged inventory to ``work_id``."""

    out: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for key in ("papers", "paper_matches"):
        block = inventory.get(key)
        if isinstance(block, list):
            rows.extend(x for x in block if isinstance(x, dict))
    for row in rows:
        wid = _norm(row.get("work_id"))
        title = _normalize_title(row.get("title"))
        if wid and title:
            out.setdefault(title, wid)
    return out


def _resolve_work_id_by_title(norm_citation_title: str, title_map: dict[str, str]) -> str | None:
    if not norm_citation_title:
        return None
    if norm_citation_title in title_map:
        return title_map[norm_citation_title]
    for inv_title, wid in title_map.items():
        if len(norm_citation_title) < 12 or len(inv_title) < 12:
            continue
        if norm_citation_title in inv_title or inv_title in norm_citation_title:
            return wid
    return None


def inject_work_ids_from_inventory(
    citations: list[dict[str, Any]],
    inventory: dict[str, Any] | None,
) -> None:
    """Mutate citations: set ``work_id`` when the model only supplied a title."""

    title_map = _title_work_map_from_inventory(inventory or {})
    if not title_map:
        return
    for c in citations:
        if _norm(c.get("work_id")):
            continue
        ct = _normalize_title(c.get("title") or c.get("work_title") or c.get("paper_title"))
        wid = _resolve_work_id_by_title(ct, title_map)
        if wid:
            c["work_id"] = wid


def collect_paper_profile_abstracts_by_work(
    *,
    messages: list[Any] | None,
    specialist_results: dict[str, list[Any]] | None,
) -> dict[str, str]:
    """Collect Neo4j abstracts from ``paper_profile`` tool payloads (writer path without quotes)."""

    out: dict[str, str] = {}
    for msg in list(messages or []):
        if not isinstance(msg, ToolMessage):
            continue
        if normalize_tool_call_name(str(getattr(msg, "name", "") or "")) != "paper_profile":
            continue
        try:
            payload = json.loads(str(msg.content or ""))
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        wid = _norm(payload.get("work_id"))
        abstract = payload.get("abstract")
        if wid and isinstance(abstract, str) and abstract.strip():
            out.setdefault(wid, abstract.strip()[:8000])
    for payloads in (specialist_results or {}).values():
        for raw in payloads or []:
            if not isinstance(raw, dict):
                continue
            if not isinstance(raw.get("authors"), list):
                continue
            wid = _norm(raw.get("work_id"))
            abstract = raw.get("abstract")
            if wid and isinstance(abstract, str) and abstract.strip():
                out.setdefault(wid, abstract.strip()[:8000])
    return out


def merge_paper_profile_abstracts_into_citations(
    citations: list[dict[str, Any]],
    abstracts_by_work: dict[str, str],
) -> None:
    """Mutate citations: use ``paper_profile.abstract`` when no chunk passage was found."""

    if not abstracts_by_work:
        return
    for c in citations:
        if _citation_has_passage(c):
            continue
        wid = _norm(c.get("work_id"))
        if not wid:
            continue
        abstract = abstracts_by_work.get(wid)
        if isinstance(abstract, str) and abstract.strip():
            c["excerpt"] = abstract.strip()


def _inventory_work_rows(inventory: dict[str, Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in ("papers", "paper_matches"):
        block = (inventory or {}).get(key)
        if isinstance(block, list):
            rows.extend(x for x in block if isinstance(x, dict))
    return rows


def _collect_cited_work_ids_from_specialist_results(
    specialist_results: dict[str, list[Any]] | None,
) -> list[str]:
    out: list[str] = []
    for payloads in (specialist_results or {}).values():
        for raw in payloads or []:
            if not isinstance(raw, dict):
                continue
            cited = raw.get("cited_work_ids")
            if isinstance(cited, list):
                out.extend(_norm(x) for x in cited if _norm(x))
    return out


def synthesize_citations_from_available_evidence(
    *,
    quote_candidates: list[dict[str, Any]] | None,
    inventory: dict[str, Any] | None,
    messages: list[Any] | None,
    specialist_results: dict[str, list[Any]] | None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    """Best-effort citations when writer omitted them despite grounded tool evidence."""

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _push(row: dict[str, Any]) -> None:
        wid = _norm(row.get("work_id"))
        chunk = _norm(row.get("chunk_id") or row.get("chunk_fingerprint"))
        if not wid:
            return
        key = (wid, chunk)
        if key in seen:
            return
        seen.add(key)
        payload: dict[str, Any] = {"work_id": wid}
        if chunk:
            payload["chunk_id"] = chunk
        title = row.get("title")
        if isinstance(title, str) and title.strip():
            payload["title"] = title.strip()
        excerpt = _quote_body(row)
        if excerpt:
            payload["excerpt"] = excerpt
        out.append(payload)

    for row in list(quote_candidates or []):
        if isinstance(row, dict):
            _push(row)
        if len(out) >= limit:
            return out[:limit]

    for row in _inventory_work_rows(inventory):
        _push(row)
        if len(out) >= limit:
            return out[:limit]

    abstracts = collect_paper_profile_abstracts_by_work(
        messages=list(messages or []),
        specialist_results=specialist_results,
    )
    for wid, abstract in abstracts.items():
        _push({"work_id": wid, "excerpt": abstract})
        if len(out) >= limit:
            return out[:limit]

    for wid in _collect_cited_work_ids_from_specialist_results(specialist_results):
        _push({"work_id": wid})
        if len(out) >= limit:
            return out[:limit]

    return out[:limit]


def _citation_chunk_key(citation: dict[str, Any]) -> str:
    """Stable chunk key from structured citations (model/tool shapes vary)."""

    return _norm(
        citation.get("chunk_fingerprint")
        or citation.get("chunk_id")
        or citation.get("fingerprint")
        or citation.get("id")
    )


def _pick_matching_quote(
    wid: str,
    fp: str,
    by_pair: dict[tuple[str, str], dict[str, Any]],
    by_work: dict[str, list[dict[str, Any]]],
) -> dict[str, Any] | None:
    if fp and (wid, fp) in by_pair:
        return by_pair[(wid, fp)]
    if wid not in by_work:
        return None
    rows = by_work[wid]
    if fp:
        for q in rows:
            if _quote_row_fingerprint(q) == fp:
                return q
        return None
    if len(rows) == 1:
        return rows[0]
    return None


def merge_quote_candidates_into_citations(
    citations: list[dict[str, Any]],
    quote_candidates: list[dict[str, Any]],
) -> None:
    """Mutate citations: copy passage text from quote_candidates when the citation lacks it."""

    if not citations or not quote_candidates:
        return

    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    by_work: dict[str, list[dict[str, Any]]] = {}
    for row in quote_candidates:
        if not isinstance(row, dict):
            continue
        wid = _norm(row.get("work_id"))
        if not wid:
            continue
        body = _quote_body(row)
        if not body:
            continue
        qfp = _quote_row_fingerprint(row)
        if qfp:
            by_pair[(wid, qfp)] = row
        by_work.setdefault(wid, []).append(row)

    for c in citations:
        if _citation_has_passage(c):
            continue
        wid = _norm(c.get("work_id"))
        if not wid:
            continue
        fp = _citation_chunk_key(c)
        picked = _pick_matching_quote(wid, fp, by_pair, by_work)
        if picked:
            body = _quote_body(picked)
            if body:
                c["excerpt"] = body


def fill_passages_from_chunk_store(
    citations: list[dict[str, Any]],
    chunk_store: Any,
) -> None:
    """Load chunk text from Qdrant when work_id + chunk_fingerprint are set."""

    getter = getattr(chunk_store, "get_chunk_text_by_work_and_fingerprint", None)
    if not callable(getter):
        return
    for c in citations:
        if _citation_has_passage(c):
            continue
        wid = _norm(c.get("work_id"))
        fp = _citation_chunk_key(c)
        if not wid or not fp:
            continue
        text = getter(work_id=wid, chunk_fingerprint=fp)
        if isinstance(text, str) and text.strip():
            c["excerpt"] = text.strip()


def hydrate_citations_for_ui(
    citations: list[dict[str, Any]],
    *,
    quote_candidates: list[dict[str, Any]] | None,
    chunk_store: Any | None,
    inventory: dict[str, Any] | None = None,
    messages: list[Any] | None = None,
    specialist_results: dict[str, list[Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return a shallow copy of citations with excerpt/snippet hydrated for the chat UI."""

    merged: list[dict[str, Any]] = []
    for raw in citations:
        merged.append(dict(raw) if isinstance(raw, dict) else {})
    if not merged:
        merged = synthesize_citations_from_available_evidence(
            quote_candidates=list(quote_candidates or []),
            inventory=inventory,
            messages=list(messages or []),
            specialist_results=specialist_results,
        )
    inject_work_ids_from_inventory(merged, inventory)
    merge_quote_candidates_into_citations(merged, list(quote_candidates or []))
    if chunk_store is not None:
        fill_passages_from_chunk_store(merged, chunk_store)
    abstracts = collect_paper_profile_abstracts_by_work(
        messages=list(messages or []),
        specialist_results=specialist_results,
    )
    merge_paper_profile_abstracts_into_citations(merged, abstracts)
    return merged
