"""Benchmark UI backend.

This router exposes benchmark fixtures, persistent run execution metadata,
and model-aware controls for the benchmark UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from eval.bench_common import (
    discover_graph_v1_case_dirs,
    discover_layer1_case_dirs,
    discover_layer2_case_dirs,
)
from eval.report_compare import (
    compare_reports,
    compare_result_to_markdown,
    normalize_api_run_for_compare,
)
from science_graphrag.api.benchmark_profiles import list_model_profiles
from science_graphrag.api.graph_snapshot_diff import (
    compare_graph_expectations_to_snapshot,
    extract_metrics_snapshot,
    snapshot_case_id,
)
from science_graphrag.api.task_store import RunPayloadTooLargeError, RunStatus, task_store

router = APIRouter()

# Guardrail for compare: very large runs can produce huge flattened metric diffs.
_MAX_COMPARE_CASE_ROWS = 2000

# Raw JSON body limit for graph snapshot preview (bytes).
_GRAPH_SNAPSHOT_PREVIEW_MAX_BYTES = 3 * 1024 * 1024


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _fixtures_root_layer1() -> Path:
    """Return fixtures root directory for layer-1 benchmark cases."""
    return _repo_root() / "tests" / "fixtures" / "benchmarks" / "layer1"


def _fixtures_root_layer2() -> Path:
    """Return fixtures root for layer-2 semantic benchmark cases."""
    return _repo_root() / "tests" / "fixtures" / "benchmarks" / "layer2"


def _fixtures_root_graph_v1() -> Path:
    """Graph-v1 benchmark cases (workspace projection expectations, etc.)."""
    return _repo_root() / "tests" / "fixtures" / "benchmarks" / "graph_v1"


def _resolve_graph_benchmark_fixture_dir(case_id: str) -> Path | None:
    """Layer-1 dir if present, else graph_v1 case directory (for catalog + detail)."""

    layer1 = _fixtures_root_layer1() / case_id
    if layer1.is_dir():
        return layer1
    gv1 = _fixtures_root_graph_v1() / case_id
    if gv1.is_dir():
        return gv1
    return None


def _teacher_gold_root_layer1() -> Path:
    return _repo_root() / "eval" / "teacher_gold" / "layer1"


def _teacher_gold_root_layer2() -> Path:
    return _repo_root() / "eval" / "teacher_gold" / "layer2"


def _rel_repo_path(path: Path) -> str:
    root = _repo_root().resolve()
    try:
        return str(path.resolve().relative_to(root))
    except ValueError:
        return str(path.resolve())


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


def _merge_case_tier_dicts(*maps: dict[str, list[str]]) -> dict[str, list[str]]:
    """Merge tier manifests (e.g. layer1 + graph_v1) without duplicate case_ids per tier."""
    out: dict[str, list[str]] = {}
    for m in maps:
        for tier, ids in m.items():
            bucket = out.setdefault(str(tier), [])
            seen = set(bucket)
            for cid in ids:
                c = str(cid)
                if c not in seen:
                    bucket.append(c)
                    seen.add(c)
    return out


def _tier_for_case_id(case_id: str, tiers: dict[str, list[str]]) -> str | None:
    """Find tier name for case_id using loaded tier mapping."""
    for tier, ids in tiers.items():
        if case_id in ids:
            return tier
    return None


def _gold_has_graph_expectations(fixture_dir: Path) -> bool:
    """True if layer-1 gold.json defines graph_expectations (graph-v1 benchmark)."""

    path = fixture_dir / "gold.json"
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    return bool(data.get("graph_expectations"))


def _build_article_sections(article_md: str) -> list[dict[str, Any]]:
    """Create a lightweight article outline for the workbench viewer."""
    lines = article_md.splitlines()
    sections: list[dict[str, Any]] = []
    for idx, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if not line.startswith("#"):
            continue
        label = line.lstrip("#").strip() or f"Section {len(sections) + 1}"
        section_id = label.lower().replace(" ", "_").replace("/", "_")
        sections.append({"id": section_id, "label": label, "start": idx, "end": len(lines)})
    if not sections:
        return [{"id": "document", "label": "Document", "start": 1, "end": max(len(lines), 1)}]
    for idx in range(len(sections) - 1):
        sections[idx]["end"] = max(sections[idx]["start"], sections[idx + 1]["start"] - 1)
    return sections


def _resolve_layer1_gold_path(
    case_id: str,
    gold_source: str | None,
    *,
    fixture_dir: Path | None = None,
) -> Path:
    base = fixture_dir or (_fixtures_root_layer1() / case_id)
    requested_source = (gold_source or "curated_gold").strip().lower()
    if requested_source == "teacher_gold":
        teacher_path = _teacher_gold_root_layer1() / case_id / "gold_teacher.json"
        if teacher_path.is_file():
            return teacher_path
    return base / "gold.json"


def _load_case_bundle(
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
            "article_sections": _build_article_sections(article_md),
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
    gold_path = _resolve_layer1_gold_path(case_id, gold_source, fixture_dir=fixture_dir)
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
        "article_sections": _build_article_sections(article_md),
        "gold": gold,
        "artifacts": {
            "article_md": True,
            "gold_json": (fixture_dir / "gold.json").is_file(),
            "teacher_gold": (_teacher_gold_root_layer1() / case_id / "gold_teacher.json").is_file(),
            "graph_expectations": bool(gold.get("graph_expectations")),
            "resolved_gold_path": str(gold_path.resolve()),
        },
    }


def _collect_case_artifacts(case_id: str, family: str) -> dict[str, Any]:
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
            "last_run_hints": task_store.find_last_run_hint_for_case(case_id, "layer2"),
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
        "last_run_hints": task_store.find_last_run_hint_for_case(case_id, fam_out),
    }


def _layer1_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    metrics = result.get("metrics") or {}
    gold_work = gold.get("work_metadata") or {}
    pred_work = predicted.get("work_metadata") or {}
    gold_auth = gold.get("authorships") or []
    pred_auth = predicted.get("authorships") or []
    gold_refs = gold.get("references") or {}
    pred_refs = predicted.get("references") or []
    failed_checks = [
        name
        for name, passed in (metrics.get("contract", {}).get("checks") or {}).items()
        if passed is False
    ]
    metadata_rows = [
        {
            "field": field_name,
            "gold_value": gold_work.get(field_name),
            "predicted_value": pred_work.get(field_name),
        }
        for field_name in ("title", "publication_year", "doi", "arxiv_id", "work_type")
    ]
    authorship_rows = []
    max_auth = max(len(gold_auth), len(pred_auth))
    for idx in range(max_auth):
        g_item = gold_auth[idx] if idx < len(gold_auth) else {}
        p_item = pred_auth[idx] if idx < len(pred_auth) else {}
        authorship_rows.append(
            {
                "position": idx + 1,
                "gold_name": g_item.get("name"),
                "predicted_name": p_item.get("author_raw_name"),
                "gold_affiliations": g_item.get("affiliations") or [],
                "predicted_affiliations": p_item.get("raw_affiliations") or [],
            }
        )
    reference_rows = [
        {
            "field": "predicted_count",
            "gold_value": gold_refs.get("expected_count"),
            "predicted_value": len(pred_refs),
        },
        {
            "field": "sample_arxiv_ids",
            "gold_value": gold_refs.get("sample_arxiv_ids") or [],
            "predicted_value": [ref.get("arxiv_id") for ref in pred_refs if ref.get("arxiv_id")],
        },
        {
            "field": "sample_dois",
            "gold_value": gold_refs.get("sample_dois") or [],
            "predicted_value": [ref.get("doi") for ref in pred_refs if ref.get("doi")],
        },
    ]
    return {
        "metadata_rows": metadata_rows,
        "authorship_rows": authorship_rows,
        "reference_rows": reference_rows,
        "failed_checks": failed_checks,
    }


def _layer2_comparison_payload(result: dict[str, Any]) -> dict[str, Any]:
    gold = result.get("gold") or {}
    predicted = result.get("predicted") or {}
    gold_methods = set(gold.get("expected_method_names_normalized") or [])
    gold_datasets = set(gold.get("expected_dataset_names_normalized") or [])
    pred_methods = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("methods") or [])
        if item.get("name")
    }
    pred_datasets = {
        str(item.get("name", "")).strip().lower()
        for item in (predicted.get("datasets") or [])
        if item.get("name")
    }
    method_rows = [
        {
            "value": name,
            "status": "match" if name in pred_methods else "miss",
            "source": "gold",
        }
        for name in sorted(gold_methods)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_methods - gold_methods)
    ]
    dataset_rows = [
        {
            "value": name,
            "status": "match" if name in pred_datasets else "miss",
            "source": "gold",
        }
        for name in sorted(gold_datasets)
    ] + [
        {"value": name, "status": "extra", "source": "predicted"}
        for name in sorted(pred_datasets - gold_datasets)
    ]
    return {"method_rows": method_rows, "dataset_rows": dataset_rows, "failed_checks": []}


def _build_evidence_links(case_id: str, benchmark_family: str) -> list[dict[str, Any]]:
    """Stable pointers for report / trace review (repo-relative paths, optional last-run hint)."""

    try:
        inv = _collect_case_artifacts(case_id, benchmark_family)
    except HTTPException:
        return []
    links: list[dict[str, Any]] = []
    fd = inv.get("fixture_dir_relative")
    if fd:
        links.append(
            {
                "id": "fixture_dir",
                "label": "fixture_directory",
                "path_relative_to_repo": fd,
            }
        )
    art = inv.get("article") or {}
    if art.get("path_relative_to_repo"):
        links.append(
            {
                "id": "article",
                "label": "article_md",
                "path_relative_to_repo": art["path_relative_to_repo"],
            }
        )
    for gv in inv.get("gold_variants") or []:
        if gv.get("present") and gv.get("path_relative_to_repo"):
            links.append(
                {
                    "id": f"gold_{gv.get('id', 'variant')}",
                    "label": str(gv.get("id", "gold")),
                    "path_relative_to_repo": gv["path_relative_to_repo"],
                }
            )
    sg = inv.get("semantic_gold")
    if isinstance(sg, dict) and sg.get("path_relative_to_repo"):
        links.append(
            {
                "id": "semantic_gold",
                "label": "semantic_gold",
                "path_relative_to_repo": sg["path_relative_to_repo"],
            }
        )
    lrh = inv.get("last_run_hints")
    if isinstance(lrh, dict) and lrh.get("run_id"):
        links.append(
            {
                "id": "last_completed_run",
                "label": "last_completed_run",
                "run_id": str(lrh["run_id"]),
            }
        )
    return links


def _append_diag_hints(issues: list[dict[str, Any]], diagnostics: dict[str, Any]) -> None:
    """Surface lightweight diagnostics as non-fatal hints (no trace URLs in current runners)."""

    if not diagnostics:
        return
    keys = (
        "metadata_source",
        "authorships_source",
        "references_source",
        "merged_reference_count",
        "extraction_llm_enabled",
    )
    snapshot = {k: diagnostics.get(k) for k in keys if diagnostics.get(k) is not None}
    if snapshot:
        issues.append({"kind": "diagnostics_hint", "severity": "info", "fields": snapshot})


def _build_inspector_highlights(
    *,
    benchmark_family: str,
    case_row: dict[str, Any],
    comparison: dict[str, Any],
    summary: dict[str, Any],
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    """Human-oriented summary for benchmark UI (keeps ``comparison`` for backwards compatibility)."""

    fam = (benchmark_family or "layer1").strip().lower()
    status = str(case_row.get("status") or "")
    issues: list[dict[str, Any]] = []
    summary_failed = [str(x) for x in (summary.get("failed_checks") or []) if x is not None]
    cmp_failed = [str(x) for x in (comparison.get("failed_checks") or []) if x is not None]
    failed_checks = sorted({*summary_failed, *cmp_failed})

    if failed_checks:
        issues.append(
            {
                "kind": "failed_check",
                "severity": "error",
                "checks": failed_checks,
            }
        )

    if status and status.lower() not in {"ok", "passed", "completed"}:
        err = case_row.get("error_message")
        issues.append(
            {
                "kind": "case_status",
                "severity": "error",
                "status": status,
                "message": err,
            }
        )

    if fam == "layer1":
        for row in comparison.get("metadata_rows") or []:
            field = row.get("field")
            gv = row.get("gold_value")
            pv = row.get("predicted_value")
            if gv != pv:
                issues.append(
                    {
                        "kind": "metadata_mismatch",
                        "severity": "warn",
                        "field": field,
                        "gold_value": gv,
                        "predicted_value": pv,
                    }
                )
        for row in comparison.get("authorship_rows") or []:
            if (row.get("gold_name") or None) != (row.get("predicted_name") or None):
                issues.append(
                    {
                        "kind": "authorship_mismatch",
                        "severity": "warn",
                        "position": row.get("position"),
                        "gold_name": row.get("gold_name"),
                        "predicted_name": row.get("predicted_name"),
                    }
                )
        for row in comparison.get("reference_rows") or []:
            field = row.get("field")
            gv = row.get("gold_value")
            pv = row.get("predicted_value")
            if gv != pv:
                issues.append(
                    {
                        "kind": "reference_mismatch",
                        "severity": "warn",
                        "field": field,
                        "gold_value": gv,
                        "predicted_value": pv,
                    }
                )
    elif fam == "layer2":
        misses = [r for r in (comparison.get("method_rows") or []) if r.get("status") == "miss"]
        extras = [r for r in (comparison.get("method_rows") or []) if r.get("status") == "extra"]
        if misses:
            issues.append(
                {
                    "kind": "layer2_missing_methods",
                    "severity": "warn",
                    "count": len(misses),
                    "sample": [m.get("value") for m in misses[:8]],
                }
            )
        if extras:
            issues.append(
                {
                    "kind": "layer2_extra_methods",
                    "severity": "warn",
                    "count": len(extras),
                    "sample": [m.get("value") for m in extras[:8]],
                }
            )
        d_misses = [r for r in (comparison.get("dataset_rows") or []) if r.get("status") == "miss"]
        d_extras = [r for r in (comparison.get("dataset_rows") or []) if r.get("status") == "extra"]
        if d_misses:
            issues.append(
                {
                    "kind": "layer2_missing_datasets",
                    "severity": "warn",
                    "count": len(d_misses),
                    "sample": [m.get("value") for m in d_misses[:8]],
                }
            )
        if d_extras:
            issues.append(
                {
                    "kind": "layer2_extra_datasets",
                    "severity": "warn",
                    "count": len(d_extras),
                    "sample": [m.get("value") for m in d_extras[:8]],
                }
            )

    _append_diag_hints(issues, diagnostics)

    if not issues:
        headline = "No blocking issues detected from automated comparison."
    elif failed_checks:
        headline = f"Failed checks: {', '.join(failed_checks[:5])}" + (
            "…" if len(failed_checks) > 5 else ""
        )
    else:
        headline = f"{len(issues)} issue(s) detected — expand raw diff for details."

    return {
        "headline": headline,
        "failed_checks": failed_checks,
        "issues": issues,
        "family": fam,
    }


class CaseListItem(BaseModel):
    """One row in the benchmark cases list (layer-1, layer-2, or graph-v1 catalog)."""

    case_id: str
    family: str = "layer1"
    tier: str | None = None
    has_article_md: int
    has_gold_json: int
    has_semantic_gold: int = 0
    has_graph_expectations: int = 0


class CasesListResponse(BaseModel):
    """Response payload for GET /benchmark/cases."""

    items: list[CaseListItem]
    total: int


class CaseDetailResponse(BaseModel):
    """Response payload for GET /benchmark/cases/{case_id}."""

    case_id: str
    tier: str | None = None
    article_md: str
    article_sections: list[dict[str, Any]] = Field(default_factory=list)
    gold: dict[str, Any]
    artifacts: dict[str, Any] = Field(default_factory=dict)


class CaseArtifactArticle(BaseModel):
    """Article file pointer for a benchmark case."""

    path_relative_to_repo: str | None = None
    present: bool


class CaseGoldVariant(BaseModel):
    """One gold file variant (e.g. curated vs teacher)."""

    id: str
    filename: str
    path_relative_to_repo: str | None = None
    present: bool


class CaseSemanticGoldRef(BaseModel):
    """Layer-2 semantic gold file presence."""

    present: bool
    path_relative_to_repo: str | None = None


class CaseArtifactsResponse(BaseModel):
    """Response payload for GET /benchmark/cases/{case_id}/artifacts."""

    case_id: str
    family: str
    fixture_dir_relative: str | None = None
    article: CaseArtifactArticle
    gold_variants: list[CaseGoldVariant] = Field(default_factory=list)
    semantic_gold: CaseSemanticGoldRef | None = None
    semantic_gold_teacher: CaseSemanticGoldRef | None = None
    graph_expectations: bool = False
    last_run_hints: dict[str, Any] | None = None


class RunCreateRequest(BaseModel):
    """Request payload for POST /benchmark/runs."""

    case_ids: list[str] | str = Field(
        ..., description='Either a list of case_ids, or "all" / "merge_safe".'
    )
    label: str | None = None
    family: str = Field(default="layer1", description='Benchmark family: "layer1" or "layer2".')
    model_profile: str | None = None
    model_id: str | None = None
    base_url_override: str | None = None
    api_key_env_name: str | None = None
    gold_source: str | None = None
    threshold_profile: str | None = None


class RunCreateResponse(BaseModel):
    """Response payload for POST /benchmark/runs."""

    run_id: str
    status: str
    benchmark_family: str = "layer1"
    label: str | None = None
    run_config: dict[str, Any] = Field(default_factory=dict)


class RunListItem(BaseModel):
    """One row in the runs list."""

    run_id: str
    benchmark_family: str = "layer1"
    label: str | None = None
    status: str
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    run_config: dict[str, Any] = Field(default_factory=dict)
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


class RunSummaryResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/summary (no per-case result blobs)."""

    data: dict[str, Any]


