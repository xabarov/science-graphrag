# Corpus quality baseline after agent stabilization (2026-05)

**Role:** **R6** execution checklist from [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R6.  
**Machine-readable manifest:** [`eval/results/corpus-quality-baseline-2026-05-13-manifest.json`](../../eval/results/corpus-quality-baseline-2026-05-13-manifest.json) (`template_ready` — set `workspaces` + `artifacts` paths after runs; set `bottleneck_hypothesis` to `ingestion` \| `runtime` \| `mixed`).

## Preconditions

- Repo root; `.venv` active; [`long-running-ops`](../../.cursor/rules/long-running-ops.mdc) preflight (`config-check`, healthy compose for live benchmarks).
- Two workspaces: **one stable CV** and **one non-CV pilot** (if available). Never average CV vs non-CV in one headline number.

## Operator commands (paste paths into manifest)

Template only — replace workspace ids and output paths:

```bash
.venv/bin/science-graphrag config-check
# Example: claims BT6 pilot (live) — see eval/claims README for exact CLI
# Example: retrieval BT2 suite — see eval/retrieval README
# paper_profile null-rate: follow OD export + eval/paper_profile_stats entrypoint in backlog
# work dedup: science-graphrag work-dedup-report … > eval/results/work-dedup-<ws>-2026-05.json
```

Prefer **diagnostics** roots for large JSON: [`eval/results/diagnostics/README.md`](../../eval/results/diagnostics/README.md).

## Runs (per workspace)

Execute separately and record JSON + short notes under `eval/results/` (or `eval/results/diagnostics/` for large trees):

1. **Claims BT6** — pilot and holdout tiers distinct; `trust_signal.runtime_mode == live` for headline artifacts.
2. **Citation edge** benchmark (family per [`benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md)).
3. **Retrieval BT2 / BT4 / BT5** — live after BGE-M3 contour; see backlog ADR-021 closure criteria.
4. **`paper_profile` null-rate** — `eval/paper_profile_stats.summarize_paper_profile_payloads` on OD export snapshot.
5. **Work dedup** — `science-graphrag work-dedup-report` (and nightly artifact pattern if used).
6. **Author / entity dedup** — when ingest parity track ships; until then document “not measured”.

## Acceptance

- Pilot vs holdout not merged; CV vs non-CV not merged.
- Any headline/public metric update names **one** changed axis and points at manifest checksum/path.
- Conclusion paragraph: **larger bottleneck = ingestion/corpus vs runtime** (one sentence).

## 2026-05-13 closed baseline (live CV contour)

- Workspace: `ws-pilot-od` (stable live API `http://127.0.0.1:18787`).
- Artifacts:
  - `eval/results/r6-claims-pilot-2026-05-13.{json,md}`
  - `eval/results/r6-claims-holdout-suite-timeout-guard-2026-05-13.{json,md}` (suite heartbeat + timeout guard; no silent hang)
  - `eval/results/r6-citation-edge-refs-mini-2026-05-13.{json,md}`
  - `eval/results/r6-retrieval-live-corpus-mini-2026-05-13.{json,md}` (BT2)
  - `eval/results/r6-retrieval-bt4-hybrid-ablation-2026-05-13.{json,md}` (BT4)
  - `eval/results/r6-retrieval-live-corpus-holdout-2026-05-13.{json,md}` + `eval/results/r6-retrieval-bt5-judge-holdout-2026-05-13.json` (BT5)
  - `eval/results/paper-profile-null-rate-od-snapshot.json`
  - `eval/results/r6-work-dedup-report-2026-05-13.json`
- Result:
  - BT2 retrieval live mini: pass.
  - BT4 hybrid ablation: 8/8 fail with `mrr_delta=0.0` (runtime/retrieval bottleneck signal).
  - BT5 holdout judge: pass (`mean_weighted_score=6.7`, `all_passed=true`).
  - Claims pilot: pass; claims holdout aggregate: fail (`pass_count=1/5`, `mean_claim_recall=0.10`).
  - Citation-edge refs mini (graph resolver): fail (`pass_count=1/3`).
- Manifest updated: `status=r6_closed_with_non_cv_waiver`, `bottleneck_hypothesis=runtime`.
- Operational stability note: claims holdout lane now has per-case heartbeat/timeout guard (`--per-case-timeout-seconds`) and emits machine-readable timeout failures instead of silent suite stalls.
- Baseline conclusion: for current contour the larger bottleneck remains runtime/retrieval behavior, not ingest write-path completeness.
- Non-CV residual closed by feasibility waiver:
  - `docs/analysis/r6-non-cv-feasibility-waiver-2026-05-14.md`
  - `eval/results/r6-non-cv-feasibility-waiver-2026-05-14.json`

## After baseline

- **R7** repairs only for axes that baseline flags (structured claims executor, year/venue writeback, dedup matrix); see [`r7-ingestion-repairs-from-baseline-2026-05.md`](./r7-ingestion-repairs-from-baseline-2026-05.md).
- Do not widen R7 refactors until this doc’s conclusion is filled in.
