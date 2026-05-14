"""Benchmark HTTP routes: fixture catalog, case payloads, graph snapshot preview."""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query, Request

from eval.bench_common import (
    discover_graph_v1_case_dirs,
    discover_layer1_case_dirs,
    discover_layer2_case_dirs,
)
from science_graphrag.api.benchmark.case_load import collect_case_artifacts, load_case_bundle
from science_graphrag.api.benchmark.constants import GRAPH_SNAPSHOT_PREVIEW_MAX_BYTES
from science_graphrag.api.benchmark.schemas import (
    BenchmarkModelsResponse,
    CaseArtifactsResponse,
    CaseDetailResponse,
    CaseListItem,
    CasesListResponse,
    GraphSnapshotPreviewResponse,
)
from science_graphrag.api.benchmark_case_utils import (
    fixtures_root_graph_v1 as _fixtures_root_graph_v1,
)
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer1 as _fixtures_root_layer1
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer2 as _fixtures_root_layer2
from science_graphrag.api.benchmark_case_utils import (
    gold_has_graph_expectations as _gold_has_graph_expectations,
)
from science_graphrag.api.benchmark_case_utils import load_case_tiers as _load_case_tiers
from science_graphrag.api.benchmark_case_utils import (
    merge_case_tier_dicts as _merge_case_tier_dicts,
)
from science_graphrag.api.benchmark_case_utils import tier_for_case_id as _tier_for_case_id
from science_graphrag.api.benchmark_profiles import list_model_profiles
from science_graphrag.api.graph_snapshot_diff import (
    compare_graph_expectations_to_snapshot,
    extract_metrics_snapshot,
    snapshot_case_id,
)

router = APIRouter()


@router.get("/benchmark/cases", response_model=CasesListResponse)
def get_benchmark_cases_list(  # pylint: disable=too-many-locals
    family: str = Query(
        default="layer1",
        description="layer1, layer2, or graph (layer1 cases that have graph_expectations in gold).",
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
    elif fam == "graph":
        root = _fixtures_root_layer1()
        root_gv1 = _fixtures_root_graph_v1()
        tiers = _merge_case_tier_dicts(_load_case_tiers(root), _load_case_tiers(root_gv1))
        layer1_graph = [
            p for p in discover_layer1_case_dirs(root, tier=tier) if _gold_has_graph_expectations(p)
        ]
        gv1_graph = [
            p
            for p in discover_graph_v1_case_dirs(root_gv1, tier=tier)
            if _gold_has_graph_expectations(p)
        ]
        seen_names: set[str] = set()
        case_dirs = []
        for p in sorted(layer1_graph + gv1_graph, key=lambda x: x.name):
            if p.name in seen_names:
                continue
            seen_names.add(p.name)
            case_dirs.append(p)
        fam_label = "graph"
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
                    has_graph_expectations=0,
                ),
            )
        elif fam_label == "graph":
            items.append(
                CaseListItem(
                    case_id=cid,
                    family="graph",
                    tier=_tier_for_case_id(cid, tiers),
                    has_article_md=int((d / "article.md").is_file()),
                    has_gold_json=int((d / "gold.json").is_file()),
                    has_semantic_gold=0,
                    has_graph_expectations=1,
                ),
            )
        else:
            gexp = _gold_has_graph_expectations(d)
            items.append(
                CaseListItem(
                    case_id=cid,
                    family=fam_label,
                    tier=_tier_for_case_id(cid, tiers),
                    has_article_md=int((d / "article.md").is_file()),
                    has_gold_json=int((d / "gold.json").is_file()),
                    has_semantic_gold=0,
                    has_graph_expectations=int(gexp),
                ),
            )

    return CasesListResponse(items=items, total=len(case_dirs))


@router.get("/benchmark/models", response_model=BenchmarkModelsResponse)
def get_benchmark_models() -> BenchmarkModelsResponse:
    """List available model presets for the benchmark launcher UI."""
    items = list_model_profiles()
    return BenchmarkModelsResponse(items=items, total=len(items))


@router.get("/benchmark/cases/{case_id}", response_model=CaseDetailResponse)
def get_benchmark_case_detail(
    case_id: str,
    family: str = Query(default="layer1", description='"layer1", "layer2", or "graph".'),
    gold_source: str | None = Query(
        default=None,
        description='Optional gold selector for layer-1: "curated_gold" or "teacher_gold".',
    ),
) -> CaseDetailResponse:
    """Return fixture contents: layer-1 article+gold, or layer-2 article + semantic_gold as gold."""
    payload = load_case_bundle(case_id, family, gold_source=gold_source)
    return CaseDetailResponse(**payload)


@router.get(
    "/benchmark/cases/{case_id}/artifacts",
    response_model=CaseArtifactsResponse,
)
def get_benchmark_case_artifacts(
    case_id: str,
    family: str = Query(
        default="layer1",
        description='"layer1", "layer2", or "graph" (layer-1 cases with graph_expectations).',
    ),
) -> CaseArtifactsResponse:
    """List gold/article files available for a case (paths relative to repo root)."""
    payload = collect_case_artifacts(case_id, family)
    return CaseArtifactsResponse(**payload)


@router.post(
    "/benchmark/cases/{case_id}/graph-snapshot-preview",
    response_model=GraphSnapshotPreviewResponse,
)
async def post_graph_snapshot_preview(
    case_id: str,
    request: Request,
    family: str = Query(
        default="graph",
        description='Use "graph" (default) or "layer1" for cases with graph_expectations.',
    ),
) -> GraphSnapshotPreviewResponse:
    """Compare uploaded graph-benchmark JSON to fixture ``graph_expectations`` (size-limited body)."""
    raw = await request.body()
    if len(raw) > GRAPH_SNAPSHOT_PREVIEW_MAX_BYTES:
        raise HTTPException(status_code=413, detail="graph_snapshot_body_too_large")
    try:
        outer = json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=422, detail="invalid_json_body") from exc
    if not isinstance(outer, dict):
        raise HTTPException(status_code=422, detail="invalid_json_body")
    snap_doc = outer.get("graph_snapshot")
    if not isinstance(snap_doc, dict):
        raise HTTPException(status_code=422, detail="graph_snapshot_required")

    bundle = load_case_bundle(case_id, family, gold_source=None)
    gold = bundle.get("gold") or {}
    expectations = gold.get("graph_expectations") if isinstance(gold, dict) else None
    if not isinstance(expectations, dict):
        raise HTTPException(status_code=404, detail="case_has_no_graph_expectations")

    metrics_snap = extract_metrics_snapshot(snap_doc)
    compared = compare_graph_expectations_to_snapshot(expectations, metrics_snap)
    sid = snapshot_case_id(snap_doc)
    mismatch = bool(sid and sid != case_id)
    payload = {
        **compared,
        "opened_case_id": case_id,
        "snapshot_case_id": sid,
        "case_id_mismatch": mismatch,
    }
    return GraphSnapshotPreviewResponse(data=payload)
