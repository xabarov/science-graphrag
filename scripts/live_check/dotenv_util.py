"""Shared dotenv loading for live_check CLIs."""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


def load_dotenv_or_warn(env_path: Path) -> bool:
    """Load ``env_path`` with override=True; print a warning if missing."""
    expanded = env_path.expanduser()
    if expanded.is_file():
        load_dotenv(expanded, override=True)
        return True
    print(f"warning: env file not found: {expanded}", file=sys.stderr)
    return False
