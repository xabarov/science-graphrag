#!/usr/bin/env python3
"""Minimal MCP JSON-RPC stub for operator live lanes (tools/list + tools/call).

Binds ``0.0.0.0`` by default so the API container can reach the host via
``http://host.docker.internal:<port>/rpc`` (see ``docker-compose.mcp-live-check.yml``).
Operator-only; do not expose on untrusted networks.

Usage::

    .venv/bin/python scripts/live_check/mcp_jsonrpc_stub.py --host 0.0.0.0 --port 19999
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def dispatch_rpc(body: dict[str, Any]) -> dict[str, Any]:
    """Handle a single JSON-RPC request object."""
    req_id = body.get("id")
    method = str(body.get("method") or "").strip()
    params = body.get("params") if isinstance(body.get("params"), dict) else {}

    if method == "tools/list":
        server = str(params.get("server") or "").strip() or "smoke"
        return _rpc_result(
            req_id,
            {
                "server": server,
                "tools": [{"name": "ping", "description": "acceptance ping tool"}],
            },
        )
    if method == "tools/call":
        server = str(params.get("server") or "").strip() or "smoke"
        tool = str(params.get("name") or params.get("tool") or "").strip() or "ping"
        return _rpc_result(
            req_id,
            {
                "server": server,
                "tool": tool,
                "content": [{"type": "text", "text": "pong"}],
            },
        )
    if method == "resources/list":
        server = str(params.get("server") or "").strip() or "smoke"
        return _rpc_result(req_id, {"server": server, "resources": []})
    if method == "resources/read":
        uri = str(params.get("resource_uri") or params.get("uri") or "").strip()
        return _rpc_result(
            req_id,
            {"resource_uri": uri, "contents": [{"uri": uri, "text": "stub-resource"}]},
        )
    return _rpc_error(req_id, -32601, f"method_not_found:{method or 'empty'}")


class _McpStubHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:  # noqa: ANN401
        sys.stderr.write(f"mcp_stub {self.address_string()} - {fmt % args}\n")

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            out = _rpc_error(None, -32700, "parse_error")
        else:
            if not isinstance(body, dict):
                out = _rpc_error(None, -32600, "invalid_request")
            else:
                out = dispatch_rpc(body)
        payload = json.dumps(out).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"mcp_jsonrpc_stub ok\n")


def main() -> int:
    p = argparse.ArgumentParser(description="MCP JSON-RPC stub for live acceptance.")
    p.add_argument(
        "--host",
        default="0.0.0.0",
        help="Bind address (0.0.0.0 allows API-in-Docker via host.docker.internal)",
    )
    p.add_argument("--port", type=int, default=19999)
    args = p.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), _McpStubHandler)
    print(f"mcp_stub_listening=http://{args.host}:{args.port}/rpc", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("mcp_stub_stopped=1", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
