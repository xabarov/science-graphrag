#!/usr/bin/env python3
"""
Aggregate benchmark JSON reports into a single machine-readable + markdown summary.

Usage (repo root):
  .venv/bin/python scripts/aggregate_benchmark_metrics.py
  .venv/bin/python scripts/aggregate_benchmark_metrics.py \\
    --out-json eval/results/benchmark-metrics-summary.json \\
    --out-md eval/results/benchmark-metrics-summary.md

Authoritative inputs (defaults) match docs/runbooks/benchmark-decision-gate.md.

Optional retrieval + hybrid/multihop ablation + claims + claims production pilot +
references_resolution + concept_topic graph JSON lanes are listed in
``benchmark-decision-gate.md`` §8 and summarized under ``retrieval_family`` /
``claims_family`` / ``claims_production_family`` / ``references_resolution_family`` /
``concept_topic_family`` / ``contradictions_family`` when the default artifact paths exist.
**Claims paraphrase pilot + holdout** (BT6) are the **core** ``decision_gate`` claims lane
when both artifacts exist; the legacy **claims production** pilot remains summarized under
``claims_production_family`` for observability (Wave 1 honest closure).
Retrieval ``workspace_scoped`` + ``judge_pilot`` blocks remain **advisory** (Wave P).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from science_graphrag.benchmarks.decision_gate import evaluate_decision_gate
from science_graphrag.benchmarks.trust_signal import (
    PHANTOM_RUNTIME_MODES,
    _cases_from_block,
    build_trust_signal_dict,
    compute_gate_trust_criteria,
    detect_runtime_mode,
    summarize_family_trust,
    trust_baseline_payload,
)

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from benchmark_aggregator.paths import (  # noqa: E402
    DEFAULT_AGENT_TOOLS_JUDGE,
    DEFAULT_AGENT_TOOLS_MINI,
    DEFAULT_BASELINE_LAYER1,
    DEFAULT_BASELINE_LAYER2,
    DEFAULT_CHAT_AGENT_CONTRACT,
    DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
    DEFAULT_CLAIMS_MERGE_CONTRACT,
    DEFAULT_CLAIMS_MINI_SUITE,
    DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
    DEFAULT_CLAIMS_PARAPHRASE_PILOT,
    DEFAULT_CLAIMS_PILOT_SUITE,
    DEFAULT_CLAIMS_PRODUCTION_PILOT,
    DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
    DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
    DEFAULT_LAYER1_NIGHTLY,
    DEFAULT_LAYER2_NIGHTLY,
    DEFAULT_REFERENCE,
    DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
    DEFAULT_REFERENCES_RESOLUTION_GRAPH,
    DEFAULT_REFERENCES_RESOLUTION_MINI,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION,
    DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
    DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
    DEFAULT_RETRIEVAL_JUDGE_PILOT,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
    DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI,
    DEFAULT_RETRIEVAL_MERGE_SAFE,
    DEFAULT_RETRIEVAL_MULTIHOP_MINI,
    DEFAULT_RETRIEVAL_STRICT_PILOT,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
    DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
    GOLD_ROOT,
    ROOT,
    SUPPLEMENTARY_RETESTS,
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
    """Count metadata/authorships/references sources across cases."""

    keys = ("metadata_source", "authorships_source", "references_source")
    out: dict[str, Counter[str]] = {k: Counter() for k in keys}
    for case in cases:
        fb = _fallback_buckets_layer1(case)
        for k in keys:
            v = fb.get(k) or "unknown"
            out[k][v] += 1
    return out


def _classify_layer1_failure(case: dict[str, Any]) -> str:
    """Heuristic: benchmark (gold) vs architecture (runtime)."""

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


def _summarize_reference(paths: tuple[str, ...]) -> dict[str, Any]:
    lanes: list[dict[str, Any]] = []
    all_ok = True
    for rel in paths:
        p = ROOT / rel
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
        elif case.get("case_id", "").endswith("_semantic") or "methods" in (
            case.get("predicted") or {}
        ):
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
            },
        )
        if passed is False:
            all_ok = False
    return {"all_passed": all_ok, "lanes": lanes}


def _summarize_layer1_suite(rel: str) -> dict[str, Any]:
    p = ROOT / rel
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


def _summarize_retrieval_suite(rel: str) -> dict[str, Any]:
    """Summarize retrieval suite JSON (merge-safe or strict_pilot tier)."""

    p = ROOT / rel
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
        "failed_cases": [
            {"case_id": c.get("case_id"), "metrics": c.get("metrics")} for c in failed
        ],
        "all_passed": bool(summary.get("all_passed")),
    }


def _claims_case_passed(case: dict[str, Any]) -> bool:
    return bool((case.get("metrics") or {}).get("passed"))


def _summarize_claims_suite(rel: str) -> dict[str, Any]:
    """Backward-compatible name for claims suite summaries."""

    return _summarize_case_metrics_suite(rel)


def _summarize_case_metrics_suite(rel: str) -> dict[str, Any]:
    """Summarize a suite JSON with ``cases[]`` + ``summary`` (claims / references_resolution)."""

    p = ROOT / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
    meta = data.get("run_metadata", {})
    cases = data.get("cases") or []
    summary = data.get("summary") or {}
    failed = [c for c in cases if not _claims_case_passed(c)]
    recalls: list[float] = []
    for c in cases:
        cr = (c.get("metrics") or {}).get("claim_recall")
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
        "failed_cases": [
            {"case_id": c.get("case_id"), "metrics": c.get("metrics")} for c in failed
        ],
        "all_passed": bool(summary.get("all_passed")),
        "mean_claim_recall": mean_claim_recall,
    }


def _summarize_multihop_mini_suite(rel: str) -> dict[str, Any]:
    """Summarize multihop artifact; attach ``last_infra_skip`` when main JSON is absent (BT3)."""

    base = _summarize_case_metrics_suite(rel)
    if base.get("error") != "missing_file":
        return base
    results_dir = ROOT / "eval" / "results"
    if not results_dir.is_dir():
        return base
    skips = sorted(
        results_dir.glob("multihop-skipped-*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not skips:
        return base
    skip_path = skips[0]
    try:
        skip_data = _read_json(skip_path)
    except (OSError, TypeError):
        skip_data = {}
    base["last_infra_skip"] = {
        "artifact": skip_path.relative_to(ROOT).as_posix(),
        "reason": skip_data.get("reason"),
        "detail": skip_data.get("detail"),
    }
    return base


def _summarize_retrieval_judge_suite(rel: str) -> dict[str, Any]:
    """Summarize ``eval/retrieval/judge.py`` output (Wave P advisory)."""

    p = ROOT / rel
    if not p.is_file():
        return {"error": "missing_file", "artifact": rel}
    data = _read_json(p)
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


def _summarize_layer2_suite(rel: str) -> dict[str, Any]:
    p = ROOT / rel
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


def _compare_suite_failures(baseline_rel: str, current_rel: str) -> dict[str, Any]:
    bp, cp = ROOT / baseline_rel, ROOT / current_rel
    if not bp.is_file() or not cp.is_file():
        return {"error": "missing_baseline_or_current"}
    b = _read_json(bp)
    c = _read_json(cp)
    bf = {x["case_id"] for x in (b.get("cases") or []) if not _contract_passed_layer1(x)}
    cf = {x["case_id"] for x in (c.get("cases") or []) if not _contract_passed_layer1(x)}
    return {
        "baseline_failed": sorted(bf),
        "current_failed": sorted(cf),
        "resolved": sorted(bf - cf),
        "new_regressions": sorted(cf - bf),
    }


def _compare_layer2_failures(baseline_rel: str, current_rel: str) -> dict[str, Any]:
    bp, cp = ROOT / baseline_rel, ROOT / current_rel
    if not bp.is_file() or not cp.is_file():
        return {"error": "missing_baseline_or_current"}
    b = _read_json(bp)
    c = _read_json(cp)
    bf = {x["case_id"] for x in (b.get("cases") or []) if not _passed_layer2(x)}
    cf = {x["case_id"] for x in (c.get("cases") or []) if not _passed_layer2(x)}
    return {
        "baseline_failed": sorted(bf),
        "current_failed": sorted(cf),
        "resolved": sorted(bf - cf),
        "new_regressions": sorted(cf - bf),
    }


def _supplementary_retests() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rel in SUPPLEMENTARY_RETESTS:
        p = ROOT / rel
        if not p.is_file():
            continue
        data = _read_json(p)
        case = data.get("case", data)
        passed = _contract_passed_layer1(case) if "metrics" in case else None
        out.append({"artifact": rel, "case_id": case.get("case_id"), "passed": passed})
    return out


def _strip_suite_cases_from_payload(payload: dict[str, Any]) -> None:
    """Remove embedded ``cases`` lists after trust_signal is computed (keep summary small)."""

    for fam_key in (
        "retrieval_family",
        "claims_family",
        "claims_production_family",
        "references_resolution_family",
        "concept_topic_family",
        "agent_tools_family",
        "chat_agent_family",
        "contradictions_family",
    ):
        fam = payload.get(fam_key)
        if not isinstance(fam, dict):
            continue
        for _mid, block in fam.items():
            if isinstance(block, dict):
                block.pop("cases", None)
                block.pop("_workspace_scoped_delegated_to_live", None)
                block.pop("_hybrid_ablation_delegated_to_live", None)
                block.pop("last_infra_skip", None)


def _finalize_family_trust(family_key: str, family: dict[str, Any]) -> None:
    """Attach ``trust_signal`` to each suite block and ``trust_aggregate`` on the family."""

    if family_key == "retrieval_family":
        live = family.get("workspace_scoped_live")
        ws = family.get("workspace_scoped")
        if isinstance(live, dict) and isinstance(ws, dict) and live.get("error") != "missing_file":
            cases_live = _cases_from_block(live)
            if (
                detect_runtime_mode("workspace_scoped_live", live, cases_live)
                not in PHANTOM_RUNTIME_MODES
            ):
                ws["_workspace_scoped_delegated_to_live"] = True

        hab_live = family.get("hybrid_ablation_live")
        hab = family.get("hybrid_ablation")
        if (
            isinstance(hab_live, dict)
            and isinstance(hab, dict)
            and hab_live.get("error") != "missing_file"
        ):
            cases_h = _cases_from_block(hab_live)
            if (
                detect_runtime_mode("hybrid_ablation_live", hab_live, cases_h)
                not in PHANTOM_RUNTIME_MODES
            ):
                summ = hab_live.get("summary") if isinstance(hab_live.get("summary"), dict) else {}
                if bool(summ.get("all_passed")):
                    hab["_hybrid_ablation_delegated_to_live"] = True

    for member_id, block in list(family.items()):
        if member_id in {"role", "trust_aggregate"} or not isinstance(block, dict):
            continue
        block["trust_signal"] = build_trust_signal_dict(family_key, member_id, block, GOLD_ROOT)
    family["trust_aggregate"] = summarize_family_trust(family, family_key=family_key)


def _md_decision_gate_section(dg: dict[str, Any]) -> list[str]:
    lines = ["## Decision gate", ""]
    lines.append(f"- **decision**: `{dg.get('decision')}`")
    lines.append(f"- **reason**: {dg.get('reason')}")
    crit = dg.get("criteria") or {}
    lines.append(f"- **reference_all_passed**: {crit.get('reference_all_passed')}")
    lines.append(f"- **layer1 nightly failed**: {crit.get('layer1_nightly_failed_count')}")
    lines.append(f"- **layer2 nightly failed**: {crit.get('layer2_nightly_failed_count')}")
    lines.append(
        f"- **claims_core_uses_paraphrase_pilot_holdout**: "
        f"{crit.get('claims_core_uses_paraphrase_pilot_holdout')}"
    )
    lines.append(
        f"- **claims_paraphrase_pilot_artifact_missing**: "
        f"{crit.get('claims_paraphrase_pilot_artifact_missing')}"
    )
    lines.append(
        f"- **claims_paraphrase_holdout_artifact_missing**: "
        f"{crit.get('claims_paraphrase_holdout_artifact_missing')}"
    )
    lines.append(
        f"- **claims_paraphrase_pilot_all_passed**: "
        f"{crit.get('claims_paraphrase_pilot_all_passed')}"
    )
    lines.append(
        f"- **claims_paraphrase_holdout_all_passed**: "
        f"{crit.get('claims_paraphrase_holdout_all_passed')}"
    )
    lines.append(
        f"- **claims_paraphrase_pilot_meets_bt6_core_bar**: "
        f"{crit.get('claims_paraphrase_pilot_meets_bt6_core_bar')}"
    )
    lines.append(
        f"- **claims_paraphrase_holdout_meets_bt6_core_bar**: "
        f"{crit.get('claims_paraphrase_holdout_meets_bt6_core_bar')}"
    )
    lines.append(
        f"- **claims_production_artifact_missing**: {crit.get('claims_production_artifact_missing')}"
    )
    lines.append(f"- **claims_production_all_passed**: {crit.get('claims_production_all_passed')}")
    lines.append(
        f"- **claims_production_mean_claim_recall**: "
        f"{crit.get('claims_production_mean_claim_recall')}"
    )
    lines.append(f"- **advisory_phantom_count**: {crit.get('advisory_phantom_count')}")
    lines.append(f"- **advisory_phantom_families**: {crit.get('advisory_phantom_families')}")
    lines.append(
        f"- **hard_block_individual_failures**: {crit.get('hard_block_individual_failures')}"
    )
    lines.append("")
    return lines


def _md_reference_section(ref: dict[str, Any]) -> list[str]:
    lines = ["## Reference lane", ""]
    for lane in ref.get("lanes") or []:
        if "error" in lane:
            lines.append(f"- {lane.get('artifact')}: **missing**")
            continue
        lines.append(
            f"- `{lane.get('case_id')}` ({lane.get('kind')}): **passed={lane.get('passed')}** "
            f"— `{lane.get('artifact')}`",
        )
    lines.append("")
    return lines


def _md_layer1_section(l1: dict[str, Any]) -> list[str]:
    lines = ["## Layer-1 nightly_heavy", ""]
    if l1.get("error"):
        lines.append(f"Error: {l1.get('error')} ({l1.get('artifact')})")
    else:
        lines.append(f"- artifact: `{l1.get('artifact')}`")
        lines.append(f"- failed_count: **{l1.get('failed_count')}**")
        if l1.get("failed_cases"):
            lines.append("- failed cases:")
            for fc in l1["failed_cases"]:
                lines.append(
                    f"  - `{fc['case_id']}` ({fc.get('classification')}): {fc.get('checks')}",
                )
        lines.append(
            f"- references_llm_failed_events (count): {l1.get('references_llm_failed_events')}"
        )
    lines.append("")
    return lines


def _md_layer2_section(l2: dict[str, Any]) -> list[str]:
    lines = ["## Layer-2 nightly_semantic", ""]
    if l2.get("error"):
        lines.append(f"Error: {l2.get('error')} ({l2.get('artifact')})")
    else:
        lines.append(f"- artifact: `{l2.get('artifact')}`")
        lines.append(f"- failed_count: **{l2.get('failed_count')}**")
        for fc in l2.get("failed_cases") or []:
            lines.append(
                f"  - `{fc['case_id']}` ({fc.get('classification')}): {fc.get('extraction_notes')}",
            )
    lines.append("")
    return lines


def _md_supplementary_section(sup: list[dict[str, Any]]) -> list[str]:
    if not sup:
        return []
    lines = ["## Supplementary single-case retests (if present)", ""]
    for s in sup:
        lines.append(f"- `{s.get('case_id')}`: passed={s.get('passed')} — `{s.get('artifact')}`")
    lines.append("")
    return lines


def _md_retrieval_family_section(rf: dict[str, Any]) -> list[str]:
    lines = [
        "## Retrieval family (advisory)",
        "",
        "Retrieval benchmarks are **not** part of the primary decision gate; they track "
        "`POST /v1/query` grounding signals. See `docs/runbooks/benchmark-decision-gate.md` §8.",
        "",
    ]
    role = (rf.get("role") or "advisory") if isinstance(rf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")

    def _one(label: str, block: dict[str, Any]) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
            for fc in block.get("failed_cases") or []:
                lines.append(f"  - `{fc.get('case_id')}`: {fc.get('metrics')}")
        lines.append("")

    _one("merge_safe_contract (mock suite)", rf.get("merge_safe_contract_mock") or {})
    _one("strict_pilot (mock suite)", rf.get("strict_pilot_mock") or {})
    _one("live_corpus_mini (live suite)", rf.get("live_corpus_mini") or {})
    _one("workspace_scoped (live suite, Wave P)", rf.get("workspace_scoped") or {})
    _one("workspace_scoped_live (BT2 live stack)", rf.get("workspace_scoped_live") or {})
    _one("judge_pilot (LLM rubric advisory, Wave P)", rf.get("judge_pilot") or {})
    _one("judge_holdout (BT5 weekly holdout)", rf.get("judge_holdout") or {})
    _one("live_corpus_holdout (BT5 holdout anti-overfit)", rf.get("live_corpus_holdout") or {})
    _one("hybrid_ablation (contract harness, Wave Q)", rf.get("hybrid_ablation") or {})
    _one("hybrid_ablation_live (BT4 real runner, Wave R)", rf.get("hybrid_ablation_live") or {})
    _one("multihop_mini (2-hop graph precision, Wave Q)", rf.get("multihop_mini") or {})
    lines.append(
        "Promotion roadmap for workspace-scoped + judge → core retrieval gate: "
        "`docs/runbooks/benchmark-decision-gate.md` §8.3.",
    )
    lines.append("")
    return lines


def _md_claims_family_section(cf: dict[str, Any]) -> list[str]:
    lines = [
        "## Claims family (advisory)",
        "",
        "Claims benchmarks are **not** part of the primary decision gate. See "
        "`docs/benchmarks/ontology-claims-benchmark-v1.md` and "
        "`docs/runbooks/benchmark-program-status.md`.",
        "",
    ]
    role = (cf.get("role") or "advisory") if isinstance(cf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")

    def _one(label: str, block: dict[str, Any]) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
            for fc in block.get("failed_cases") or []:
                lines.append(f"  - `{fc.get('case_id')}`: {fc.get('metrics')}")
        lines.append("")

    _one("claims_merge_contract", cf.get("claims_merge_contract") or {})
    _one("claims_mini", cf.get("claims_mini") or {})
    _one("claims_corpus_v2_mini", cf.get("claims_corpus_v2_mini") or {})
    _one("claims_pilot", cf.get("claims_pilot") or {})
    _one("claims_paraphrase_pilot (BT6)", cf.get("claims_paraphrase_pilot") or {})
    _one("claims_paraphrase_holdout (BT6)", cf.get("claims_paraphrase_holdout") or {})
    return lines


def _md_claims_production_family_section(pf: dict[str, Any]) -> list[str]:
    lines = [
        "## Claims production lane (legacy / advisory; Wave O pilot)",
        "",
        (
            "LLM extractor via ``science-graphrag-claims-benchmark --suite --tier claims_pilot "
            "--extractor production``; artifact "
            f"default: `{DEFAULT_CLAIMS_PRODUCTION_PILOT}`. "
        ),
        (
            "``decision_gate`` **core** claims lane uses ``claims_paraphrase_{pilot,holdout}`` "
            "when both artifacts exist (BT6). This block remains for drift monitoring on the "
            "older trivial-gold pilot."
        ),
        "",
    ]
    role = (pf.get("role") or "core") if isinstance(pf, dict) else "core"
    lines.append(f"- **role**: `{role}`")
    lines.append("")

    def _one(label: str, block: dict[str, Any]) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
            for fc in block.get("failed_cases") or []:
                lines.append(f"  - `{fc.get('case_id')}`: {fc.get('metrics')}")
        lines.append("")

    _one("claims_pilot (production extractor)", pf.get("claims_pilot_production") or {})
    return lines


def _md_references_resolution_family_section(rf: dict[str, Any]) -> list[str]:
    lines = [
        "## References resolution family (advisory)",
        "",
        "Structural scoring harness for bibliography resolution keys; **not** a substitute for "
        "Neo4j-backed canonicalization yet. See "
        "`docs/specs/benchmark-family-references-resolution-v1.md`.",
        "",
    ]
    role = (rf.get("role") or "advisory") if isinstance(rf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")

    def _one(label: str, block: dict[str, Any]) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
            for fc in block.get("failed_cases") or []:
                lines.append(f"  - `{fc.get('case_id')}`: {fc.get('metrics')}")
        lines.append("")

    _one("refs_merge_contract", rf.get("refs_merge_contract") or {})
    _one("refs_mini (synthetic harness)", rf.get("refs_mini") or {})
    _one("refs_graph (Neo4j resolver lane, Wave M)", rf.get("refs_graph") or {})
    return lines


def _md_concept_topic_family_section(cf: dict[str, Any]) -> list[str]:
    lines = [
        "## Concept / ResearchTopic family (advisory)",
        "",
        "Ontology v1.5 concept and topic extraction benchmarks are **not** part of the primary "
        "decision gate. See [ADR 013](../../docs/adr/013-concept-research-topic-ontology-v1-5.md) and "
        "[semantic-concept-topic-v1.md](../../docs/specs/extraction/semantic-concept-topic-v1.md).",
        "",
    ]
    role = (cf.get("role") or "advisory") if isinstance(cf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")

    def _one(label: str, block: dict[str, Any]) -> None:
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
            for fc in block.get("failed_cases") or []:
                lines.append(f"  - `{fc.get('case_id')}`: {fc.get('metrics')}")
        lines.append("")

    _one("concept_topic_mini (harness)", cf.get("concept_topic_mini") or {})
    return lines


def _md_baseline_deltas_section(deltas: dict[str, Any]) -> list[str]:
    return [
        "## Baseline deltas (vs stored baseline JSON)",
        "",
        "```json",
        json.dumps(deltas, indent=2, ensure_ascii=False),
        "```",
        "",
    ]


def _md_contradictions_family_section(cf: dict[str, Any]) -> list[str]:
    lines = [
        "## Contradictions family (advisory)",
        "",
        "Wave 9 / BT12 — verify ``:CONTRADICTS`` edges for ``contradictions_v1`` gold pairs.",
        "",
    ]
    role = (cf.get("role") or "advisory") if isinstance(cf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")
    block = (cf.get("contradictions_v1_mini") or {}) if isinstance(cf, dict) else {}
    lines.append("### contradictions_v1_mini")
    lines.append("")
    if block.get("error"):
        lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
    else:
        lines.append(f"- artifact: `{block.get('artifact')}`")
        lines.append(f"- all_passed: **{block.get('all_passed')}**")
        lines.append(f"- failed_count: **{block.get('failed_count')}**")
    lines.append("")
    return lines


def _md_chat_agent_family_section(cf: dict[str, Any]) -> list[str]:
    lines = [
        "## Chat agent family (advisory)",
        "",
        "Contract checks for `POST /v2/agent/query` (see `python -m eval.chat_agent`).",
        "",
    ]
    role = (cf.get("role") or "advisory") if isinstance(cf, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")
    block = (cf.get("chat_agent_contract") or {}) if isinstance(cf, dict) else {}
    lines.append("### chat_agent_contract")
    lines.append("")
    if block.get("error"):
        lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
    else:
        lines.append(f"- artifact: `{block.get('artifact')}`")
        lines.append(f"- all_passed: **{block.get('all_passed')}**")
        lines.append(f"- failed_count: **{block.get('failed_count')}**")
    lines.append("")
    return lines


def _md_agent_tools_family_section(af: dict[str, Any]) -> list[str]:
    lines = [
        "## Agent tools family (advisory)",
        "",
        "Wave R benchmark family for `POST /v1/agent/query`.",
        "",
    ]
    role = (af.get("role") or "advisory") if isinstance(af, dict) else "advisory"
    lines.append(f"- **role**: `{role}`")
    lines.append("")
    for label, key in (
        ("agent_tools_mini", "agent_tools_mini"),
        ("agent_tools_judge", "agent_tools_judge"),
    ):
        block = af.get(key) or {}
        lines.append(f"### {label}")
        lines.append("")
        if block.get("error"):
            lines.append(f"- **status**: missing artifact `{block.get('artifact')}`")
        else:
            lines.append(f"- artifact: `{block.get('artifact')}`")
            lines.append(f"- all_passed: **{block.get('all_passed')}**")
            lines.append(f"- failed_count: **{block.get('failed_count')}**")
        lines.append("")
    return lines


def _render_markdown(payload: dict[str, Any]) -> str:
    """Human-readable markdown mirror of benchmark-metrics-summary.json."""

    header = [
        "# Benchmark metrics summary (generated)",
        "",
        "Generated by `scripts/aggregate_benchmark_metrics.py`.",
        "",
    ]
    parts = [
        *header,
        *_md_decision_gate_section(payload.get("decision_gate") or {}),
        *_md_reference_section(payload.get("reference") or {}),
        *_md_layer1_section(payload.get("layer1_nightly") or {}),
        *_md_layer2_section(payload.get("layer2_nightly") or {}),
        *_md_supplementary_section(payload.get("supplementary_retests") or []),
        *_md_retrieval_family_section(payload.get("retrieval_family") or {}),
        *_md_claims_family_section(payload.get("claims_family") or {}),
        *_md_claims_production_family_section(payload.get("claims_production_family") or {}),
        *_md_references_resolution_family_section(
            payload.get("references_resolution_family") or {}
        ),
        *_md_concept_topic_family_section(payload.get("concept_topic_family") or {}),
        *_md_agent_tools_family_section(payload.get("agent_tools_family") or {}),
        *_md_chat_agent_family_section(payload.get("chat_agent_family") or {}),
        *_md_contradictions_family_section(payload.get("contradictions_family") or {}),
        *_md_baseline_deltas_section(payload.get("deltas") or {}),
    ]
    return "\n".join(parts)


def main() -> int:
    """CLI: write JSON + Markdown summaries under eval/results/."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-json",
        type=Path,
        default=ROOT / "eval/results/benchmark-metrics-summary.json",
    )
    parser.add_argument(
        "--out-md",
        type=Path,
        default=ROOT / "eval/results/benchmark-metrics-summary.md",
    )
    parser.add_argument(
        "--refs-graph-json",
        type=str,
        default=DEFAULT_REFERENCES_RESOLUTION_GRAPH,
        help=(
            "Optional references_resolution suite JSON from "
            "`science-graphrag-references-resolution-benchmark --resolver graph` (advisory)."
        ),
    )
    parser.add_argument(
        "--concept-topic-json",
        type=str,
        default=DEFAULT_CONCEPT_TOPIC_MINI_SUITE,
        help=(
            "Optional concept/topic suite JSON from "
            "`science-graphrag-concept-topic-benchmark --suite --tier concept_topic_mini` (advisory)."
        ),
    )
    parser.add_argument(
        "--claims-production-json",
        type=str,
        default=DEFAULT_CLAIMS_PRODUCTION_PILOT,
        help=(
            "Optional claims pilot JSON from "
            "`science-graphrag-claims-benchmark --suite --tier claims_pilot --extractor production` "
            "(core gate, Wave O; see benchmark-decision-gate.md §8.1)."
        ),
    )
    parser.add_argument(
        "--claims-paraphrase-pilot-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_PILOT,
        help=(
            "Optional BT6 paraphrase pilot JSON from "
            "`science-graphrag-claims-paraphrase-benchmark --suite --tier claims_pilot_v2` "
            "(use `--extractor oracle` for wiring smoke without LLM keys; advisory)."
        ),
    )
    parser.add_argument(
        "--claims-paraphrase-holdout-json",
        type=str,
        default=DEFAULT_CLAIMS_PARAPHRASE_HOLDOUT,
        help=(
            "Optional BT6 paraphrase holdout JSON from "
            "`science-graphrag-claims-paraphrase-benchmark --suite --tier claims_holdout_v1` (advisory)."
        ),
    )
    parser.add_argument(
        "--retrieval-workspace-scoped-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED,
        help=(
            "Optional retrieval workspace_scoped suite JSON (advisory, Wave P). "
            "Default path is committed when live stack is green."
        ),
    )
    parser.add_argument(
        "--retrieval-judge-json",
        type=str,
        default=DEFAULT_RETRIEVAL_JUDGE_PILOT,
        help="Optional retrieval LLM-judge pilot JSON from eval/retrieval/judge.py (advisory, Wave P).",
    )
    parser.add_argument(
        "--retrieval-workspace-scoped-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_WORKSPACE_SCOPED_LIVE,
        help=(
            "Optional BT2 live workspace-scoped suite JSON "
            "(``science-graphrag-retrieval-benchmark …/workspace_scoped_live --tier workspace_scoped_live_pilot``)."
        ),
    )
    parser.add_argument(
        "--retrieval-judge-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_JUDGE_HOLDOUT,
        help="Optional BT5 judge holdout JSON (``eval/retrieval/judge.py --case-tier judge_holdout_v1``).",
    )
    parser.add_argument(
        "--hybrid-ablation-json",
        type=str,
        default=DEFAULT_RETRIEVAL_HYBRID_ABLATION,
        help=(
            "Optional hybrid retrieval ablation suite JSON from "
            "`science-graphrag-retrieval-hybrid-ablation --suite` (advisory, Wave Q)."
        ),
    )
    parser.add_argument(
        "--hybrid-ablation-live-json",
        type=str,
        default=DEFAULT_RETRIEVAL_HYBRID_ABLATION_LIVE,
        help=(
            "Optional BT4 live hybrid ablation JSON from "
            "`science-graphrag-retrieval-hybrid-ablation --suite --tier hybrid_ablation_v2_pilot` "
            "(advisory, Wave R)."
        ),
    )
    parser.add_argument(
        "--retrieval-live-corpus-holdout-json",
        type=str,
        default=DEFAULT_RETRIEVAL_LIVE_CORPUS_HOLDOUT,
        help="Optional BT5 live_corpus_holdout suite JSON (advisory, weekly anti-overfit check).",
    )
    parser.add_argument(
        "--retrieval-multihop-json",
        type=str,
        default=DEFAULT_RETRIEVAL_MULTIHOP_MINI,
        help=(
            "Optional retrieval multihop mini JSON from "
            "`science-graphrag-retrieval-multihop-benchmark --suite` (advisory, Wave Q)."
        ),
    )
    parser.add_argument(
        "--agent-tools-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_MINI,
        help="Optional Wave R suite JSON from science-graphrag-agent-benchmark.",
    )
    parser.add_argument(
        "--agent-judge-json",
        type=str,
        default=DEFAULT_AGENT_TOOLS_JUDGE,
        help="Optional Wave R judge JSON from science-graphrag-agent-judge-benchmark.",
    )
    parser.add_argument(
        "--chat-agent-contract-json",
        type=str,
        default=DEFAULT_CHAT_AGENT_CONTRACT,
        help=(
            "Optional advisory JSON from chat contract runner invariants "
            "(``python -m eval.chat_agent`` + committed ``current-chat-agent-contract.json``)."
        ),
    )
    parser.add_argument(
        "--contradictions-v1-json",
        type=str,
        default=DEFAULT_CONTRADICTIONS_V1_MINI_SUITE,
        help=(
            "Optional BT12 suite JSON from "
            "`python -m eval.contradictions.runner tests/fixtures/benchmarks/contradictions_v1 "
            "--suite [--materialize]` (advisory)."
        ),
    )
    parser.add_argument(
        "--write-trust-baseline",
        type=Path,
        default=None,
        help=(
            "Also write a frozen trust snapshot (decision_gate + trust aggregates) to this path, "
            "e.g. eval/results/benchmark-trust-baseline.json"
        ),
    )
    args = parser.parse_args()

    reference = _summarize_reference(DEFAULT_REFERENCE)
    layer1 = _summarize_layer1_suite(DEFAULT_LAYER1_NIGHTLY)
    layer2 = _summarize_layer2_suite(DEFAULT_LAYER2_NIGHTLY)
    claims_prod = _summarize_case_metrics_suite(args.claims_production_json)
    claims_paraphrase_pilot = _summarize_case_metrics_suite(args.claims_paraphrase_pilot_json)
    claims_paraphrase_holdout = _summarize_case_metrics_suite(args.claims_paraphrase_holdout_json)

    deltas = {
        "layer1_nightly_vs_baseline": _compare_suite_failures(
            DEFAULT_BASELINE_LAYER1,
            DEFAULT_LAYER1_NIGHTLY,
        ),
        "layer2_nightly_vs_baseline": _compare_layer2_failures(
            DEFAULT_BASELINE_LAYER2,
            DEFAULT_LAYER2_NIGHTLY,
        ),
    }

    payload: dict[str, Any] = {
        "authoritative_artifacts": {
            "reference": list(DEFAULT_REFERENCE),
            "layer1_nightly": DEFAULT_LAYER1_NIGHTLY,
            "layer2_nightly": DEFAULT_LAYER2_NIGHTLY,
            "baseline_layer1": DEFAULT_BASELINE_LAYER1,
            "baseline_layer2": DEFAULT_BASELINE_LAYER2,
            "retrieval_merge_safe_mock": DEFAULT_RETRIEVAL_MERGE_SAFE,
            "retrieval_strict_pilot_mock": DEFAULT_RETRIEVAL_STRICT_PILOT,
            "retrieval_live_corpus_mini": DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI,
            "retrieval_workspace_scoped": args.retrieval_workspace_scoped_json,
            "retrieval_workspace_scoped_live": args.retrieval_workspace_scoped_live_json,
            "retrieval_judge_pilot": args.retrieval_judge_json,
            "retrieval_judge_holdout": args.retrieval_judge_holdout_json,
            "retrieval_hybrid_ablation": args.hybrid_ablation_json,
            "retrieval_hybrid_ablation_live": args.hybrid_ablation_live_json,
            "retrieval_live_corpus_holdout": args.retrieval_live_corpus_holdout_json,
            "retrieval_multihop_mini": args.retrieval_multihop_json,
            "claims_merge_contract": DEFAULT_CLAIMS_MERGE_CONTRACT,
            "claims_mini_suite": DEFAULT_CLAIMS_MINI_SUITE,
            "claims_corpus_v2_mini_suite": DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE,
            "claims_pilot_suite": DEFAULT_CLAIMS_PILOT_SUITE,
            "claims_production_pilot_suite": args.claims_production_json,
            "claims_paraphrase_pilot_suite": args.claims_paraphrase_pilot_json,
            "claims_paraphrase_holdout_suite": args.claims_paraphrase_holdout_json,
            "references_resolution_contract": DEFAULT_REFERENCES_RESOLUTION_CONTRACT,
            "references_resolution_mini": DEFAULT_REFERENCES_RESOLUTION_MINI,
            "references_resolution_graph": args.refs_graph_json,
            "concept_topic_mini_suite": args.concept_topic_json,
            "agent_tools_mini_suite": args.agent_tools_json,
            "agent_tools_judge_suite": args.agent_judge_json,
            "chat_agent_contract_suite": args.chat_agent_contract_json,
            "contradictions_v1_mini_suite": args.contradictions_v1_json,
        },
        "reference": reference,
        "layer1_nightly": layer1,
        "layer2_nightly": layer2,
        "deltas": deltas,
        "supplementary_retests": _supplementary_retests(),
        "retrieval_family": {
            "role": "advisory",
            "merge_safe_contract_mock": _summarize_retrieval_suite(DEFAULT_RETRIEVAL_MERGE_SAFE),
            "strict_pilot_mock": _summarize_retrieval_suite(DEFAULT_RETRIEVAL_STRICT_PILOT),
            "live_corpus_mini": _summarize_retrieval_suite(DEFAULT_RETRIEVAL_LIVE_CORPUS_MINI),
            "workspace_scoped": _summarize_retrieval_suite(args.retrieval_workspace_scoped_json),
            "workspace_scoped_live": _summarize_retrieval_suite(
                args.retrieval_workspace_scoped_live_json
            ),
            "judge_pilot": _summarize_retrieval_judge_suite(args.retrieval_judge_json),
            "judge_holdout": _summarize_retrieval_judge_suite(args.retrieval_judge_holdout_json),
            "hybrid_ablation": _summarize_case_metrics_suite(args.hybrid_ablation_json),
            "hybrid_ablation_live": _summarize_case_metrics_suite(args.hybrid_ablation_live_json),
            "live_corpus_holdout": _summarize_retrieval_suite(
                args.retrieval_live_corpus_holdout_json
            ),
            "multihop_mini": _summarize_multihop_mini_suite(args.retrieval_multihop_json),
        },
        "claims_family": {
            "role": "advisory",
            "claims_merge_contract": _summarize_claims_suite(DEFAULT_CLAIMS_MERGE_CONTRACT),
            "claims_mini": _summarize_claims_suite(DEFAULT_CLAIMS_MINI_SUITE),
            "claims_corpus_v2_mini": _summarize_case_metrics_suite(
                DEFAULT_CLAIMS_CORPUS_V2_MINI_SUITE
            ),
            "claims_pilot": _summarize_case_metrics_suite(DEFAULT_CLAIMS_PILOT_SUITE),
            "claims_paraphrase_pilot": _summarize_case_metrics_suite(
                args.claims_paraphrase_pilot_json
            ),
            "claims_paraphrase_holdout": _summarize_case_metrics_suite(
                args.claims_paraphrase_holdout_json
            ),
        },
        "claims_production_family": {
            "role": "advisory",
            "claims_pilot_production": claims_prod,
        },
        "references_resolution_family": {
            "role": "advisory",
            "refs_merge_contract": _summarize_case_metrics_suite(
                DEFAULT_REFERENCES_RESOLUTION_CONTRACT
            ),
            "refs_mini": _summarize_case_metrics_suite(DEFAULT_REFERENCES_RESOLUTION_MINI),
            "refs_graph": _summarize_case_metrics_suite(args.refs_graph_json),
        },
        "concept_topic_family": {
            "role": "advisory",
            "concept_topic_mini": _summarize_case_metrics_suite(args.concept_topic_json),
        },
        "agent_tools_family": {
            "role": "advisory",
            "agent_tools_mini": _summarize_case_metrics_suite(args.agent_tools_json),
            "agent_tools_judge": _summarize_retrieval_judge_suite(args.agent_judge_json),
        },
        "chat_agent_family": {
            "role": "advisory",
            "chat_agent_contract": _summarize_case_metrics_suite(args.chat_agent_contract_json),
        },
        "contradictions_family": {
            "role": "advisory",
            "contradictions_v1_mini": _summarize_case_metrics_suite(args.contradictions_v1_json),
        },
    }

    _finalize_family_trust("retrieval_family", payload["retrieval_family"])
    _finalize_family_trust("claims_family", payload["claims_family"])
    _finalize_family_trust("claims_production_family", payload["claims_production_family"])
    _finalize_family_trust("references_resolution_family", payload["references_resolution_family"])
    _finalize_family_trust("concept_topic_family", payload["concept_topic_family"])
    _finalize_family_trust("agent_tools_family", payload["agent_tools_family"])
    _finalize_family_trust("chat_agent_family", payload["chat_agent_family"])
    _finalize_family_trust("contradictions_family", payload["contradictions_family"])

    trust_criteria = compute_gate_trust_criteria(
        retrieval_family=payload["retrieval_family"],
        claims_family=payload["claims_family"],
        claims_production_family=payload["claims_production_family"],
        references_resolution_family=payload["references_resolution_family"],
        concept_topic_family=payload["concept_topic_family"],
        agent_tools_family=payload["agent_tools_family"],
        chat_agent_family=payload["chat_agent_family"],
        contradictions_family=payload["contradictions_family"],
    )
    payload["decision_gate"] = evaluate_decision_gate(
        reference,
        layer1,
        layer2,
        claims_prod,
        claims_paraphrase_pilot=claims_paraphrase_pilot,
        claims_paraphrase_holdout=claims_paraphrase_holdout,
        trust_criteria=trust_criteria,
    )
    _strip_suite_cases_from_payload(payload)

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(_render_markdown(payload), encoding="utf-8")
    if args.write_trust_baseline is not None:
        args.write_trust_baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline_body = (
            json.dumps(trust_baseline_payload(payload), indent=2, ensure_ascii=False) + "\n"
        )
        args.write_trust_baseline.write_text(baseline_body, encoding="utf-8")
        print(f"Wrote {args.write_trust_baseline}")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
