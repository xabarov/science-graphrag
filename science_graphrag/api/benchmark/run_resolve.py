"""Resolve benchmark run creation selectors into concrete case id lists."""

from __future__ import annotations

from fastapi import HTTPException

from eval.bench_common import discover_layer1_case_dirs, discover_layer2_case_dirs
from science_graphrag.api.benchmark.schemas import RunCreateRequest
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer1 as _fixtures_root_layer1
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer2 as _fixtures_root_layer2


def resolve_case_ids(req: RunCreateRequest) -> list[str]:
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
