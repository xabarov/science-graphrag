"""Scoring for ontology claims benchmark v1."""

from __future__ import annotations

from typing import Any


def _min_claim_recall(gold: dict[str, Any]) -> float:
    min_rr = gold.get("min_claim_recall")
    try:
        return float(min_rr) if min_rr is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


def _score_non_contract(pred_ids: set[str], gold: dict[str, Any]) -> dict[str, Any]:
    expected_rows = [
        r for r in (gold.get("expected_claims") or []) if isinstance(r, dict) and r.get("claim_id")
    ]
    exp_ids = [str(r["claim_id"]) for r in expected_rows]
    matched = [cid for cid in exp_ids if cid in pred_ids]
    missing = [cid for cid in exp_ids if cid not in pred_ids]
    denom_r = len(exp_ids)
    recall = (len(matched) / denom_r) if denom_r else 1.0
    denom_p = len(pred_ids) if pred_ids else 1
    precision = len(matched) / denom_p
    min_recall = _min_claim_recall(gold)
    passed = recall + 1e-9 >= min_recall
    return {
        "contract_only": False,
        "contract_passed": True,
        "passed": passed,
        "claim_recall": recall,
        "claim_precision": precision,
        "expected_count": denom_r,
        "predicted_count": len(pred_ids),
        "matched_claim_ids": matched,
        "missing_claim_ids": missing,
        "min_claim_recall": min_recall,
    }


def score_claims_extraction(
    predictions: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    """Score predicted claim dicts against ``gold['expected_claims']``."""

    contract_only = bool(gold.get("contract_only"))
    preds = predictions if isinstance(predictions, list) else []
    pred_ids = {str(p.get("claim_id")) for p in preds if isinstance(p, dict) and p.get("claim_id")}

    if contract_only:
        ok = isinstance(predictions, list)
        return {
            "contract_only": True,
            "contract_passed": ok,
            "passed": ok,
            "claim_recall": 1.0 if ok else 0.0,
            "claim_precision": 1.0 if ok else 0.0,
            "expected_count": 0,
            "predicted_count": len(pred_ids),
            "matched_claim_ids": [],
            "missing_claim_ids": [],
        }

    return _score_non_contract(pred_ids, gold)
