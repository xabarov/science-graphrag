"""Filesystem helpers shared by ``retrieval_v1`` dual-validate extractors."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def discover_pack_directories(fixtures_root: Path, fixtures_subdir: str) -> list[Path]:
    """Return sorted pack dirs under ``fixtures_subdir`` that contain ``gold.json``."""

    base = fixtures_root / fixtures_subdir
    if not base.exists():
        return []
    return sorted(d for d in base.iterdir() if d.is_dir() and (d / "gold.json").exists())


def read_pack_gold_json(pack_dir: Path) -> dict[str, Any]:
    """Load ``gold.json`` for a pack directory."""

    return json.loads((pack_dir / "gold.json").read_text(encoding="utf-8"))
