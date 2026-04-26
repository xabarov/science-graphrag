"""Scoring for ontology claims benchmark v1."""

from __future__ import annotations

from typing import Any

from eval.layer1.text_similarity import rouge_l_f1


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


def _row_paraphrase_mode(row: dict[str, Any]) -> str | None:
    m = row.get("match_mode")
    if isinstance(m, str) and m.strip():
        v = m.strip().lower()
        if v in {"embedding_sim", "rouge_l", "exact"}:
            return v
    return None


def _needs_paraphrase_scoring(gold: dict[str, Any]) -> bool:
    for r in gold.get("expected_claims") or []:
        if isinstance(r, dict) and _row_paraphrase_mode(r):
            return True
    return False


def _embedding_threshold(gold: dict[str, Any], row: dict[str, Any]) -> float:
    for key in ("min_embedding_sim",):
        v = row.get(key) or gold.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                break
    return 0.75


def _rouge_threshold(gold: dict[str, Any], row: dict[str, Any]) -> float:
    for key in ("min_claim_rouge_l", "min_rouge_l"):
        v = row.get(key) or gold.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                break
    return 0.35


def _pred_candidate_strings(pred: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for k in ("claim_text", "claim_text_normalized", "text"):
        t = pred.get(k)
        if isinstance(t, str) and t.strip():
            out.append(t.strip())
    return out or [""]


def _row_matched_paraphrase(
    row: dict[str, Any],
    preds: list[dict[str, Any]],
    gold: dict[str, Any],
    *,
    embedder: Any,
) -> bool:
    cid = str(row.get("claim_id") or "")
    if cid:
        for p in preds:
            if isinstance(p, dict) and str(p.get("claim_id") or "") == cid:
                return True
    mode = _row_paraphrase_mode(row)
    gold_norm = _normalize_claim_text(row.get("claim_text_normalized"))
    if mode == "embedding_sim" and embedder is not None and gold_norm:
        try:
            gold_vec = embedder.embed_one(gold_norm)
        except Exception:
            return False
        best = 0.0
        for p in preds:
            if not isinstance(p, dict):
                continue
            for cand in _pred_candidate_strings(p):
                if not cand.strip():
                    continue
                try:
                    pv = embedder.embed_one(cand[:8000])
                    best = max(best, float(embedder.cosine(gold_vec, pv)))
                except Exception:
                    continue
        return best + 1e-9 >= _embedding_threshold(gold, row)
    if mode == "rouge_l" and gold_norm:
        best_r = 0.0
        for p in preds:
            if not isinstance(p, dict):
                continue
            for cand in _pred_candidate_strings(p):
                best_r = max(best_r, float(rouge_l_f1(gold_norm, cand)))
        return best_r + 1e-9 >= _rouge_threshold(gold, row)
    if mode == "exact" and gold_norm:
        return _row_matched_by_text(gold_norm, preds)
    mode_top = _claim_match_mode(gold)
    if cid:
        pred_ids = {
            str(p.get("claim_id"))
            for p in preds
            if isinstance(p, dict) and p.get("claim_id")
        }
        if cid in pred_ids:
            return True
    if mode_top == "claim_id_or_normalized_text" and gold_norm:
        return _row_matched_by_text(gold_norm, preds)
    return False


def _precision_matched_preds(
    expected_rows: list[dict[str, Any]],
    preds: list[dict[str, Any]],
    gold: dict[str, Any],
    *,
    embedder: Any,
) -> tuple[float, int]:
    if not preds:
        return 0.0, 0
    matched = 0
    for pred in preds:
        if not isinstance(pred, dict):
            continue
        ok = False
        for row in expected_rows:
            if not isinstance(row, dict):
                continue
            if not row.get("claim_id") and not row.get("claim_text_normalized"):
                continue
            if _row_matched_paraphrase(row, [pred], gold, embedder=embedder):
                ok = True
                break
        if ok:
            matched += 1
    return matched / len(preds), matched


def score_claims_paraphrase_extraction(
    predictions_plain: list[dict[str, Any]],
    predictions_distracted: list[dict[str, Any]] | None,
    gold: dict[str, Any],
    *,
    settings: Any = None,
) -> dict[str, Any]:
    """BT6: ``expected_claims[].match_mode`` (embedding_sim / rouge_l) + distractor precision drop."""

    contract_only = bool(gold.get("contract_only"))
    plain = predictions_plain if isinstance(predictions_plain, list) else []
    if contract_only:
        return score_claims_extraction(plain, gold)

    if not _needs_paraphrase_scoring(gold):
        merged = score_claims_extraction(plain, gold)
        merged["paraphrase_scoring"] = False
        return merged

    needs_emb = any(_row_paraphrase_mode(r) == "embedding_sim" for r in (gold.get("expected_claims") or []) if isinstance(r, dict))
    embedder: Any = None
    if needs_emb:
        try:
            from science_graphrag.embeddings.openrouter_provider import (
                OpenRouterEmbeddingProvider,
                resolve_openrouter_embedding_settings,
            )

            cfg = resolve_openrouter_embedding_settings(settings=settings)
            embedder = OpenRouterEmbeddingProvider(cfg)
        except Exception as exc:  # noqa: BLE001
            denom = len(
                [r for r in (gold.get("expected_claims") or []) if isinstance(r, dict)],
            )
            return {
                "contract_only": False,
                "contract_passed": False,
                "passed": False,
                "claim_recall": 0.0,
                "claim_precision": 0.0,
                "paraphrase_scoring": True,
                "paraphrase_embed_error": str(exc),
                "expected_count": denom,
                "predicted_count": len(plain),
            }

    expected_rows = [r for r in (gold.get("expected_claims") or []) if isinstance(r, dict)]
    matched_ids: list[str] = []
    missing_ids: list[str] = []
    for row in expected_rows:
        cid = str(row.get("claim_id") or "") or "?"
        if _row_matched_paraphrase(row, plain, gold, embedder=embedder):
            matched_ids.append(cid)
        else:
            missing_ids.append(cid)

    denom_r = len(expected_rows)
    recall = (len(matched_ids) / denom_r) if denom_r else 1.0
    min_rr = float(gold.get("min_claim_recall") or 0.55)

    prec_plain, _ = _precision_matched_preds(expected_rows, plain, gold, embedder=embedder)
    prec_drop = 0.0
    max_drop = float(gold.get("max_precision_drop_with_distractors") or 0.15)
    pass_drop = True
    prec_dist: float | None = None
    distracted: list[dict[str, Any]] | None = None
    if predictions_distracted is not None:
        distracted = (
            predictions_distracted if isinstance(predictions_distracted, list) else []
        )
        prec_dist, _ = _precision_matched_preds(
            expected_rows,
            distracted,
            gold,
            embedder=embedder,
        )
        prec_drop = max(0.0, prec_plain - prec_dist)
        pass_drop = prec_drop <= max_drop + 1e-9

    passed = recall + 1e-9 >= min_rr and pass_drop

    return {
        "contract_only": False,
        "contract_passed": True,
        "passed": passed,
        "claim_recall": recall,
        "claim_precision": prec_plain,
        "claim_precision_distracted": prec_dist,
        "precision_drop_with_distractors": prec_drop,
        "max_precision_drop_with_distractors": max_drop,
        "paraphrase_scoring": True,
        "claim_match_mode": _claim_match_mode(gold),
        "expected_count": denom_r,
        "predicted_count_plain": len(plain),
        "predicted_count_distracted": len(distracted) if distracted is not None else None,
        "matched_claim_ids": matched_ids,
        "missing_claim_ids": missing_ids,
        "min_claim_recall": min_rr,
    }
