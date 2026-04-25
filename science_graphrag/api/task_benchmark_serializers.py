"""Serialize and deserialize benchmark run records (API / disk JSON)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from science_graphrag.api.benchmark_profiles import public_run_config
from science_graphrag.api.task_benchmark_models import (
    FULL_RUN_BLOCK_DETAIL,
    FULL_RUN_MAX_CASE_IDS,
    FULL_RUN_MAX_FILE_BYTES,
    RunCaseRecord,
    RunRecord,
    RunStatus,
    now_iso,
)


def extract_case_f1_for_averages(case_result: dict[str, Any]) -> dict[str, float]:
    """Best-effort extraction of commonly used f1 values for UI summary."""
    metrics = (case_result or {}).get("metrics") or {}
    authorships = metrics.get("authorships") or {}
    references = metrics.get("references") or {}
    names_f1 = float(authorships.get("names_f1") or 0.0)
    sample_arxiv_f1 = float(references.get("sample_arxiv_f1") or 0.0)
    sample_doi_f1 = float(references.get("sample_doi_f1") or 0.0)
    return {
        "names_f1": names_f1,
        "sample_arxiv_f1": sample_arxiv_f1,
        "sample_doi_f1": sample_doi_f1,
    }


def mean_values(values: list[float]) -> float:
    """Arithmetic mean; empty input returns 0.0."""
    if not values:
        return 0.0
    return float(sum(values)) / float(len(values))


def case_contract_passed(result: dict[str, Any] | None) -> bool:
    """Layer-1 uses metrics.contract.passed; layer-2 uses metrics.passed."""
    if not result:
        return False
    metrics = result.get("metrics") or {}
    contract = metrics.get("contract") or {}
    if contract.get("passed") is True:
        return True
    if metrics.get("passed") is True:
        return True
    return False


def layer2_recall_ratio(metrics: dict[str, Any]) -> float:
    """Single scalar for summary: mean of method and dataset recall ratios."""
    m_num = float(metrics.get("recall_methods_num") or 0)
    m_den = float(metrics.get("recall_methods_denom") or 0) or 1.0
    d_num = float(metrics.get("recall_datasets_num") or 0)
    d_den = float(metrics.get("recall_datasets_denom") or 0) or 1.0
    return float((m_num / m_den + d_num / d_den) / 2.0)


def case_result_summary(case_record: RunCaseRecord) -> dict[str, Any]:
    """Per-case summary for UI tables."""
    result = case_record.result or {}
    metrics = result.get("metrics") or {}
    failed_checks = [
        name
        for name, passed in (metrics.get("contract", {}).get("checks") or {}).items()
        if passed is False
    ]
    out: dict[str, Any] = {
        "passed": case_contract_passed(result),
        "failed_checks": failed_checks,
        "names_f1": metrics.get("authorships", {}).get("names_f1"),
        "sample_arxiv_f1": metrics.get("references", {}).get("sample_arxiv_f1"),
        "sample_doi_f1": metrics.get("references", {}).get("sample_doi_f1"),
        "precision_methods": metrics.get("precision_methods"),
        "precision_datasets": metrics.get("precision_datasets"),
    }
    if metrics.get("precision_methods") is not None:
        out["layer2_recall_ratio"] = layer2_recall_ratio(metrics)
    return out


def full_run_blocked(
    rec: RunRecord,
    main_json_path: Path | None,
    *,
    max_case_ids: int | None = None,
    max_file_bytes: int | None = None,
) -> bool:
    """Return True if the run must not be returned as a single giant JSON payload."""
    case_limit = FULL_RUN_MAX_CASE_IDS if max_case_ids is None else max_case_ids
    file_limit = FULL_RUN_MAX_FILE_BYTES if max_file_bytes is None else max_file_bytes
    if len(rec.case_ids) > case_limit:
        return True
    if main_json_path is not None and main_json_path.is_file():
        try:
            if main_json_path.stat().st_size > file_limit:
                return True
        except OSError:
            return False
    return False


def annotate_full_run_guard(
    summary: dict[str, Any],
    *,
    rec: RunRecord | None,
    main_json_path: Path | None,
    max_case_ids: int | None = None,
    max_file_bytes: int | None = None,
) -> None:
    """Set ``full_run_blocked`` / ``full_run_block_reason`` on a summary payload for the UI."""
    case_limit = FULL_RUN_MAX_CASE_IDS if max_case_ids is None else max_case_ids
    file_limit = FULL_RUN_MAX_FILE_BYTES if max_file_bytes is None else max_file_bytes
    reason: str | None = None
    if rec is not None:
        if full_run_blocked(
            rec,
            main_json_path,
            max_case_ids=case_limit,
            max_file_bytes=file_limit,
        ):
            reason = FULL_RUN_BLOCK_DETAIL
    else:
        ct_raw = summary.get("cases_total")
        if ct_raw is None:
            ct_raw = len(summary.get("cases") or [])
        try:
            if int(ct_raw) > case_limit:
                reason = FULL_RUN_BLOCK_DETAIL
        except (TypeError, ValueError):
            pass
        if reason is None and main_json_path is not None:
            if main_json_path.is_file():
                try:
                    if main_json_path.stat().st_size > file_limit:
                        reason = FULL_RUN_BLOCK_DETAIL
                except OSError:
                    pass
    summary["full_run_blocked"] = reason is not None
    summary["full_run_block_reason"] = reason


def run_from_dict(payload: dict[str, Any]) -> RunRecord:
    """Rebuild a :class:`RunRecord` from persisted JSON (startup restore / disk reads)."""
    case_rows = payload.get("cases") or []
    case_ids = [str(row.get("case_id")) for row in case_rows if row.get("case_id")]
    rec = RunRecord(
        run_id=str(payload["run_id"]),
        label=payload.get("label"),
        case_ids=case_ids,
        benchmark_family=(payload.get("benchmark_family") or "layer1"),
        status=payload.get("status") or RunStatus.COMPLETED,
        created_at=payload.get("created_at") or now_iso(),
        started_at=payload.get("started_at"),
        completed_at=payload.get("completed_at"),
        cancel_requested=bool(payload.get("cancel_requested")),
        error_message=payload.get("error_message"),
        run_config=dict(payload.get("run_config") or {}),
    )
    for row in case_rows:
        case_id = row.get("case_id")
        if not case_id or row.get("status") == "pending":
            continue
        rec.cases[str(case_id)] = RunCaseRecord(
            case_id=str(case_id),
            status=row.get("status") or "pending",
            result=row.get("result"),
            error_message=row.get("error_message"),
            finished_at=row.get("finished_at"),
        )
    if rec.status in (RunStatus.QUEUED, RunStatus.RUNNING):
        rec.status = RunStatus.FAILED
        rec.completed_at = rec.completed_at or now_iso()
        rec.error_message = rec.error_message or "run_interrupted_after_api_restart"
    return rec


def slim_case_row(cid: str, case_rec: RunCaseRecord | None) -> dict[str, Any]:
    """Slim per-case row for summaries and pagination (no full ``result`` blob)."""
    if case_rec is None:
        return {"case_id": cid, "status": "pending"}
    return {
        "case_id": case_rec.case_id,
        "status": case_rec.status,
        "error_message": case_rec.error_message,
        "finished_at": case_rec.finished_at,
        "summary": case_result_summary(case_rec),
    }


def run_aggregate_summary(rec: RunRecord) -> dict[str, Any]:
    """Aggregate pass/fail counts and mean F1-style metrics for a run."""
    counts = rec.progress_counts()
    ok_results = [c.result for c in rec.cases.values() if c.status == "ok" and c.result]
    f1_names = [extract_case_f1_for_averages(r)["names_f1"] for r in ok_results]
    f1_arxiv = [extract_case_f1_for_averages(r)["sample_arxiv_f1"] for r in ok_results]
    f1_doi = [extract_case_f1_for_averages(r)["sample_doi_f1"] for r in ok_results]
    l2_recalls = []
    for r in ok_results:
        m = r.get("metrics") or {}
        if m.get("precision_methods") is not None:
            l2_recalls.append(layer2_recall_ratio(m))
    return {
        "avg_names_f1": mean_values(f1_names),
        "avg_sample_arxiv_f1": mean_values(f1_arxiv),
        "avg_sample_doi_f1": mean_values(f1_doi),
        "avg_layer2_recall_ratio": mean_values(l2_recalls),
        "pass_count": len(
            [1 for c in rec.cases.values() if c.status == "ok" and case_contract_passed(c.result)]
        ),
        "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
        "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
        "case_count": counts["total"],
    }


def run_to_full_api_dict(rec: RunRecord) -> dict[str, Any]:
    """Serialize a full run (progress + summaries + all case results)."""
    counts = rec.progress_counts()
    cases_out: list[dict[str, Any]] = []
    for cid in rec.case_ids:
        if cid in rec.cases:
            case_row = rec.cases[cid].to_dict()
            case_row["summary"] = case_result_summary(rec.cases[cid])
            cases_out.append(case_row)
        else:
            cases_out.append({"case_id": cid, "status": "pending"})

    ok_results = [c.result for c in rec.cases.values() if c.status == "ok" and c.result]
    f1_names = [extract_case_f1_for_averages(r)["names_f1"] for r in ok_results]
    f1_arxiv = [extract_case_f1_for_averages(r)["sample_arxiv_f1"] for r in ok_results]
    f1_doi = [extract_case_f1_for_averages(r)["sample_doi_f1"] for r in ok_results]
    l2_recalls = []
    for r in ok_results:
        m = r.get("metrics") or {}
        if m.get("precision_methods") is not None:
            l2_recalls.append(layer2_recall_ratio(m))

    return {
        "run_id": rec.run_id,
        "label": rec.label,
        "benchmark_family": rec.benchmark_family,
        "status": rec.status,
        "created_at": rec.created_at,
        "started_at": rec.started_at,
        "completed_at": rec.completed_at,
        "error_message": rec.error_message,
        "run_config": public_run_config(rec.run_config),
        "progress": {
            "total": counts["total"],
            "completed": counts["completed"],
            "percent": (
                (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
            ),
        },
        "summary": {
            "avg_names_f1": mean_values(f1_names),
            "avg_sample_arxiv_f1": mean_values(f1_arxiv),
            "avg_sample_doi_f1": mean_values(f1_doi),
            "avg_layer2_recall_ratio": mean_values(l2_recalls),
            "pass_count": len(
                [
                    1
                    for c in rec.cases.values()
                    if c.status == "ok" and case_contract_passed(c.result)
                ]
            ),
            "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
            "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
            "case_count": counts["total"],
        },
        "cases": cases_out,
    }


def run_to_summary_dict(rec: RunRecord, *, inline_cases_limit: int) -> dict[str, Any]:
    """Like full dict but omits per-case ``result``; optionally omits ``cases`` when huge."""
    counts = rec.progress_counts()
    total = counts["total"]
    base: dict[str, Any] = {
        "run_id": rec.run_id,
        "label": rec.label,
        "benchmark_family": rec.benchmark_family,
        "status": rec.status,
        "created_at": rec.created_at,
        "started_at": rec.started_at,
        "completed_at": rec.completed_at,
        "error_message": rec.error_message,
        "run_config": public_run_config(rec.run_config),
        "progress": {
            "total": counts["total"],
            "completed": counts["completed"],
            "percent": (
                (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
            ),
        },
        "summary": run_aggregate_summary(rec),
    }
    if total > inline_cases_limit:
        base["cases"] = []
        base["cases_paginated"] = True
        base["cases_total"] = total
    else:
        base["cases"] = [slim_case_row(cid, rec.cases.get(cid)) for cid in rec.case_ids]
        base["cases_paginated"] = False
        base["cases_total"] = total
    return base


def persisted_row_to_case_record(row: dict[str, Any]) -> RunCaseRecord:
    """Map a JSON case row into :class:`RunCaseRecord`."""
    return RunCaseRecord(
        case_id=str(row.get("case_id") or ""),
        status=str(row.get("status") or "pending"),
        result=row.get("result") if isinstance(row.get("result"), dict) else None,
        error_message=row.get("error_message"),
        finished_at=row.get("finished_at"),
    )


def persisted_payload_to_summary_dict(
    payload: dict[str, Any], *, inline_cases_limit: int
) -> dict[str, Any] | None:
    """Build summary dict from on-disk full-run JSON."""
    try:
        rec = run_from_dict(payload)
    except (KeyError, TypeError, ValueError):
        return None
    return run_to_summary_dict(rec, inline_cases_limit=inline_cases_limit)


def run_cases_page_from_record(rec: RunRecord, *, offset: int, limit: int) -> dict[str, Any]:
    """Paginate slim case rows from an in-memory :class:`RunRecord`."""
    total = len(rec.case_ids)
    slice_ids = rec.case_ids[offset : offset + limit]
    items = [slim_case_row(cid, rec.cases.get(cid)) for cid in slice_ids]
    return {
        "run_id": rec.run_id,
        "benchmark_family": rec.benchmark_family,
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


def persisted_payload_to_cases_page(
    payload: dict[str, Any], *, offset: int, limit: int
) -> dict[str, Any]:
    """Paginate slim case rows from persisted full-run JSON."""
    case_rows = [r for r in (payload.get("cases") or []) if isinstance(r, dict)]
    case_ids = [str(r.get("case_id")) for r in case_rows if r.get("case_id")]
    total = len(case_ids)
    slice_ids = case_ids[offset : offset + limit]
    row_by_id = {str(r.get("case_id")): r for r in case_rows if r.get("case_id")}
    items: list[dict[str, Any]] = []
    for cid in slice_ids:
        row = row_by_id.get(cid)
        if not row:
            items.append({"case_id": cid, "status": "pending"})
        else:
            cr = persisted_row_to_case_record(row)
            items.append(slim_case_row(cid, cr))
    return {
        "run_id": payload.get("run_id"),
        "benchmark_family": payload.get("benchmark_family"),
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items,
    }


def run_summary_list_row(rec: RunRecord) -> dict[str, Any]:
    """Serialize a compact run row for the runs list."""
    counts = rec.progress_counts()
    return {
        "run_id": rec.run_id,
        "label": rec.label,
        "benchmark_family": rec.benchmark_family,
        "status": rec.status,
        "created_at": rec.created_at,
        "started_at": rec.started_at,
        "completed_at": rec.completed_at,
        "run_config": public_run_config(rec.run_config),
        "progress": {
            "total": counts["total"],
            "completed": counts["completed"],
            "percent": (
                (counts["completed"] / counts["total"] * 100.0) if counts["total"] else 0.0
            ),
        },
        "summary": {
            "avg_names_f1": mean_values(
                [
                    extract_case_f1_for_averages(c.result)["names_f1"]
                    for c in rec.cases.values()
                    if c.status == "ok" and c.result
                ]
            ),
            "avg_sample_arxiv_f1": mean_values(
                [
                    extract_case_f1_for_averages(c.result)["sample_arxiv_f1"]
                    for c in rec.cases.values()
                    if c.status == "ok" and c.result
                ]
            ),
            "avg_sample_doi_f1": mean_values(
                [
                    extract_case_f1_for_averages(c.result)["sample_doi_f1"]
                    for c in rec.cases.values()
                    if c.status == "ok" and c.result
                ]
            ),
            "avg_layer2_recall_ratio": mean_values(
                [
                    layer2_recall_ratio(c.result.get("metrics") or {})
                    for c in rec.cases.values()
                    if c.status == "ok" and c.result
                ]
            ),
            "pass_count": len(
                [
                    1
                    for c in rec.cases.values()
                    if c.status == "ok" and c.result and case_contract_passed(c.result)
                ]
            ),
            "fail_count": len([1 for c in rec.cases.values() if c.status == "failed"]),
            "cancelled_count": len([1 for c in rec.cases.values() if c.status == "cancelled"]),
            "case_count": counts["total"],
        },
    }
