#!/usr/bin/env python3
"""Compare baseline vs candidate trace-review artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from trace_compare.runner import main  # pylint: disable=import-error, wrong-import-position

if __name__ == "__main__":
    raise SystemExit(main())
