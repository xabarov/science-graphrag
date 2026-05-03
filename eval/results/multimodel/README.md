# Multi-model benchmark outputs

Run from the repository root (requires keys in `.env` and `pip install -e .` in `.venv`):

```bash
.venv/bin/python scripts/run_multimodel_benchmark.py \
  --models openai/gpt-4o-mini,anthropic/claude-3.5-sonnet,mistralai/mistral-small-3.2-24b-instruct \
  --out-dir eval/results/multimodel
```

This writes one subdirectory per model slug and `summary.json` with `failed_count` for L1/L2 and mean per-case `claim_recall` for paraphrase pilot/holdout tiers.

`SCIENCE_GRAPHRAG_EXTRACTION_LLM_MODEL` is set for each run; the extraction pipeline reads it via `Settings` (see `science_graphrag/config.py`).

After regenerating extraction/graph/claims diagnostics artifacts, merge macro metrics into a report-facing snapshot:

```bash
.venv/bin/python scripts/enrich_multimodel_summary_for_report.py
```

Output: `summary-for-report.json` (does not overwrite `summary.json`).
