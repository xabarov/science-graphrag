# R7 — targeted ingestion repairs (triggered by R6 baseline)

**Role:** execution gate for **R7** in [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R7.  
**Dependency:** fill [`corpus-quality-baseline-after-agent-stabilization-2026-05.md`](./corpus-quality-baseline-after-agent-stabilization-2026-05.md) and
[`eval/results/corpus-quality-baseline-2026-05-13-manifest.json`](../eval/results/corpus-quality-baseline-2026-05-13-manifest.json) first.

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
