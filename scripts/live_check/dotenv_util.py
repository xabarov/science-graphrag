"""Shared dotenv loading for live_check CLIs."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


def load_dotenv_or_warn(env_path: Path) -> bool:
    """Load ``env_path`` with override=True; print a warning if missing."""
    expanded = env_path.expanduser()
    if expanded.is_file():
        load_dotenv(expanded, override=True)
        return True
    print(f"warning: env file not found: {expanded}", file=sys.stderr)
    return False


def resolve_live_base_url(raw_base: str | None) -> str:
    """Normalize AGENT_LIVE_BASE aliases into a concrete HTTP base URL.

    Supported aliases:
    - ``dev`` -> ``AGENT_LIVE_DEV_URL`` (if set) else ``http://127.0.0.1:8787``
    - ``stable`` -> ``AGENT_LIVE_STABLE_URL`` (if set) else ``http://127.0.0.1:18787``
    """

    value = str(raw_base or "").strip()
    if not value:
        value = "http://127.0.0.1:8000"
    alias = value.lower()
    if alias == "dev":
        value = (os.environ.get("AGENT_LIVE_DEV_URL") or "").strip() or "http://127.0.0.1:8787"
    elif alias == "stable":
        value = (os.environ.get("AGENT_LIVE_STABLE_URL") or "").strip() or "http://127.0.0.1:18787"
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(
            "invalid AGENT_LIVE_BASE (expected http(s) URL or alias dev/stable): "
            f"{raw_base!r}"
        )
    return value.rstrip("/")
