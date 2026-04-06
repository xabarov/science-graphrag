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

from eval.bench_common import discover_layer1_case_dirs, discover_layer2_case_dirs
from science_graphrag.api.task_store import RunStatus, task_store

router = APIRouter()


def _fixtures_root_layer1() -> Path:
    """Return fixtures root directory for layer-1 benchmark cases."""
    # science_graphrag/api/benchmark.py -> .../science_graphrag/
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "tests" / "fixtures" / "benchmarks" / "layer1"


def _fixtures_root_layer2() -> Path:
    """Return fixtures root for layer-2 semantic benchmark cases."""
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "tests" / "fixtures" / "benchmarks" / "layer2"


def _load_case_tiers(root: Path) -> dict[str, list[str]]:
    """Load case_tiers.json mapping (tier -> list[case_id])."""
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
    """One row in the benchmark cases list (layer-1 or layer-2)."""

    case_id: str
    family: str = "layer1"
    tier: str | None = None
    has_article_md: int
    has_gold_json: int
    has_semantic_gold: int = 0


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
    family: str = Field(default="layer1", description='Benchmark family: "layer1" or "layer2".')


class RunCreateResponse(BaseModel):
    """Response payload for POST /benchmark/runs."""

    run_id: str
    status: str


class RunListItem(BaseModel):
    """One row in the runs list."""

    run_id: str
    benchmark_family: str = "layer1"
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
def get_benchmark_cases_list(  # pylint: disable=too-many-locals
    family: str = Query(
        default="layer1",
        description="Fixture family: layer1 (article+gold.json) or layer2 (semantic_gold.json).",
    ),
    tier: str | None = Query(
        default=None,
        description="Tier filter: merge_safe, nightly_heavy (L1), nightly_semantic (L2).",
    ),
    q: str | None = Query(default=None, description="Optional substring match on case_id."),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> CasesListResponse:
    """List benchmark case directories available to the UI (layer-1 or layer-2)."""
    fam = (family or "layer1").strip().lower()
    if fam == "layer2":
        root = _fixtures_root_layer2()
        tiers = _load_case_tiers(root)
        case_dirs = discover_layer2_case_dirs(root, tier=tier)
        fam_label = "layer2"
    else:
        root = _fixtures_root_layer1()
        tiers = _load_case_tiers(root)
        case_dirs = discover_layer1_case_dirs(root, tier=tier)
        fam_label = "layer1"

    needle = (q or "").strip().lower()
    if needle:
        case_dirs = [p for p in case_dirs if needle in p.name.lower()]

    case_dirs = sorted(case_dirs, key=lambda p: p.name)
    slice_dirs = case_dirs[offset : offset + limit]

    items: list[CaseListItem] = []
    for d in slice_dirs:
        cid = d.name
        if fam_label == "layer2":
            sg = (d / "semantic_gold.json").is_file()
            article_ok = False
            if sg:
                try:
                    meta = json.loads((d / "semantic_gold.json").read_text(encoding="utf-8"))
                    rel = meta.get("article_path") or "article.md"
                    article_ok = (d / rel).resolve().is_file()
                except (OSError, json.JSONDecodeError, TypeError):
                    article_ok = False
            items.append(
                CaseListItem(
                    case_id=cid,
                    family=fam_label,
                    tier=_tier_for_case_id(cid, tiers),
                    has_article_md=int(article_ok),
                    has_gold_json=0,
                    has_semantic_gold=int(sg),
                ),
            )
        else:
            items.append(
                CaseListItem(
                    case_id=cid,
                    family=fam_label,
                    tier=_tier_for_case_id(cid, tiers),
                    has_article_md=int((d / "article.md").is_file()),
                    has_gold_json=int((d / "gold.json").is_file()),
                    has_semantic_gold=0,
                ),
            )

    return CasesListResponse(items=items, total=len(case_dirs))


@router.get("/benchmark/cases/{case_id}", response_model=CaseDetailResponse)
def get_benchmark_case_detail(
    case_id: str,
    family: str = Query(default="layer1", description='"layer1" or "layer2".'),
) -> CaseDetailResponse:
    """Return fixture contents: layer-1 article+gold, or layer-2 article + semantic_gold as gold."""
    fam = (family or "layer1").strip().lower()
    if fam == "layer2":
        root = _fixtures_root_layer2()
        tiers = _load_case_tiers(root)
        fixture_dir = root / case_id
        if not fixture_dir.is_dir():
            raise HTTPException(status_code=404, detail="case_not_found")
        sg_path = fixture_dir / "semantic_gold.json"
        if not sg_path.is_file():
            raise HTTPException(status_code=404, detail="case_incomplete")
        gold = json.loads(sg_path.read_text(encoding="utf-8"))
        rel = gold.get("article_path") or "article.md"
        article_path = (fixture_dir / rel).resolve()
        if not article_path.is_file():
            raise HTTPException(status_code=404, detail="article_not_found")
        article_md = article_path.read_text(encoding="utf-8")
        return CaseDetailResponse(
            case_id=case_id,
            tier=_tier_for_case_id(case_id, tiers),
            article_md=article_md,
            gold=gold,
        )

    root = _fixtures_root_layer1()
    tiers = _load_case_tiers(root)
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
    fam = (req.family or "layer1").strip().lower()
    if fam == "layer2":
        root = _fixtures_root_layer2()
        discover = discover_layer2_case_dirs
    else:
        root = _fixtures_root_layer1()
        discover = discover_layer1_case_dirs

    if isinstance(req.case_ids, str):
        selector = req.case_ids.strip()
        if selector == "all":
            return [p.name for p in discover(root)]
        if selector == "merge_safe":
            return [p.name for p in discover(root, tier="merge_safe")]
        if selector == "nightly_heavy":
            tier = "nightly_semantic" if fam == "layer2" else "nightly_heavy"
            return [p.name for p in discover(root, tier=tier)]
        if selector == "nightly_semantic":
            return [p.name for p in discover(root, tier="nightly_semantic")]
        raise HTTPException(status_code=400, detail="unknown_case_selector")

    allowed = {p.name for p in discover(root)}
    missing = [x for x in req.case_ids if x not in allowed]
    if missing:
        raise HTTPException(status_code=400, detail=f"unknown_case_ids:{missing}")
    return list(req.case_ids)


@router.post("/benchmark/runs", response_model=RunCreateResponse)
def create_benchmark_run(body: RunCreateRequest) -> RunCreateResponse:
    """Create and immediately start a benchmark run (layer-1 or layer-2)."""
    case_ids = _resolve_case_ids(body)
    fam = (body.family or "layer1").strip().lower()
    if fam not in ("layer1", "layer2"):
        raise HTTPException(status_code=400, detail="invalid_family")
    run_id = task_store.create_run(
        case_ids=case_ids,
        label=body.label,
        benchmark_family=fam,
    )
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
