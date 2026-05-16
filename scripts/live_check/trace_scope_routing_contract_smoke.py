#!/usr/bin/env python3
"""Validate Graph↔Chat trace-scope routing contract (Vitest, no browser).

Usage (from repo root):
  .venv/bin/python scripts/live_check/trace_scope_routing_contract_smoke.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
UI_ROOT = REPO_ROOT / "ui"

ROUTING_CONTRACT_TESTS = [
    "src/components/layout/shellNavHref.test.js",
    "src/graphNavigationDashboardShell.test.jsx",
    "src/components/work/ask/orchestration/useAskSessionLifecycle.test.js",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Graph↔Chat trace-scope routing contract smoke")
    parser.parse_args()
    if not (UI_ROOT / "package.json").is_file():
        print(f"FAIL: ui package missing at {UI_ROOT}", file=sys.stderr)
        return 1

    cmd = ["npm", "test", "--", "run", *ROUTING_CONTRACT_TESTS]
    print(f"manifest tests={len(ROUTING_CONTRACT_TESTS)} cwd={UI_ROOT}", flush=True)
    proc = subprocess.run(cmd, cwd=UI_ROOT, check=False)
    if proc.returncode != 0:
        print("FAIL trace_scope_routing_contract_smoke", file=sys.stderr)
        return proc.returncode or 1
    print("OK trace_scope_routing_contract_smoke", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
