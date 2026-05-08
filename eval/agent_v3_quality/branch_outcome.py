"""Stable branch status / error taxonomy for ``agent_v3_quality`` benchmark rows."""

from __future__ import annotations

import re
from typing import Any

# Matches ``subprocess_timeout_after_120.0s: ...`` from runner subprocess wrapper.
_SUBPROC_TIMEOUT_RE = re.compile(
    r"^subprocess_timeout_after_([0-9]+(?:\.[0-9]+)?)s",
    re.IGNORECASE,
)


def classify_branch_error(error: str | None) -> dict[str, Any]:  # pylint: disable=too-many-return-statements
    """Map raw ``branch['error']`` string to stable ``status`` + ``error_kind``.

    Returns keys: ``status`` (ok | timeout | error), ``error_kind`` (short slug or null),
    ``timeout_seconds`` (float when timeout), ``error_message`` (truncated original).
    """

    err = (error or "").strip()
    if not err:
        return {
            "status": "ok",
            "error_kind": None,
            "timeout_seconds": None,
            "error_message": None,
        }
    msg = err[:800]
    m = _SUBPROC_TIMEOUT_RE.match(err)
    if m:
        return {
            "status": "timeout",
            "error_kind": "subprocess_timeout",
            "timeout_seconds": float(m.group(1)),
            "error_message": msg,
        }
    if err.startswith("subprocess_exit_"):
        return {
            "status": "error",
            "error_kind": "subprocess_nonzero_exit",
            "timeout_seconds": None,
            "error_message": msg,
        }
    if err.startswith("subprocess_bad_json"):
        return {
            "status": "error",
            "error_kind": "subprocess_bad_json",
            "timeout_seconds": None,
            "error_message": msg,
        }
    if err.startswith("bad_request_json"):
        return {
            "status": "error",
            "error_kind": "bad_request_json",
            "timeout_seconds": None,
            "error_message": msg,
        }
    # HTTP client / server errors from ``_run_http_agent`` (``{ExcType}: {msg}``).
    lowered = err.lower()
    if "readtimeout" in lowered or "read timeout" in lowered:
        return {
            "status": "timeout",
            "error_kind": "http_read_timeout",
            "timeout_seconds": None,
            "error_message": msg,
        }
    if "connecttimeout" in lowered or "connect timeout" in lowered:
        return {
            "status": "timeout",
            "error_kind": "http_connect_timeout",
            "timeout_seconds": None,
            "error_message": msg,
        }
    if "httperror" in lowered or "httpstatuserror" in lowered:
        return {
            "status": "error",
            "error_kind": "http_status_error",
            "timeout_seconds": None,
            "error_message": msg,
        }
    if lowered.startswith("httpx."):
        return {
            "status": "error",
            "error_kind": "http_client_error",
            "timeout_seconds": None,
            "error_message": msg,
        }
    return {
        "status": "error",
        "error_kind": "unknown",
        "timeout_seconds": None,
        "error_message": msg,
    }


def branch_outcome_from_branch(
    branch: dict[str, Any] | None,
) -> dict[str, Any]:
    """Outcome record from a post-judge baseline/candidate branch dict."""

    b = branch or {}
    return classify_branch_error(b.get("error") if isinstance(b.get("error"), str) else None)


def aggregate_branch_outcomes(cases: list[dict[str, Any]]) -> dict[str, Any]:
    """Roll up ``baseline_outcome`` / ``candidate_outcome`` for suite ``summary``."""

    baseline_status_counts: dict[str, int] = {}
    candidate_status_counts: dict[str, int] = {}
    error_kind_counts: dict[str, int] = {}
    baseline_timeout_cases: list[str] = []
    candidate_timeout_cases: list[str] = []
    baseline_error_cases: list[str] = []
    candidate_error_cases: list[str] = []

    for row in cases:
        cid = str(row.get("case_id") or "")
        bo = row.get("baseline_outcome")
        co = row.get("candidate_outcome")
        if isinstance(bo, dict):
            bs = str(bo.get("status") or "ok")
            baseline_status_counts[bs] = baseline_status_counts.get(bs, 0) + 1
            bk = bo.get("error_kind")
            if bk:
                key = f"baseline:{bk}"
                error_kind_counts[key] = error_kind_counts.get(key, 0) + 1
            if bs == "timeout" and cid:
                baseline_timeout_cases.append(cid)
            if bs == "error" and cid:
                baseline_error_cases.append(cid)
        if isinstance(co, dict):
            cs = str(co.get("status") or "ok")
            candidate_status_counts[cs] = candidate_status_counts.get(cs, 0) + 1
            ck = co.get("error_kind")
            if ck:
                key = f"candidate:{ck}"
                error_kind_counts[key] = error_kind_counts.get(key, 0) + 1
            if cs == "timeout" and cid:
                candidate_timeout_cases.append(cid)
            if cs == "error" and cid:
                candidate_error_cases.append(cid)

    any_branch_problem = sum(
        1
        for row in cases
        if (
            isinstance(row.get("baseline_outcome"), dict)
            and row["baseline_outcome"].get("status") != "ok"
        )
        or (
            isinstance(row.get("candidate_outcome"), dict)
            and row["candidate_outcome"].get("status") != "ok"
        )
    )

    return {
        "branch_outcome_schema": "branch_outcome_v1",
        "cases_with_any_branch_non_ok": any_branch_problem,
        "baseline_status_counts": baseline_status_counts,
        "candidate_status_counts": candidate_status_counts,
        "error_kind_counts": error_kind_counts,
        "baseline_timeout_cases": baseline_timeout_cases,
        "candidate_timeout_cases": candidate_timeout_cases,
        "baseline_error_cases": baseline_error_cases,
        "candidate_error_cases": candidate_error_cases,
    }
