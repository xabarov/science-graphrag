"""Consistency report builders for retrieval_v1 extractors (split from ``retrieval_v1.py``)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.dual_validate.consistency_report import ConsistencyReport, ExtractorInfo
from scripts.dual_validate.extractors.base import ExtractorRunOutput
from scripts.dual_validate.extractors.retrieval_v1_ranking import kendall_order as _kendall_order
from scripts.dual_validate.extractors.retrieval_v1_ranking import set_metrics as _set_metrics
from scripts.dual_validate.extractors.retrieval_v1_workspace_priority import (
    classify_workspace_scoped_spot_check,
)
from scripts.dual_validate.matcher import EmbeddingScorerProtocol


def _pack_rel_paths(pack_dir: Path) -> tuple[Path, str]:
    gold_path = (pack_dir / "gold.json").resolve()
    try:
        rel_pack = pack_dir.resolve().relative_to(Path.cwd())
        rel_gold = gold_path.relative_to(Path.cwd())
    except ValueError:
        rel_pack = pack_dir
        rel_gold = gold_path
    return rel_pack, str(rel_gold)


def workspace_scoped_live_consistency_report(
    pack_dir: Path,
    *,
    run: ExtractorRunOutput | None,
    gold_a: dict,
    layer_name: str,
    embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG001
) -> ConsistencyReport:
    a_required = {
        c["corpus_work_id"]
        for c in gold_a.get("expected_citations", [])
        if c.get("required") is True
    }
    a_optional = {
        c["corpus_work_id"]
        for c in gold_a.get("expected_citations", [])
        if c.get("required") is False
    }
    a_all = a_required | a_optional
    a_forbidden = set(gold_a.get("forbidden_corpus_work_ids", []))

    if run is not None and run.structured_b:
        payload = run.structured_b[0]
        b_expected = set(payload["expected_corpus_work_ids"])
        b_violations = set(payload["would_violate_workspace_with"])
        rationale = payload["rationale"]
    else:
        b_expected = set()
        b_violations = set()
        rationale = ""

    b_real_violations = b_violations & a_forbidden
    b_phantom_violations = b_violations - a_forbidden
    crossed_boundary_directly = b_expected & a_forbidden
    metrics_required = _set_metrics(a_required, b_expected)
    metrics_all = _set_metrics(a_all, b_expected)

    matched_pairs: list[dict[str, Any]] = []
    for wid in sorted(a_all & b_expected):
        matched_pairs.append(
            {
                "corpus_work_id": wid,
                "match_score": 1.0,
                "match_source": "set",
                "field_disagreements": [],
            }
        )
    unmatched_a = [
        {"corpus_work_id": wid, "kind": "missed_by_b", "required": wid in a_required}
        for wid in sorted(a_all - b_expected)
    ]
    unmatched_b = [
        {"corpus_work_id": wid, "kind": "extra_in_b"} for wid in sorted(b_expected - a_all)
    ]
    for wid in sorted(crossed_boundary_directly):
        unmatched_b.append(
            {
                "corpus_work_id": wid,
                "kind": "boundary_violation",
                "comment": "B proposed an out-of-scope paper as a citation",
            }
        )

    priority, why = classify_workspace_scoped_spot_check(
        metrics_required=metrics_required,
        metrics_all=metrics_all,
        boundary_violations=len(crossed_boundary_directly),
        real_violations_predicted=len(b_real_violations),
        a_empty_negative_case=(len(a_all) == 0),
        b_empty=(len(b_expected) == 0),
    )

    rel_pack, rel_gold_str = _pack_rel_paths(pack_dir)

    a_info = ExtractorInfo(
        role="human_authored_existing_gold",
        source=str(rel_gold_str),
        count=len(a_all),
    )
    if run is None:
        b_info = ExtractorInfo(
            role="llm_independent_extraction_dry_run",
            source="dry-run (no LLM call)",
            count=0,
        )
    else:
        b_info = ExtractorInfo(
            role="llm_independent_extraction",
            source=f"workspace={gold_a.get('workspace_id', '?')} | question.txt",
            model=run.call_spec.model,
            base_url=run.call_spec.base_url,
            prompt_hash=run.prompt_hash,
            count=len(b_expected),
            usage_tokens=run.usage_tokens,
            latency_ms=run.latency_ms,
        )

    summary = {
        "a_total": len(a_all),
        "b_total": len(b_expected),
        "matched": len(matched_pairs),
        "matched_lexical": len(matched_pairs),
        "matched_embedding": 0,
        "unmatched_a": len(unmatched_a),
        "unmatched_b": len(unmatched_b),
        "metrics_required_only": metrics_required,
        "metrics_required_or_optional": metrics_all,
        "boundary_violations_count": len(crossed_boundary_directly),
        "real_forbidden_predictions": len(b_real_violations),
        "phantom_forbidden_predictions": len(b_phantom_violations),
        "rationale_b": rationale,
    }
    return ConsistencyReport(
        pack_id=pack_dir.name,
        pack_path=str(rel_pack),
        layer=layer_name,
        extractor_a=a_info,
        extractor_b=b_info,
        matched_pairs=matched_pairs,
        unmatched_a=unmatched_a,
        unmatched_b=unmatched_b,
        summary=summary,
        spot_check_priority=priority,
        spot_check_priority_rationale=why,
    )


def hybrid_ablation_v2_consistency_report(
    pack_dir: Path,
    *,
    run: ExtractorRunOutput | None,
    gold_a: dict,
    layer_name: str,
    embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG001
) -> ConsistencyReport:
    a_relevant = set(gold_a.get("relevant_corpus_work_ids", []))
    a_irrelevant = set(gold_a.get("irrelevant_corpus_work_ids", []))
    candidates = a_relevant | a_irrelevant

    if run is not None and run.structured_b:
        payload = run.structured_b[0]
        b_relevant = set(payload["relevant"]) & candidates
        rationale = payload["rationale"]
    else:
        b_relevant = set()
        rationale = ""
    b_irrelevant = candidates - b_relevant

    agree_relevant = a_relevant & b_relevant
    agree_irrelevant = a_irrelevant & b_irrelevant
    disagree_a_relevant_b_irrelevant = a_relevant & b_irrelevant
    disagree_a_irrelevant_b_relevant = a_irrelevant & b_relevant

    metrics = _set_metrics(a_relevant, b_relevant)
    accuracy = (
        (len(agree_relevant) + len(agree_irrelevant)) / len(candidates) if candidates else 0.0
    )

    matched_pairs = [
        {
            "corpus_work_id": wid,
            "label": "relevant",
            "match_score": 1.0,
            "match_source": "set",
            "field_disagreements": [],
        }
        for wid in sorted(agree_relevant)
    ] + [
        {
            "corpus_work_id": wid,
            "label": "irrelevant",
            "match_score": 1.0,
            "match_source": "set",
            "field_disagreements": [],
        }
        for wid in sorted(agree_irrelevant)
    ]
    unmatched_a = [
        {"corpus_work_id": wid, "label_a": "relevant", "label_b": "irrelevant"}
        for wid in sorted(disagree_a_relevant_b_irrelevant)
    ] + [
        {"corpus_work_id": wid, "label_a": "irrelevant", "label_b": "relevant"}
        for wid in sorted(disagree_a_irrelevant_b_relevant)
    ]
    unmatched_b: list[dict[str, Any]] = []

    if accuracy >= 0.9 and metrics["f1"] >= 0.9:
        priority = "low"
        why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f}"
    elif accuracy >= 0.75 and metrics["f1"] >= 0.6:
        priority = "medium"
        why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f}"
    else:
        priority = "high"
        why = f"accuracy={accuracy:.2f}, f1_relevant={metrics['f1']:.2f} (gate)"

    rel_pack, rel_gold_str = _pack_rel_paths(pack_dir)

    a_info = ExtractorInfo(
        role="human_authored_existing_gold",
        source=str(rel_gold_str),
        count=len(a_relevant),
    )
    if run is None:
        b_info = ExtractorInfo(
            role="llm_independent_extraction_dry_run",
            source="dry-run (no LLM call)",
            count=0,
        )
    else:
        b_info = ExtractorInfo(
            role="llm_independent_extraction",
            source=f"question.txt | candidates={len(candidates)}",
            model=run.call_spec.model,
            base_url=run.call_spec.base_url,
            prompt_hash=run.prompt_hash,
            count=len(b_relevant),
            usage_tokens=run.usage_tokens,
            latency_ms=run.latency_ms,
        )

    summary = {
        "a_total": len(a_relevant),
        "b_total": len(b_relevant),
        "matched": len(matched_pairs),
        "matched_lexical": len(matched_pairs),
        "matched_embedding": 0,
        "unmatched_a": len(unmatched_a),
        "unmatched_b": 0,
        "candidates_total": len(candidates),
        "accuracy": round(accuracy, 3),
        "metrics_relevant": metrics,
        "rationale_b": rationale,
    }
    return ConsistencyReport(
        pack_id=pack_dir.name,
        pack_path=str(rel_pack),
        layer=layer_name,
        extractor_a=a_info,
        extractor_b=b_info,
        matched_pairs=matched_pairs,
        unmatched_a=unmatched_a,
        unmatched_b=unmatched_b,
        summary=summary,
        spot_check_priority=priority,
        spot_check_priority_rationale=why,
    )


def classify_multihop_spot_check_priority(
    metrics: dict[str, float],
    order: float | None,
    min_order: float | None,
) -> tuple[str, str]:
    if metrics["f1"] >= 0.9 and (order is None or order >= (min_order or 0.8)):
        return ("low", f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'}")
    if metrics["f1"] >= 0.6:
        return ("medium", f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'}")
    return ("high", f"f1={metrics['f1']:.2f}, order={order if order is not None else 'n/a'} (gate)")


def multihop_v2_consistency_report(
    pack_dir: Path,
    *,
    run: ExtractorRunOutput | None,
    gold_a: dict,
    layer_name: str,
    embedding_scorer: EmbeddingScorerProtocol | None = None,  # noqa: ARG001
) -> ConsistencyReport:
    path_kind = gold_a.get("expected_path_kind", "unordered_set")
    if path_kind == "ordered_chain":
        a_chain = list(gold_a.get("expected_chain_corpus_work_ids", []))
        a_set = set(a_chain)
        if run is not None and run.structured_b:
            b_chain = run.structured_b[0]["expected_chain_corpus_work_ids"]
        else:
            b_chain = []
        b_set = set(b_chain)
        metrics = _set_metrics(a_set, b_set)
        order_correctness = _kendall_order(a_chain, b_chain)
        extra_payload = {
            "a_chain": a_chain,
            "b_chain": b_chain,
            "order_correctness": order_correctness,
            "min_chain_order_correctness": gold_a.get("min_chain_order_correctness", 0.8),
        }
    else:
        a_chain = []
        b_chain = []
        a_set = set(gold_a.get("expected_node_canonical_names", []))
        if run is not None and run.structured_b:
            b_set = set(run.structured_b[0]["expected_node_canonical_names"])
        else:
            b_set = set()
        metrics = _set_metrics(a_set, b_set)
        order_correctness = None
        extra_payload = {
            "expected_node_kind": gold_a.get("expected_node_kind"),
            "a_node_canonical_names": sorted(a_set),
            "b_node_canonical_names": sorted(b_set),
            "min_recall": gold_a.get("min_recall"),
            "min_precision": gold_a.get("min_precision"),
        }

    matched_pairs = [
        {
            "node_or_work_id": wid,
            "match_score": 1.0,
            "match_source": "set",
            "field_disagreements": [],
        }
        for wid in sorted(a_set & b_set)
    ]
    unmatched_a = [{"node_or_work_id": wid} for wid in sorted(a_set - b_set)]
    unmatched_b = [{"node_or_work_id": wid} for wid in sorted(b_set - a_set)]

    priority, why = classify_multihop_spot_check_priority(
        metrics, order_correctness, gold_a.get("min_chain_order_correctness")
    )

    rel_pack, rel_gold_str = _pack_rel_paths(pack_dir)

    a_info = ExtractorInfo(
        role="human_authored_existing_gold",
        source=str(rel_gold_str),
        count=len(a_set),
    )
    if run is None:
        b_info = ExtractorInfo(
            role="llm_independent_extraction_dry_run",
            source="dry-run (no LLM call)",
            count=0,
        )
    else:
        b_info = ExtractorInfo(
            role="llm_independent_extraction",
            source=f"path_kind={path_kind} | question.txt",
            model=run.call_spec.model,
            base_url=run.call_spec.base_url,
            prompt_hash=run.prompt_hash,
            count=len(b_set),
            usage_tokens=run.usage_tokens,
            latency_ms=run.latency_ms,
        )

    summary = {
        "a_total": len(a_set),
        "b_total": len(b_set),
        "matched": len(matched_pairs),
        "matched_lexical": len(matched_pairs),
        "matched_embedding": 0,
        "unmatched_a": len(unmatched_a),
        "unmatched_b": len(unmatched_b),
        "expected_path_kind": path_kind,
        "metrics": metrics,
        **extra_payload,
    }
    return ConsistencyReport(
        pack_id=pack_dir.name,
        pack_path=str(rel_pack),
        layer=layer_name,
        extractor_a=a_info,
        extractor_b=b_info,
        matched_pairs=matched_pairs,
        unmatched_a=unmatched_a,
        unmatched_b=unmatched_b,
        summary=summary,
        spot_check_priority=priority,
        spot_check_priority_rationale=why,
    )
