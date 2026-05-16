#!/usr/bin/env python3
"""Optional live smoke: MCP HTTP JSON-RPC adapter (tools/list ping).

Requires ``SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL`` (or ``--base-url``).
Exits 0 on HTTP 200 with JSON object body; exits 1 on transport/HTTP errors.

Usage::

    export SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL=http://127.0.0.1:9999/rpc
    .venv/bin/python scripts/live_check/mcp_adapter_smoke.py
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid

import httpx


def main() -> int:
    p = argparse.ArgumentParser(description="MCP adapter JSON-RPC smoke (tools/list).")
    p.add_argument(
        "--base-url",
        default=(os.getenv("SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL") or "").strip(),
        help="MCP adapter base URL",
    )
    p.add_argument("--server", default="smoke", help="Logical server id for params")
    p.add_argument("--timeout", type=float, default=15.0)
    args = p.parse_args()

    base = str(args.base_url or "").strip()
    if not base:
        print("missing_base_url: set SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL", file=sys.stderr)
        return 1

    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/list",
        "params": {"server": args.server},
    }
    headers = {"User-Agent": "science-graphrag-mcp-adapter-smoke/1.0"}
    try:
        with httpx.Client(timeout=args.timeout) as client:
            r = client.post(base, json=payload, headers=headers)
    except (httpx.HTTPError, OSError) as exc:
        print(f"transport_error: {exc}", file=sys.stderr)
        return 1

    print(f"http_status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        return 1
    try:
        body = r.json()
    except ValueError as exc:
        print(f"json_error: {exc}", file=sys.stderr)
        return 1
    if not isinstance(body, dict):
        print("invalid_json_shape: expected object", file=sys.stderr)
        return 1
    if body.get("error"):
        print(f"rpc_error: {body.get('error')}", file=sys.stderr)
        return 1
    print("rpc_ok=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
