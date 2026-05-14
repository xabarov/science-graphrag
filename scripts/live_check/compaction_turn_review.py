#!/usr/bin/env python3
"""Review multi-turn compaction behavior for one thread."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent

if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

# Back-compat for tests that import this file by path (``spec_from_file_location``).
from compaction_review import retry_policy as _cr_retry
from compaction_review.http_client import stderr_wait_heartbeat_line as _stderr_wait_heartbeat_line
from compaction_review.run import run_compaction_review_from_parsed_args

_classify_turn_failure = _cr_retry.classify_turn_failure
compaction_review_stop_outcome = _cr_retry.compaction_review_stop_outcome


def main() -> int:
    """Run N sync turns, collect compaction telemetry, and write JSON/MD verdict."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url", default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000")
    )
    parser.add_argument(
        "--workspace-id", default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None
    )
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--require-compaction-after", type=int, default=2)
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=_REPO_ROOT / "eval" / "results" / "compaction-turn-review.json",
    )
    parser.add_argument(
        "--out-md", type=Path, default=_REPO_ROOT / "eval" / "results" / "compaction-turn-review.md"
    )
    parser.add_argument(
        "--emit-merged-into",
        type=Path,
        default=None,
        help="Merge compaction_events into an existing trace-review-v1 JSON at this path",
    )
    parser.add_argument(
        "--heartbeat-sec",
        type=float,
        default=None,
        help=(
            "Progress heartbeat interval for per-turn logs (minimum 5s). "
            "When omitted, uses mode-specific defaults (15s focused_long_thread, 30s default) "
            "and AGENT_LIVE_COMPACTION_* env overrides."
        ),
    )
    parser.add_argument(
        "--no-in-turn-heartbeat",
        action="store_true",
        help=(
            "Disable stderr heartbeats during blocking JSON /v2/agent/query wait " "(between turns)"
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["default", "focused_long_thread"],
        default="default",
        help="Failure policy profile for multi-turn compaction review.",
    )
    parser.add_argument(
        "--max-retries-per-turn",
        type=int,
        default=int(os.environ.get("AGENT_LIVE_COMPACTION_RETRY_MAX", "0") or 0),
        help="Bounded retries for timeout-like failures (focused mode).",
    )
    parser.add_argument(
        "--retry-backoff-sec",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_COMPACTION_RETRY_BACKOFF_SEC", "2.0")),
        help="Sleep between focused-mode retries (seconds).",
    )
    parser.add_argument(
        "--silent-hang-threshold-sec",
        type=float,
        default=float(os.environ.get("AGENT_LIVE_COMPACTION_SILENT_HANG_SEC", "180")),
        help="Timeout elapsed >= threshold is classified as silent_hang in focused mode.",
    )
    args = parser.parse_args()
    from dotenv_util import (  # pylint: disable=import-outside-toplevel,import-error
        resolve_live_base_url,
    )

    args.base_url = resolve_live_base_url(args.base_url)
    return run_compaction_review_from_parsed_args(args)


if __name__ == "__main__":
    raise SystemExit(main())
