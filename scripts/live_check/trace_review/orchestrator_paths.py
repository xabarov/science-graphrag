"""Filesystem anchors for trace-review orchestration."""

from __future__ import annotations

from pathlib import Path

_ORCH_DIR = Path(__file__).resolve().parent
SCRIPT_DIR = _ORCH_DIR.parent
REPO_ROOT = SCRIPT_DIR.parent.parent

__all__ = ["ORCH_DIR", "SCRIPT_DIR", "REPO_ROOT"]

ORCH_DIR = _ORCH_DIR
