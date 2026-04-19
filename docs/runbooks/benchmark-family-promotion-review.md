# Benchmark family promotion review (advisory → stronger gate)

Use this checklist when an **advisory** benchmark family has completed **mini → pilot** stabilization and the team wants to change policy (for example: mandatory nightly, merge-safe contract gate, or inclusion in primary `decision`).

## Preconditions

- **Core gate healthy:** `eval/results/benchmark-metrics-summary.md` shows acceptable `decision` for the primary lane (see [`benchmark-decision-gate.md`](benchmark-decision-gate.md)).
- **Family stability:** the family has a **frozen mini-pack** and a **pilot-pack** tier; failures are classifiable (gold vs extractor vs runtime vs infra).
- **Signal quality:** the family catches real regressions without chronic gold churn (track churn in PR history / fixture diffs).
- **Cost model:** runtime, secrets, and service dependencies are acceptable for the proposed enforcement tier.

## Promotion options (increasing strength)

1. **Advisory + documented expectation** (default): keep out of `decision`; require on release branches or weekly manual runs.
2. **Advisory + mandatory nightly:** still non-blocking for merge; must be green before tagging releases.
3. **Merge-safe contract only:** add a **fast** contract tier to merge CI; still avoid flaky live dependencies.
4. **Blocking for merge:** family participates in `decision` (requires explicit maintainer decision + code changes in [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) and [`benchmark-decision-gate.md`](benchmark-decision-gate.md)).

## Anti-patterns (do not promote when)

- The suite is mostly **mock** or **self-referential** (predictions copied from gold) *without* a parallel **live / graph-backed** lane for the same schema.
- Failures are dominated by **moving targets** (fingerprints, timestamps, model wording) rather than structured invariants.
- Gold lacks **holdout** separation while prompts/models are actively tuned on the same cases.

## Exit of this review

Record the outcome in the family spec header (status + policy) and, if applicable, update:

- [`benchmark-program-status.md`](benchmark-program-status.md)
- [`benchmark-decision-gate.md`](benchmark-decision-gate.md)
- [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py)

## Current snapshot (examples)

| Family | Typical enforcement today | Notes |
|--------|---------------------------|-------|
| Layer-1 / graph / layer-2 semantic | Core / blocking | Primary `decision` inputs |
| Retrieval | Advisory | Includes mock tiers + optional live mini-tier |
| Claims | Advisory | Start with harness-friendly packs; tighten match modes when wiring real extraction |
| References resolution | Advisory | Start with structural scoring harness; add Neo4j-backed resolver when ready |
