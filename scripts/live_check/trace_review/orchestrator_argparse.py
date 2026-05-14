"""Argument parser for ``agent_trace_review`` (thin CLI surface)."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .orchestrator_paths import REPO_ROOT


def build_agent_trace_review_parser() -> argparse.ArgumentParser:
    """Construct the ``agent_trace_review`` CLI (flags are a public contract)."""
    parser = argparse.ArgumentParser(
        description=(
            "Canonical live trace-review orchestrator (trace-review-v1). "
            "Runs base HTTP checks plus optional OD E2E audit and emits JSON/MD artifacts."
        ),
    )
    parser.add_argument(
        "--base-url", default=os.environ.get("AGENT_LIVE_BASE", "http://127.0.0.1:8000")
    )
    parser.add_argument("--env-file", type=Path, default=REPO_ROOT / ".env")
    parser.add_argument(
        "--workspace-id", default=os.environ.get("AGENT_LIVE_WORKSPACE_ID", "").strip() or None
    )
    parser.add_argument(
        "--timeout", type=float, default=float(os.environ.get("AGENT_LIVE_TIMEOUT_SEC", "240"))
    )
    parser.add_argument(
        "--suite",
        choices=["default", "heavy", "full", "acceptance"],
        default="default",
        help=(
            "E2E question pack; acceptance = full OD suite + v3 hardening cases "
            "(requires live v3)."
        ),
    )
    parser.add_argument(
        "--profile",
        choices=["quick", "default", "heavy"],
        default="default",
        help="Execution profile controlling default skip flags/timeouts.",
    )
    parser.add_argument("--skip-sse", action="store_true")
    parser.add_argument("--skip-multi-turn", action="store_true")
    parser.add_argument("--skip-e2e", action="store_true")
    parser.add_argument("--with-trace-audit", action="store_true")
    parser.add_argument("--with-phoenix", action="store_true")
    parser.add_argument("--with-db-audit", action="store_true")
    parser.add_argument(
        "--with-compaction-turns", type=int, default=0, help="If >0, run compaction_turn_review.py"
    )
    parser.add_argument(
        "--require-compaction-after",
        type=int,
        default=2,
        help="Threshold turn for compaction_turn_review (default 2)",
    )
    parser.add_argument(
        "--emit-merged-review",
        type=Path,
        default=None,
        help="Path for compaction_turn_review --emit-merged-into (default: --out-json)",
    )
    parser.add_argument(
        "--compaction-mode",
        choices=["default", "focused_long_thread"],
        default="default",
        help="Compaction review mode for --with-compaction-turns lane.",
    )
    parser.add_argument(
        "--compaction-max-retries-per-turn",
        type=int,
        default=int(os.environ.get("AGENT_LIVE_COMPACTION_RETRY_MAX", "0") or 0),
        help="Retries passed to compaction_turn_review focused mode.",
    )
    parser.add_argument(
        "--out-json", type=Path, default=REPO_ROOT / "eval" / "results" / "trace-review.json"
    )
    parser.add_argument(
        "--out-md", type=Path, default=REPO_ROOT / "eval" / "results" / "trace-review.md"
    )
    parser.add_argument("--e2e-json", type=Path, default=None)
    parser.add_argument(
        "--with-long-thread-eval",
        action="store_true",
        help="Merge offline Epic A3 long-thread prompt-memory metrics into trace-review output.",
    )
    parser.add_argument(
        "--strict-v3-lifecycle",
        action="store_true",
        help="Fail trace-review when subagent_lifecycle_missing_count>0 (Epic B1 hard gate).",
    )
    parser.add_argument(
        "--min-claim-verification-parse-rate",
        type=float,
        default=None,
        help="Fail when claim_verification_verdict_parse_rate is below threshold (0..1).",
    )
    parser.add_argument(
        "--with-acceptance-summary",
        action="store_true",
        help="Embed acceptance_summary_v1 (§10.10) into the JSON artifact.",
    )
    parser.add_argument(
        "--no-acceptance-summary",
        action="store_true",
        help="Disable auto acceptance_summary for suite=acceptance.",
    )
    return parser


__all__ = ["build_agent_trace_review_parser"]
