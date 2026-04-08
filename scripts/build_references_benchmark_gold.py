#!/usr/bin/env python3
"""
One-shot helper: populate ``references_benchmark`` in layer-1 ``gold.json`` files.

Run from repo root:
  .venv/bin/python scripts/build_references_benchmark_gold.py

Re-run after changing slicing rules; committed gold remains the source of truth.

Bootstrap for bracket-numbered real-PDF fixtures uses
``eval.references_harness.bibliography_gold_span`` (see
``docs/benchmarks/references-benchmark-gold-sop.md``).
Committed spans and ``raw_entries`` are summarized in
``scripts/references_benchmark_gold_manifest.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

from eval.references_harness.validate import split_reference_entries
from science_graphrag.ingestion.stages.references import extract_references

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "benchmarks" / "layer1"


def _silver_entries(block: str) -> list[str]:
    chunk = "# Synthetic\n\n## References\n\n" + block
    refs = extract_references(chunk)
    return [r.raw_reference.strip() for r in refs if (r.raw_reference or "").strip()]


def _merge_gold(case_id: str, rb: dict) -> None:
    path = FIXTURES / case_id / "gold.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["references_benchmark"] = rb
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("updated", case_id, "entries", len(rb["raw_entries"]))


def main() -> None:
    """Populate ``references_benchmark`` on tier ``references_benchmark_v1`` fixtures."""
    # --- merge_safe + yolov2 (strict / bracket) ---
    for case_id, start, end, style, strat in [
        ("doi_refs_heavy", 11, 15, "bracket_numbered", "doi_heavy"),
        ("arxiv_refs_heavy", 11, 16, "bracket_numbered", "arxiv_heavy"),
        ("noisy_layout_stub", 23, 25, "bracket_numbered", "noisy_layout"),
    ]:
        lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
        chunk = lines[start - 1 : end]
        entries = split_reference_entries(chunk, style)
        _merge_gold(
            case_id,
            {
                "bibliography": {"start_line": start, "end_line": end},
                "raw_entries": entries,
                "expected_count": len(entries),
                "stratum": strat,
                "annotation_kind": "manual",
                "notes": "Synthetic fixture; bracket-numbered segmentation.",
            },
        )

    for case_id, start, end, style, strat in [
        ("yolov1", 812, 945, "bracket_numbered", "numbered_cvpr_hyphenation"),
        ("yolov2_realpdf", 772, 839, "bracket_numbered", "numbered_cvpr_hyphenation"),
    ]:
        lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
        chunk = lines[start - 1 : end]
        entries = split_reference_entries(chunk, style)
        _merge_gold(
            case_id,
            {
                "bibliography": {"start_line": start, "end_line": end},
                "raw_entries": entries,
                "expected_count": len(entries),
                "stratum": strat,
                "annotation_kind": "manual",
                "notes": (
                    "Bracket [n] entries in ## References only; "
                    "count may differ from layer-1 references.expected_count "
                    "when body cites overlap."
                ),
            },
        )

    # atss: numbered author-line CVPR
    case_id = "atss_realpdf"
    start, end = 755, 980
    lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
    entries = split_reference_entries(lines[start - 1 : end], "bracket_numbered")
    _merge_gold(
        case_id,
        {
            "bibliography": {"start_line": start, "end_line": end},
            "raw_entries": entries,
            "expected_count": len(entries),
            "stratum": "long_numbered_cvpr",
            "annotation_kind": "manual",
            "notes": "Real PDF MD; bibliography lines exclude ## References heading.",
        },
    )

    # SSD: numeric dot
    case_id = "ssd_realpdf"
    start, end = 1263, 1316
    lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
    entries = split_reference_entries(lines[start - 1 : end], "numeric_dot")
    _merge_gold(
        case_id,
        {
            "bibliography": {"start_line": start, "end_line": end},
            "raw_entries": entries,
            "expected_count": len(entries),
            "stratum": "numeric_dot_embedded_noise",
            "annotation_kind": "manual",
            "notes": "Includes mid-list OCR noise lines; split on ^\\d+\\. ",
        },
    )

    # FCOS: bracket
    case_id = "fcos_realpdf"
    start, end = 817, 938
    lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
    entries = split_reference_entries(lines[start - 1 : end], "bracket_numbered")
    _merge_gold(
        case_id,
        {
            "bibliography": {"start_line": start, "end_line": end},
            "raw_entries": entries,
            "expected_count": len(entries),
            "stratum": "bracket_numbered_mixed",
            "annotation_kind": "manual",
            "notes": "Spans [1]–[34]; page-number-only lines omitted after last entry.",
        },
    )

    # DETR + CornerNet: silver (noisy PDF / footers / author-year)
    case_id = "detr_realpdf"
    start, end = 737, 851
    lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
    block = "\n".join(lines[start - 1 : end])
    entries = _silver_entries(block)
    _merge_gold(
        case_id,
        {
            "bibliography": {"start_line": start, "end_line": end},
            "raw_entries": entries,
            "expected_count": len(entries),
            "stratum": "numeric_dot_page_footers",
            "annotation_kind": "silver_heuristic",
            "notes": (
                "Silver: extract_references on synthetic heading + bibliography slice; "
                "footer lines inside slice may merge into adjacent entries."
            ),
        },
    )

    case_id = "cornernet_realpdf"
    start, end = 853, 1041
    lines = (FIXTURES / case_id / "article.md").read_text(encoding="utf-8").splitlines()
    block = "\n".join(lines[start - 1 : end])
    entries = _silver_entries(block)
    _merge_gold(
        case_id,
        {
            "bibliography": {"start_line": start, "end_line": end},
            "raw_entries": entries,
            "expected_count": len(entries),
            "stratum": "author_year_compact",
            "annotation_kind": "silver_heuristic",
            "notes": "Silver: author-year layout; human audit recommended for production gold.",
        },
    )


if __name__ == "__main__":
    main()
