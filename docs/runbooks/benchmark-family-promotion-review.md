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
| References resolution | Advisory | Synthetic + graph_stub harness in CI; **Neo4j `--resolver graph` lane** (Wave M) — advisory; **conditional core** после 7 зелёных ночей + promotion review (см. `benchmark-decision-gate.md` §8.1) |

## Checklist: References resolution — graph resolver lane (Wave M → core)

Use when promoting the **Neo4j-backed** lane from advisory to **blocking / merge-safe** (or into primary `decision`). Aligns with [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8.1.

### Preconditions

- [ ] **Core gate healthy:** primary `decision` in `benchmark-metrics-summary` is acceptable (reference + nightly lanes as today).
- [ ] **Artifact path stable:** default `eval/results/current-references-resolution-graph.json` is produced by CI or nightly with the same CLI flags documented in the gate runbook.
- [ ] **Resolver contract frozen:** `eval/references_resolution/graph_resolver.py` behavior and fixture `expected_resolutions` in `tests/fixtures/benchmarks/references_resolution/` are reviewed; no silent broadening of match keys (DOI / arXiv / work_id only as spec’d).
- [ ] **Infra:** Neo4j pilot/staging has required `Work` nodes (DOI/arXiv/title fingerprint) so the lane is not flaky-empty; Bolt timeouts and empty-DB failures are classified separately from scoring fails.

### Stabilization window

- [ ] **7 consecutive nights** green: suite tier `refs_mini` (or agreed pilot tier) with `--resolver graph` (see `science-graphrag-references-resolution-benchmark` help for exact flag spelling in-repo).
- [ ] **No chronic infra fails:** no dominant class of Bolt timeout / auth / “zero rows” unrelated to resolver logic.

### Exit (same PR or follow-up)

- [ ] Record outcome in [`docs/specs/benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md) (status + enforcement).
- [ ] Update [`benchmark-program-status.md`](benchmark-program-status.md) and §8 in [`benchmark-decision-gate.md`](benchmark-decision-gate.md) if policy changes.
- [ ] If lane becomes blocking: update [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) so `decision` incorporates the graph lane (explicit maintainer decision only).
