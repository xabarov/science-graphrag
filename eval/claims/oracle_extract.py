"""Deterministic \"oracle\" predictions from gold (BT6 wiring / CI smoke without LLM keys)."""

from __future__ import annotations

from typing import Any


def extract_claims_oracle_from_gold(_article: str, gold: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one prediction dict per ``expected_claims`` row (claim_id + normalized text)."""

    out: list[dict[str, Any]] = []
    for row in gold.get("expected_claims") or []:
        if not isinstance(row, dict):
            continue
        cid = str(row.get("claim_id") or "").strip()
        if not cid:
            continue
        txt = str(row.get("claim_text_normalized") or "").strip()
        out.append(
            {
                "claim_id": cid,
                "claim_text_normalized": txt,
                "claim_text": txt,
            }
        )
    return out
