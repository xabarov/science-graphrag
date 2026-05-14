"""Retry / acceptance heuristics for OD workspace E2E audit."""

from __future__ import annotations

from typing import Any


def case_passes_acceptance(case_report: dict[str, Any]) -> bool:
    """Return True when a case satisfies E2E acceptance gates."""
    return bool(
        case_report.get("http_ok")
        and case_report.get("final_answer_reached")
        and int(case_report.get("answer_len") or 0) >= 40
    )


def should_retry_after_case_failure(case_report: dict[str, Any]) -> bool:
    """Retry only on known transport/runtime deadline flakes."""
    warnings = case_report.get("warnings") or []
    if not isinstance(warnings, list):
        warnings = []
    if "agent_turn_deadline_exceeded" in {str(x).strip() for x in warnings}:
        return True
    notes = case_report.get("notes") or []
    if isinstance(notes, list) and "last_tool_not_final_answer" in {str(x).strip() for x in notes}:
        run_meta = case_report.get("run_metadata") or {}
        if isinstance(run_meta, dict) and bool(run_meta.get("agent_turn_deadline_exceeded")):
            return True
    return False


def should_retry_after_transport_flake(case_report: dict[str, Any]) -> bool:
    """One-shot retry for infra disconnects (uvicorn reload, transient proxy, API restart)."""
    if case_report.get("http_ok"):
        return False
    err = str(case_report.get("error") or "")
    needles = (
        "Server disconnected",
        "Connection refused",
        "ReadTimeout",
        "Read timeout",
        "timed out",
        "RemoteProtocolError",
        "Connection reset",
        "ConnectError",
    )
    if any(n in err for n in needles):
        return True
    # httpx.HTTPStatusError string shapes: ``Client error '524' for url ...``
    for code in ("502", "503", "504", "524"):
        if f"'{code}'" in err or f'"{code}"' in err:
            return True
    return False


def should_retry_after_provider_flake(case_report: dict[str, Any]) -> bool:
    """HTTP 200 but degraded body after upstream/gateway flake (sync JSON normalization)."""
    if not case_report.get("http_ok"):
        return False
    if case_passes_acceptance(case_report):
        return False
    if case_report.get("retryable_provider_flake"):
        return True
    warns = case_report.get("warnings") or []
    if isinstance(warns, list) and "retryable_provider_flake" in {str(x).strip() for x in warns}:
        return True
    rm = case_report.get("run_metadata") or {}
    if isinstance(rm, dict) and rm.get("agent_sync_error"):
        from science_graphrag.api.agent_v2_modules.errors import (  # pylint: disable=import-outside-toplevel
            is_retryable_provider_error_class,
        )

        if is_retryable_provider_error_class(str(rm.get("error_class") or "")):
            return True
    return False
