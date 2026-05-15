"""arXiv API tools (Atom export) — structured search + metadata fetch without PDF extraction."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.tools.base import ToolResult
from science_graphrag.agent.tools.external.http_transport import external_research_user_agent
from science_graphrag.agent.tools.trace_wrappers import run_tool_result_with_span
from science_graphrag.config import Settings

# --- arXiv API (official Atom export) ---
_ARXIV_API_URL = "https://export.arxiv.org/api/query"

# --- Public contract / guardrails (not operator Settings knobs) ---
_ARXIV_SEARCH_MAX_RESULTS = 25
_ARXIV_SEARCH_DEFAULT_RESULTS = 5
_ARXIV_MAX_CATEGORIES = 8
_ARXIV_TRACE_QUERY_PREVIEW_CHARS = 200
_ARXIV_TRACE_ID_PREVIEW_CHARS = 120
_ARXIV_ERROR_DETAIL_CHARS = 240

# arXiv id: new-style NNNN.NNNNN + optional version
_ARXIV_NEW_ID_RE = re.compile(
    r"(?P<id>\d{4}\.\d{4,5}(?:v\d+)?)",
    re.IGNORECASE,
)


def _strip_xml_ns(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _local_findall(parent: ET.Element, local: str) -> list[ET.Element]:
    return [c for c in list(parent) if _strip_xml_ns(c.tag) == local]


def _local_find(parent: ET.Element, local: str) -> ET.Element | None:
    for c in list(parent):
        if _strip_xml_ns(c.tag) == local:
            return c
    return None


def _elem_text(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return "".join(el.itertext()).strip()


def _parse_arxiv_id_from_atom_id(atom_id: str) -> str:
    """Extract arXiv paper id (with optional version) from Atom ``<id>``."""
    s = (atom_id or "").strip()
    if not s:
        return ""
    m = re.search(r"arxiv\.org/abs/(?P<id>[^/\s#?]+)", s, re.IGNORECASE)
    if m:
        return m.group("id").strip()
    m = _ARXIV_NEW_ID_RE.search(s)
    if m:
        return m.group("id").strip()
    return ""


def _normalize_date_token(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        y, mo, d = s[0:4], s[5:7], s[8:10]
        if y.isdigit() and mo.isdigit() and d.isdigit():
            return f"{y}{mo}{d}"
    if len(s) == 8 and s.isdigit():
        return s
    return None


def _arxiv_timestamp(date_token: str, *, end_of_day: bool) -> str:
    """arXiv ``submittedDate`` range uses YYYYMMDDHHMM (minute precision)."""
    tok = (date_token or "").strip()
    if len(tok) != 8 or not tok.isdigit():
        return ""
    return tok + ("2359" if end_of_day else "0000")


def _build_search_query(
    query: str,
    *,
    categories: list[str] | None,
    date_from: str | None,
    date_to: str | None,
) -> tuple[str | None, str | None]:
    """Return (search_query, error_detail). ``error_detail`` set when input is invalid."""
    q = str(query or "").strip()
    if not q:
        return None, "empty_query"
    inner = q.replace('"', " ").strip()
    if not inner:
        return None, "empty_query"
    parts: list[str] = [f'all:"{inner}"']

    cats: list[str] = []
    if categories:
        for c in categories:
            cc = str(c or "").strip()
            if not cc:
                continue
            cats.append(cc)
            if len(cats) >= _ARXIV_MAX_CATEGORIES:
                break
    if cats:
        or_expr = "+OR+".join(f"cat:{c}" for c in cats)
        parts.append(f"+AND+({or_expr})")

    df = _normalize_date_token(date_from)
    dt = _normalize_date_token(date_to)
    if (date_from and not df) or (date_to and not dt):
        return None, "invalid_date_range"
    if df and dt and df > dt:
        return None, "invalid_date_range"
    if df or dt:
        start = _arxiv_timestamp(df or "00010101", end_of_day=False)
        end = _arxiv_timestamp(dt or "99991231", end_of_day=True)
        if not start or not end:
            return None, "invalid_date_range"
        parts.append(f"+AND+submittedDate:[{start}+TO+{end}]")

    return "".join(parts), None


def _parse_feed_entries(xml_text: str) -> list[ET.Element]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    # API returns <feed> with <entry> children (Atom namespace on tags).
    entries: list[ET.Element] = []
    for child in list(root):
        if _strip_xml_ns(child.tag) == "entry":
            entries.append(child)
    return entries


def _entry_collect_authors(entry: ET.Element) -> list[str]:
    authors: list[str] = []
    for au in _local_findall(entry, "author"):
        nm = _elem_text(_local_find(au, "name"))
        if nm:
            authors.append(nm)
    return authors


def _entry_collect_categories_and_doi(entry: ET.Element) -> tuple[list[str], str]:
    categories: list[str] = []
    doi = ""
    for ch in list(entry):
        tag = _strip_xml_ns(ch.tag)
        if tag == "category":
            term = (ch.attrib.get("term") or "").strip()
            if term:
                categories.append(term)
        elif tag == "doi":
            t = _elem_text(ch)
            if t:
                doi = t.strip()
    return categories, doi


def _entry_collect_link_urls(entry: ET.Element) -> tuple[str, str]:
    entry_url = ""
    pdf_url = ""
    for lk in _local_findall(entry, "link"):
        href = (lk.attrib.get("href") or "").strip()
        rel = (lk.attrib.get("rel") or "").strip().lower()
        typ = (lk.attrib.get("type") or "").strip().lower()
        title_attr = (lk.attrib.get("title") or "").strip().lower()
        if not href:
            continue
        if rel in {"alternate", ""} and (not entry_url or "arxiv.org/abs/" in href):
            entry_url = href
        if "pdf" in typ or title_attr == "pdf" or href.lower().endswith(".pdf"):
            pdf_url = href
    return entry_url, pdf_url


def _entry_to_item(entry: ET.Element) -> dict[str, Any]:
    atom_id_el = _local_find(entry, "id")
    atom_id = _elem_text(atom_id_el)
    arxiv_id = _parse_arxiv_id_from_atom_id(atom_id)

    title = _elem_text(_local_find(entry, "title"))
    summary = _elem_text(_local_find(entry, "summary"))
    published = _elem_text(_local_find(entry, "published"))
    updated = _elem_text(_local_find(entry, "updated"))

    authors = _entry_collect_authors(entry)
    categories, doi = _entry_collect_categories_and_doi(entry)
    entry_url, pdf_url = _entry_collect_link_urls(entry)

    if not entry_url and arxiv_id:
        entry_url = f"https://arxiv.org/abs/{arxiv_id}"
    if not pdf_url and arxiv_id:
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return {
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "summary": summary,
        "published": published,
        "updated": updated,
        "entry_url": entry_url,
        "pdf_url": pdf_url,
        "categories": categories,
        "doi": doi,
    }


def _web_sources_from_items(
    items: list[dict[str, Any]], *, source_tool: str
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        url = str(it.get("entry_url") or "").strip()
        title = str(it.get("title") or "").strip()
        snippet = str(it.get("summary") or "").strip()
        if len(snippet) > 600:
            snippet = snippet[:600].rstrip() + "…"
        doi = str(it.get("doi") or "").strip()
        if not url and not title:
            continue
        row: dict[str, Any] = {
            "title": title or url,
            "url": url,
            "doi": doi,
            "source_tool": source_tool,
            "snippet": snippet,
        }
        out.append(row)
    return out


def _arxiv_http_get(
    url: str,
    *,
    settings: Settings,
    params: dict[str, Any] | None = None,
) -> tuple[int, str, str | None]:
    timeout = float(settings.agent_web_search_http_timeout_seconds)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            r = client.get(
                url,
                params=params,
                headers={"User-Agent": external_research_user_agent(settings)},
            )
            text = r.text
            if r.status_code >= 400:
                return r.status_code, text, f"http_{r.status_code}"
            return r.status_code, text, None
    except (httpx.HTTPError, OSError, ValueError) as exc:
        return 0, "", str(exc)[:_ARXIV_ERROR_DETAIL_CHARS]


def _arxiv_search_impl(
    query: str,
    *,
    settings: Settings,
    max_results: int,
    categories: list[str] | None,
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    built, err = _build_search_query(
        query,
        categories=categories,
        date_from=date_from,
        date_to=date_to,
    )
    if built is None:
        return {
            "ok": False,
            "error": "bad_request",
            "detail": err or "bad_request",
            "row_count": 0,
            "items": [],
            "web_sources": [],
            "evidence_origin": "external_web",
        }

    n = max(1, min(int(max_results), _ARXIV_SEARCH_MAX_RESULTS))
    params = {
        "search_query": built,
        "start": 0,
        "max_results": n,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    status, body, http_err = _arxiv_http_get(_ARXIV_API_URL, settings=settings, params=params)
    if http_err:
        return {
            "ok": False,
            "error": "arxiv_search_failed",
            "detail": http_err,
            "row_count": 0,
            "items": [],
            "web_sources": [],
            "evidence_origin": "external_web",
        }

    entries = _parse_feed_entries(body)
    items: list[dict[str, Any]] = []
    for ent in entries[:n]:
        items.append(_entry_to_item(ent))
    row_count = len(items)
    web_sources = _web_sources_from_items(items, source_tool="arxiv_search")
    return {
        "ok": True,
        "row_count": row_count,
        "items": items,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": _ARXIV_API_URL,
            "status": status,
            "bytes": len(body.encode("utf-8", errors="replace")),
            "cache_hit": False,
            "mode": "arxiv_search",
        },
    }


def _resolve_arxiv_id_from_user_input(raw: str) -> tuple[str | None, str | None]:
    """Return (arxiv_id, error_code)."""
    s = str(raw or "").strip()
    if not s:
        return None, "empty_id"
    s2 = s.strip()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/(?P<id>[^/\s#?]+)", s2, re.IGNORECASE)
    if m:
        cand = m.group("id").strip()
        if cand.lower().endswith(".pdf"):
            cand = cand[:-4]
        return cand, None
    m = re.match(r"^arxiv:\s*(?P<id>\S+)$", s2, re.IGNORECASE)
    if m:
        return m.group("id").strip(), None
    m = _ARXIV_NEW_ID_RE.search(s2)
    if m:
        return m.group("id").strip(), None
    return None, "invalid_arxiv_id"


def _arxiv_fetch_impl(
    arxiv_id_or_url: str,
    *,
    settings: Settings,
    include_pdf_text: bool,
) -> dict[str, Any]:
    if include_pdf_text:
        return {
            "ok": False,
            "error": "unsupported_pdf_text",
            "detail": "PDF full text extraction is not supported in this tool version.",
            "row_count": 0,
            "item": None,
            "web_sources": [],
            "evidence_origin": "external_web",
        }

    aid, err = _resolve_arxiv_id_from_user_input(arxiv_id_or_url)
    if not aid:
        return {
            "ok": False,
            "error": err or "invalid_arxiv_id",
            "detail": str(arxiv_id_or_url or "").strip()[:_ARXIV_TRACE_ID_PREVIEW_CHARS],
            "row_count": 0,
            "item": None,
            "web_sources": [],
            "evidence_origin": "external_web",
        }

    status, body, http_err = _arxiv_http_get(
        _ARXIV_API_URL,
        settings=settings,
        params={"id_list": aid},
    )
    if http_err:
        return {
            "ok": False,
            "error": "arxiv_fetch_failed",
            "detail": http_err,
            "row_count": 0,
            "item": None,
            "web_sources": [],
            "evidence_origin": "external_web",
        }

    entries = _parse_feed_entries(body)
    if not entries:
        return {
            "ok": True,
            "row_count": 0,
            "item": None,
            "web_sources": [],
            "evidence_origin": "external_web",
            "sse_hint": {
                "type": "web_fetched",
                "url": _ARXIV_API_URL,
                "status": status,
                "bytes": len(body.encode("utf-8", errors="replace")),
                "cache_hit": False,
                "mode": "arxiv_fetch",
            },
        }

    item = _entry_to_item(entries[0])
    web_sources = _web_sources_from_items([item], source_tool="arxiv_fetch")
    return {
        "ok": True,
        "row_count": 1,
        "item": item,
        "web_sources": web_sources,
        "evidence_origin": "external_web",
        "sse_hint": {
            "type": "web_fetched",
            "url": _ARXIV_API_URL,
            "status": status,
            "bytes": len(body.encode("utf-8", errors="replace")),
            "cache_hit": False,
            "mode": "arxiv_fetch",
        },
    }


class ArxivSearchArgs(BaseModel):
    """Arguments for ``arxiv_search`` (Atom API search)."""

    query: str = Field(..., min_length=1, max_length=512)
    max_results: int = Field(
        default=_ARXIV_SEARCH_DEFAULT_RESULTS, ge=1, le=_ARXIV_SEARCH_MAX_RESULTS
    )
    categories: list[str] | None = Field(
        default=None,
        description="Optional arXiv category filters (e.g. cs.CV, cs.LG).",
    )
    date_from: str | None = Field(
        default=None,
        description="Optional submittedDate lower bound (YYYY-MM-DD or YYYYMMDD).",
        max_length=32,
    )
    date_to: str | None = Field(
        default=None,
        description="Optional submittedDate upper bound (YYYY-MM-DD or YYYYMMDD).",
        max_length=32,
    )


class ArxivFetchArgs(BaseModel):
    """Arguments for ``arxiv_fetch`` (single-record Atom lookup)."""

    arxiv_id_or_url: str = Field(..., min_length=4, max_length=512)
    include_pdf_text: bool = Field(
        default=False,
        description="Reserved; PDF text extraction is not supported yet.",
    )


def build_arxiv_tools(*, settings: Settings) -> list[Any]:
    """Return LangChain arXiv tools (Atom API; no PDF body extraction)."""

    @tool("arxiv_search", args_schema=ArxivSearchArgs, return_direct=False)
    def arxiv_search_tool(
        query: str,
        max_results: int = _ARXIV_SEARCH_DEFAULT_RESULTS,
        categories: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Search arXiv via the official Atom API (titles, abstracts, abs/pdf links)."""

        def _run() -> ToolResult:
            pl = _arxiv_search_impl(
                query,
                settings=settings,
                max_results=max_results,
                categories=categories,
                date_from=date_from,
                date_to=date_to,
            )
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="arxiv_search",
            tool_parameters={
                "query": query[:_ARXIV_TRACE_QUERY_PREVIEW_CHARS],
                "max_results": max_results,
            },
            fn=_run,
        )
        return res.payload

    @tool("arxiv_fetch", args_schema=ArxivFetchArgs, return_direct=False)
    def arxiv_fetch_tool(
        arxiv_id_or_url: str,
        include_pdf_text: bool = False,
    ) -> dict[str, Any]:
        """Fetch one arXiv record (metadata + abstract) via the Atom API."""

        def _run() -> ToolResult:
            pl = _arxiv_fetch_impl(
                arxiv_id_or_url,
                settings=settings,
                include_pdf_text=include_pdf_text,
            )
            return ToolResult(payload=pl, row_count=int(pl.get("row_count") or 0))

        res = run_tool_result_with_span(
            tool_name="arxiv_fetch",
            tool_parameters={
                "id": str(arxiv_id_or_url or "")[:_ARXIV_TRACE_ID_PREVIEW_CHARS],
                "include_pdf_text": include_pdf_text,
            },
            fn=_run,
        )
        return res.payload

    return [arxiv_search_tool, arxiv_fetch_tool]
