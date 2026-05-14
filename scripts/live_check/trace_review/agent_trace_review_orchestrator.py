"""Orchestration for agent_trace_review CLI (trace-review-v1).

Delegates from scripts/live_check/agent_trace_review.py entrypoint.

Imports below are intentionally re-exported for ``tests/scripts/live_check`` monkeypatch
targets on this module (historical surface after splitting the runner body).
"""

from __future__ import annotations

from .orchestrator_argparse import build_agent_trace_review_parser
from .orchestrator_env import ensure_local_imports as _ensure_local_imports
from .orchestrator_env import load_dotenv as _load_dotenv
from .orchestrator_main_runner import run_agent_trace_review
from .orchestrator_report import json_safe_value as _json_safe_value
from .orchestrator_report import (
    server_agent_runtime_from_checks as _server_agent_runtime_from_checks,
)
from .orchestrator_subprocess import run_compaction_turn_review as _run_compaction_turn_review

__all__ = [
    "main",
    "_ensure_local_imports",
    "_load_dotenv",
    "_json_safe_value",
    "_server_agent_runtime_from_checks",
    "_run_compaction_turn_review",
]


def main() -> int:
    """CLI entry: parse argv and run the trace-review pipeline."""
    parser = build_agent_trace_review_parser()
    return run_agent_trace_review(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
