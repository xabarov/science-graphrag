"""Core / nightly decision gate with BT1 trust overlays."""

from __future__ import annotations

from typing import Any


def evaluate_decision_gate(
    reference: dict[str, Any],
    layer1: dict[str, Any],
    layer2: dict[str, Any],
    claims_production: dict[str, Any] | None = None,
    *,
    trust_criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{decision, reason, criteria}`` including BT1 trust fields."""

    ref_ok = reference.get("all_passed") is True
    l1_failed = layer1.get("failed_count", 0) if "error" not in layer1 else None
    l2_failed = layer2.get("failed_count", 0) if "error" not in layer2 else None

    cp = claims_production or {}
    cp_missing = bool(cp.get("error") == "missing_file")
    cp_ok = bool(cp.get("all_passed")) if cp and "error" not in cp else False
    mcr = cp.get("mean_claim_recall") if cp and "error" not in cp else None
    cp_recall_ok = mcr is None or (float(mcr) + 1e-9 >= 0.8)

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

    if decision == "GO" and cp_missing:
        decision = "CONDITIONAL-GO"
        reason = f"{reason};claims_production_artifact_missing"
    elif not cp_missing and cp and "error" not in cp:
        if not cp_ok:
            decision = "NO-GO"
            reason = "claims_production_pilot_not_all_passed"
        elif not cp_recall_ok:
            decision = "NO-GO"
            reason = "claims_production_mean_recall_below_0_8"

    tc = trust_criteria or {}
    criteria: dict[str, Any] = {
        "reference_all_passed": ref_ok,
        "layer1_nightly_failed_count": l1_failed,
        "layer2_nightly_failed_count": l2_failed,
        "claims_production_artifact_missing": cp_missing,
        "claims_production_all_passed": None if cp_missing else cp_ok,
        "claims_production_mean_claim_recall": mcr,
        "advisory_phantom_count": tc.get("advisory_phantom_count", 0),
        "advisory_phantom_families": tc.get("advisory_phantom_families", []),
        "advisory_individual_failures": tc.get("advisory_individual_failures", []),
        "hard_block_individual_failures": tc.get("hard_block_individual_failures", []),
    }

    if decision == "GO" and int(criteria.get("advisory_phantom_count") or 0) > 0:
        decision = "CONDITIONAL-GO"
        reason = f"{reason};advisory_phantom_count={criteria['advisory_phantom_count']}"

    hard_list = criteria.get("hard_block_individual_failures") or []
    if hard_list:
        decision = "NO-GO"
        reason = f"hard_block_individual_failures:{','.join(hard_list)}"

    return {"decision": decision, "reason": reason, "criteria": criteria}
