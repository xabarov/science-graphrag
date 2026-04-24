# Benchmark program status (living)

Single entry point for **what is authoritative today**, which benchmark families are **merge-blocking** vs **advisory**, and how **Wave H ontology expansion** is gated.

Ontology expansion policy (benchmark-ready definition + sequencing): [`benchmark-ontology-expansion-policy.md`](benchmark-ontology-expansion-policy.md).

Promotion checklist (advisory → stronger gate): [`benchmark-family-promotion-review.md`](benchmark-family-promotion-review.md).

## Authoritative baseline (decision gate)

- **Machine-readable:** [`eval/results/benchmark-metrics-summary.json`](../../eval/results/benchmark-metrics-summary.json)
- **Human-readable:** [`eval/results/benchmark-metrics-summary.md`](../../eval/results/benchmark-metrics-summary.md)

Rules for **GO / CONDITIONAL-GO / NO-GO** are in [`benchmark-decision-gate.md`](benchmark-decision-gate.md). As of the last committed summary refresh, **reference lane** (YOLOv1: layer1 + graph + layer2 semantic), **nightly** layer1/layer2 suites, and **claims production pilot** (`current-claims-production-pilot.json`, Wave O) feed **`decision_gate`** in [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py).

## Stable benchmark families (core)

| Family | Role | Artifacts / docs |
|--------|------|------------------|
| Layer-1 KG draft | Core extraction quality | `eval/layer1/`, `tests/fixtures/benchmarks/layer1/` |
| Graph post-ingest | Neo4j invariants | `eval/graph_v1/`, `graph_expectations` in layer1 `gold.json` |
| Layer-2 semantic (Method / Dataset) | Ontology v1 semantic slice | `eval/layer2/`, `tests/fixtures/benchmarks/layer2/` |
| Claims production LLM (Wave O) | Core `decision_gate` (pilot tier) | `eval/claims/`, `eval/results/current-claims-production-pilot.json`; см. [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8.1 |

Policy: **LLM-on** runs are the quality reference for these families; merge CI may use heuristics-only paths — see [`eval/README.md`](../../eval/README.md) and [`roadmap.md`](../roadmap.md) Phase 4.

## Advisory lanes (non-blocking for decision)

| Lane | Purpose | Notes |
|------|---------|--------|
| Retrieval / `POST /v1/query` | Grounding: trace, citations, optional chunk fingerprints | Advisory per [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8; mock suite for CI in [`eval/README.md`](../../eval/README.md) |
| **Live retrieval mini-tier** | Real stack checks on a **small frozen** question set | [`retrieval-live-tier-v1.md`](../benchmarks/retrieval-live-tier-v1.md); tier `live_corpus_mini`; default artifact: `eval/results/current-retrieval-live-corpus-mini.json` |
| **Retrieval workspace-scoped (Wave P)** | Workspace membership + forbidden-work leak checks | Tier `workspace_scoped` under `tests/fixtures/benchmarks/retrieval/workspace_scoped/`; seed `scripts/seed_benchmark_workspaces.py`; artifact `eval/results/current-retrieval-workspace-scoped.json`; promotion §8.3 |
| **Retrieval LLM-judge pilot (Wave P)** | Advisory rubric scores on frozen prompt | CLI `science-graphrag-retrieval-judge-benchmark`; `eval/results/current-retrieval-judge-pilot.json`; holdout strategy в [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8.3 |
| **Claims / epistemic (Wave H1, harness packs)** | Regression / contract / harness pilot | Advisory; [`ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md), `eval/claims/`; defaults: `current-claims-merge-contract.json`, `current-claims-mini-suite.json`, `current-claims-corpus-v2-mini.json`, `current-claims-pilot-suite.json` |
| **References resolution (v1 harness)** | Canonicalize bibliography strings → DOI / arXiv / `work_id` keys | Advisory; spec [`benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md), `eval/references_resolution/`; default artifacts: `eval/results/current-references-resolution-contract.json`, `eval/results/current-references-resolution-mini.json` |

These advisory lanes **must not** flip `decision` to NO-GO until maintainers update [`benchmark-decision-gate.md`](benchmark-decision-gate.md) and [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py). **Исключение:** production claims pilot уже в **`decision_gate`** (см. таблицу **Stable benchmark families** выше).

## Wave H ontology expansion — gate

Per [`ontology-wave-h-backlog.md`](../specs/ontology-wave-h-backlog.md):

- **No new Neo4j node types / edges in merge CI** without at least one **benchmark case** (or an agreed pilot rubric row) and a documented gold schema.
- **Claims** start from a **frozen mini-pack** under `tests/fixtures/benchmarks/claims/`, then **pilot** and **wide** packs per [`ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md) (expansion ladder).

## Expansion rule (all new surface)

From [`benchmark-expansion-v1.md`](../benchmarks/benchmark-expansion-v1.md): a new pipeline entity or relation should ship with **fixture + gold + metric** in the same change set or the immediately following one.

## Related runbooks

- [`benchmark-driven-dev-loop.md`](benchmark-driven-dev-loop.md)
- [`roadmap-next-waves.md`](roadmap-next-waves.md) (Waves E–H)
- [`benchmark-decision-gate.md`](benchmark-decision-gate.md)
