# [ARCHIVED] Snapshot after Wave 4 — Honesty close (2026-04-26 night)

> **Source:** extracted from `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §0 (2026-04-27 cleanup). For **current** gate numbers and next steps use [`../master-roadmap-and-refactor-plan-2026-04-25.md`](../master-roadmap-and-refactor-plan-2026-04-25.md) §10 and [`eval/results/benchmark-trust-baseline.json`](../../../eval/results/benchmark-trust-baseline.json). Wave 6 quality closure write-up: [`wave6-benchmarks-quality-2026-04-26.md`](./wave6-benchmarks-quality-2026-04-26.md).

This section was written **after the fact**, after Wave 4 closed on branch `wave4-honesty-close`. Truth source at capture time: `eval/results/benchmark-trust-baseline.json` + `benchmark-metrics-summary.{json,md}`.

**What Wave 4 closed:**

- **BT1 — honest `decision_gate`** DONE — `trust_signal`, `advisory_phantom_count`, etc. in aggregate metrics.
- **BT2** partial — live workspace-scoped runner; historical fails mixed Qdrant payload + small corpus (see master §10 when current).
- **BT4** partial — live hybrid ablation; honest zero MRR delta on small corpus.
- **BT5** DONE on corpus at the time — judge pilot + holdout.
- **BT6** oracle + **P0 quote gate** DONE — details in [`wave5-bt6-quote-tolerance-2026-04-26.md`](./wave5-bt6-quote-tolerance-2026-04-26.md).

**Backlog items spawned (see `docs/backlog/refactor-backend.md`):**

- Robust ingest orchestration (timeout / checkpoint / resume) — later marked DONE in master §10.1.
- Backfill `workspace_id` for unbounded `ws_full_corpus="*"` — later marked DONE in master §10.1.

**Historical `decision_gate` snippet (2026-04-26 night):**

```
decision_gate.decision = "CONDITIONAL-GO"
decision_gate.reason   = "all_nightly_passed;advisory_phantom_count=9"
```

**Update 2026-04-27 (same document era):** `current-agent-tools-judge-pilot.json` added; `advisory_phantom_count` dropped to 6 in a later baseline.

**Update (Wave 5 ops):** After full ingest + backfill, `benchmark-metrics-summary` showed NO-GO on judge pilot; unbounded Qdrant payload fixed — remaining BT2 reds were citations / ROUGE / abstain, not missing `workspace_ids`.
