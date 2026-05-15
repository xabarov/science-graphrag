"""Stable evidence link pointers for benchmark inspector UI."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from science_graphrag.api.benchmark.case_load import collect_case_artifacts


def build_evidence_links(case_id: str, benchmark_family: str) -> list[dict[str, Any]]:
    """Stable pointers for report / trace review (repo-relative paths, optional last-run hint)."""

    try:
        inv = collect_case_artifacts(case_id, benchmark_family)
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
