"""Resolve benchmark article text for claims cases (inline or layer1 fixture)."""

from __future__ import annotations

import json
from pathlib import Path

from science_graphrag.ingestion.claims.quote_match import normalize_text_for_llm


def read_claims_article(case_dir: Path) -> str:
    """Return ``article.md`` from the case dir, or from ``source_layer1_fixture`` under layer1."""

    root = Path(case_dir)
    local = root / "article.md"
    if local.is_file():
        return normalize_text_for_llm(local.read_text(encoding="utf-8"))

    gold_path = root / "gold.json"
    if not gold_path.is_file():
        return ""
    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return ""

    slug = str(gold.get("source_layer1_fixture") or "").strip()
    if not slug:
        return ""

    # case_dir = <repo>/tests/fixtures/benchmarks/claims/<case_id>
    repo = root.resolve().parents[4]
    layer1_article = repo / "tests" / "fixtures" / "benchmarks" / "layer1" / slug / "article.md"
    if layer1_article.is_file():
        return normalize_text_for_llm(layer1_article.read_text(encoding="utf-8"))
    return ""


def claims_case_has_article(case_dir: Path) -> bool:
    """True if ``read_claims_article`` would return non-empty text."""

    return bool(read_claims_article(case_dir))
