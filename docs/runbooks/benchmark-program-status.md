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
| **Retrieval multi-hop mini (Wave Q)** | Precision/recall on `GET /v1/works/{id}/graph?depth=2` for frozen 2-hop cases | Tier `multihop_mini` under `tests/fixtures/benchmarks/retrieval/multihop_v1/`; CLI `science-graphrag-retrieval-multihop-benchmark`; default artifact `eval/results/current-retrieval-multihop-mini.json`; advisory until explicit promotion review |
| **Claims / epistemic (Wave H1, harness packs)** | Regression / contract / harness pilot | Advisory; [`ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md), `eval/claims/`; defaults: `current-claims-merge-contract.json`, `current-claims-mini-suite.json`, `current-claims-corpus-v2-mini.json`, `current-claims-pilot-suite.json` |
| **References resolution (v1 harness)** | Canonicalize bibliography strings → DOI / arXiv / `work_id` keys | Advisory; spec [`benchmark-family-references-resolution-v1.md`](../specs/benchmark-family-references-resolution-v1.md), `eval/references_resolution/`; default artifacts: `eval/results/current-references-resolution-contract.json`, `eval/results/current-references-resolution-mini.json` |
| **References resolution graph lane (Wave M)** | Neo4j-backed resolver (`--resolver graph`) on same schema | Advisory-only at the moment; latest `refs_mini` run (`current-references-resolution-graph-mini.json`) is red due to empty/missing graph seed in test stack (0 predictions). Keep contract-only policy until 7 green nights preconditions from promotion checklist are met |
| **Agent tools (Wave R)** | Tool-using retrieval agent (`/v1/agent/query`) + trace/judge | Advisory-only; artifacts: `current-agent-tools-mini.json`, `current-agent-tools-multiagent.json`, `current-agent-tools-judge-pilot.json`; promotion checklist in `benchmark-family-promotion-review.md` |
| **Agent v3 quality judge (Wave B)** | Pairwise answer quality: `langgraph_research_v1` vs `langgraph_supervisor_v3` + judge | **Advisory-only**; не входит в `_decision_gate`; CLI `science-graphrag-agent-v3-quality-benchmark`; артефакты `current-agent-v3-quality-judge-{mini,pilot,holdout}.json`, опционально `current-agent-v3-quality-judge-compare.json`; см. [`eval/agent_v3_quality/README.md`](../../eval/agent_v3_quality/README.md) |

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
