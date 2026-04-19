# Benchmark policy: ontology expansion vs quality gates

This document complements [`benchmark-program-status.md`](benchmark-program-status.md) and [`benchmark-decision-gate.md`](benchmark-decision-gate.md). It answers: **when is it safe to expand ontology** in a benchmark-driven way, and **what “green” means** beyond the primary `GO` decision.

## Authoritative sources (do not fork mentally)

| Role | Path |
|------|------|
| Machine-readable gate snapshot | [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.json) |
| Human-readable gate snapshot | [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md) |
| GO / NO-GO rules | [`benchmark-decision-gate.md`](benchmark-decision-gate.md) |
| Core vs advisory map | [`benchmark-program-status.md`](benchmark-program-status.md) |
| Fixture + gold + metric rule | [`../benchmarks/benchmark-expansion-v1.md`](../benchmarks/benchmark-expansion-v1.md) |

## Definitions

### Core (merge-blocking decision inputs)

Today: **Layer-1 KG draft**, **Graph post-ingest**, **Layer-2 semantic (Method / Dataset)**. These families flip `decision` in `benchmark-metrics-summary.json`.

Policy: treat **LLM-on** runs as the quality reference for these families; merge CI may run faster/heuristic paths — see [`eval/README.md`](../../eval/README.md).

### Advisory (non-blocking today)

Examples: **Retrieval / `POST /v1/query`**, **Claims / epistemic (Wave H1)**, **References resolution (v1 harness)**.

Advisory lanes **must not** change `decision` until maintainers update [`benchmark-decision-gate.md`](benchmark-decision-gate.md) and [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py).

### “Ontology expansion is benchmark-ready”

A new ontology surface (node type, edge type, extraction stage output) is **benchmark-ready** when all of the following hold:

1. **Fixture + gold + metric exist** in-repo (same PR or the immediate follow-up), per [`benchmark-expansion-v1.md`](../benchmarks/benchmark-expansion-v1.md).
2. **Gold schema is versioned** (`schema_version` in `gold.json`) and the human `description` states provenance (corpus slice, excerpt bounds, adjudication notes).
3. **Tiers are explicit**: at least one **merge-safe / contract** tier (cheap CI) and a **mini-pack** tier (3–5 frozen cases) before widening to pilot/wide.
4. **Holdout policy is stated** for anything used to tune prompts/models (mark cases or tiers; do not tune on holdout rows).
5. **Scoring contract is extractor-agnostic enough** for the next step: benchmarks should survive swapping a deterministic harness for a real extractor without rewriting the entire gold set (use stable ids + normalized text rules as documented in the family spec).

### When “core is green” allows ontology expansion

If `decision` is **`GO`** (reference lane green and nightly suites green per [`benchmark-decision-gate.md`](benchmark-decision-gate.md)), the project may **start or continue ontology expansion** in parallel, gated by the checklist above.

If `decision` is **`CONDITIONAL-GO`**, expansion is allowed only with **classified** nightly debt (gold vs runtime vs mixed) and documented risk — same discipline as Wave B/C/D in [`benchmark-decision-gate.md`](benchmark-decision-gate.md).

### What “advisory green” does *not* mean

A green advisory lane is **not** automatically evidence that:

- production LLM extraction matches gold,
- Neo4j canonicalization is correct end-to-end,
- retrieval relevance is solved (fingerprints/trace are structural signals, not semantic relevance).

Treat advisory green as: **contract + frozen pack stability**, then tighten metrics and/or promote policy deliberately (see [`benchmark-family-promotion-review.md`](benchmark-family-promotion-review.md)).

## Practical sequencing (Wave H)

Aligned with [`../specs/ontology-wave-h-backlog.md`](../specs/ontology-wave-h-backlog.md):

1. Claims / evidence benchmark packs (mini → pilot → wide).
2. References resolution benchmark pack + harness, then graph-backed resolver.
3. Author / institution merge catalog families.
4. Automatic `Work` dedup automation **last** (highest operational risk).

## Related

- Claims family: [`../benchmarks/ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md)
- References family: [`../specs/benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md)
- Advisory runbook: [`benchmark-pilot-advisory-runs.md`](benchmark-pilot-advisory-runs.md)
