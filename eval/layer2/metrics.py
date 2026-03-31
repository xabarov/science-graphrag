"""Scores for semantic Method/Dataset layer-2 extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from eval.layer2.spec import SemanticGoldSpec
from science_graphrag.domain.semantic_models import SemanticExtractionV1


def _norm_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


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
    pred_methods = [
        _norm_name(m.name)
        for m in pred.methods
        if m.confidence >= confidence_threshold and (m.name or "").strip()
    ]
    pred_datasets = [
        _norm_name(d.name)
        for d in pred.datasets
        if d.confidence >= confidence_threshold and (d.name or "").strip()
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

    method_tp = len(gold_methods & set(pred_methods))
    method_fp = len(set(pred_methods) - gold_methods)
    method_p = method_tp / (method_tp + method_fp) if (method_tp + method_fp) else 1.0
    method_r_denom = len(gold_methods) if gold_methods else 1
    method_r_num = method_tp

    ds_tp = len(gold_ds & set(pred_datasets))
    ds_fp = len(set(pred_datasets) - gold_ds)
    ds_p = ds_tp / (ds_tp + ds_fp) if (ds_tp + ds_fp) else 1.0
    ds_r_denom = len(gold_ds) if gold_ds else 1
    ds_r_num = ds_tp

    ok = True
    notes_parts = []
    if gold_methods and method_tp < gold.min_method_names:
        ok = False
    if gold.max_method_names is not None and len(pred_methods) > gold.max_method_names:
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
            notes_parts.append(
                f"dataset_recall_below_min={dataset_recall:.3f}<{gold.min_dataset_recall_ratio:.3f}",
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
