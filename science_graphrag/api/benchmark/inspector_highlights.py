"""Human-oriented inspector headline + issue list for benchmark UI."""

from __future__ import annotations

from typing import Any


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


def _append_layer1_mismatch_issues(
    issues: list[dict[str, Any]], comparison: dict[str, Any]
) -> None:
    """Append layer-1 metadata/authorship/reference mismatch issues."""

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


def _append_layer2_semantic_issues(
    issues: list[dict[str, Any]], comparison: dict[str, Any]
) -> None:
    """Append layer-2 method/dataset miss/extra summary issues."""

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


def build_inspector_highlights(
    *,
    benchmark_family: str,
    case_row: dict[str, Any],
    comparison: dict[str, Any],
    summary: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Human-oriented summary for benchmark UI.

    Keeps ``comparison`` for backwards compatibility.
    """

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
        _append_layer1_mismatch_issues(issues, comparison)
    elif fam == "layer2":
        _append_layer2_semantic_issues(issues, comparison)

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
