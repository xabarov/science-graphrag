"""Load benchmark fixture bundles and artifact inventories (HTTP-layer helpers)."""

from __future__ import annotations

import json
from typing import Any

from fastapi import HTTPException

from science_graphrag.api.benchmark.runtime import task_store as get_task_store
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer1 as _fixtures_root_layer1
from science_graphrag.api.benchmark_case_utils import fixtures_root_layer2 as _fixtures_root_layer2
from science_graphrag.api.benchmark_case_utils import load_case_tiers as _load_case_tiers
from science_graphrag.api.benchmark_case_utils import rel_repo_path as _rel_repo_path
from science_graphrag.api.benchmark_case_utils import (
    resolve_graph_benchmark_fixture_dir as _resolve_graph_benchmark_fixture_dir,
)
from science_graphrag.api.benchmark_case_utils import (
    teacher_gold_root_layer1 as _teacher_gold_root_layer1,
)
from science_graphrag.api.benchmark_case_utils import (
    teacher_gold_root_layer2 as _teacher_gold_root_layer2,
)
from science_graphrag.api.benchmark_case_utils import tier_for_case_id as _tier_for_case_id
from science_graphrag.api.benchmark_helpers import (
    build_article_sections,
    resolve_layer1_gold_path,
)


def load_case_bundle(
    case_id: str, family: str, *, gold_source: str | None = None
) -> dict[str, Any]:
    """Load article and gold payload for a benchmark case."""
    raw_fam = (family or "layer1").strip().lower()
    if raw_fam == "layer2":
        root = _fixtures_root_layer2()
        tiers = _load_case_tiers(root)
        fixture_dir = root / case_id
        if not fixture_dir.is_dir():
            raise HTTPException(status_code=404, detail="case_not_found")
        gold_path = fixture_dir / "semantic_gold.json"
        if not gold_path.is_file():
            raise HTTPException(status_code=404, detail="case_incomplete")
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
        rel = gold.get("article_path") or "article.md"
        article_path = (fixture_dir / rel).resolve()
        if not article_path.is_file():
            raise HTTPException(status_code=404, detail="article_not_found")
        article_md = article_path.read_text(encoding="utf-8")
        return {
            "case_id": case_id,
            "tier": _tier_for_case_id(case_id, tiers),
            "article_md": article_md,
            "article_sections": build_article_sections(article_md),
            "gold": gold,
            "artifacts": {
                "article_md": True,
                "semantic_gold": True,
                "teacher_gold": False,
            },
        }

    fixture_dir = _resolve_graph_benchmark_fixture_dir(case_id)
    if fixture_dir is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    tiers = _load_case_tiers(fixture_dir.parent)
    article_path = fixture_dir / "article.md"
    gold_path = resolve_layer1_gold_path(case_id, gold_source, fixture_dir=fixture_dir)
    if not article_path.is_file() or not gold_path.is_file():
        raise HTTPException(status_code=404, detail="case_incomplete")
    article_md = article_path.read_text(encoding="utf-8")
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    if raw_fam == "graph" and not gold.get("graph_expectations"):
        raise HTTPException(status_code=404, detail="case_has_no_graph_expectations")
    return {
        "case_id": case_id,
        "tier": _tier_for_case_id(case_id, tiers),
        "article_md": article_md,
        "article_sections": build_article_sections(article_md),
        "gold": gold,
        "artifacts": {
            "article_md": True,
            "gold_json": (fixture_dir / "gold.json").is_file(),
            "teacher_gold": (_teacher_gold_root_layer1() / case_id / "gold_teacher.json").is_file(),
            "graph_expectations": bool(gold.get("graph_expectations")),
            "resolved_gold_path": str(gold_path.resolve()),
        },
    }


def collect_case_artifacts(case_id: str, family: str) -> dict[str, Any]:
    """Build artifact inventory for a benchmark case (paths relative to repo root)."""
    raw_fam = (family or "layer1").strip().lower()
    if raw_fam == "layer2":
        root = _fixtures_root_layer2()
        fixture_dir = root / case_id
        if not fixture_dir.is_dir():
            raise HTTPException(status_code=404, detail="case_not_found")
        sg_path = fixture_dir / "semantic_gold.json"
        semantic_present = sg_path.is_file()
        article_path_str: str | None = None
        article_present = False
        if semantic_present:
            try:
                meta = json.loads(sg_path.read_text(encoding="utf-8"))
                rel = meta.get("article_path") or "article.md"
                apath = (fixture_dir / rel).resolve()
                article_present = apath.is_file()
                article_path_str = _rel_repo_path(apath if article_present else fixture_dir / rel)
            except (OSError, json.JSONDecodeError, TypeError):
                article_path_str = _rel_repo_path(fixture_dir / "article.md")
        teacher_path = _teacher_gold_root_layer2() / case_id / "semantic_gold_teacher.json"
        return {
            "case_id": case_id,
            "family": "layer2",
            "fixture_dir_relative": _rel_repo_path(fixture_dir),
            "article": {
                "path_relative_to_repo": article_path_str,
                "present": article_present,
            },
            "gold_variants": [],
            "semantic_gold": {
                "present": semantic_present,
                "path_relative_to_repo": _rel_repo_path(sg_path) if semantic_present else None,
            },
            "semantic_gold_teacher": {
                "present": teacher_path.is_file(),
                "path_relative_to_repo": (
                    _rel_repo_path(teacher_path) if teacher_path.is_file() else None
                ),
            },
            "graph_expectations": False,
            "last_run_hints": get_task_store().find_last_run_hint_for_case(case_id, "layer2"),
        }

    fixture_dir = _resolve_graph_benchmark_fixture_dir(case_id)
    if fixture_dir is None:
        raise HTTPException(status_code=404, detail="case_not_found")
    curated = fixture_dir / "gold.json"
    teacher = _teacher_gold_root_layer1() / case_id / "gold_teacher.json"
    article_p = fixture_dir / "article.md"
    graph_expectations = False
    if curated.is_file():
        try:
            data = json.loads(curated.read_text(encoding="utf-8"))
            graph_expectations = bool(data.get("graph_expectations"))
        except (OSError, json.JSONDecodeError, TypeError):
            graph_expectations = False
    if raw_fam == "graph" and not graph_expectations:
        raise HTTPException(status_code=404, detail="case_has_no_graph_expectations")
    fam_out = "graph" if raw_fam == "graph" else "layer1"
    gold_variants: list[dict[str, Any]] = [
        {
            "id": "curated_gold",
            "filename": "gold.json",
            "path_relative_to_repo": _rel_repo_path(curated) if curated.is_file() else None,
            "present": curated.is_file(),
        },
        {
            "id": "teacher_gold",
            "filename": "gold_teacher.json",
            "path_relative_to_repo": _rel_repo_path(teacher) if teacher.is_file() else None,
            "present": teacher.is_file(),
        },
    ]
    return {
        "case_id": case_id,
        "family": fam_out,
        "fixture_dir_relative": _rel_repo_path(fixture_dir),
        "article": {
            "path_relative_to_repo": _rel_repo_path(article_p) if article_p.is_file() else None,
            "present": article_p.is_file(),
        },
        "gold_variants": gold_variants,
        "semantic_gold": None,
        "semantic_gold_teacher": None,
        "graph_expectations": graph_expectations,
        "last_run_hints": get_task_store().find_last_run_hint_for_case(case_id, fam_out),
    }
