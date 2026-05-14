"""Shared helpers for benchmark UI routes (keeps ``benchmark.py`` router thinner)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from science_graphrag.api.benchmark_case_utils import fixtures_root_layer1 as _fixtures_root_layer1
from science_graphrag.api.benchmark_case_utils import (
    teacher_gold_root_layer1 as _teacher_gold_root_layer1,
)


def build_article_sections(article_md: str) -> list[dict[str, Any]]:
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


def resolve_layer1_gold_path(
    case_id: str,
    gold_source: str | None,
    *,
    fixture_dir: Path | None = None,
) -> Path:
    """Resolve gold.json path for a layer1 benchmark case."""
    base = fixture_dir or (_fixtures_root_layer1() / case_id)
    requested_source = (gold_source or "curated_gold").strip().lower()
    if requested_source == "teacher_gold":
        teacher_path = _teacher_gold_root_layer1() / case_id / "gold_teacher.json"
        if teacher_path.is_file():
            return teacher_path
    return base / "gold.json"


__all__ = ["build_article_sections", "resolve_layer1_gold_path"]
