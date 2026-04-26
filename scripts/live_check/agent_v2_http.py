#!/usr/bin/env python3
"""Live HTTP checks: GET /health + POST /v2/agent/query (JSON, SSE, multi-turn).

Loads the repository ``.env`` first (override=True) so you can run this from a shell
without exporting keys; the **API server** must still be configured to reach Neo4j,
Qdrant, and the LLM.

Environment (optional)::

    AGENT_LIVE_BASE           API root (default: http://127.0.0.1:8000)
    AGENT_LIVE_WORKSPACE_ID   workspace UUID for graph/chunk tools
    AGENT_LIVE_TIMEOUT_SEC    per-request timeout (default: 240)
    AGENT_LIVE_AUTHORIZATION  full header value, e.g. ``Bearer <jwt>``
    AGENT_LIVE_ADMIN_KEY      ``X-Admin-Key`` if your deployment requires it
    AGENT_LIVE_QUESTION       override first sync question
    AGENT_LIVE_QUESTION_T1/T2 multi-turn prompts
    AGENT_LIVE_QUESTION_SSE   SSE-only question

Usage::

    cd /path/to/science-graphrag
    .venv/bin/python scripts/live_check/agent_v2_http.py --verbose
    .venv/bin/python scripts/live_check/agent_v2_http.py --skip-sse --env-file /tmp/prod.env
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent


def _ensure_suite_path() -> None:
    """Allow ``import http_suite`` when this file is run as a script."""
    if str(_SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPT_DIR))


def main() -> int:
    """Parse CLI, load env, run HTTP suite, return shell exit code."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000"),
        help="API base URL (env AGENT_LIVE_BASE)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=_REPO_ROOT / ".env",
        help="Dotenv path loaded before checks (default: repo .env)",
    )
    parser.add_argument(
        "--workspace-id",
        default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None,
        help="Optional workspace_id (env AGENT_LIVE_WORKSPACE_ID)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240")),
        help="HTTP timeout seconds (env AGENT_LIVE_TIMEOUT_SEC)",
    )
    parser.add_argument("--skip-sse", action="store_true", help="Skip SSE stream check")
    parser.add_argument(
        "--skip-multi-turn",
        action="store_true",
        help="Skip second sync JSON turn with history_digest",
    )
    parser.add_argument("--verbose", action="store_true", help="Print JSON per check")
    args = parser.parse_args()

    _ensure_suite_path()
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        load_dotenv_or_warn,
    )

    load_dotenv_or_warn(args.env_file)

    from http_suite import (  # pylint: disable=import-outside-toplevel,import-error
        CheckResult,
        run_default_suite,
    )

    def _print(res: CheckResult) -> None:
        line = f"[{'OK' if res.ok else 'FAIL'}] {res.name}: {res.detail}"
        print(line)
        if args.verbose and res.data:
            print(json.dumps(res.data, indent=2, ensure_ascii=False))

    results = run_default_suite(
        args.base_url.rstrip("/"),
        workspace_id=args.workspace_id,
        timeout=args.timeout,
        skip_sse=args.skip_sse,
        skip_multi_turn=args.skip_multi_turn,
        on_event=_print,
    )
    failed = [r for r in results if not r.ok]
    if failed:
        print(f"\n{len(failed)} check(s) failed.", file=sys.stderr)
        return 1
    print(f"\nAll {len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
