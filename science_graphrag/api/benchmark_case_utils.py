"""Shared path and fixture helpers for benchmark API routes."""

from __future__ import annotations

import json
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def fixtures_root_layer1() -> Path:
    return repo_root() / "tests" / "fixtures" / "benchmarks" / "layer1"


def fixtures_root_layer2() -> Path:
    return repo_root() / "tests" / "fixtures" / "benchmarks" / "layer2"


def fixtures_root_graph_v1() -> Path:
    return repo_root() / "tests" / "fixtures" / "benchmarks" / "graph_v1"


def resolve_graph_benchmark_fixture_dir(case_id: str) -> Path | None:
    layer1 = fixtures_root_layer1() / case_id
    if layer1.is_dir():
        return layer1
    gv1 = fixtures_root_graph_v1() / case_id
    if gv1.is_dir():
        return gv1
    return None


def teacher_gold_root_layer1() -> Path:
    return repo_root() / "eval" / "teacher_gold" / "layer1"


def teacher_gold_root_layer2() -> Path:
    return repo_root() / "eval" / "teacher_gold" / "layer2"


def rel_repo_path(path: Path) -> str:
    root = repo_root().resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


def load_case_tiers(root: Path) -> dict[str, list[str]]:
    tiers_path = root / "case_tiers.json"
    if not tiers_path.is_file():
        return {}
    raw = json.loads(tiers_path.read_text(encoding="utf-8"))
    out: dict[str, list[str]] = {}
    for key, value in raw.items():
        out[str(key)] = [str(x) for x in (value or [])]
    return out


def merge_case_tier_dicts(*maps: dict[str, list[str]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for mapping in maps:
        for tier, ids in mapping.items():
            bucket = out.setdefault(str(tier), [])
            seen = set(bucket)
            for case_id in ids:
                cid = str(case_id)
                if cid not in seen:
                    bucket.append(cid)
                    seen.add(cid)
    return out


def tier_for_case_id(case_id: str, tiers: dict[str, list[str]]) -> str | None:
    for tier, ids in tiers.items():
        if case_id in ids:
            return tier
    return None


def gold_has_graph_expectations(fixture_dir: Path) -> bool:
    path = fixture_dir / "gold.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return bool(data.get("graph_expectations"))
