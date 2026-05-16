#!/usr/bin/env python3
"""Optional live smoke: OpenAlex Works search API.

Does not require the SciGraph API server. Exits 0 on HTTP 200 with expected JSON
shape. Exits 1 on transport/HTTP/JSON-shape errors.

Usage::

    .venv/bin/python scripts/live_check/openalex_smoke.py
    .venv/bin/python scripts/live_check/openalex_smoke.py --query "object detection" --max-results 1
"""

from __future__ import annotations

import argparse
import sys

import httpx

_OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def main() -> int:
    p = argparse.ArgumentParser(description="OpenAlex Works API smoke.")
    p.add_argument("--query", default="object detection", help="Search query string")
    p.add_argument("--max-results", type=int, default=1, dest="max_results")
    p.add_argument("--timeout", type=float, default=20.0)
    args = p.parse_args()

    per_page = max(1, min(5, int(args.max_results)))
    params = {"search": args.query.strip(), "per-page": per_page}
    headers = {"User-Agent": "science-graphrag-openalex-smoke/1.0"}

    try:
        with httpx.Client(timeout=args.timeout) as client:
            r = client.get(_OPENALEX_WORKS_URL, params=params, headers=headers)
    except (httpx.HTTPError, OSError) as exc:
        print(f"transport_error: {exc}", file=sys.stderr)
        return 1

    print(f"http_status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        return 1
    try:
        payload = r.json()
    except ValueError as exc:
        print(f"json_error: {exc}", file=sys.stderr)
        return 1
    results = payload.get("results") if isinstance(payload, dict) else None
    if not isinstance(results, list):
        print("invalid_json_shape: missing results[]", file=sys.stderr)
        return 1
    print(f"results={len(results)}")
    if results:
        first = results[0] or {}
        print(f"first_openalex_id={str(first.get('id') or '')[:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
