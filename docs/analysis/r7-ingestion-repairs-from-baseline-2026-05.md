# R7 — targeted ingestion repairs (triggered by R6 baseline)

**Role:** execution gate for **R7** in [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R7.  
**Dependency:** fill [`corpus-quality-baseline-after-agent-stabilization-2026-05.md`](./corpus-quality-baseline-after-agent-stabilization-2026-05.md) and
[`eval/results/corpus-quality-baseline-2026-05-13-manifest.json`](../../eval/results/corpus-quality-baseline-2026-05-13-manifest.json) first.

## Decision table (after R6)

| Baseline signal | R7 slice (examples) | Stop |
|-----------------|---------------------|------|
| Claims BT6 pilot vs holdout drift | Structured executor standardization for claims | No widening until gold tiers reviewed |
| Retrieval BT2/BT4/BT5 regression | BGE-M3 acceptance + Qdrant seam per ADR-021 | Stop if runtime is the larger bottleneck |
| `paper_profile` null-rate high | Year/venue writeback + profile repair | Document thin corpus before deeper extractor churn |
| Dedup mismatch work/author/entity | Parity matrix: work × scan/ingest | One axis per PR |

## Non-goals

- No wide `ingestion/_pipeline_impl.py` refactor until R6 conclusion names ingestion as the bottleneck.
- Do not merge CV vs non-CV metrics in one headline.

## 2026-05-13 decision (from closed R6 live baseline)

- Current manifest hypothesis: `runtime` with R6 closure (`eval/results/corpus-quality-baseline-2026-05-13-manifest.json`) and explicit non-CV feasibility waiver (`docs/analysis/r6-non-cv-feasibility-waiver-2026-05-14.md`).
- Therefore R7 enters **hold mode**: no broad ingestion refactor in this cycle.
- Allowed now: only low-risk prep slices (instrumentation/runbook clarity) that do not change extraction behavior.

## Runtime-first blockers (R6 signals → prep focus, not ingestion churn)

These rows tie **R6 manifest artifacts** to **runtime / retrieval / agent** work that must move before widening R7 ingestion repairs. They do **not** authorize `_pipeline_impl` refactors or extractor churn.

| R6 signal (manifest key) | Symptom for product evidence | Prep slice (allowed now) | Ingestion slice (still **hold** until exit triggers) |
|--------------------------|------------------------------|--------------------------|------------------------------------------------------|
| `retrieval_bt4` | Hybrid/ablation shows **zero useful delta** — looks like runtime/seam or config, not corpus gap | Document BT4 repro + Qdrant/BGE seam checklist (ADR-021); add trace-review metric notes for hybrid path | BGE-M3 acceptance / index parity **only** after bottleneck flips |
| `citation_edge` | Citation / ref edge cases fail usability gates | Live-check / trace-review **citation** lane + writer/citation policy in agent runtime; extend compaction compare flags where relevant | Year/venue / `paper_profile` writeback stays deferred unless citation failures trace to ingest nulls with proof |
| `claims_bt6_pilot` vs `claims_bt6_holdout` | Holdout drift or suite infra noise (timeouts) | Claims executor **observability** + timeout guards in benchmark harness (already partially shipped); align golden vs holdout **documentation** | Structured claims ingest executor changes **one axis per PR** only after holdout is trustworthy |
| `retrieval_bt2` / `retrieval_bt5` | Retrieval judge or mini suites red | Keep retrieval regression **compare** lanes; runtime knobs and hybrid routing evidence | Corpus refresh / dedup parity **not** the first lever while `bottleneck_hypothesis=runtime` |

## Hold exit triggers (when R7 broad repairs may leave hold)

All of the following are **documentation + measurement** gates — not automatic code merges.

1. **Hypothesis flip (manifest):** update [`eval/results/corpus-quality-baseline-2026-05-13-manifest.json`](../../eval/results/corpus-quality-baseline-2026-05-13-manifest.json) (or successor dated manifest) so `bottleneck_hypothesis` is no longer `runtime`, with **two** independent artifacts (e.g. BT4 shows material delta after a **runtime** fix **and** citation-edge or claims holdout improves without only fixing the benchmark harness).
2. **Operator waiver:** explicit short doc (like the non-CV waiver) naming **one** ingestion axis to thaw, expected effect size, and rollback — still **no** wide pipeline refactor.
3. **R3 / E2 cache story:** if long-thread acceptance shows stable `side_llm_cache_read_ratio` (or agreed proxy) **and** trace-regression compare is green for the compaction lane, treat retrieval cost path as unblocked for **narrow** R7 rows tied to evidence (not blanket promotion).

Until (1) or (2) holds, keep R7 table §“Decision table (after R6)” in **hold**: ingestion repairs remain design-only except the low-risk prep column above.
