"""Benchmark HTTP routes: run lifecycle, compare, per-case inspector payloads."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from eval.report_compare import (
    compare_reports,
    compare_result_to_markdown,
    normalize_api_run_for_compare,
)
from science_graphrag.api.benchmark.case_load import load_case_bundle
from science_graphrag.api.benchmark.constants import MAX_COMPARE_CASE_ROWS
from science_graphrag.api.benchmark.inspector import (
    build_evidence_links,
    build_inspector_highlights,
    layer1_comparison_payload,
    layer2_comparison_payload,
)
from science_graphrag.api.benchmark.run_resolve import resolve_case_ids
from science_graphrag.api.benchmark.runtime import task_store as get_task_store
from science_graphrag.api.benchmark.schemas import (
    RunCaseDetailResponse,
    RunCasesListResponse,
    RunCreateRequest,
    RunCreateResponse,
    RunDetailResponse,
    RunsCompareResponse,
    RunsListResponse,
    RunSummaryResponse,
)
from science_graphrag.api.task_store import RunPayloadTooLargeError, RunStatus

router = APIRouter()


@router.post("/benchmark/runs", response_model=RunCreateResponse)
def create_benchmark_run(body: RunCreateRequest) -> RunCreateResponse:
    """Create and immediately start a benchmark run (layer-1 or layer-2)."""
    case_ids = resolve_case_ids(body)
    fam = (body.family or "layer1").strip().lower()
    if fam == "graph":
        raise HTTPException(
            status_code=400,
            detail="graph_benchmark_use_cli",
        )
    if fam not in ("layer1", "layer2"):
        raise HTTPException(status_code=400, detail="invalid_family")
    try:
        run_id = get_task_store().create_run(
            case_ids=case_ids,
            label=body.label,
            benchmark_family=fam,
            run_config={
                "model_profile": body.model_profile,
                "model_id": body.model_id,
                "base_url_override": body.base_url_override,
                "api_key_env_name": body.api_key_env_name,
                "gold_source": body.gold_source,
                "threshold_profile": body.threshold_profile,
            },
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    # We just created; store might still be running.
    run = get_task_store().get_run(run_id)
    status = run.get("status") if run else RunStatus.RUNNING
    return RunCreateResponse(
        run_id=run_id,
        status=status,
        benchmark_family=fam,
        label=body.label,
        run_config=(run.get("run_config") if run else {}) or {},
    )


@router.get("/benchmark/runs", response_model=RunsListResponse)
def list_layer1_benchmark_runs(
    family: str | None = Query(
        default=None,
        description="Filter by benchmark_family (exact, case-insensitive).",
    ),
    status: str | None = Query(
        default=None,
        description="Filter by run status (exact, case-insensitive).",
    ),
    q: str | None = Query(
        default=None,
        description="Substring match on run_id or label (case-insensitive).",
    ),
) -> RunsListResponse:
    """List all known runs with a compact metrics summary."""
    items = get_task_store().list_runs_summary()
    fam_f = (family or "").strip().lower() or None
    st_f = (status or "").strip().lower() or None
    needle = (q or "").strip().lower()
    if fam_f:
        items = [x for x in items if (x.get("benchmark_family") or "layer1").lower() == fam_f]
    if st_f:
        items = [x for x in items if (x.get("status") or "").lower() == st_f]
    if needle:
        items = [
            x
            for x in items
            if needle in (x.get("run_id") or "").lower() or needle in (x.get("label") or "").lower()
        ]
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    return RunsListResponse(items=items, total=len(items))


@router.get("/benchmark/runs/compare", response_model=RunsCompareResponse)
def compare_benchmark_runs(
    baseline_run_id: str = Query(..., description="Baseline run_id (older / reference)."),
    current_run_id: str = Query(..., description="Current run_id (newer / candidate)."),
) -> RunsCompareResponse:
    """Compare two persisted runs using flattened per-case metrics (same benchmark_family only)."""
    if baseline_run_id.strip() == current_run_id.strip():
        raise HTTPException(status_code=400, detail="same_run_id")
    baseline = get_task_store().get_run(baseline_run_id)
    current = get_task_store().get_run(current_run_id)
    if not baseline:
        raise HTTPException(status_code=404, detail="baseline_run_not_found")
    if not current:
        raise HTTPException(status_code=404, detail="current_run_not_found")
    fam_b = (baseline.get("benchmark_family") or "layer1").strip().lower()
    fam_c = (current.get("benchmark_family") or "layer1").strip().lower()
    if fam_b != fam_c:
        raise HTTPException(
            status_code=400,
            detail="benchmark_family_mismatch",
        )
    b_cases = baseline.get("cases") or []
    c_cases = current.get("cases") or []
    if len(b_cases) > MAX_COMPARE_CASE_ROWS or len(c_cases) > MAX_COMPARE_CASE_ROWS:
        raise HTTPException(
            status_code=400,
            detail="compare_case_limit_exceeded",
        )
    b_norm, b_skipped = normalize_api_run_for_compare(baseline)
    c_norm, c_skipped = normalize_api_run_for_compare(current)
    compared = compare_reports(b_norm, c_norm)
    md = compare_result_to_markdown(
        compared,
        baseline_label=baseline_run_id.strip(),
        current_label=current_run_id.strip(),
    )
    payload = {
        **compared,
        "skipped_baseline": b_skipped,
        "skipped_current": c_skipped,
        "baseline_run_id": baseline_run_id,
        "current_run_id": current_run_id,
        "benchmark_family": fam_b,
        "markdown": md,
    }
    return RunsCompareResponse(data=payload)


@router.get("/benchmark/runs/{run_id}", response_model=RunDetailResponse)
def get_layer1_benchmark_run(run_id: str) -> RunDetailResponse:
    """Return full run details for a given run_id."""
    try:
        run = get_task_store().get_run(run_id)
    except RunPayloadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from None
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunDetailResponse(data=run)


@router.get("/benchmark/runs/{run_id}/summary", response_model=RunSummaryResponse)
def get_benchmark_run_summary(run_id: str) -> RunSummaryResponse:
    """Return compact run payload for suite analytics (cases without result blobs)."""
    summary = get_task_store().get_run_summary(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunSummaryResponse(data=summary)


@router.get("/benchmark/runs/{run_id}/cases", response_model=RunCasesListResponse)
def list_benchmark_run_cases(
    run_id: str,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> RunCasesListResponse:
    """Paginated slim case rows without per-case ``result`` (large runs / ``cases_paginated``)."""
    page = get_task_store().get_run_cases_page(run_id, offset=offset, limit=limit)
    if page is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunCasesListResponse(data=page)


@router.get("/benchmark/runs/{run_id}/cases/{case_id}", response_model=RunCaseDetailResponse)
def get_benchmark_run_case_detail(run_id: str, case_id: str) -> RunCaseDetailResponse:
    """Return workbench-ready case payload for a specific run and case."""
    run = get_task_store().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    benchmark_family = run.get("benchmark_family") or "layer1"
    run_config = run.get("run_config") or {}
    bundle = load_case_bundle(
        case_id,
        benchmark_family,
        gold_source=run_config.get("gold_source"),
    )
    case_row = next((item for item in run.get("cases", []) if item.get("case_id") == case_id), None)
    if case_row is None:
        raise HTTPException(status_code=404, detail="case_not_found_in_run")
    result = case_row.get("result") or {}
    comparison = (
        layer2_comparison_payload(result)
        if benchmark_family == "layer2"
        else layer1_comparison_payload(result)
    )
    diag = result.get("diagnostics") or {}
    highlights = build_inspector_highlights(
        benchmark_family=benchmark_family,
        case_row=case_row,
        comparison=comparison,
        summary=case_row.get("summary") or {},
        diagnostics=diag if isinstance(diag, dict) else {},
    )
    evidence_links = build_evidence_links(case_id, benchmark_family)
    payload = {
        "run_id": run_id,
        "case_id": case_id,
        "family": benchmark_family,
        "status": case_row.get("status"),
        "summary": case_row.get("summary") or {},
        "article": {
            "raw_markdown": bundle["article_md"],
            "sections": bundle["article_sections"],
        },
        "gold": {
            "source": run_config.get("gold_source")
            or ("semantic_gold" if benchmark_family == "layer2" else "curated_gold"),
            "payload": result.get("gold") or bundle["gold"],
        },
        "predicted": {
            "payload": result.get("predicted"),
        },
        "comparison": comparison,
        "metrics": result.get("metrics") or {},
        "diagnostics": diag,
        "artifacts": bundle.get("artifacts") or {},
        "run_config": run_config,
        "highlights": highlights,
        "evidence_links": evidence_links,
    }
    return RunCaseDetailResponse(data=payload)


@router.delete("/benchmark/runs/{run_id}")
def delete_layer1_benchmark_run(run_id: str) -> dict[str, Any]:
    """Delete run record from in-memory store."""
    ok = get_task_store().delete_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"deleted": True, "run_id": run_id}
