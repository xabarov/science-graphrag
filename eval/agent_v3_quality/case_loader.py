"""Discover frozen agent v3 quality benchmark cases from fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def discover_agent_v3_quality_case_dirs(
    fixtures_root: Path,
    *,
    tier: str,
) -> list[Path]:
    """Return case directories for ``tier`` using ``case_tiers.json`` manifest."""

    manifest = fixtures_root / "case_tiers.json"
    allowed: set[str] | None = None
    if manifest.is_file():
        raw: dict[str, Any] = json.loads(manifest.read_text(encoding="utf-8"))
        if tier in raw:
            allowed = {str(x) for x in raw[tier]}
    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "question.txt").is_file() or not (child / "gold.json").is_file():
            continue
        if allowed is not None and child.name not in allowed:
            continue
        out.append(child)
    return out


def load_case_gold(case_dir: Path) -> dict[str, Any]:
    """Load ``gold.json`` for a case directory."""

    return json.loads((case_dir / "gold.json").read_text(encoding="utf-8"))


def load_case_question(case_dir: Path) -> str:
    """Load ``question.txt`` for a case directory."""

    return (case_dir / "question.txt").read_text(encoding="utf-8").strip()
