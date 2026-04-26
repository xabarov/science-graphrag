"""Gold-shape helpers for BT6 paraphrase routing (keeps import graph acyclic)."""

from __future__ import annotations

from typing import Any


def gold_expects_paraphrase_row_matching(gold: dict[str, Any]) -> bool:
    """True when any ``expected_claims[]`` row uses paraphrase ``match_mode``."""

    for row in gold.get("expected_claims") or []:
        if not isinstance(row, dict):
            continue
        mode = str(row.get("match_mode") or "").strip().lower()
        if mode in {"embedding_sim", "rouge_l"}:
            return True
    return False
