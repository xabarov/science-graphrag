"""Benchmark UI backend.

This router exposes layer-1 benchmark fixtures and in-memory run execution
controls for the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from eval.bench_common import discover_layer1_case_dirs
from science_graphrag.api.task_store import RunStatus, task_store

router = APIRouter()


def _fixtures_root_layer1() -> Path:
    """Return fixtures root directory for layer-1 benchmark cases."""
    # science_graphrag/api/benchmark.py -> .../science_graphrag/
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "tests" / "fixtures" / "benchmarks" / "layer1"


def _load_case_tiers() -> dict[str, list[str]]:
    """Load case_tiers.json mapping (tier -> list[case_id])."""
    root = _fixtures_root_layer1()
    tiers_path = root / "case_tiers.json"
    if not tiers_path.is_file():
        return {}
    raw = json.loads(tiers_path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for k, v in raw.items():
        out[str(k)] = [str(x) for x in (v or [])]
    return out


def _tier_for_case_id(case_id: str, tiers: dict[str, list[str]]) -> str | None:
    """Find tier name for case_id using loaded tier mapping."""
    for tier, ids in tiers.items():
        if case_id in ids:
            return tier
    return None


class CaseListItem(BaseModel):
    """One row in the layer-1 cases list."""

    case_id: str
    tier: str | None = None
    has_article_md: int
    has_gold_json: int


class CasesListResponse(BaseModel):
    """Response payload for GET /benchmark/cases."""

    items: list[CaseListItem]
    total: int


class CaseDetailResponse(BaseModel):
    """Response payload for GET /benchmark/cases/{case_id}."""

    case_id: str
    tier: str | None = None
    article_md: str
    gold: dict[str, Any]


class RunCreateRequest(BaseModel):
    """Request payload for POST /benchmark/runs."""

    case_ids: list[str] | str = Field(
        ..., description='Either a list of case_ids, or "all" / "merge_safe".'
    )
    label: str | None = None


class RunCreateResponse(BaseModel):
    """Response payload for POST /benchmark/runs."""

    run_id: str
    status: str


class RunListItem(BaseModel):
    """One row in the runs list."""

    run_id: str
    label: str | None = None
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    progress: dict[str, Any]
    summary: dict[str, Any]


class RunsListResponse(BaseModel):
    """Response payload for GET /benchmark/runs."""

    items: list[RunListItem]
    total: int


class RunDetailResponse(BaseModel):
    # We intentionally keep it untyped to allow evolution of metrics/predicted payloads.
    """Response payload for GET /benchmark/runs/{run_id}."""

    data: dict[str, Any]


@router.get("/benchmark/cases", response_model=CasesListResponse)
def get_layer1_cases_list(
    tier: str | None = Query(
        default=None, description='Optional: "merge_safe" or "nightly_heavy".'
    ),
    q: str | None = Query(default=None, description="Optional substring match on case_id."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> CasesListResponse:
    """List layer-1 benchmark case directories available to the UI."""
    root = _fixtures_root_layer1()
    tiers = _load_case_tiers()

    case_dirs = discover_layer1_case_dirs(root, tier=tier)
    # Optional filter by q.
    needle = (q or "").strip().lower()
    if needle:
        case_dirs = [p for p in case_dirs if needle in p.name.lower()]

    # Stable ordering.
    case_dirs = sorted(case_dirs, key=lambda p: p.name)
    slice_dirs = case_dirs[offset : offset + limit]

    items: list[CaseListItem] = []
    for d in slice_dirs:
        cid = d.name
        items.append(
            CaseListItem(
                case_id=cid,
                tier=_tier_for_case_id(cid, tiers),
                has_article_md=int((d / "article.md").is_file()),
                has_gold_json=int((d / "gold.json").is_file()),
            )
        )

    return CasesListResponse(items=items, total=len(case_dirs))


@router.get("/benchmark/cases/{case_id}", response_model=CaseDetailResponse)
def get_layer1_case_detail(case_id: str) -> CaseDetailResponse:
    """Return fixture contents (article.md + parsed gold.json) for a case."""
    root = _fixtures_root_layer1()
    tiers = _load_case_tiers()
    fixture_dir = root / case_id
    if not fixture_dir.is_dir():
        raise HTTPException(status_code=404, detail="case_not_found")

    article_path = fixture_dir / "article.md"
    gold_path = fixture_dir / "gold.json"
    if not article_path.is_file() or not gold_path.is_file():
        raise HTTPException(status_code=404, detail="case_incomplete")

    article_md = article_path.read_text(encoding="utf-8")
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    return CaseDetailResponse(
        case_id=case_id,
        tier=_tier_for_case_id(case_id, tiers),
        article_md=article_md,
        gold=gold,
    )


def _resolve_case_ids(req: RunCreateRequest) -> list[str]:
    """Resolve request selectors ("all"/"merge_safe") into concrete case_ids."""
    root = _fixtures_root_layer1()
    if isinstance(req.case_ids, str):
        selector = req.case_ids.strip()
        if selector == "all":
            return [p.name for p in discover_layer1_case_dirs(root)]
        if selector == "merge_safe":
            return [p.name for p in discover_layer1_case_dirs(root, tier="merge_safe")]
        if selector == "nightly_heavy":
            return [p.name for p in discover_layer1_case_dirs(root, tier="nightly_heavy")]
        raise HTTPException(status_code=400, detail="unknown_case_selector")

    # Explicit list: validate existence.
    allowed = {p.name for p in discover_layer1_case_dirs(root)}
    missing = [x for x in req.case_ids if x not in allowed]
    if missing:
        raise HTTPException(status_code=400, detail=f"unknown_case_ids:{missing}")
    return list(req.case_ids)


@router.post("/benchmark/runs", response_model=RunCreateResponse)
def create_layer1_benchmark_run(body: RunCreateRequest) -> RunCreateResponse:
    """Create and immediately start a benchmark run."""
    case_ids = _resolve_case_ids(body)
    run_id = task_store.create_run(case_ids=case_ids, label=body.label)
    # We just created; store might still be running.
    run = task_store.get_run(run_id)
    status = run.get("status") if run else RunStatus.RUNNING
    return RunCreateResponse(run_id=run_id, status=status)


@router.get("/benchmark/runs", response_model=RunsListResponse)
def list_layer1_benchmark_runs() -> RunsListResponse:
    """List all known in-memory runs with a compact metrics summary."""
    items = task_store.list_runs_summary()
    # Newest first.
    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    return RunsListResponse(items=items, total=len(items))


@router.get("/benchmark/runs/{run_id}", response_model=RunDetailResponse)
def get_layer1_benchmark_run(run_id: str) -> RunDetailResponse:
    """Return full run details for a given run_id."""
    run = task_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunDetailResponse(data=run)


@router.delete("/benchmark/runs/{run_id}")
def delete_layer1_benchmark_run(run_id: str) -> dict[str, Any]:
    """Delete run record from in-memory store."""
    ok = task_store.delete_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"deleted": True, "run_id": run_id}
