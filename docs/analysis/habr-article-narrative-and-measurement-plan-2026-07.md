# Habr article — narrative & measurement plan (July 2026+)

**Goal:** keep the Habr story **evidence-first**: pinned JSON, honest limitations, one axis per wave, and prose that matches what the repo actually measures.

**Replaces (archived in git history):** `habr-article-experiment-window-plan-2026-05.md`, `habr-article-plan-2026-06.md`.

**Primary article draft:** [`docs/report/habr-article-2026-04-29.md`](../report/habr-article-2026-04-29.md)

**Benchmark contract (claims paraphrase / BT6):** [`docs/benchmarks/ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md) — Appendix A

**Pinned artifacts:** `eval/results/habr-window-2026-05-manifest.txt`, `eval/results/habr-window-2026-06-manifest.txt`, `eval/results/habr-window-2026-07-manifest.txt` (gold-v2 + multimodel / RCA pointers)

**Raised:** 2026-07-01

---

## 1. Closeout — May 2026 experiment window

| Item | Status | Evidence |
|------|--------|----------|
| Claims paraphrase before/after (same protocol, one axis) | **Done** | Prompt-only v2 vs baseline in `habr-window-2026-05-*.json`; June wave added **post-process dedupe** + **live** re-run (`habr-window-2026-06-*.json`). |
| Single benchmark contract | **Done** | Appendix A in `ontology-claims-benchmark-v1.md` (splits, match modes, exit code `--no-fail-on-red-cases`, production dedupe path). |
| Failure analysis (2–3 cases) | **Done** | `eval/results/habr-window-2026-05-failure-analysis.md` + compact table in article §4.1 / §6. |
| Article checklist: frozen snapshot | **Done** | Manifests + git pin in `habr-window-2026-06-manifest.txt`. |
| `tool_search` ablation (narrow) | **Partial** | June A/B on `agent_tools_mini` (bands 1.35 vs 1.5) logged in `eval/results/habr-window-2026-06-tier-b-tool-search.txt` — useful as **negative / honest** signal (both 1/10 pass, latency differs); not a “win” narrative without deeper diagnosis. |
| Multimodel stability | **Addressed** | §6 table pinned to `eval/results/multimodel-2026-07/` (2026-07 re-run); disclaimer vs TL;DR headline (June live macro-F1) unchanged. |
| Retrieval: one tight benchmark | **Done** | `live_corpus_mini` 3/3 + `merge_safe_contract` mock in June manifest. |

---

## 2. Closeout — June 2026 plan

| Tier | Item | Status | Notes |
|------|------|--------|-------|
| A1 | Second claims iteration (one axis: post-process, not prompt+post together) | **Done** | Dedupe (token Jaccard ≥ 0.92) in scoring + production path; offline re-score isolates dedupe on May preds; live BT6 re-run shows larger lift. |
| A1 target | Holdout +0.03 vs May v2 (~0.19 → ~0.22) | **Met on live path** | Offline rescoring ≈ flat on holdout (expected — same LLM output); live holdout **~0.219** ≈ target. |
| A2 | Multimodel vs current prompt | **Done (note path)** | Re-run three models on current `SYSTEM_BENCHMARK` remains **optional**; article freezes the distinction. |
| A3 | Failure cases in article body | **Done** | Table from failure-analysis doc. |
| A4 | Publication polish | **Mostly done** | Long slot table moved to `docs/report/habr-article-appendix-metrics-table-2026-06.md`; GitHub link present. **Optional:** refresh UI screenshot if chat chrome changed materially. |
| B5 | `tool_search` downstream signal | **Done** | Same A/B + manifest row; interpret as env sensitivity / infra cost, not “quality up”. |
| B6 | Retrieval live or strict tier | **Done** | See June manifest. |
| B7 | BT6 exit code ergonomics | **Done** | `--no-fail-on-red-cases` documented in Appendix A + manifest. |

---

## 3. How this relates to `docs/analysis/` and the rest of the backlog

- **`docs/analysis/README.md`** lists long-lived product tracks (agent chat, graph UX, ingest, ontology roadmaps). The Habr line is **not** a substitute for those docs; it is a **short publication + measurement spine** so article numbers stay tied to `eval/results/` and Appendix A.
- **Ontology / benchmarks (engineering)** — [`ontology-extraction-benchmarks-plan.md`](ontology-extraction-benchmarks-plan.md) + trust-audit; this Habr plan only guards **what goes into the Habr draft** (live-only headlines, no pilot/holdout mixing).
- **`docs/report/habr-article-2026-04-29.md`** should remain the single reader-facing narrative; new waves add rows to manifests + **minimal** deltas in §4.1 / TL;DR.

---

## 4. Next level — what would elevate the article further

Prioritized for **credibility** and **reader memory** (not feature sprawl).

1. **Gold realism wave (alternative to another prompt tweak)** — **Done (May 2026 wave).** Five `expected_claims` rows across `holdout_dino_v1`, `corpus_detr_v2`, `corpus_efficientdet_v2`; `schema_version: 3` + `meta.gold_v2_revision`; artifacts `eval/results/habr-window-2026-07-gold-v2-*.json` + `habr-window-2026-07-manifest.txt`; article §4.1 documents variance caveat (headline stays June live).

2. **Optional: multimodel re-run on *current* benchmark prompt** — **Done.**  
   Artifacts: `eval/results/multimodel-2026-07/` (Layer1/L2 + claims pilot/holdout × 3 models); article §6 + export updated to those numbers; `summary.json` / `summary-for-report.json` in same folder.

3. **`tool_search` → root cause, not only A/B** — **Done.**  
   RCA markdown + классификация провалов по сохранённому `tool_trace` (без нового LLM); черновик Habr §7.4 ссылается на материалы в репозитории без путей к файлам в тексте для Хабра. Детали и имена файлов — только во внутренних артефактах / манифесте.

4. **Statistical honesty on n=5 holdout** — **Done.**  
   Paragraph + numeric range from `habr-window-2026-06-live-holdout.json` in article §6 after «Принцип 3».

5. **Reproducibility UX** — **Done.**  
   Command block in article §6 (clone → venv → `config-check` → holdout BT6).

6. **Visual: one Phoenix or JSON excerpt** — **Done (JSON excerpt path).**  
   [`docs/analysis/_snippets/phoenix-trace-multistep-excerpt.json`](./_snippets/phoenix-trace-multistep-excerpt.json) + links in §3 (Observability) and §7.4 of the Habr draft.

7. **Habr-specific polish** — **Done.**  
   Method-first paragraph before TL;DR; title unchanged (already states honest eval).

**Explicit non-goals (unchanged):** full agent router redesign; large corpus expansion without gold refresh; rewriting all metrics “for fairness” without a versioned contract.

---

## 5. Suggested rhythm (optional)

| Week | Focus |
|------|--------|
| 1 | Pick one item from §4; freeze “before” JSON + manifest row |
| 2 | Implement / run; capture failure or success table |
| 3 | Patch article §4.1 / TL;DR + appendix paths only |
| 4 | Read-through; pin commit in manifest |

---

## 6. Related paths (quick)

| Kind | Path |
|------|------|
| Claims fixtures | `tests/fixtures/benchmarks/claims/` |
| Paraphrase diagnostics script | `scripts/report_claims_paraphrase_diagnostics.py` |
| Post-process dedupe | `eval/claims/prediction_postprocess.py` |
| June tool_search note | `eval/results/habr-window-2026-06-tier-b-tool-search.txt` |
| July 2026 tool_search RCA | `eval/results/habr-window-2026-07-tool-search-rca.md` |
| July 2026 multimodel re-run | `eval/results/multimodel-2026-07/` |
