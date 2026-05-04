"""Core / nightly decision gate with BT1 trust overlays."""

from __future__ import annotations

from typing import Any

# Wave 1 (BT6): core claims lane promotion bar on paraphrase suites (per case).
_PAR_CORE_RECALL = 0.7
_PAR_CORE_PRECISION = 0.7


def _paraphrase_suite_meets_bt6_core_bar(suite: dict[str, Any]) -> bool:
    """True when suite is present, summary agrees, and every case clears recall/precision floors."""

    if not suite or suite.get("error") == "missing_file":
        return False
    if not bool(suite.get("all_passed")):
        return False
    cases = suite.get("cases") or []
    if not cases:
        return False
    for case in cases:
        metrics = case.get("metrics") or {}
        if not metrics.get("passed"):
            return False
        cr = metrics.get("claim_recall")
        cp = metrics.get("claim_precision")
        if cr is None or cp is None:
            return False
        try:
            if float(cr) + 1e-12 < _PAR_CORE_RECALL:
                return False
            if float(cp) + 1e-12 < _PAR_CORE_PRECISION:
                return False
        except (TypeError, ValueError):
            return False
    return True


def evaluate_decision_gate(
    reference: dict[str, Any],
    layer1: dict[str, Any],
    layer2: dict[str, Any],
    claims_production: dict[str, Any] | None = None,
    *,
    claims_paraphrase_pilot: dict[str, Any] | None = None,
    claims_paraphrase_holdout: dict[str, Any] | None = None,
    trust_criteria: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{decision, reason, criteria}`` including BT1 trust fields.

    When both ``claims_paraphrase_*`` artifacts are present (non-``missing_file``), the **core**
    claims gate uses their ``all_passed`` flags (BT6 / Wave 1 honest closure). The legacy
    ``claims_production`` pilot remains in ``criteria`` for observability only.
    """

    ref_ok = reference.get("all_passed") is True
    l1_failed = layer1.get("failed_count", 0) if "error" not in layer1 else None
    l2_failed = layer2.get("failed_count", 0) if "error" not in layer2 else None

    cpp = claims_paraphrase_pilot or {}
    cph = claims_paraphrase_holdout or {}
    cpp_missing = bool(cpp.get("error") == "missing_file")
    cph_missing = bool(cph.get("error") == "missing_file")
    cpp_ok = _paraphrase_suite_meets_bt6_core_bar(cpp) if cpp and not cpp_missing else False
    cph_ok = _paraphrase_suite_meets_bt6_core_bar(cph) if cph and not cph_missing else False
    use_paraphrase_core = not cpp_missing and not cph_missing

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

    if decision in {"GO", "CONDITIONAL-GO"}:
        if use_paraphrase_core:
            if not cpp_ok or not cph_ok:
                decision = "NO-GO"
                failed = []
                if not cpp_ok:
                    failed.append("pilot")
                if not cph_ok:
                    failed.append("holdout")
                reason = f"{reason};claims_paraphrase_core_bar_not_met:" + ",".join(failed)
        else:
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
        "claims_paraphrase_pilot_artifact_missing": cpp_missing,
        "claims_paraphrase_holdout_artifact_missing": cph_missing,
        "claims_paraphrase_pilot_all_passed": None if cpp_missing else bool(cpp.get("all_passed")),
        "claims_paraphrase_holdout_all_passed": (
            None if cph_missing else bool(cph.get("all_passed"))
        ),
        "claims_paraphrase_pilot_meets_bt6_core_bar": None if cpp_missing else cpp_ok,
        "claims_paraphrase_holdout_meets_bt6_core_bar": None if cph_missing else cph_ok,
        "claims_production_artifact_missing": cp_missing,
        "claims_production_all_passed": None if cp_missing else cp_ok,
        "claims_production_mean_claim_recall": mcr,
        "claims_core_uses_paraphrase_pilot_holdout": use_paraphrase_core,
        "advisory_phantom_count": tc.get("advisory_phantom_count", 0),
        "advisory_phantom_families": tc.get("advisory_phantom_families", []),
        "advisory_individual_failures": tc.get("advisory_individual_failures", []),
        "hard_block_individual_failures": tc.get("hard_block_individual_failures", []),
    }

    # By design, `merge_safe_contract_mock` + `strict_pilot_mock` stay on canned runtimes.
    # Downgrade only when unexpected phantom families appear (more than the two allowed).
    phantom_families = list(criteria.get("advisory_phantom_families") or [])
    if decision == "GO" and len(phantom_families) > 2:
        decision = "CONDITIONAL-GO"
        reason = f"{reason};advisory_phantom_count={len(phantom_families)}"

    hard_list = criteria.get("hard_block_individual_failures") or []
    if hard_list:
        decision = "NO-GO"
        reason = f"hard_block_individual_failures:{','.join(hard_list)}"

    return {"decision": decision, "reason": reason, "criteria": criteria}
