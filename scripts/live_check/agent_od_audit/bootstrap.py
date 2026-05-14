"""Path bootstrap and HTTP headers for OD workspace E2E audit script."""

from __future__ import annotations

import os
import sys
from pathlib import Path

LIVE_CHECK_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = LIVE_CHECK_DIR.parent.parent


def ensure_paths() -> None:
    """Ensure ``scripts/live_check`` and repo root are importable."""
    if str(LIVE_CHECK_DIR) not in sys.path:
        sys.path.insert(0, str(LIVE_CHECK_DIR))
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))


def extra_headers() -> dict[str, str]:
    """Optional auth headers from operator env."""
    out: dict[str, str] = {}
    auth = (os.environ.get("AGENT_LIVE_AUTHORIZATION") or "").strip()
    if auth:
        out["Authorization"] = auth
    admin = (os.environ.get("AGENT_LIVE_ADMIN_KEY") or "").strip()
    if admin:
        out["X-Admin-Key"] = admin
    return out


__all__ = ["LIVE_CHECK_DIR", "REPO_ROOT", "ensure_paths", "extra_headers"]
