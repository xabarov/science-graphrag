"""Post-processors for benchmark prediction lists (BT6 / eval only)."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


def _tokens(s: str) -> list[str]:
    t = re.sub(r"\s+", " ", str(s or "").strip().lower())
    return [x for x in re.split(r"\s+", t) if x]


def _token_jaccard(a: str, b: str) -> float:
    ta, tb = Counter(_tokens(a)), Counter(_tokens(b))
    if not ta or not tb:
        return 0.0
    inter = sum((ta & tb).values())
    uni = sum((ta | tb).values())
    return float(inter) / float(uni) if uni else 0.0


def dedupe_near_duplicate_predictions(
    predictions: list[dict[str, Any]],
    *,
    jaccard_min: float = 0.92,
) -> list[dict[str, Any]]:
    """Drop predictions whose claim text is near-duplicate of an earlier row (token Jaccard).

    Keeps the first occurrence (typically higher in model output order). Intended only for
    BT6 benchmark scoring to reduce precision noise from redundant phrasings; not used in
    production ingestion.
    """

    if jaccard_min <= 0.0 or jaccard_min > 1.0:
        raise ValueError("jaccard_min must be in (0, 1]")
    out: list[dict[str, Any]] = []
    texts_kept: list[str] = []
    for row in predictions:
        if not isinstance(row, dict):
            continue
        text = str(
            row.get("claim_text_normalized")
            or row.get("claim_text")
            or row.get("text")
            or "",
        ).strip()
        if not text:
            out.append(row)
            continue
        dup = any(_token_jaccard(text, prev) >= jaccard_min for prev in texts_kept)
        if dup:
            continue
        out.append(row)
        texts_kept.append(text)
    return out
