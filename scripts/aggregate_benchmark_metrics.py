#!/usr/bin/env python3
"""
Aggregate benchmark JSON reports into a single machine-readable + markdown summary.

Usage (repo root):
  .venv/bin/python scripts/aggregate_benchmark_metrics.py
  .venv/bin/python scripts/aggregate_benchmark_metrics.py \\
    --out-json eval/results/benchmark-metrics-summary.json \\
    --out-md eval/results/benchmark-metrics-summary.md

Authoritative inputs (defaults) match docs/runbooks/benchmark-decision-gate.md.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REFERENCE = (
    "eval/results/current-reference-layer1-yolov1.json",
    "eval/results/current-reference-graph-yolov1.json",
    "eval/results/current-reference-layer2-yolov1-semantic.json",
)
DEFAULT_LAYER1_NIGHTLY = "eval/results/current-llm-layer1-nightly-heavy-suite-after-prompt-fix.json"
DEFAULT_LAYER2_NIGHTLY = "eval/results/current-llm-layer2-nightly-semantic-suite.json"
DEFAULT_BASELINE_LAYER1 = "eval/results/baseline-llm-layer1-nightly-heavy-suite.json"
DEFAULT_BASELINE_LAYER2 = "eval/results/baseline-llm-layer2-nightly-semantic-suite.json"

# Optional single-case retests after gold fixes (if present, listed in summary)
SUPPLEMENTARY_RETESTS = (
    "eval/results/retest-centernet-after-gold-fix.json",
    "eval/results/retest-fcos-after-gold-fix.json",
    "eval/results/retest-selective-search-after-gold-fix.json",
    "eval/results/retest-hog-realpdf-after-gold-fix.json",
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
    if not checks.get("reference_count_ok_required", True):
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


def _decision_gate(
    reference: dict[str, Any],
    layer1: dict[str, Any],
    layer2: dict[str, Any],
) -> dict[str, Any]:
    ref_ok = reference.get("all_passed") is True
    l1_failed = layer1.get("failed_count", 0) if "error" not in layer1 else None
    l2_failed = layer2.get("failed_count", 0) if "error" not in layer2 else None

    # GO: reference stable; nightly may still have classified debt
    if not ref_ok:
        decision = "NO-GO"
        reason = "reference_lane_not_all_passed"
    elif l1_failed is None or l2_failed is None:
        decision = "NO-GO"
        reason = "missing_suite_artifacts"
    elif l1_failed == 0 and l2_failed == 0:
        decision = "GO"
        reason = "all_nightly_passed"
    else:
        decision = "CONDITIONAL-GO"
        reason = "reference_ok_nightly_has_residual_failures_document_in_gate_report"

    return {
        "decision": decision,
        "reason": reason,
        "criteria": {
            "reference_all_passed": ref_ok,
            "layer1_nightly_failed_count": l1_failed,
            "layer2_nightly_failed_count": l2_failed,
        },
    }


def _md_decision_gate_section(dg: dict[str, Any]) -> list[str]:
    lines = ["## Decision gate", ""]
    lines.append(f"- **decision**: `{dg.get('decision')}`")
    lines.append(f"- **reason**: {dg.get('reason')}")
    crit = dg.get("criteria") or {}
    lines.append(f"- **reference_all_passed**: {crit.get('reference_all_passed')}")
    lines.append(f"- **layer1 nightly failed**: {crit.get('layer1_nightly_failed_count')}")
    lines.append(f"- **layer2 nightly failed**: {crit.get('layer2_nightly_failed_count')}")
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
        lines.append(
            f"- `{s.get('case_id')}`: passed={s.get('passed')} — `{s.get('artifact')}`"
        )
    lines.append("")
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
    args = parser.parse_args()

    reference = _summarize_reference(DEFAULT_REFERENCE)
    layer1 = _summarize_layer1_suite(DEFAULT_LAYER1_NIGHTLY)
    layer2 = _summarize_layer2_suite(DEFAULT_LAYER2_NIGHTLY)

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
        },
        "reference": reference,
        "layer1_nightly": layer1,
        "layer2_nightly": layer2,
        "deltas": deltas,
        "supplementary_retests": _supplementary_retests(),
        "decision_gate": _decision_gate(reference, layer1, layer2),
    }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.out_md.write_text(_render_markdown(payload), encoding="utf-8")
    print(f"Wrote {args.out_json}")
    print(f"Wrote {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
