"""Contract metrics for hybrid ablation tier (Wave Q, advisory)."""

from __future__ import annotations

from typing import Any


def mrr_first_relevant(ranked_ids: list[str], relevant: set[str]) -> float:
    """Reciprocal rank of the first document in ``ranked_ids`` that lies in ``relevant``."""

    for i, x in enumerate(ranked_ids, start=1):
        if x in relevant:
            return 1.0 / float(i)
    return 0.0


def score_hybrid_ablation_gold(gold: dict[str, Any]) -> dict[str, Any]:
    """Compare synthetic ranked work-id lists (contract-only, no live Qdrant)."""

    rel = {str(x).strip() for x in (gold.get("relevant_work_ids") or []) if str(x).strip()}
    v = [str(x).strip() for x in (gold.get("vector_ranked_work_ids") or []) if str(x).strip()]
    h = [str(x).strip() for x in (gold.get("hybrid_ranked_work_ids") or []) if str(x).strip()]
    mv = mrr_first_relevant(v, rel)
    mh = mrr_first_relevant(h, rel)
    delta = mh - mv
    min_d = float(gold.get("min_mrr_delta", 0.05))
    passed = delta + 1e-9 >= min_d
    return {
        "passed": passed,
        "mrr_vector": mv,
        "mrr_hybrid": mh,
        "mrr_delta": delta,
        "min_mrr_delta": min_d,
        "relevant_count": len(rel),
    }
