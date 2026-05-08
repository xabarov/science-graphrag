"""Suite summarizers for aggregate_benchmark_metrics."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from science_graphrag.benchmarks.trust_signal import (
    PHANTOM_RUNTIME_MODES,
    _cases_from_block,
    build_trust_signal_dict,
    detect_runtime_mode,
    summarize_family_trust,
)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_passed_layer1(case: dict[str, Any]) -> bool:
    return bool(case.get("metrics", {}).get("contract", {}).get("passed"))


def _contract_passed_graph(case: dict[str, Any]) -> bool:
    m = case.get("metrics", {})
    c = m.get("contract")
    if c is not None:
        return bool(c.get("passed"))
    return bool(m.get("contract_passed"))


def _passed_layer2(case: dict[str, Any]) -> bool:
    return bool(case.get("metrics", {}).get("passed"))


def _fallback_buckets_layer1(case: dict[str, Any]) -> dict[str, str]:
    diag = case.get("diagnostics") or {}
    out: dict[str, str] = {
        "metadata_source": str(diag.get("metadata_source") or ""),
        "authorships_source": str(diag.get("authorships_source") or ""),
        "references_source": str(diag.get("references_source") or ""),
    }
    return out


def _aggregate_fallbacks(cases: list[dict[str, Any]]) -> dict[str, Counter[str]]:
    keys = ("metadata_source", "authorships_source", "references_source")
    out: dict[str, Counter[str]] = {k: Counter() for k in keys}
    for case in cases:
        fb = _fallback_buckets_layer1(case)
        for k in keys:
            v = fb.get(k) or "unknown"
            out[k][v] += 1
    return out


def _classify_layer1_failure(case: dict[str, Any]) -> str:
    checks = (case.get("metrics") or {}).get("contract", {}).get("checks") or {}
    fr = case.get("diagnostics", {}).get("fallback_reasons") or []
    if any(x.get("stage") == "metadata" for x in fr):
        return "architecture_or_runtime"
    if checks.get("reference_count_ok_required") is False:
        return "benchmark_gold_references"
    if checks.get("reference_count_in_expected_range") is False:
        return "benchmark_gold_references"
    if not checks.get("abstract_prefix_required", True):
        return "benchmark_gold_abstract_prefix"
    if not checks.get("title_match_required", True):
        return "benchmark_gold_title"
    return "unknown"


def _classify_layer2_failure(case: dict[str, Any]) -> str:
    notes = (case.get("predicted") or {}).get("extraction_notes") or ""
    if "llm_failed" in notes or "llm_empty_result" in notes:
        return "architecture_or_runtime"
    return "benchmark_gold_or_metrics"


def summarize_reference(paths: tuple[str, ...], *, root: Path) -> dict[str, Any]:
    lanes: list[dict[str, Any]] = []
    all_ok = True
    for rel in paths:
        p = root / rel
        if not p.is_file():
            lanes.append({"artifact": rel, "error": "missing_file", "passed": None})
            all_ok = False
            continue
        data = _read_json(p)
        meta = data.get("run_metadata", {})
        case = data.get("case", {})
        cid = case.get("case_id", rel)
        if "document_id" in case and "metrics" in case and "snapshot" in case["metrics"]:
            passed = _contract_passed_graph(case)
            kind = "graph"
        elif case.get("case_id", "").endswith("_semantic") or "methods" in (case.get("predicted") or {}):
            passed = _passed_layer2(case)
            kind = "layer2_semantic"
        else:
            passed = _contract_passed_layer1(case)
            kind = "layer1"
        lanes.append(
            {
                "artifact": rel,
                "case_id": cid,
                "kind": kind,
                "passed": passed,
                "run_metadata": {
                    "extraction_llm_model": meta.get("extraction_llm_model"),
                    "extraction_llm_base_url": meta.get("extraction_llm_base_url"),
                    "layer1_prompt_fingerprint": meta.get("layer1_prompt_fingerprint"),
                    "semantic_prompt_fingerprint": meta.get("semantic_prompt_fingerprint"),
                    "semantic_extraction_enabled": meta.get("semantic_extraction_enabled"),
                },
            }
        )
        if passed is False:
            all_ok = False
    return {"all_passed": all_ok, "lanes": lanes}


def summarize_layer1_suite(rel: str, *, root: Path) -> dict[str, Any]:
    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    meta = data.get("run_metadata", {})
    cases = data.get("cases") or []
    failed = [c for c in cases if not _contract_passed_layer1(c)]
    fb_agg = _aggregate_fallbacks(cases)
    ref_llm_fail = sum(
        1
        for c in cases
        for fr in (c.get("diagnostics") or {}).get("fallback_reasons") or []
        if fr.get("stage") == "references" and fr.get("reason") == "llm_failed"
    )
    classifications = Counter(_classify_layer1_failure(c) for c in failed)
    return {
        "artifact": rel,
        "run_metadata": {
            "extraction_llm_model": meta.get("extraction_llm_model"),
            "extraction_llm_base_url": meta.get("extraction_llm_base_url"),
            "layer1_prompt_fingerprint": meta.get("layer1_prompt_fingerprint"),
            "semantic_prompt_fingerprint": meta.get("semantic_prompt_fingerprint"),
            "semantic_extraction_enabled": meta.get("semantic_extraction_enabled"),
        },
        "summary": data.get("summary"),
        "failed_count": len(failed),
        "failed_cases": [
            {
                "case_id": c["case_id"],
                "checks": (c.get("metrics") or {}).get("contract", {}).get("checks"),
                "classification": _classify_layer1_failure(c),
            }
            for c in failed
        ],
        "source_histogram": {k: dict(v) for k, v in fb_agg.items()},
        "references_llm_failed_events": ref_llm_fail,
        "failure_class_histogram": dict(classifications),
    }


def _retrieval_case_passed(case: dict[str, Any]) -> bool:
    return bool((case.get("metrics") or {}).get("passed"))


def summarize_retrieval_suite(rel: str, *, root: Path) -> dict[str, Any]:
    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    meta = data.get("run_metadata", {})
    cases = data.get("cases") or []
    summary = data.get("summary") or {}
    failed = [c for c in cases if not _retrieval_case_passed(c)]
    return {
        "artifact": rel,
        "run_metadata": {
            "extraction_llm_model": meta.get("extraction_llm_model"),
            "extraction_llm_base_url": meta.get("extraction_llm_base_url"),
        },
        "summary": summary,
        "cases": cases,
        "failed_count": len(failed),
        "failed_cases": [{"case_id": c.get("case_id"), "metrics": c.get("metrics")} for c in failed],
        "all_passed": bool(summary.get("all_passed")),
    }


def _claims_case_passed(case: dict[str, Any]) -> bool:
    return bool((case.get("metrics") or {}).get("passed"))


def summarize_claims_suite(rel: str, *, root: Path) -> dict[str, Any]:
    return summarize_case_metrics_suite(rel, root=root)


def summarize_case_metrics_suite(rel: str, *, root: Path) -> dict[str, Any]:
    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    meta = data.get("run_metadata", {})
    cases = data.get("cases") or []
    summary = data.get("summary") or {}
    failed = [c for c in cases if not _claims_case_passed(c)]
    recalls: list[float] = []
    for case in cases:
        cr = (case.get("metrics") or {}).get("claim_recall")
        if cr is not None:
            try:
                recalls.append(float(cr))
            except (TypeError, ValueError):
                pass
    mean_claim_recall = (sum(recalls) / len(recalls)) if recalls else None
    return {
        "artifact": rel,
        "run_metadata": {
            "extraction_llm_model": meta.get("extraction_llm_model"),
            "extraction_llm_base_url": meta.get("extraction_llm_base_url"),
            "layer1_prompt_fingerprint": meta.get("layer1_prompt_fingerprint"),
            "semantic_prompt_fingerprint": meta.get("semantic_prompt_fingerprint"),
        },
        "summary": summary,
        "cases": cases,
        "failed_count": len(failed),
        "failed_cases": [{"case_id": c.get("case_id"), "metrics": c.get("metrics")} for c in failed],
        "all_passed": bool(summary.get("all_passed")),
        "mean_claim_recall": mean_claim_recall,
    }


def summarize_multihop_mini_suite(rel: str, *, root: Path) -> dict[str, Any]:
    base = summarize_case_metrics_suite(rel, root=root)
    if base.get("error") != "missing_file":
        return base
    results_dir = root / "eval" / "results"
    if not results_dir.is_dir():
        return base
    skips = sorted(results_dir.glob("multihop-skipped-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not skips:
        return base
    skip_path = skips[0]
    try:
        skip_data = _read_json(skip_path)
    except (OSError, TypeError):
        skip_data = {}
    base["last_infra_skip"] = {
        "artifact": skip_path.relative_to(root).as_posix(),
        "reason": skip_data.get("reason"),
        "detail": skip_data.get("detail"),
    }
    return base


def summarize_retrieval_judge_suite(rel: str, *, root: Path) -> dict[str, Any]:
    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    return _judge_like_suite_dict(_read_json(p), rel)


def _judge_like_suite_dict(data: dict[str, Any], rel: str) -> dict[str, Any]:
    """Shared shape for retrieval judge JSON and agent_v3_quality judge JSON."""

    meta = data.get("run_metadata") or {}
    cases = data.get("cases") or []
    summary = data.get("summary") or {}
    failed = [c for c in cases if not bool(c.get("passed"))]
    return {
        "artifact": rel,
        "run_metadata": {
            "extraction_llm_model": meta.get("extraction_llm_model"),
            "judge_prompt_fingerprint": meta.get("judge_prompt_fingerprint"),
            "judge_schema_version": meta.get("judge_schema_version"),
        },
        "summary": summary,
        "cases": cases,
        "failed_count": len(failed),
        "failed_cases": [{"case_id": c.get("case_id"), "error": c.get("error")} for c in failed],
        "all_passed": bool(summary.get("all_passed")),
        "mean_weighted_score": summary.get("mean_weighted_score"),
    }


def summarize_agent_v3_quality_judge_suite(rel: str, *, root: Path) -> dict[str, Any]:
    """Summarize ``agent-v3-quality-judge-*.json`` (pairwise baseline vs candidate)."""

    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    base = _judge_like_suite_dict(data, rel)
    meta = data.get("run_metadata") or {}
    summary = base.get("summary") if isinstance(base.get("summary"), dict) else {}
    rm = dict(base.get("run_metadata") or {})
    rm["mock_agent"] = meta.get("mock_agent")
    rm["baseline_runtime"] = meta.get("baseline_runtime")
    rm["candidate_runtime"] = meta.get("candidate_runtime")
    rm["transport"] = meta.get("transport")
    base["run_metadata"] = rm
    base["mean_weighted_score_baseline"] = summary.get("mean_weighted_score_baseline")
    base["mean_weighted_score_candidate"] = summary.get("mean_weighted_score_candidate")
    base["mean_delta"] = summary.get("mean_delta")
    base["cases_with_any_branch_non_ok"] = summary.get("cases_with_any_branch_non_ok")
    base["branch_outcome_schema"] = summary.get("branch_outcome_schema")
    return base


def summarize_layer2_suite(rel: str, *, root: Path) -> dict[str, Any]:
    p = root / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    meta = data.get("run_metadata", {})
    cases = data.get("cases") or []
    failed = [c for c in cases if not _passed_layer2(c)]
    hist = Counter(_classify_layer2_failure(c) for c in failed)
    return {
        "artifact": rel,
        "run_metadata": {
            "extraction_llm_model": meta.get("extraction_llm_model"),
            "extraction_llm_base_url": meta.get("extraction_llm_base_url"),
            "layer1_prompt_fingerprint": meta.get("layer1_prompt_fingerprint"),
            "semantic_prompt_fingerprint": meta.get("semantic_prompt_fingerprint"),
            "semantic_extraction_enabled": meta.get("semantic_extraction_enabled"),
        },
        "summary": data.get("summary"),
        "failed_count": len(failed),
        "failed_cases": [
            {
                "case_id": c["case_id"],
                "notes": c.get("metrics", {}).get("notes"),
                "extraction_notes": (c.get("predicted") or {}).get("extraction_notes"),
                "classification": _classify_layer2_failure(c),
            }
            for c in failed
        ],
        "failure_class_histogram": dict(hist),
    }


def compare_suite_failures(baseline_rel: str, current_rel: str, *, root: Path) -> dict[str, Any]:
    bp, cp = root / baseline_rel, root / current_rel
    if not bp.is_file() or not cp.is_file():
        return {"error": "missing_baseline_or_current"}
    base = _read_json(bp)
    cur = _read_json(cp)
    bf = {x["case_id"] for x in (base.get("cases") or []) if not _contract_passed_layer1(x)}
    cf = {x["case_id"] for x in (cur.get("cases") or []) if not _contract_passed_layer1(x)}
    return {
        "baseline_failed": sorted(bf),
        "current_failed": sorted(cf),
        "resolved": sorted(bf - cf),
        "new_regressions": sorted(cf - bf),
    }


def compare_layer2_failures(baseline_rel: str, current_rel: str, *, root: Path) -> dict[str, Any]:
    bp, cp = root / baseline_rel, root / current_rel
    if not bp.is_file() or not cp.is_file():
        return {"error": "missing_baseline_or_current"}
    base = _read_json(bp)
    cur = _read_json(cp)
    bf = {x["case_id"] for x in (base.get("cases") or []) if not _passed_layer2(x)}
    cf = {x["case_id"] for x in (cur.get("cases") or []) if not _passed_layer2(x)}
    return {
        "baseline_failed": sorted(bf),
        "current_failed": sorted(cf),
        "resolved": sorted(bf - cf),
        "new_regressions": sorted(cf - bf),
    }


def supplementary_retests(*, root: Path, supplementary_paths: tuple[str, ...]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in supplementary_paths:
        p = root / rel
        if not p.is_file():
            continue
        data = _read_json(p)
        case = data.get("case", data)
        passed = _contract_passed_layer1(case) if "metrics" in case else None
        out.append({"artifact": rel, "case_id": case.get("case_id"), "passed": passed})
    return out


def strip_suite_cases_from_payload(payload: dict[str, Any]) -> None:
    for fam_key in (
        "retrieval_family",
        "claims_family",
        "claims_production_family",
        "references_resolution_family",
        "concept_topic_family",
        "agent_tools_family",
        "agent_v3_quality_family",
        "chat_agent_family",
        "contradictions_family",
    ):
        fam = payload.get(fam_key)
        if not isinstance(fam, dict):
            continue
        for _member_id, block in fam.items():
            if isinstance(block, dict):
                block.pop("cases", None)
                block.pop("_workspace_scoped_delegated_to_live", None)
                block.pop("_hybrid_ablation_delegated_to_live", None)
                block.pop("last_infra_skip", None)


def finalize_family_trust(
    family_key: str,
    family: dict[str, Any],
    *,
    gold_root: Path,
) -> None:
    if family_key == "retrieval_family":
        live = family.get("workspace_scoped_live")
        ws = family.get("workspace_scoped")
        if isinstance(live, dict) and isinstance(ws, dict) and live.get("error") != "missing_file":
            cases_live = _cases_from_block(live)
            if detect_runtime_mode("workspace_scoped_live", live, cases_live) not in PHANTOM_RUNTIME_MODES:
                ws["_workspace_scoped_delegated_to_live"] = True

        hab_live = family.get("hybrid_ablation_live")
        hab = family.get("hybrid_ablation")
        if isinstance(hab_live, dict) and isinstance(hab, dict) and hab_live.get("error") != "missing_file":
            cases_h = _cases_from_block(hab_live)
            if detect_runtime_mode("hybrid_ablation_live", hab_live, cases_h) not in PHANTOM_RUNTIME_MODES:
                summ = hab_live.get("summary") if isinstance(hab_live.get("summary"), dict) else {}
                if bool(summ.get("all_passed")):
                    hab["_hybrid_ablation_delegated_to_live"] = True

    for member_id, block in list(family.items()):
        if member_id in {"role", "trust_aggregate"} or not isinstance(block, dict):
            continue
        block["trust_signal"] = build_trust_signal_dict(family_key, member_id, block, gold_root)
    family["trust_aggregate"] = summarize_family_trust(family, family_key=family_key)
