# BT6 quote tolerance (P0) — 2026-04-26

## Goal

Reduce false-negative quote rejection on PDF-derived `article.md` (hyphenation, `×` vs `x`, glued `For300`, footnote markers) without touching `gold.json`. Implementation: [`science_graphrag/ingestion/claims/quote_match.py`](../../science_graphrag/ingestion/claims/quote_match.py), 4-level `_quote_accepted` + normalized chunk input in [`science_graphrag/ingestion/claims/extractor.py`](../../science_graphrag/ingestion/claims/extractor.py), mirrored read path in [`eval/claims/article_source.py`](../../eval/claims/article_source.py).

## Case: `corpus_ssd_v2`

Command (single case dir, default extraction model from `Settings` unless `MAIN_LLM_MODEL` is set):

```bash
.venv/bin/science-graphrag-claims-paraphrase-benchmark \
  tests/fixtures/benchmarks/claims/corpus_ssd_v2 \
  --extractor production \
  --json-out /tmp/bt6_ssd_after_<model_slug>.json
```

## Metrics table (before vs after)

**Before (pre-P0, prior BT6 debugging session)** — diagnostics from runs where quote gate dropped almost everything on Mistral; Minimax retained a subset via legacy strict/jaccard only.

| Model | Phase | `raw_claims_from_llm` | `evidence_quote_strict` | `evidence_quote_strict_normalized` | `evidence_quote_fuzzy` | `evidence_quote_jaccard` | `dropped_claim_count_quote_rejected` | `predicted_count_plain` | `claim_recall` |
|-------|-------|----------------------:|--------------------------:|-------------------------------------:|-------------------------:|---------------------------:|---------------------------------------:|------------------------:|---------------:|
| `mistralai/mistral-small-3.2-24b-instruct` | before | 28 | 0 | — | — | 0 | 28 | 0 | 0.0 |
| `mistralai/mistral-small-3.2-24b-instruct` | after | 28 | 28 | 0 | 0 | 0 | 0 | 28 | 0.50 |
| `minimax/minimax-m2.7` | before | 20 | 6 | — | — | 0 | 14 | 6 | 0.0 |
| `minimax/minimax-m2.7` | after (plain) | 26 | 8 | 0 | 3 | 0 | 14 | 11 | 0.25 |

Notes:

- **Mistral after:** normalized article + normalized quotes align closely enough that the first gate (`strict`, legacy whitespace+lower substring) accepts all 28 evidence rows; `min_claim_recall` is still **0.55** — run **failed** gate with **0.50** recall (gold semantic mismatch / barrier 2), not quote throughput.
- **Minimax after:** `fuzzy_normalized` fired **3** times; distracted article run hit **InstructorRetryException** (truncated tool JSON + provider 400 on retry) — see `extraction_diagnostics_distracted` in `/tmp/bt6_ssd_after_minimax.json`. Re-run distracted lane when provider/instructor path is stable.

## Follow-up (barrier 2)

See backlog: **[OPEN] BT6 gold realism + optional embedding-soft quote fallback** in [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md).
