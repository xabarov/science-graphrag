"""Helpers for sidechain transcript enablement and root directory resolution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from science_graphrag.config import Settings

_DEFAULT_SIDECHAIN_DIR = ".agent_sidechains"
_TRUE_STRINGS = frozenset({"1", "true", "yes", "on"})


def sidechain_transcripts_enabled(settings: Settings) -> bool:
    """Treat only real bool/flag values as enabled, not arbitrary truthy mocks."""

    raw = getattr(settings, "agent_sidechain_transcripts_enabled", False)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return raw.strip().lower() in _TRUE_STRINGS
    return False


def sidechain_transcripts_root(settings: Settings) -> Path:
    """Stable sidechain transcript root with safe fallback for unwritable default path."""

    raw = getattr(settings, "agent_sidechain_transcripts_dir", None)
    configured = raw.strip() if isinstance(raw, str) else ""
    candidate = Path(configured or _DEFAULT_SIDECHAIN_DIR).expanduser()
    if configured and configured != _DEFAULT_SIDECHAIN_DIR:
        return candidate
    if _path_is_writable_or_creatable(candidate):
        return candidate
    fallback = _fallback_sidechain_dir()
    if _path_is_writable_or_creatable(fallback):
        return fallback
    return candidate


def _path_is_writable_or_creatable(path: Path) -> bool:
    """Whether current process can append under ``path`` or create it if missing."""

    try:
        if path.exists():
            return path.is_dir() and os.access(path, os.W_OK | os.X_OK)
        parent = path.parent
        while not parent.exists() and parent != parent.parent:
            parent = parent.parent
        return parent.exists() and os.access(parent, os.W_OK | os.X_OK)
    except OSError:
        return False


def _fallback_sidechain_dir() -> Path:
    """User-writable fallback outside the repo working tree."""

    return Path.home() / ".scigraph" / "agent_sidechains"


__all__ = ["sidechain_transcripts_enabled", "sidechain_transcripts_root"]
