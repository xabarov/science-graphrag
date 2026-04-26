"""Append neighboring-paper excerpts for claims paraphrase / distractor benchmarks (BT6)."""

from __future__ import annotations

import json
from pathlib import Path


def augment_article_with_distractors(
    article: str,
    gold: dict[str, Any],
    *,
    repo_root: Path,
    layer1_root: Path | None = None,
) -> tuple[str, bool]:
    """Return ``(text, augmented)`` — neighbor paragraphs appended when strategy is present."""

    strat = gold.get("distractor_strategy")
    if not isinstance(strat, dict):
        return article, False
    if str(strat.get("type") or "").strip() != "neighboring_paper_paragraphs":
        return article, False
    neighbors = strat.get("neighbor_corpus_work_ids") or []
    if not isinstance(neighbors, list) or not neighbors:
        return article, False
    max_para = int(strat.get("max_distractor_paragraphs") or 3)
    root = layer1_root or (repo_root / "tests" / "fixtures" / "benchmarks" / "layer1")
    chunks: list[str] = []
    for slug in neighbors[:max_para]:
        sid = str(slug).strip()
        if not sid:
            continue
        art_path = root / sid / "article.md"
        if not art_path.is_file():
            continue
        try:
            body = art_path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        excerpt = body[:2400].strip()
        if excerpt:
            chunks.append(f"\n\n## Distractor context: {sid}\n\n{excerpt}\n")
    if not chunks:
        return article, False
    return article + "".join(chunks), True
