"""Load trace-review JSON artifacts for regression compare.

Requires ``scripts/live_check`` on ``sys.path`` (``trace_compare.runner`` does this before
importing this module).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from trace_regression_metrics import load_review as _load  # pylint: disable=import-error
from trace_review.constants import REVIEW_VERSION


def require_version(doc: dict[str, Any], label: str) -> None:
    """Exit with code 2 when ``review_version`` is not ``trace-review-v1``."""
    ver = str(doc.get("review_version") or "")
    if ver != REVIEW_VERSION:
        print(
            f"[trace-regression] FATAL: {label} has review_version={ver!r}, "
            f"expected {REVIEW_VERSION!r}",
            file=sys.stderr,
        )
        raise SystemExit(2)


def load_pair(baseline: Path, candidate: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load baseline and candidate JSON, enforcing matching ``review_version``."""
    base = _load(baseline)
    cand = _load(candidate)
    require_version(base, "baseline")
    require_version(cand, "candidate")
    return base, cand
