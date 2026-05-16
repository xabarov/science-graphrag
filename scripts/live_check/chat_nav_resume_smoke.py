#!/usr/bin/env python3
"""Smoke: agent run buffer + resume endpoint; optional Graph↔Chat trace routing contract.

Usage (from repo root, dev API up):
  AGENT_LIVE_BASE=http://127.0.0.1:18787 .venv/bin/python scripts/live_check/chat_nav_resume_smoke.py

Routing contract only (no API):
  .venv/bin/python scripts/live_check/chat_nav_resume_smoke.py --routing-contract-only
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import httpx

from scripts.live_check.dotenv_util import resolve_live_base_url

REPO_ROOT = Path(__file__).resolve().parents[2]


SSE_FRAME_SPLIT = re.compile(r"\r?\n\r?\n")


def _parse_sse_chunk(text: str) -> tuple[list[dict], str]:
    """Parse complete SSE frames from *text* and return (events, tail)."""
    out: list[dict] = []
    frames = SSE_FRAME_SPLIT.split(text)
    tail = frames.pop() if frames else ""
    for frame in frames:
        if not frame.strip():
            continue
        for line in frame.split("\n"):
            if line.startswith("data:"):
                raw = line[5:].strip()
                if raw:
                    try:
                        out.append(json.loads(raw))
                    except json.JSONDecodeError:
                        pass
    return out, tail


def _run_routing_contract_smoke() -> int:
    script = REPO_ROOT / "scripts" / "live_check" / "trace_scope_routing_contract_smoke.py"
    proc = subprocess.run([sys.executable, str(script)], cwd=REPO_ROOT, check=False)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Chat nav / run resume API smoke")
    parser.add_argument("--base-url", default=None, help="API base (or AGENT_LIVE_BASE)")
    parser.add_argument("--workspace-id", default="ws-pilot-od")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--routing-contract-only",
        action="store_true",
        help="Run Graph↔Chat trace-scope Vitest contract only (no API)",
    )
    parser.add_argument(
        "--skip-routing-contract",
        action="store_true",
        help="Skip Graph↔Chat trace-scope Vitest contract before API smoke",
    )
    args = parser.parse_args()

    if args.routing_contract_only:
        return _run_routing_contract_smoke()

    if not args.skip_routing_contract:
        rc = _run_routing_contract_smoke()
        if rc != 0:
            return rc

    base = resolve_live_base_url(args.base_url)
    url = f"{base.rstrip('/')}/v2/agent/query"
    print(f"manifest base={base} workspace_id={args.workspace_id}", flush=True)

    run_id: str | None = None
    with httpx.Client(timeout=args.timeout) as client:
        with client.stream(
            "POST",
            url,
            headers={"Accept": "text/event-stream", "Content-Type": "application/json"},
            json={
                "question": "Say hello in one short sentence.",
                "workspace_id": args.workspace_id,
                "max_tool_calls": 4,
                "agent_mode": "agent",
            },
        ) as res:
            res.raise_for_status()
            buf = ""
            for chunk in res.iter_text():
                buf += chunk
                events, buf = _parse_sse_chunk(buf)
                for ev in events:
                    if ev.get("type") == "run_started":
                        run_id = str(ev.get("run_id") or "")
                        print(f"run_started run_id={run_id}", flush=True)
                        break
                if run_id:
                    break
                if len(buf) > 200_000:
                    buf = buf[-50_000:]
            # Simulate leaving Chat page: close primary SSE without waiting for final_answer.
            res.close()

        if not run_id:
            print("FAIL: no run_started in stream", file=sys.stderr)
            return 1

        resume_url = f"{base.rstrip('/')}/v2/agent/query/runs/{run_id}/stream"
        with client.stream(
            "GET",
            resume_url,
            params={"after_seq": 0},
            headers={"Accept": "text/event-stream"},
        ) as r2:
            r2.raise_for_status()
            resume_buf = ""
            events: list[dict] = []
            for chunk in r2.iter_text():
                resume_buf += chunk
                parsed, resume_buf = _parse_sse_chunk(resume_buf)
                events.extend(parsed)
                if any(e.get("type") in ("final_answer", "run_interrupted") for e in events):
                    break
        types = [e.get("type") for e in events]
        print(f"resume events={len(events)} types_sample={types[:8]}", flush=True)
        if any(e.get("type") == "error" and "network" in str(e.get("detail", "")).lower() for e in events):
            print("FAIL: resume stream returned raw network error event", file=sys.stderr)
            return 1
        if not any(t in ("run_started", "product_step", "final_answer") for t in types):
            print("FAIL: resume stream had no recognizable events", file=sys.stderr)
            return 1
    print("OK chat_nav_resume_smoke", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
