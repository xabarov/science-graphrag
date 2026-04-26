"""Discover claims benchmark case directories (shared by BT6 paraphrase + main runner)."""

from __future__ import annotations

import json
from pathlib import Path

from eval.claims.article_source import claims_case_has_article


def load_claims_case_tiers(fixtures_root: Path) -> dict[str, list[str]] | None:
    path = fixtures_root / "case_tiers.json"
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    if not isinstance(raw, dict):
        return None
    out: dict[str, list[str]] = {}
    for key, val in raw.items():
        if isinstance(val, list):
            out[str(key)] = [str(x) for x in val]
    return out or None


def discover_claims_case_dirs(
    fixtures_root: Path,
    *,
    tier: str = "claims_merge_contract",
) -> list[Path]:
    """Subdirectories containing resolvable ``article.md`` (or layer1) and ``gold.json``."""

    if not fixtures_root.is_dir():
        return []
    tiers: dict[str, list[str]] | None = load_claims_case_tiers(fixtures_root)
    allowed: set[str] | None
    if tier == "all":
        allowed = None
    elif tiers is not None:
        tier_ids = tiers.get(tier)
        if tier_ids is None:
            return []
        allowed = set(tier_ids)
    else:
        allowed = None

    out: list[Path] = []
    for child in sorted(fixtures_root.iterdir()):
        if not child.is_dir():
            continue
        gold_path = child / "gold.json"
        if not gold_path.is_file():
            continue
        if not claims_case_has_article(child):
            continue
        try:
            meta = json.loads(gold_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, TypeError):
            meta = {}
        if meta.get("skip_in_suite_cli"):
            continue
        cid = child.name
        if allowed is not None and cid not in allowed:
            continue
        out.append(child)
    return out
