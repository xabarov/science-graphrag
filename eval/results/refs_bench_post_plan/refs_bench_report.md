# References benchmark — post-plan run (2026-04-08)

Source data: `refs_bench_summary.json` in this directory (15 cases in `references_benchmark_v1`).

## Modes run

- `heuristic_full` — `find_reference_section_spans` + `extract_references` on full document.
- `heuristic_scope` — same span; parse on references-scope text (synthetic heading prefix).
- `heuristic_bib_gold` — same span; `extract_references` only on gold bibliography line slice (fair count vs full-document noise).

LLM modes (`scope_llm`, `batched_llm`) were not executed in this run (no API key in environment). Re-run with keys set, e.g.:

`python scripts/run_references_benchmark.py --modes heuristic_full,heuristic_scope,heuristic_bib_gold,scope_llm,batched_llm`

## Aggregate means (15 cases)

| Mode | Mean span line IoU | Mean entry overlap F1 | Total wall (s) |
|------|-------------------:|----------------------:|---------------:|
| heuristic_full | 0.852 | 0.898 | 0.071 |
| heuristic_scope | 0.852 | 0.900 | 0.056 |
| heuristic_bib_gold | 0.852 | 0.903 | 0.054 |

## Notable changes from the plan

1. **Level-A IoU** — Gold line set includes the `## References` heading when it sits above the first body line (possibly separated by blanks), matching heuristic spans that start after the heading line.
2. **`scope_llm` entry segmentation** — Predicted entries use `split_reference_entries` / style hints with fallback to `extract_references_from_bibliography_excerpt` (`eval/references_harness/scope_segmentation.py`).
3. **EOF span trim** — `find_reference_section_spans` stops before appendix/code/listing heuristics when there is no following markdown heading (including OCR `A A PPENDIX`).
4. **New gold** — Five manually verified fixtures: `deformable_detr_realpdf`, `retinanet_focal_realpdf`, `fpn_realpdf`, `cascade_rcnn_realpdf`, `dino_realpdf`.

## Limitations

- Author-year PDF markdown (e.g. deformable_detr) may still yield **zero** `extract_references` predictions on full text; span IoU can be good while entry F1 stays low until parsing improves.
- OCR noise (page numbers, repeated conference footers) remains inside some gold spans by design.
- Two-column PDF→MD and hyphenation still affect boundary heuristics.

## Production path

Per plan: choose baseline vs LLM scope vs batched LLM **after** running all modes with live API and reviewing per-stratum breakdowns in `refs_bench_summary.json`.
