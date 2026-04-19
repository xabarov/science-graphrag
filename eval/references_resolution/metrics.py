"""Scoring for references_resolution benchmark v1."""

from __future__ import annotations

from typing import Any


def _min_resolution_recall(gold: dict[str, Any]) -> float:
    raw = gold.get("min_resolution_recall")
    try:
        return float(raw) if raw is not None else 1.0
    except (TypeError, ValueError):
        return 1.0


def _normalize_key(key: str | None) -> str:
    return str(key or "").strip().lower()


def score_references_resolution(  # pylint: disable=too-many-locals
    predictions: list[dict[str, Any]], gold: dict[str, Any]
) -> dict[str, Any]:
    """Score predicted resolutions against ``gold['expected_resolutions']``."""

    contract_only = bool(gold.get("contract_only"))
    preds = predictions if isinstance(predictions, list) else []

    if contract_only:
        ok = isinstance(predictions, list) and all(
            isinstance(p, dict) and p.get("raw_citation_span_id") and p.get("canonical_key")
            for p in preds
        )
        return {
            "contract_only": True,
            "contract_passed": ok,
            "passed": ok,
            "resolution_recall": 1.0 if ok else 0.0,
            "resolution_precision": 1.0 if ok else 0.0,
            "expected_count": 0,
            "predicted_count": len(preds),
            "matched_span_ids": [],
            "missing_span_ids": [],
            "min_resolution_recall": _min_resolution_recall(gold),
        }

    expected_rows = [
        r
        for r in (gold.get("expected_resolutions") or [])
        if isinstance(r, dict) and r.get("raw_citation_span_id") and r.get("canonical_key")
    ]
    pred_map = {
        str(p.get("raw_citation_span_id")): _normalize_key(str(p.get("canonical_key")))
        for p in preds
        if isinstance(p, dict) and p.get("raw_citation_span_id") and p.get("canonical_key")
    }

    matched: list[str] = []
    missing: list[str] = []
    for row in expected_rows:
        sid = str(row["raw_citation_span_id"])
        want = _normalize_key(str(row["canonical_key"]))
        got = pred_map.get(sid)
        if got is not None and got == want:
            matched.append(sid)
        else:
            missing.append(sid)

    denom_r = len(expected_rows)
    recall = (len(matched) / denom_r) if denom_r else 1.0
    if pred_map:
        denom_p = len(pred_map)
        precision = len(matched) / denom_p
    else:
        precision = 1.0 if denom_r == 0 else 0.0

    min_rr = _min_resolution_recall(gold)
    passed = recall + 1e-9 >= min_rr

    return {
        "contract_only": False,
        "contract_passed": True,
        "passed": passed,
        "resolution_recall": recall,
        "resolution_precision": precision,
        "expected_count": denom_r,
        "predicted_count": len(pred_map),
        "matched_span_ids": matched,
        "missing_span_ids": missing,
        "min_resolution_recall": min_rr,
    }
