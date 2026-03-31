"""Scores for semantic Method/Dataset layer-2 extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.domain.semantic_models import SemanticExtractionV1


def _norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _strip_paren_chunks(value: str) -> str:
    """Remove parenthetical fragments for looser phrase overlap (e.g. abbreviations)."""

    return re.sub(r"\([^)]*\)", " ", value).strip()


def _word_jaccard(a: str, b: str) -> float:
    wa = set(_strip_paren_chunks(_norm_name(a)).split())
    wb = set(_strip_paren_chunks(_norm_name(b)).split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _gold_matches_pred_token(gold: str, pred: str) -> bool:
    """
    Match gold needle to a predicted name/alias token.

    Supports exact equality, substring containment, and high word-overlap for
    singular/plural drift (e.g. HOG phrasing).
    """

    g = _norm_name(gold)
    p = _norm_name(pred)
    if not g or not p:
        return False
    if g == p:
        return True
    if len(g) >= 3 and g in p:
        return True
    # Pred inside gold: avoid counting "yolo" as covering "fast yolo" (short pred ⊂ long gold).
    if len(p) >= 5 and p in g:
        return True
    # Long phrases: tolerate minor tokenization / plural drift
    if len(g) >= 12 and len(p) >= 12 and _word_jaccard(g, p) >= 0.55:
        return True
    return False


def _collect_pred_tokens(
    items: list,
    *,
    confidence_threshold: float,
) -> set[str]:
    tokens: list[str] = []
    for item in items:
        if item.confidence < confidence_threshold:
            continue
        if (item.name or "").strip():
            tokens.append(_norm_name(item.name))
        for alias in item.aliases:
            if alias and str(alias).strip():
                tokens.append(_norm_name(str(alias)))
    return {t for t in tokens if t}


def _count_gold_hits(golds: set[str], pred_tokens: set[str]) -> int:
    return sum(1 for g in golds if any(_gold_matches_pred_token(g, p) for p in pred_tokens))


def _count_unmatched_preds(pred_tokens: set[str], golds: set[str]) -> int:
    if not golds:
        return len(pred_tokens)
    return sum(1 for p in pred_tokens if not any(_gold_matches_pred_token(g, p) for g in golds))


@dataclass
class SemanticMetrics:
    precision_methods: float
    recall_methods_denom: int
    recall_methods_num: int
    precision_datasets: float
    recall_datasets_denom: int
    recall_datasets_num: int
    passed: bool
    notes: str

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "precision_methods": self.precision_methods,
            "recall_methods_num": self.recall_methods_num,
            "recall_methods_denom": self.recall_methods_denom,
            "precision_datasets": self.precision_datasets,
            "recall_datasets_num": self.recall_datasets_num,
            "recall_datasets_denom": self.recall_datasets_denom,
            "passed": self.passed,
            "notes": self.notes,
        }


def score_semantic(
    pred: SemanticExtractionV1,
    gold: SemanticGoldSpec,
    *,
    extraction_llm_enabled: bool,
    confidence_threshold: float = 0.35,
) -> SemanticMetrics:
    pred_method_tokens = _collect_pred_tokens(
        pred.methods,
        confidence_threshold=confidence_threshold,
    )
    pred_dataset_tokens = _collect_pred_tokens(
        pred.datasets,
        confidence_threshold=confidence_threshold,
    )
    pred_method_names_only = [
        _norm_name(m.name)
        for m in pred.methods
        if m.confidence >= confidence_threshold and (m.name or "").strip()
    ]
    gold_methods = {_norm_name(x) for x in gold.expected_method_names_normalized if x.strip()}
    gold_ds = {_norm_name(x) for x in gold.expected_dataset_names_normalized if x.strip()}

    if not extraction_llm_enabled and gold.allow_empty_when_no_llm:
        ok = True
        notes = "no_llm: skipped strict micro-F1"
        return SemanticMetrics(
            precision_methods=1.0,
            recall_methods_num=len(gold_methods),
            recall_methods_denom=max(len(gold_methods), 1),
            precision_datasets=1.0,
            recall_datasets_num=len(gold_ds),
            recall_datasets_denom=max(len(gold_ds), 1),
            passed=ok,
            notes=notes,
        )

    method_tp = _count_gold_hits(gold_methods, pred_method_tokens)
    method_fp = _count_unmatched_preds(pred_method_tokens, gold_methods)
    method_p = method_tp / (method_tp + method_fp) if (method_tp + method_fp) else 1.0
    method_r_denom = len(gold_methods) if gold_methods else 1
    method_r_num = method_tp

    ds_tp = _count_gold_hits(gold_ds, pred_dataset_tokens)
    ds_fp = _count_unmatched_preds(pred_dataset_tokens, gold_ds)
    ds_p = ds_tp / (ds_tp + ds_fp) if (ds_tp + ds_fp) else 1.0
    ds_r_denom = len(gold_ds) if gold_ds else 1
    ds_r_num = ds_tp

    ok = True
    notes_parts = []
    if gold_methods and method_tp < gold.min_method_names:
        ok = False
    if gold.max_method_names is not None and len(pred_method_names_only) > gold.max_method_names:
        ok = False
    if gold.min_method_recall_ratio is not None:
        method_recall = method_tp / method_r_denom if method_r_denom else 1.0
        if method_recall < gold.min_method_recall_ratio:
            ok = False
            notes_parts.append(
                f"method_recall_below_min={method_recall:.3f}<{gold.min_method_recall_ratio:.3f}",
            )
    if gold.min_dataset_recall_ratio is not None:
        dataset_recall = ds_tp / ds_r_denom if ds_r_denom else 1.0
        if dataset_recall < gold.min_dataset_recall_ratio:
            ok = False
            dr = gold.min_dataset_recall_ratio
            notes_parts.append(
                f"dataset_recall_below_min={dataset_recall:.3f}<{dr:.3f}",
            )

    if gold_methods:
        notes_parts.append(f"method_tp={method_tp}/{len(gold_methods)}")
    if gold_ds:
        notes_parts.append(f"dataset_tp={ds_tp}/{len(gold_ds)}")
    if not notes_parts:
        notes_parts.append("no gold names; structure-only pass")

    return SemanticMetrics(
        precision_methods=float(method_p),
        recall_methods_denom=method_r_denom,
        recall_methods_num=method_r_num,
        precision_datasets=float(ds_p),
        recall_datasets_denom=ds_r_denom,
        recall_datasets_num=ds_r_num,
        passed=ok,
        notes="; ".join(notes_parts),
    )


def load_article_for_case(case_dir, gold: SemanticGoldSpec) -> str:
    if gold.article_path:
        path = (case_dir / gold.article_path).resolve()
    else:
        path = (case_dir / "article.md").resolve()
    return path.read_text(encoding="utf-8")
