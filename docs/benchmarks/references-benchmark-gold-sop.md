# SOP: `references_benchmark` gold (layer 1)

## Scope

Layer-1 fixtures live under `tests/fixtures/benchmarks/layer1/<case_id>/` with `article.md` and `gold.json`. The optional block `references_benchmark` ([`ReferencesBenchmarkGold`](../../eval/layer1/spec.py)) supports the references harness and agent suite (span line IoU, entry overlap F1).

## Line numbering

- Line numbers are **1-based** and **inclusive**.
- `bibliography.start_line` / `end_line` cover **reference entry lines only** — typically **exclude** the `## References` heading (see `GoldBibliographySpan` in `eval/layer1/spec.py`).
- Level-A IoU in the harness may extend the gold line set with the heading line when it immediately precedes the first entry; keep that contract when choosing spans.

## `annotation_kind`

- **`manual`**: `"\n".join(raw_entries)` must match the bibliography slice **after whitespace normalization** (`assert_references_benchmark_consistent` in `eval/references_harness/validate.py`).
- **`silver_heuristic`**: use when PDF→MD noise, footers, or author-year layout make strict reconstruction unreliable; bootstrap with `extract_references` on a synthetic heading + slice (see existing `detr_realpdf` / `cornernet_realpdf` in `scripts/build_references_benchmark_gold.py`).

## Bootstrap helper

[`eval/references_harness/bibliography_gold_span.py`](../../eval/references_harness/bibliography_gold_span.py) detects the main `## References` block for bracket-numbered CV-style lists:

- Truncates before `– Supplementary` / `# Supplementary`.
- Collects lines starting with `[n]` with **monotonic** `n` (stops when `n` drops, e.g. inline `[2]` in YOLOv3 rebuttal after `[21]`).
- Ends the span before junk lines (standalone short page numbers, `Figure …` at line start, detection-label noise, appendix titles like `A More …`).

Re-run after changing slicing rules; **committed `gold.json` remains authoritative** if hand-edited.

## Coverage report

From repo root:

```bash
.venv/bin/python scripts/report_references_benchmark_coverage.py
```

## Layer 2 (semantic)

Layer-2 benchmarks use `tests/fixtures/benchmarks/layer2/*/semantic_gold.json` and a different evaluation surface. Completing `references_benchmark` on layer 1 does **not** automatically update semantic gold; treat that as a separate pass if needed.
