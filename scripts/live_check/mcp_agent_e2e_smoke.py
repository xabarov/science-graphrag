#!/usr/bin/env python3
"""Live E2E: POST ``/v2/agent/query`` and assert MCP tool + audit telemetry.

Prerequisites (operator contour):
1. Dev stack up (``make dev-up``) with stable API + MCP overlay::
     COMPOSE_FILE=docker-compose.dev.yml:docker-compose.live-check.yml:docker-compose.mcp-live-check.yml \\
       docker compose up -d api --force-recreate
2. MCP stub on host (this script can start it with ``--start-stub``)::
     .venv/bin/python scripts/live_check/mcp_jsonrpc_stub.py --host 0.0.0.0 --port 19999
3. Env::
     export AGENT_LIVE_BASE=http://127.0.0.1:18787
     export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od

Usage::

    .venv/bin/python scripts/live_check/mcp_agent_e2e_smoke.py --start-stub
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dotenv_util import load_dotenv_or_warn, resolve_live_base_url  # noqa: E402
from http_suite_core import _extra_headers, check_health  # noqa: E402
from mcp_agent_e2e_validate import (  # noqa: E402
    MCP_E2E_DEFAULT_QUESTION,
    tool_names_from_trace,
    validate_mcp_agent_response,
)


def _start_stub(port: int, *, host: str = "0.0.0.0") -> subprocess.Popen[str]:
    cmd = [
        str(_REPO_ROOT / ".venv/bin/python"),
        str(_SCRIPT_DIR / "mcp_jsonrpc_stub.py"),
        "--host",
        host,
        "--port",
        str(port),
    ]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 10.0
    while time.time() < deadline:
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"mcp stub exited early: {out[:500]}")
        line = proc.stdout.readline() if proc.stdout else ""
        if "mcp_stub_listening=" in line:
            return proc
        time.sleep(0.05)
    raise RuntimeError("mcp stub did not print listening line within 10s")


def _adapter_smoke(base_url: str, server: str, timeout: float) -> int:
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "method": "tools/list",
        "params": {"server": server},
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            r = client.post(base_url, json=payload)
    except (httpx.HTTPError, OSError) as exc:
        print(f"adapter_transport_error: {exc}", file=sys.stderr)
        return 1
    print(f"adapter_http_status={r.status_code}")
    if r.status_code != 200:
        print(r.text[:500], file=sys.stderr)
        return 1
    body = r.json()
    if not isinstance(body, dict) or body.get("error"):
        print(f"adapter_rpc_error: {body}", file=sys.stderr)
        return 1
    print("adapter_rpc_ok=1")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="MCP agent E2E smoke via /v2/agent/query.")
    p.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:18787"),
        help="SciGraph API base (env AGENT_LIVE_BASE)",
    )
    p.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Dotenv path (default: repo .env)",
    )
    p.add_argument(
        "--workspace-id",
        default=(os.environ.get("AGENT_LIVE_WORKSPACE_ID") or "").strip() or None,
    )
    p.add_argument(
        "--mcp-adapter-url",
        default=(
            os.environ.get("SCIENCE_GRAPHRAG_AGENT_MCP_HTTP_BASE_URL")
            or "http://127.0.0.1:19999/rpc"
        ).strip(),
        help="Adapter URL for preflight tools/list (host view)",
    )
    p.add_argument("--server", default="smoke", help="MCP logical server id")
    p.add_argument("--tool", default="ping", help="Expected MCP tool name")
    p.add_argument("--question", default=MCP_E2E_DEFAULT_QUESTION)
    p.add_argument(
        "--timeout", type=float, default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))
    )
    p.add_argument("--stub-port", type=int, default=19999)
    p.add_argument(
        "--start-stub",
        action="store_true",
        help="Spawn mcp_jsonrpc_stub.py on host before checks",
    )
    p.add_argument("--skip-adapter-smoke", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    load_dotenv_or_warn(args.env_file)
    base = resolve_live_base_url(args.base_url)

    stub_proc: subprocess.Popen[str] | None = None
    if args.start_stub:
        print(f"starting_mcp_stub port={args.stub_port}", flush=True)
        stub_proc = _start_stub(args.stub_port)
        adapter_url = f"http://127.0.0.1:{args.stub_port}/rpc"
    else:
        adapter_url = str(args.mcp_adapter_url or "").strip()

    exit_code = 1
    try:
        if not args.skip_adapter_smoke:
            if not adapter_url:
                print("missing_mcp_adapter_url", file=sys.stderr)
                return 1
            if _adapter_smoke(adapter_url, args.server, min(15.0, args.timeout)) != 0:
                return 1

        with httpx.Client(timeout=httpx.Timeout(args.timeout)) as client:
            health = check_health(client, base)
            print(f"api_health_ok={health.ok}")
            if not health.ok:
                print(health.detail, file=sys.stderr)
                return 1

            payload: dict[str, object] = {"question": args.question}
            if args.workspace_id:
                payload["workspace_id"] = args.workspace_id
            url = f"{base.rstrip('/')}/v2/agent/query"
            print(f"agent_query_url={url}", flush=True)
            try:
                r = client.post(
                    url,
                    json=payload,
                    headers={"Accept": "application/json", **_extra_headers()},
                )
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as exc:
                print(
                    f"agent_http_error: {exc.response.status_code} {exc.response.text[:800]}",
                    file=sys.stderr,
                )
                return 1
            except Exception as exc:  # noqa: BLE001
                print(f"agent_transport_error: {exc}", file=sys.stderr)
                return 1

        if not isinstance(data, dict):
            print("agent_invalid_body: expected object", file=sys.stderr)
            return 1

        tools = tool_names_from_trace(
            data.get("tool_trace") if isinstance(data.get("tool_trace"), list) else []
        )
        print(f"tool_trace_tools={tools}")
        rm = data.get("run_metadata") if isinstance(data.get("run_metadata"), dict) else {}
        mc = rm.get("mcp_audit_summary") if isinstance(rm, dict) else None
        print(f"mcp_audit_summary={json.dumps(mc, ensure_ascii=False) if mc else 'null'}")

        ok, issues = validate_mcp_agent_response(
            data,
            expected_server=args.server,
            expected_tool=args.tool,
        )
        if args.verbose:
            print(json.dumps(data, indent=2, ensure_ascii=False)[:12000])
        if ok:
            print("mcp_agent_e2e_ok=1")
            exit_code = 0
        else:
            for issue in issues:
                print(f"issue: {issue}", file=sys.stderr)
            if any(i.startswith("agent_sync_error:") for i in issues):
                print(
                    "hint: ensure API container can reach LLM "
                    "(OpenRouter keys or Ollama at host.docker.internal:11434/v1)",
                    file=sys.stderr,
                )
            print("mcp_agent_e2e_ok=0", file=sys.stderr)
            exit_code = 1
    finally:
        if stub_proc is not None and stub_proc.poll() is None:
            stub_proc.terminate()
            try:
                stub_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                stub_proc.kill()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
