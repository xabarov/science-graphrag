"""E2E case acceptance helpers."""

from __future__ import annotations

from typing import Any


def e2e_case_passes_acceptance(case: dict[str, Any]) -> bool:
    """Mirror ``agent_od_workspace_e2e_audit._case_passes_acceptance`` for report JSON."""
    return bool(
        case.get("http_ok")
        and case.get("final_answer_reached")
        and int(case.get("answer_len") or 0) >= 40
    )


def e2e_failures_are_retryable_provider_flakes(report: dict[str, Any]) -> bool:
    """True when every non-passing E2E case is tagged ``retryable_provider_flake``."""
    cases = report.get("cases") or []
    if not isinstance(cases, list):
        return False
    non_passing = [c for c in cases if isinstance(c, dict) and not e2e_case_passes_acceptance(c)]
    if not non_passing:
        return False
    return all(bool(c.get("retryable_provider_flake")) for c in non_passing)