class RunsCompareResponse(BaseModel):
    """Response payload for GET /benchmark/runs/compare."""

    data: dict[str, Any]


class RunCasesListResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/cases (paginated slim rows)."""

    data: dict[str, Any]


class RunCaseDetailResponse(BaseModel):
    """Response payload for GET /benchmark/runs/{run_id}/cases/{case_id}."""

    data: dict[str, Any]


class GraphSnapshotPreviewResponse(BaseModel):
    """Response payload for POST /benchmark/cases/{case_id}/graph-snapshot-preview."""

    data: dict[str, Any]


class BenchmarkModelProfileResponse(BaseModel):
    """One model preset available to the benchmark launcher."""

    profile_id: str
    label: str
    role: str
    family_support: list[str]
    model_id: str | None = None
    default_gold_source: str | None = None
    default_threshold_profile: str | None = None
    supports_custom_model_id: bool = False


class BenchmarkModelsResponse(BaseModel):
    """Response payload for GET /benchmark/models."""

    items: list[BenchmarkModelProfileResponse]
    total: int


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
    payload = _load_case_bundle(case_id, family, gold_source=gold_source)
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
    payload = _collect_case_artifacts(case_id, family)
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
    if len(raw) > _GRAPH_SNAPSHOT_PREVIEW_MAX_BYTES:
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

    bundle = _load_case_bundle(case_id, family, gold_source=None)
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
    if fam == "graph":
        raise HTTPException(
            status_code=400,
            detail="graph_benchmark_use_cli",
        )
    if fam not in ("layer1", "layer2"):
        raise HTTPException(status_code=400, detail="invalid_family")
    try:
        run_id = task_store.create_run(
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
    run = task_store.get_run(run_id)
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
    items = task_store.list_runs_summary()
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
    baseline = task_store.get_run(baseline_run_id)
    current = task_store.get_run(current_run_id)
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
    if len(b_cases) > _MAX_COMPARE_CASE_ROWS or len(c_cases) > _MAX_COMPARE_CASE_ROWS:
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
        run = task_store.get_run(run_id)
    except RunPayloadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from None
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunDetailResponse(data=run)


@router.get("/benchmark/runs/{run_id}/summary", response_model=RunSummaryResponse)
def get_benchmark_run_summary(run_id: str) -> RunSummaryResponse:
    """Return compact run payload for suite analytics (cases without result blobs)."""
    summary = task_store.get_run_summary(run_id)
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
    page = task_store.get_run_cases_page(run_id, offset=offset, limit=limit)
    if page is None:
        raise HTTPException(status_code=404, detail="run_not_found")
    return RunCasesListResponse(data=page)


@router.get("/benchmark/runs/{run_id}/cases/{case_id}", response_model=RunCaseDetailResponse)
def get_benchmark_run_case_detail(run_id: str, case_id: str) -> RunCaseDetailResponse:
    """Return workbench-ready case payload for a specific run and case."""
    run = task_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run_not_found")
    benchmark_family = run.get("benchmark_family") or "layer1"
    run_config = run.get("run_config") or {}
    bundle = _load_case_bundle(
        case_id,
        benchmark_family,
        gold_source=run_config.get("gold_source"),
    )
    case_row = next((item for item in run.get("cases", []) if item.get("case_id") == case_id), None)
    if case_row is None:
        raise HTTPException(status_code=404, detail="case_not_found_in_run")
    result = case_row.get("result") or {}
    comparison = (
        _layer2_comparison_payload(result)
        if benchmark_family == "layer2"
        else _layer1_comparison_payload(result)
    )
    diag = result.get("diagnostics") or {}
    highlights = _build_inspector_highlights(
        benchmark_family=benchmark_family,
        case_row=case_row,
        comparison=comparison,
        summary=case_row.get("summary") or {},
        diagnostics=diag if isinstance(diag, dict) else {},
    )
    evidence_links = _build_evidence_links(case_id, benchmark_family)
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
    ok = task_store.delete_run(run_id)
    if not ok:
        raise HTTPException(status_code=404, detail="run_not_found")
    return {"deleted": True, "run_id": run_id}
