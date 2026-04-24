"""Scoring for concept / research-topic benchmark v1 (Wave N)."""

from __future__ import annotations

from typing import Any


def _min_float(gold: dict[str, Any], key: str, default: float) -> float:
    raw = gold.get(key)
    try:
        return float(raw) if raw is not None else default
    except (TypeError, ValueError):
        return default


def _normalize(s: str | None) -> str:
    if s is None:
        return ""
    return " ".join(str(s).lower().split())


def _pred_concept_blob(pred: dict[str, Any]) -> str:
    parts = [pred.get("name"), pred.get("normalized_name"), pred.get("concept_id")]
    return _normalize(" ".join(str(p) for p in parts if p))


def _pred_topic_blob(pred: dict[str, Any]) -> str:
    parts = [pred.get("name"), pred.get("normalized_name"), pred.get("topic_id")]
    return _normalize(" ".join(str(p) for p in parts if p))


def _match_expected_rows(
    expected_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    id_key: str,
    pred_blob_fn: Any,
) -> tuple[list[str], list[str]]:
    """Return (matched_ids, missing_ids) using id match first, then anchor phrase in blob."""

    matched: list[str] = []
    missing: list[str] = []
    pred_list = [p for p in predictions if isinstance(p, dict)]
    pred_ids = {str(p.get(id_key)) for p in pred_list if p.get(id_key)}

    for row in expected_rows:
        if not isinstance(row, dict):
            continue
        eid = str(row.get(id_key) or "")
        if not eid:
            continue
        if eid in pred_ids:
            matched.append(eid)
            continue
        anchor = _normalize(str(row.get("anchor_phrase") or ""))
        if anchor and any(anchor in pred_blob_fn(p) for p in pred_list):
            matched.append(eid)
            continue
        missing.append(eid)
    return matched, missing


def _precision_for_side(
    expected_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    id_key: str,
    pred_blob_fn: Any,
) -> float:
    """Micro-style precision: predictions that hit at least one expected row."""

    if not predictions:
        return 1.0
    exp_ids = {str(r.get(id_key)) for r in expected_rows if isinstance(r, dict) and r.get(id_key)}
    matched_pred_indices: set[int] = set()
    for i, pred in enumerate(predictions):
        if not isinstance(pred, dict):
            continue
        pid = str(pred.get(id_key) or "")
        if pid and pid in exp_ids:
            matched_pred_indices.add(i)
            continue
        blob = pred_blob_fn(pred)
        for row in expected_rows:
            if not isinstance(row, dict):
                continue
            anchor = _normalize(str(row.get("anchor_phrase") or ""))
            if anchor and anchor in blob:
                matched_pred_indices.add(i)
                break
    return len(matched_pred_indices) / len(predictions)


def score_concept_topic_extraction(
    predictions: dict[str, Any] | None, gold: dict[str, Any]
) -> dict[str, Any]:
    """Score predicted ``{concepts:[], topics:[]}`` against gold expected rows."""

    contract_only = bool(gold.get("contract_only"))
    preds = predictions if isinstance(predictions, dict) else {}
    concept_preds = preds.get("concepts") if isinstance(preds.get("concepts"), list) else []
    topic_preds = preds.get("topics") if isinstance(preds.get("topics"), list) else []

    if contract_only:
        ok = isinstance(predictions, dict) and isinstance(concept_preds, list) and isinstance(
            topic_preds,
            list,
        )
        return {
            "contract_only": True,
            "contract_passed": ok,
            "passed": ok,
            "concept_recall": 1.0 if ok else 0.0,
            "concept_precision": 1.0 if ok else 0.0,
            "topic_recall": 1.0 if ok else 0.0,
            "topic_precision": 1.0 if ok else 0.0,
            "expected_concepts": 0,
            "expected_topics": 0,
            "predicted_concepts": len(concept_preds),
            "predicted_topics": len(topic_preds),
        }

    exp_c = [r for r in (gold.get("expected_concepts") or []) if isinstance(r, dict)]
    exp_t = [r for r in (gold.get("expected_topics") or []) if isinstance(r, dict)]
    c_conc = [p for p in concept_preds if isinstance(p, dict)]
    c_top = [p for p in topic_preds if isinstance(p, dict)]

    min_cr = _min_float(gold, "min_concept_recall", 1.0)
    min_tr = _min_float(gold, "min_topic_recall", 1.0)

    def _recall(matched: int, denom: int) -> float:
        return (matched / denom) if denom else 1.0

    m_c, miss_c = _match_expected_rows(exp_c, c_conc, id_key="concept_id", pred_blob_fn=_pred_concept_blob)
    m_t, miss_t = _match_expected_rows(exp_t, c_top, id_key="topic_id", pred_blob_fn=_pred_topic_blob)

    recall_c = _recall(len(m_c), len(exp_c))
    recall_t = _recall(len(m_t), len(exp_t))
    prec_c = _precision_for_side(exp_c, c_conc, id_key="concept_id", pred_blob_fn=_pred_concept_blob)
    prec_t = _precision_for_side(exp_t, c_top, id_key="topic_id", pred_blob_fn=_pred_topic_blob)

    passed = (recall_c + 1e-9 >= min_cr) and (recall_t + 1e-9 >= min_tr)

    return {
        "contract_only": False,
        "contract_passed": True,
        "passed": passed,
        "concept_recall": recall_c,
        "concept_precision": prec_c,
        "topic_recall": recall_t,
        "topic_precision": prec_t,
        "min_concept_recall": min_cr,
        "min_topic_recall": min_tr,
        "expected_concepts": len(exp_c),
        "expected_topics": len(exp_t),
        "predicted_concepts": len(c_conc),
        "predicted_topics": len(c_top),
        "matched_concept_ids": m_c,
        "missing_concept_ids": miss_c,
        "matched_topic_ids": m_t,
        "missing_topic_ids": miss_t,
    }
