"""Scoring for ontology claims benchmark v1."""

from __future__ import annotations

from typing import Any


def _min_claim_recall(gold: dict[str, Any]) -> float:
    min_rr = gold.get("min_claim_recall")
    try:
        return float(min_rr) if min_rr is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


def _normalize_claim_text(text: str | None) -> str:
    if text is None:
        return ""
    return " ".join(str(text).lower().split())


def _claim_match_mode(gold: dict[str, Any]) -> str:
    """Return ``claim_id`` (default) or ``claim_id_or_normalized_text``."""

    mode = str(gold.get("claim_match_mode") or "claim_id").strip().lower()
    if mode in {"claim_id", "id", "claim_id_only"}:
        return "claim_id"
    if mode in {
        "claim_id_or_normalized_text",
        "claim_id_or_text",
        "id_or_text",
    }:
        return "claim_id_or_normalized_text"
    return "claim_id"


def _pred_text_blob(pred: dict[str, Any]) -> str:
    parts = [
        pred.get("claim_text"),
        pred.get("claim_text_normalized"),
        pred.get("text"),
    ]
    return _normalize_claim_text(" ".join(str(p) for p in parts if p))


def _row_matched_by_text(expected_norm: str, predictions: list[dict[str, Any]]) -> bool:
    if not expected_norm:
        return False
    for pred in predictions:
        if not isinstance(pred, dict):
            continue
        blob = _pred_text_blob(pred)
        if expected_norm in blob:
            return True
    return False


def _score_non_contract(  # pylint: disable=too-many-locals
    predictions: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    mode = _claim_match_mode(gold)
    expected_rows = [
        r for r in (gold.get("expected_claims") or []) if isinstance(r, dict) and r.get("claim_id")
    ]
    pred_ids = {
        str(p.get("claim_id")) for p in predictions if isinstance(p, dict) and p.get("claim_id")
    }

    matched_ids: list[str] = []
    missing_ids: list[str] = []
    for row in expected_rows:
        cid = str(row["claim_id"])
        if cid in pred_ids:
            matched_ids.append(cid)
            continue
        if mode == "claim_id_or_normalized_text":
            gold_norm = _normalize_claim_text(row.get("claim_text_normalized"))
            if _row_matched_by_text(gold_norm, predictions):
                matched_ids.append(cid)
                continue
        missing_ids.append(cid)

    denom_r = len(expected_rows)
    recall = (len(matched_ids) / denom_r) if denom_r else 1.0

    def _pred_matches_any_row(pred: dict[str, Any]) -> bool:
        pid = str(pred.get("claim_id") or "")
        blob = _pred_text_blob(pred)
        for row in expected_rows:
            cid = str(row.get("claim_id") or "")
            if pid and cid and pid == cid:
                return True
            if mode == "claim_id_or_normalized_text":
                gold_norm = _normalize_claim_text(row.get("claim_text_normalized"))
                if gold_norm and gold_norm in blob:
                    return True
        return False

    matched_pred_indices = {
        i
        for i, pred in enumerate(predictions)
        if isinstance(pred, dict) and _pred_matches_any_row(pred)
    }

    denom_p = len(predictions) if predictions else 1
    precision = len(matched_pred_indices) / denom_p

    min_recall = _min_claim_recall(gold)
    passed = recall + 1e-9 >= min_recall
    return {
        "contract_only": False,
        "contract_passed": True,
        "passed": passed,
        "claim_recall": recall,
        "claim_precision": precision,
        "claim_match_mode": mode,
        "expected_count": denom_r,
        "predicted_count": len(predictions),
        "matched_claim_ids": matched_ids,
        "missing_claim_ids": missing_ids,
        "min_claim_recall": min_recall,
    }


def score_claims_extraction(
    predictions: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    """Score predicted claim dicts against ``gold['expected_claims']``."""

    contract_only = bool(gold.get("contract_only"))
    preds = predictions if isinstance(predictions, list) else []

    if contract_only:
        ok = isinstance(predictions, list)
        return {
            "contract_only": True,
            "contract_passed": ok,
            "passed": ok,
            "claim_recall": 1.0 if ok else 0.0,
            "claim_precision": 1.0 if ok else 0.0,
            "claim_match_mode": _claim_match_mode(gold),
            "expected_count": 0,
            "predicted_count": len(preds),
            "matched_claim_ids": [],
            "missing_claim_ids": [],
        }

    return _score_non_contract(preds, gold)
