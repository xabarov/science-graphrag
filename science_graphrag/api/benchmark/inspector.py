"""Benchmark inspector payloads (comparison tables + UI highlights)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from science_graphrag.api.benchmark.case_load import collect_case_artifacts


def layer1_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    metrics = result.get("metrics") or {}
    gold_work = gold.get("work_metadata") or {}
    pred_work = predicted.get("work_metadata") or {}
    gold_auth = gold.get("authorships") or []
    pred_auth = predicted.get("authorships") or []
    gold_refs = gold.get("references") or {}
    pred_refs = predicted.get("references") or []
    failed_checks = [
        name
        for name, passed in (metrics.get("contract", {}).get("checks") or {}).items()
        if passed is False
    ]
    metadata_rows = [
        {
            "field": field_name,
            "gold_value": gold_work.get(field_name),
            "predicted_value": pred_work.get(field_name),
        }
        for field_name in ("title", "publication_year", "doi", "arxiv_id", "work_type")
    ]
    authorship_rows = []
    max_auth = max(len(gold_auth), len(pred_auth))
    for idx in range(max_auth):
        g_item = gold_auth[idx] if idx < len(gold_auth) else {}
        p_item = pred_auth[idx] if idx < len(pred_auth) else {}
        authorship_rows.append(
            {
                "position": idx + 1,
                "gold_name": g_item.get("name"),
                "predicted_name": p_item.get("author_raw_name"),
                "gold_affiliations": g_item.get("affiliations") or [],
                "predicted_affiliations": p_item.get("raw_affiliations") or [],
            }
        )
    reference_rows = [
        {
            "field": "predicted_count",
            "gold_value": gold_refs.get("expected_count"),
            "predicted_value": len(pred_refs),
        },
        {
            "field": "sample_arxiv_ids",
            "gold_value": gold_refs.get("sample_arxiv_ids") or [],
            "predicted_value": [ref.get("arxiv_id") for ref in pred_refs if ref.get("arxiv_id")],
        },
        {
            "field": "sample_dois",
            "gold_value": gold_refs.get("sample_dois") or [],
            "predicted_value": [ref.get("doi") for ref in pred_refs if ref.get("doi")],
        },
    ]
    return {
        "metadata_rows": metadata_rows,
        "authorship_rows": authorship_rows,
        "reference_rows": reference_rows,
        "failed_checks": failed_checks,
    }


def layer2_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    gold_methods = set(gold.get("expected_method_names_normalized") or [])
    gold_datasets = set(gold.get("expected_dataset_names_normalized") or [])
    pred_methods = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("methods") or [])
        if item.get("name")
    }
    pred_datasets = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("datasets") or [])
        if item.get("name")
    }
    method_rows = [
        {
            "value": name,
            "status": "match" if name in pred_methods else "miss",
            "source": "gold",
        }
        for name in sorted(gold_methods)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_methods - gold_methods)
    ]
    dataset_rows = [
        {
            "value": name,
            "status": "match" if name in pred_datasets else "miss",
            "source": "gold",
        }
        for name in sorted(gold_datasets)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_datasets - gold_datasets)
    ]
    return {"method_rows": method_rows, "dataset_rows": dataset_rows, "failed_checks": []}


def build_evidence_links(case_id: str, benchmark_family: str) -> list[dict[str, Any]]:
    """Stable pointers for report / trace review (repo-relative paths, optional last-run hint)."""

    try:
        inv = collect_case_artifacts(case_id, benchmark_family)
    except HTTPException:
        return []
    links: list[dict[str, Any]] = []
    fd = inv.get("fixture_dir_relative")
    if fd:
        links.append(
            {
                "id": "fixture_dir",
                "label": "fixture_directory",
                "path_relative_to_repo": fd,
            }
        )
    art = inv.get("article") or {}
    if art.get("path_relative_to_repo"):
        links.append(
            {
                "id": "article",
                "label": "article_md",
                "path_relative_to_repo": art["path_relative_to_repo"],
            }
        )
    for gv in inv.get("gold_variants") or []:
        if gv.get("present") and gv.get("path_relative_to_repo"):
            links.append(
                {
                    "id": f"gold_{gv.get('id', 'variant')}",
                    "label": str(gv.get("id", "gold")),
                    "path_relative_to_repo": gv["path_relative_to_repo"],
                }
            )
    sg = inv.get("semantic_gold")
    if isinstance(sg, dict) and sg.get("path_relative_to_repo"):
        links.append(
            {
                "id": "semantic_gold",
                "label": "semantic_gold",
                "path_relative_to_repo": sg["path_relative_to_repo"],
            }
        )
    lrh = inv.get("last_run_hints")
    if isinstance(lrh, dict) and lrh.get("run_id"):
        links.append(
            {
                "id": "last_completed_run",
                "label": "last_completed_run",
                "run_id": str(lrh["run_id"]),
            }
        )
    return links


def append_diag_hints(issues: list[dict[str, Any]], diagnostics: dict[str, Any]) -> None:
    """Surface lightweight diagnostics as non-fatal hints (no trace URLs in current runners)."""

    if not diagnostics:
        return
    keys = (
        "metadata_source",
        "authorships_source",
        "references_source",
        "merged_reference_count",
        "extraction_llm_enabled",
    )
    snapshot = {k: diagnostics.get(k) for k in keys if diagnostics.get(k) is not None}
    if snapshot:
        issues.append({"kind": "diagnostics_hint", "severity": "info", "fields": snapshot})


def build_inspector_highlights(
    *,
    benchmark_family: str,
    case_row: dict[str, Any],
    comparison: dict[str, Any],
    summary: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Human-oriented summary for benchmark UI (keeps ``comparison`` for backwards compatibility)."""

    fam = (benchmark_family or "layer1").strip().lower()
    status = str(case_row.get("status") or "")
    issues: list[dict[str, Any]] = []
    summary_failed = [str(x) for x in (summary.get("failed_checks") or []) if x is not None]
    cmp_failed = [str(x) for x in (comparison.get("failed_checks") or []) if x is not None]
    failed_checks = sorted({*summary_failed, *cmp_failed})

    if failed_checks:
        issues.append(
            {
                "kind": "failed_check",
                "severity": "error",
                "checks": failed_checks,
            }
        )

    if status and status.lower() not in {"ok", "passed", "completed"}:
        err = case_row.get("error_message")
        issues.append(
            {
                "kind": "case_status",
                "severity": "error",
                "status": status,
                "message": err,
            }
        )

    if fam == "layer1":
        for row in comparison.get("metadata_rows") or []:
            field = row.get("field")
            gv = row.get("gold_value")
            pv = row.get("predicted_value")
            if gv != pv:
                issues.append(
                    {
                        "kind": "metadata_mismatch",
                        "severity": "warn",
                        "field": field,
                        "gold_value": gv,
                        "predicted_value": pv,
                    }
                )
        for row in comparison.get("authorship_rows") or []:
            if (row.get("gold_name") or None) != (row.get("predicted_name") or None):
                issues.append(
                    {
                        "kind": "authorship_mismatch",
                        "severity": "warn",
                        "position": row.get("position"),
                        "gold_name": row.get("gold_name"),
                        "predicted_name": row.get("predicted_name"),
                    }
                )
        for row in comparison.get("reference_rows") or []:
            field = row.get("field")
            gv = row.get("gold_value")
            pv = row.get("predicted_value")
            if gv != pv:
                issues.append(
                    {
                        "kind": "reference_mismatch",
                        "severity": "warn",
                        "field": field,
                        "gold_value": gv,
                        "predicted_value": pv,
                    }
                )
    elif fam == "layer2":
        misses = [r for r in (comparison.get("method_rows") or []) if r.get("status") == "miss"]
        extras = [r for r in (comparison.get("method_rows") or []) if r.get("status") == "extra"]
        if misses:
            issues.append(
                {
                    "kind": "layer2_missing_methods",
                    "severity": "warn",
                    "count": len(misses),
                    "sample": [m.get("value") for m in misses[:8]],
                }
            )
        if extras:
            issues.append(
                {
                    "kind": "layer2_extra_methods",
                    "severity": "warn",
                    "count": len(extras),
                    "sample": [m.get("value") for m in extras[:8]],
                }
            )
        d_misses = [r for r in (comparison.get("dataset_rows") or []) if r.get("status") == "miss"]
        d_extras = [r for r in (comparison.get("dataset_rows") or []) if r.get("status") == "extra"]
        if d_misses:
            issues.append(
                {
                    "kind": "layer2_missing_datasets",
                    "severity": "warn",
                    "count": len(d_misses),
                    "sample": [m.get("value") for m in d_misses[:8]],
                }
            )
        if d_extras:
            issues.append(
                {
                    "kind": "layer2_extra_datasets",
                    "severity": "warn",
                    "count": len(d_extras),
                    "sample": [m.get("value") for m in d_extras[:8]],
                }
            )

    append_diag_hints(issues, diagnostics)

    if not issues:
        headline = "No blocking issues detected from automated comparison."
    elif failed_checks:
        headline = f"Failed checks: {', '.join(failed_checks[:5])}" + (
            "…" if len(failed_checks) > 5 else ""
        )
    else:
        headline = f"{len(issues)} issue(s) detected — expand raw diff for details."

    return {
        "headline": headline,
        "failed_checks": failed_checks,
        "issues": issues,
        "family": fam,
    }
