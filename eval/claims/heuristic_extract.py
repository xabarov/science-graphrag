"""Deterministic claims extraction harness for benchmark v1 (not production LLM)."""

from __future__ import annotations

from typing import Any


def extract_claims_anchor_harness(article_text: str, gold: dict[str, Any]) -> list[dict[str, Any]]:
    """Emit one prediction per expected row whose ``anchor_phrase`` appears in ``article_text``.

    Case-insensitive substring match. Used until real claims extraction is wired behind
    ``SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED``.
    """

    text_l = (article_text or "").lower()
    out: list[dict[str, Any]] = []
    for row in gold.get("expected_claims") or []:
        if not isinstance(row, dict):
            continue
        cid = row.get("claim_id")
        anchor = str(row.get("anchor_phrase") or "").strip()
        if not cid or not anchor:
            continue
        if anchor.lower() in text_l:
            out.append(
                {
                    "claim_id": str(cid),
                    "claim_text_normalized": row.get("claim_text_normalized"),
                    "claim_type": row.get("claim_type"),
                    "polarity": row.get("polarity"),
                }
            )
    return out
