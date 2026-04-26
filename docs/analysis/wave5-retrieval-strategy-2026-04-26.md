# Wave 5 — retrieval & BT6 strategy (2026-04-26)

## Decision

1. **BT2 / BT4 signal (Path A vs Path B from master roadmap §10.3)**  
   **Primary:** **Path A** — follow [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md) **ADR-021** (OpenRouter `baai/bge-m3`, collection vector size, re-embed, reingest). This is the honest way to get non-zero hybrid MRR and better workspace-scoped citations without loosening gold.  
   **Fallback:** **Path B** — after **7 nightly** runs logging `mrr_delta` in CI or operator notes, if delta stays 0, promote `hybrid_ablation_live` to `fixture_consistency_only` in `scripts/aggregate_benchmark_metrics.py` **with an explicit `benchmark-trust-baseline.json` diff** (per §10.3).

2. **BT6 claims paraphrase — production extractor**  
   `--extractor production` on full `claims_pilot_v2` previously hit **completion length / JSON truncation** and **Instructor multi-tool-call** edge cases when the model emitted huge claim lists. Mitigations:  
   - `claims_extraction_max_tokens` upper bound **16384** when `force_benchmark=True` (see config + extractor).  
   - **Benchmark-only compact schema** in [`science_graphrag/ingestion/claims/extractor.py`](../../science_graphrag/ingestion/claims/extractor.py): when `force_benchmark=True`, Instructor uses `_ClaimsLLMResponseBenchmark` — **≤28** claims, **1** evidence each, shorter `quote` / `claim_text` caps, plus `_SYSTEM_BENCHMARK` instructing distinct high-signal claims only.  
   - **DONE 2026-04-26 — P0 quote tolerance (barrier 1):** [`science_graphrag/ingestion/claims/quote_match.py`](../../science_graphrag/ingestion/claims/quote_match.py) + 4-level `_quote_accepted` + нормализация `chunk.text` перед LLM; зеркало в [`eval/claims/article_source.py`](../../eval/claims/article_source.py). Подробности и замер `corpus_ssd_v2`: [`wave5-bt6-quote-tolerance-2026-04-26.md`](./wave5-bt6-quote-tolerance-2026-04-26.md).  
   **Next steps for `trust_signal.runtime_mode=live`:** rerun `science-graphrag-claims-paraphrase-benchmark --extractor production` on `claims_paraphrase_bt6_mini` then pilot; optional model with JSON mode / `extraction_llm_mode=json` if the provider supports it; gold realism — backlog **BT6 gold realism** в `refactor-backend.md`.

3. **Committed BT6 artifacts (interim)**  
   Tiers `claims_paraphrase_bt6_mini` and `claims_paraphrase_holdout_mini` in [`tests/fixtures/benchmarks/claims/case_tiers.json`](../../tests/fixtures/benchmarks/claims/case_tiers.json) feed `eval/results/current-claims-paraphrase-{pilot,holdout}.json` via **`--extractor oracle`** until production is stable — `trust_signal` remains **synthetic_gold** by design (`oracle_predictions` on cases).
