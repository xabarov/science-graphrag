#!/usr/bin/env python3
"""Optional live smoke: Semantic Scholar Graph API (paper search + paper lookup).

Does not require the SciGraph API server. Exits 0 when both search and paper lookup
return HTTP 200 with expected JSON shapes (or empty search list). Exits 1 on transport/HTTP errors.

Environment::

    SCIENCE_GRAPHRAG_SEMANTIC_SCHOLAR_API_KEY   optional x-api-key header for higher limits

Usage::

    .venv/bin/python scripts/live_check/semantic_scholar_smoke.py
    .venv/bin/python scripts/live_check/semantic_scholar_smoke.py --query "graph neural networks"
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from urllib.parse import quote

import httpx

from science_graphrag.config import Settings

_S2_GRAPH_BASE = "https://api.semanticscholar.org/graph/v1"


def _headers() -> dict[str, str]:
    headers = {"User-Agent": "science-graphrag-semantic-scholar-smoke/1.0"}
    key = (
        os.getenv("SCIENCE_GRAPHRAG_SEMANTIC_SCHOLAR_API_KEY")
        or getattr(Settings(), "semantic_scholar_api_key", "")
        or ""
    ).strip()
    if key:
        headers["x-api-key"] = key
    return headers


def _search(client: httpx.Client, query: str) -> tuple[int, str | None]:
    url = f"{_S2_GRAPH_BASE}/paper/search"
    params = {"query": query.strip(), "limit": 1, "fields": "paperId,title,year"}
    r = client.get(url, params=params, headers=_headers())
    print(f"search_http_status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        return r.status_code, None
    try:
        data = r.json()
    except ValueError as exc:
        print(f"search_json_error: {exc}", file=sys.stderr)
        return r.status_code, None
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        print("search_invalid_json_shape: missing data[]", file=sys.stderr)
        return r.status_code, None
    print(f"search_results={len(rows)}")
    if not rows:
        return r.status_code, None
    pid = str((rows[0] or {}).get("paperId") or "").strip()
    return r.status_code, pid or None


def _paper(client: httpx.Client, paper_id: str) -> int:
    pid = quote(paper_id.strip(), safe="")
    url = f"{_S2_GRAPH_BASE}/paper/{pid}"
    params = {"fields": "paperId,title,year"}
    r = client.get(url, params=params, headers=_headers())
    print(f"paper_http_status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        return r.status_code
    try:
        data = r.json()
    except ValueError as exc:
        print(f"paper_json_error: {exc}", file=sys.stderr)
        return r.status_code
    if not isinstance(data, dict) or not str(data.get("paperId") or "").strip():
        print("paper_invalid_json_shape: missing paperId", file=sys.stderr)
        return r.status_code
    print(f"paper_title={str(data.get('title') or '')[:120]}")
    return r.status_code


def main() -> int:
    p = argparse.ArgumentParser(description="Semantic Scholar API smoke (search + paper lookup).")
    p.add_argument("--query", default="attention is all you need", help="Search query string")
    p.add_argument(
        "--paper-id",
        default="",
        help="Optional paper id for lookup; when omitted, uses first search hit",
    )
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument(
        "--request-interval-seconds",
        type=float,
        default=1.1,
        help="Minimum pause before the second S2 request; default respects the 1 request/second key limit.",
    )
    args = p.parse_args()

    try:
        with httpx.Client(timeout=args.timeout) as client:
            status, pid_from_search = _search(client, args.query)
            if status != 200:
                return 1
            paper_id = (args.paper_id or "").strip() or (pid_from_search or "").strip()
            if not paper_id:
                print("paper_lookup_skipped: no paper id from search (empty results)")
                return 0
            time.sleep(max(0.0, args.request_interval_seconds))
            paper_status = _paper(client, paper_id)
    except (httpx.HTTPError, OSError) as exc:
        print(f"transport_error: {exc}", file=sys.stderr)
        return 1

    return 0 if paper_status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
