#!/usr/bin/env python3
"""Canonical live trace-review orchestrator (trace-review-v1).

Runs base HTTP checks plus optional OD E2E audit and emits a single JSON/MD
artifact pair suitable for PR evidence and baseline diff.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from trace_review.agent_trace_review_orchestrator import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
