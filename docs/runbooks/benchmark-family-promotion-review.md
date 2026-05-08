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
| Retrieval | Advisory | Mock tiers + live mini-tier; **Wave P** `workspace_scoped` + `judge_pilot` — advisory; promotion roadmap — `benchmark-decision-gate.md` §8.3 |
| Claims | Mixed | Harness / merge contract — **advisory**; **Wave O** production pilot `current-claims-production-pilot.json` — **core** в `decision_gate` (см. `benchmark-decision-gate.md` §8.1) |
| References resolution | Advisory | Synthetic + graph_stub harness in CI; **Neo4j `--resolver graph` lane** (Wave M) — advisory; **conditional core** после 7 зелёных ночей + promotion review (см. `benchmark-decision-gate.md` §8.2) |
| Agent tools (`agent_tools_v1`) | Advisory | Wave R: `current-agent-tools-mini.json` + `current-agent-tools-judge-pilot.json`; promotion только после стабильного nightly и holdout |
| Agent v3 quality judge (`agent_v3_quality_judge_v1`) | Advisory | Wave B: `current-agent-v3-quality-judge-{mini,pilot,holdout}.json`; pairwise lane поверх engineering gate; см. [`eval/agent_v3_quality/README.md`](../../eval/agent_v3_quality/README.md) |

## Checklist: Agent v3 quality judge (Wave B → stronger gate)

Использовать только после стабилизации **engineering** gate (`trace-review-v1`) и отдельного решения мейнтейнеров. См. [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](../analysis/agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md) §9.

### Preconditions

- [ ] **Frozen tiers:** `judge_mini`, `judge_pilot`, `judge_holdout` зафиксированы; holdout не пересекается с pilot.
- [ ] **Judge fingerprint:** в артефакте есть `judge_prompt_sha256` / `judge_prompt_version`; смена промпта = новое окно стабилизации.
- [ ] **Runtime truth:** при `subprocess` transport оба `SCIENCE_GRAPHRAG_AGENT_RUNTIME` ветвления подтверждены в `run_metadata`/`agent_runtime_label`; при `http` — задокументированы один или два API base.
- [ ] **Cost / variance:** judge LLM (`--llm-judge`) не даёт хронического drift на одном и том же snapshot без смены модели.

### Stabilization window (рекомендация из spec)

- [ ] Серия pilot-прогонов без «ломающей» judge-variance и без роста hard-fail у candidate относительно baseline (см. spec §9.2).

### Exit

- [ ] Запись в этом файле + [`benchmark-program-status.md`](benchmark-program-status.md); включение в `decision_gate` / `aggregate_benchmark_metrics.py` — **только** явным решением (как для других advisory → core переходов).

## Checklist: References resolution — graph resolver lane (Wave M → core)

Use when promoting the **Neo4j-backed** lane from advisory to **blocking / merge-safe** (or into primary `decision`). Aligns with [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8.2.

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

## Checklist: Retrieval — workspace-scoped + LLM-judge (Wave P → core)

Use when promoting **workspace-scoped retrieval** and/or **LLM-judge** from advisory into a **blocking** retrieval gate. Aligns with [`benchmark-decision-gate.md`](benchmark-decision-gate.md) §8.3.

### Preconditions

- [ ] **Core gate healthy:** primary `decision` acceptable with current backbone + claims production inputs.
- [ ] **Seeded workspaces stable:** `ws-pilot-od` / `ws-pilot-pdf` documented; `scripts/seed_benchmark_workspaces.py` idempotent; `_workspaces.json` is single source of truth for member `work_id` lists in gold.
- [ ] **Artifacts:** default paths `eval/results/current-retrieval-workspace-scoped.json` and `eval/results/current-retrieval-judge-pilot.json` produced by documented CLIs on the agreed stack.

### Stabilization window

- [ ] **14 consecutive nights** `workspace_scoped` suite `summary.all_passed = true` (live, not `--mock-answer`, unless policy explicitly allows mock for interim).
- [ ] **14 consecutive nights** judge pilot `mean_weighted_score ≥ 4.5/6` on the frozen rubric (`eval/retrieval/judge_prompt_v1.md`); prompt changes require a new fingerprint + restart window.
- [ ] **Holdout:** ~30% judge cases excluded from nightly `current-retrieval-judge-pilot.json`, evaluated weekly via `current-retrieval-judge-holdout.json` (mitigate overfit).

### Exit (same PR or follow-up)

- [ ] Update [`benchmark-program-status.md`](benchmark-program-status.md) and §8.3 in [`benchmark-decision-gate.md`](benchmark-decision-gate.md) if policy changes.
- [ ] If retrieval becomes blocking: extend [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) `_decision_gate` with explicit criteria (maintainer decision only).

## Checklist: Agent tools (Wave R → stronger gate)

### Preconditions

- [ ] `POST /v1/agent/query` стабилен на frozen mini-suite (`agent_tools_mini`) и не требует write-операций в graph/vector stores.
- [ ] `cypher_safety` policy и тесты атак зафиксированы; нет bypass через tool args.
- [ ] Артефакты `current-agent-tools-mini.json` и `current-agent-tools-judge-pilot.json` публикуются регулярно.

### Stabilization window

- [ ] 14 ночей подряд `agent_tools_mini` проходит (`tool_call_correctness ≥ 0.7`, `cypher_safety = 1.0`).
- [ ] 14 ночей подряд judge-пилот `mean_weighted_score ≥ 4.5/6`.
- [ ] Holdout: не менее 5 кейсов вне nightly snapshot, недельный прогон отдельно.

### Exit

- [ ] Обновить `benchmark-program-status.md` и `benchmark-decision-gate.md` (policy change).
- [ ] Если lane становится blocking — явно расширить `_decision_gate` в агрегаторе отдельным PR.
