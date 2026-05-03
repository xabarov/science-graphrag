# Habr article — plan for June 2026

**Goal:** one more **credible measurement wave** and tighter prose for publication, building on May 2026 (claims v2 prompt, Appendix A contract, frozen JSON in `eval/results/habr-window-2026-05-*`).

**Non-goals:** full agent router redesign, large corpus expansion without gold refresh, metric redesign «for fairness».

---

## Tier A — article narrative (highest priority)

1. **Claims paraphrase — second iteration (pick one axis again)**  
   - May used **prompt-only** changes in `SYSTEM_BENCHMARK`. June: either **gold realism** (subset of `expected_claims` wording toward achievable production paraphrase — see backlog BT6) **or** **post-process** (dedup / merge of near-duplicate predictions) — not both in one wave.  
   - Re-run **`claims_pilot_v2`** + **`claims_holdout_v1`** with production extractor; pin new JSON + manifest row.  
   - **Target:** holdout macro-F1 **+0.03** vs May v2 (`~0.190` → `~0.22`) *or* honest write-up if barrier is gold semantics (cite failure table).

2. **Align multimodel story with current prompt**  
   - Table in §6 uses historical `eval/results/multimodel/` holdout slice; Mistral column F1 ≠ May macro by construction.  
   - Either **re-run** the three-model holdout with **current** `SYSTEM_BENCHMARK` text and update table + paths, **or** add a short boxed note «значения в таблице — микро-агрегат того прогона; актуальная линия — §4.1» and freeze the distinction in one paragraph (no new GPU if time-boxed).

3. **Failure analysis for readers**  
   - Move 2–3 cases from `eval/results/habr-window-2026-05-failure-analysis.md` into the article body as a **compact table** (gold one-liner → model output → error class).  
   - Optional: one **success** case where v2 helped vs baseline (diff JSON).

4. **Publication polish**  
   - Shorten §6 if Habr length cap; move long tables to appendix in repo (`docs/report/` or `eval/results/`).  
   - Replace placeholder `<@nickname>`; final GitHub URL check.  
   - Screens: one refreshed UI capture if the product changed since defense assets.

---

## Tier B — one downstream «signal» (if time after Tier A)

5. **`tool_search` ablation (single knob)**  
   - One of: low-signal cutoff, score band, or retrieval baseline merge — see Appendix A in [`docs/benchmarks/ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md).  
   - Measure **one** of: `agent_tools_mini` pass rate, or p95 from suite JSON — before/after only.

6. **Retrieval — one live or strict tier**  
   - If stack is up: `live_corpus_mini` before/after **one** retrieval tweak, one scalar (e.g. `passed` fraction or documented hit metric from runner).  
   - If not: keep `merge_safe_contract` + `--canned-answer` as regression smoke only (already fixed in May for mock signature).

7. **BT6 CLI exit code (optional engineering)**  
   - Today suite exits `1` when any case fails but JSON is written — confusing for CI. Optional flag `--no-fail-on-red-cases` or document «expect exit 1» in Appendix A.

---

## Weekly rhythm (suggested)

| Week | Focus |
|------|--------|
| 1 | Choose June claims axis; baseline = May v2 JSON as «before»; draft multimodel note or re-run plan |
| 2 | Implement axis; re-run pilot + holdout; update failure table + article §4.1 |
| 3 | Tier B (tool_search **or** retrieval); trim §6 for Habr |
| 4 | Pin artifacts; final read-through; OTUS footer + links |

---

## References

- Article draft: [`docs/report/habr-article-2026-04-29.md`](../report/habr-article-2026-04-29.md)  
- May window plan (archive): [`habr-article-experiment-window-plan-2026-05.md`](habr-article-experiment-window-plan-2026-05.md)  
- Benchmark contract: [`docs/benchmarks/ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md) Appendix A  
- May artifacts: `eval/results/habr-window-2026-05-manifest.txt`

**Raised:** 2026-06-01
