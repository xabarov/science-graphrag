# Agent unified plan — доработки и бенчмарки (2026-05-08)

**Doc status:** `active`

**Read hint:** canonical agent/planning entrypoint. If unsure where to start, use this document first (or [`ACTIVE.md`](./ACTIVE.md)).

**Статус:** каноническая точка входа по оси **agent runtime / orchestration / trace-review / benchmark program**.

**Зачем этот документ:** собрать в одном месте:
- что уже закрыто по стабилизации и рантайму агента,
- какие доработки ещё остались,
- какими артефактами мы меряем качество,
- какой benchmark stack является обязательным,
- где нужен новый `LLM-as-a-judge` контур именно для `langgraph_supervisor_v3`.

Документ намеренно **не дублирует** длинные roadmap/runbook/ADR. Он задаёт:
- канонические ссылки,
- текущую очередь работ,
- правила измерения качества,
- порядок следующей волны.

---

## 1. Источники истины

| Тема | Канонический источник |
|------|------------------------|
| Общая навигация по `docs/analysis/` | [`README.md`](./README.md) |
| Agent runtime / tools / context roadmap | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) |
| Orchestration stabilization rationale | [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md) |
| Orchestration stabilization closeout | [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) |
| Baseline до стабилизации | [`orchestration-stabilization-baseline-2026-05-08.md`](./orchestration-stabilization-baseline-2026-05-08.md) |
| Agent eval / trace audit / Phoenix | [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) |
| Agent v3 quality judge benchmark spec | [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md) |
| Agent v3 quality benchmark implementation plan | [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md) |
| Trace-review runtime SOP | [`../runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) |
| Benchmark program status (core vs advisory) | [`../runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md) |
| Decision gate / GO-CONDITIONAL-NO-GO | [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) |
| Ontology / extraction / benchmarks entrypoint | [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md) |
| Live BT queue / trust queue | [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) |
| Structural `[OPEN]` items | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| Agent ADR spine | [`../adr/016-agent-tool-registry-and-langgraph.md`](../adr/016-agent-tool-registry-and-langgraph.md), [`../adr/020-langgraph-supervisor-multiagent.md`](../adr/020-langgraph-supervisor-multiagent.md), [`../adr/027-agent-trace-runtime-attribution.md`](../adr/027-agent-trace-runtime-attribution.md), [`../adr/028-agent-runtime-v3-subagents.md`](../adr/028-agent-runtime-v3-subagents.md), [`../adr/029-single-supervisor-backbone.md`](../adr/029-single-supervisor-backbone.md) |

---

## 2. Что уже стабилизировано

### 2.1 Orchestration / routing

Закрытая программа стабилизации:
- `RoutePlan` + `QuestionFeatures` стали основным routing-контрактом.
- `supervisor_node` больше не primary owner правил маршрута.
- `completion_state` проведён от specialists к planner/runtime.
- dev default runtime выровнен на `langgraph_supervisor_v3`.
- strict live compare `v3` vs `langgraph_research_v1` собран с Phoenix evidence.

Подробности и артефакты:
- rationale: [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md)
- baseline: [`orchestration-stabilization-baseline-2026-05-08.md`](./orchestration-stabilization-baseline-2026-05-08.md)
- итог: [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md)

### 2.2 Acceptance evidence

Канонические live артефакты этой волны:
- `eval/results/trace-review-acceptance-v3.json`
- `eval/results/trace-review-acceptance-v3.md`
- `eval/results/trace-review-acceptance-v3_phoenix_spans.jsonl`
- `eval/results/trace-review-acceptance-react.json`
- `eval/results/trace-review-acceptance-react.md`
- `eval/results/trace-review-acceptance-react_phoenix_spans.jsonl`
- `eval/results/trace-compare-v3-vs-react.json`
- `eval/results/trace-compare-v3-vs-react.md`

Ключевой вывод текущей волны:
- стабилизация **достигнута** как engineering baseline;
- дальнейшие работы нужны уже как **hardening / simplification / quality expansion**, а не как emergency fix программы оркестрации.

---

## 3. Остаточные работы по агенту

### 3.1 P0-P1: поддерживаемость и сужение ответственности

Эти пункты не отменяют stabilisation closeout, но важны для следующей безопасной итерации.

| Приоритет | Задача | Источник |
|-----------|--------|----------|
| P0 | Упростить `writer_agent` до terminal synthesis seam | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| P0 | Разбить `runtime.py` на deadline salvage / envelope / post-turn seams | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| P0 | Разбить `retrieval_agent.py` на specialist orchestration / forks / completion glue | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| P1 | Добить split `tool_search.py` (`discovery_merge`, `strict_deferred_telemetry`) | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| P1 | Дедуплицировать micro-helpers вокруг subagent runtime | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md), backlog |

### 3.2 P1-P2: runtime/product hardening

| Приоритет | Задача | Почему |
|-----------|--------|--------|
| P1 | Отдельно добить `writer_agent` oscillation-risk late-turn | чтобы writer оставался terminal boundary, а не вторым coordinator'ом |
| P1 | Удерживать `tool_loop_repeat_max` и latency drift на acceptance live | это главный runtime KPI после стабилизации |
| P1 | Продолжать trace-review discipline на каждую правку `agent/graph/*`, `agent/tool_*`, `agent_v2.py` | защита от скрытых regressions в trace/SSE/Phoenix |
| P2 | Свести delivery/ops knobs для agent tools в отдельный persisted settings slice | не смешивать operator knobs с LLM runtime overrides |

---

## 4. Benchmark stack: что у нас уже есть

### 4.1 Engineering-quality benchmark stack

Это уже существует и остаётся обязательным:

1. `trace-review-v1` / live acceptance  
   Канон: [`../runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md)

2. Decision gate / trust baseline по benchmark families  
   Канон: [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md)

3. Living status core/advisory benchmark lanes  
   Канон: [`../runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md)

4. Ontology / extraction / BT queue  
   Канон: [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md) + [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md)

### 4.2 Что этот стек хорошо меряет

- пропажу `final_answer`
- ошибки trace/SSE/Phoenix alignment
- missing spans / missing lifecycle rows
- routing churn (`tool_loop_repeat_max`)
- latency drift
- tool/runtime regression
- доверие к extraction / graph / layer2 benchmark families

### 4.3 Чего ему не хватает для `v3`

После стабилизации `langgraph_supervisor_v3` основной незакрытый вопрос уже не “не развалился ли runtime?”, а:

- стал ли ответ **лучше для пользователя**,
- лучше ли synthesis,
- лучше ли multi-hop reasoning,
- лучше ли compare / dual-evidence ответы,
- оправдан ли архитектурный overhead `v3` по latency/tokens.

Именно это старый stack меряет недостаточно.

---

## 5. Новый benchmark для `v3`: нужен ли LLM-as-a-judge

**Короткий ответ:** да, нужен новый benchmark, но **не вместо** текущего stack, а **поверх него**.

Детальная спецификация следующей волны: [`agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md`](./agent-v3-quality-llm-judge-benchmark-plan-2026-05-08.md).
Исполняемый engineering plan по файлам/CLI/runbook: [`agent-v3-quality-benchmark-implementation-plan-2026-05-08.md`](./agent-v3-quality-benchmark-implementation-plan-2026-05-08.md).

### 5.1 Правило

- Существующий trace-review + decision-gate stack остаётся **обязательным engineering gate**.
- Новый `LLM-as-a-judge` benchmark нужен как **product-quality gate** для `v3`.

### 5.2 Scope нового benchmark

Новый benchmark должен быть узким и продуктовым:

| Срез | Что проверяем |
|------|----------------|
| `workspace_stats` | correctness + conciseness |
| `catalog_resolution` | resolution accuracy + useful metadata synthesis |
| `quote_evidence` | groundedness + quote relevance |
| `dual_evidence_compare` | compare structure + balanced evidence + citation discipline |
| `relation_tracing` | structural correctness + explanation quality |
| `open research` | usefulness / synthesis / not-overclaiming |

### 5.3 Формат judge

Рекомендуемый минимальный контур:
- frozen набор кейсов (`30-50` prompts),
- два runtime режима: `react` и `v3`,
- pairwise judge (`A/B`) + rubric judge,
- machine-readable JSON output,
- human-readable markdown summary,
- compare against previous baseline.

### 5.4 Judge rubric

Минимальные оси:
- correctness
- completeness
- groundedness / citation faithfulness
- synthesis quality
- actionability / usefulness
- unnecessary verbosity

### 5.5 Promotion rule

Новый judge lane должен стартовать как **advisory**.

Повышать его до более жёсткого gate можно только после:
- нескольких стабильных прогонов,
- понятной rubric calibration,
- отсутствия сильной judge-variance на одной и той же frozen выборке.

Эта политика должна быть согласована с:
- [`../runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md)
- [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md)

---

## 6. Следующий план работ

### Wave A — structural hardening after stabilisation (**DONE**, 2026-05-08)

Execution checklist and closeout: [`wave-a-residual-structural-hardening-2026-05-08.md`](./wave-a-residual-structural-hardening-2026-05-08.md).

Delivered:
1. `writer_agent` narrowed to terminal synthesis seam.
2. `runtime.py` split into dedicated seams (`deadline_salvage`, `runtime_answer_salvage`, `runtime_post_turn`, `runtime_envelope`).
3. `retrieval_agent.py` split into specialist seams (`retrieval_subgraph`, `retrieval_completion`, `retrieval_fork_legs`).
4. `tool_search.py` deeper split (`tool_search_discovery_carryover`, `tool_search_strict_deferred`).
5. Verification: `tests/agent/` pass on Wave A patchset; live `trace-review-v1` remains operator runbook gate when dev stack is up.

### Wave B — v3 quality benchmark

**Статус:** реализовано в репозитории (advisory lane `agent_v3_quality_judge_v1`); live прогон — по runbook.

**Validation step (2026-05-09, operator evidence)**

- **Runner hardening:** `--progress` / `SCIENCE_GRAPHRAG_AGENT_V3_QUALITY_PROGRESS=1` — stderr-фазы по кейсу (`baseline_*`, `candidate_*`, `judge_*`) + in-process heartbeat в `one_shot` для долгих веток; в JSON suite — `baseline_outcome` / `candidate_outcome` (`branch_outcome_v1`) и rollup `cases_with_any_branch_non_ok` + счётчики статусов в `summary` (см. `eval/agent_v3_quality/branch_outcome.py`).
- **Повторный live `judge_pilot`:** `eval/results/current-agent-v3-quality-judge-pilot-live-v2.json` при `--subprocess-timeout-s 600` — `all_passed=true`, **0** веток с non-ok (против 3 execution-error кейсов в более раннем batched snapshot `…-pilot-live-batched.json` на timeout 120s). Сводка сравнения: `eval/results/current-agent-v3-quality-judge-pilot-batched-vs-v2-compare.{json,md}` — метрики pairwise/weighted **варьируются** между прогонами (ожидаемо при live LLM), зато **наблюдаемость и отсутствие batch-abort** подтверждены.
- **LLM-judge calibration subset (4 кейса):** `scripts/run_agent_v3_quality_llm_calibration_subset.py` → `eval/results/current-agent-v3-quality-judge-llm-calibration-subset.{json,md}`. На текущем срезе `agreement_winner_rate=0.5` (расхождение на `mini_dual_evidence_compare_01` и `mini_relation_tracing_01`) — **heuristic lane остаётся быстрым smoke**, LLM-judge — для продуктового среза и калибровки; promotion до жёсткого gate без стабилизации judge-variance не делаем.

**Код и фикстуры**

- Пакет: [`eval/agent_v3_quality/`](../../eval/agent_v3_quality/) (`runner`, `judge`, `judge_metrics`, `compare`, `one_shot`, `judge_prompt_v1.md`, [`README.md`](../../eval/agent_v3_quality/README.md)).
- Фикстуры: [`tests/fixtures/benchmarks/agent_v3_quality/`](../../tests/fixtures/benchmarks/agent_v3_quality/) + `case_tiers.json` (`judge_mini` / `judge_pilot` / `judge_holdout`, holdout не пересекается с pilot).
- CLI: `science-graphrag-agent-v3-quality-benchmark` (suite + `--mock-agent` для CI / `--transport subprocess|http` + `--llm-judge` опционально); `science-graphrag-agent-v3-quality-compare` для snapshot diff.
- Канонические артефакты: `eval/results/current-agent-v3-quality-judge-{mini,pilot,holdout,compare}.{json,md}`; пути в [`science_graphrag/artifacts/benchmark_paths.py`](../../science_graphrag/artifacts/benchmark_paths.py).

**Чеклист оператора (live)**

1. Pre-flight: `trace-review-v1` / acceptance зелёные на текущей ветке (engineering gate).
2. Поднять стек + `ws-pilot-od` (как для agent-tools / retrieval pilot).
3. `judge_mini`: `science-graphrag-agent-v3-quality-benchmark … --suite --tier judge_mini --transport subprocess --json-out eval/results/current-agent-v3-quality-judge-mini.json` (или два API base через `--candidate-api-base-url` при `--transport http`).
4. По расписанию: `judge_pilot` (основной advisory KPI), `judge_holdout` weekly; compare через `science-graphrag-agent-v3-quality-compare`.
5. Политика: lane **advisory-only** до promotion review; не меняет `decision_gate` автоматически.

**Документация runbook:** [`docs/runbooks/benchmark-program-status.md`](../runbooks/benchmark-program-status.md), [`docs/runbooks/benchmark-pilot-advisory-runs.md`](../runbooks/benchmark-pilot-advisory-runs.md), [`docs/runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md), [`docs/runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) §8.x.

### Wave C — promotion / rollout discipline

**Статус:** **DONE** (2026-05-09) — карта KPI, cadence, baseline/compare/fingerprint policy, promotion review flow и advisory visibility (`agent_v3_quality_family` в сводке) зафиксированы в runbook’ах и коде агрегатора; lane `agent_v3_quality_judge_v1` остаётся **advisory-only** до явного решения мейнтейнеров (см. [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)).

Wave C **не** заменяет engineering gate (`trace-review-v1`, Wave R agent-tools): он задаёт, как измерять и продвигать **продуктовое** качество `v3` поверх уже зелёного runtime.

**Operator evidence (2026-05-09, live `subprocess`, dev contour URL, `--subprocess-timeout-s 600`, `--progress`):**

- `judge_mini` → `eval/results/current-agent-v3-quality-judge-mini.{json,md}` — `all_passed=true`, `cases_with_any_branch_non_ok=0`
- `judge_pilot` → `eval/results/current-agent-v3-quality-judge-pilot.{json,md}` — то же (10 кейсов, wall ~11.5 min)
- `judge_holdout` → `eval/results/current-agent-v3-quality-judge-holdout.{json,md}` — то же (`holdout_open_01`)
- Пересборка сводки и trust baseline: `scripts/aggregate_benchmark_metrics.py … --write-trust-baseline eval/results/benchmark-trust-baseline.json` → `eval/results/benchmark-metrics-summary.{json,md}`; регрессия `tests/benchmarks/test_trust_baseline_regression.py` — зелёная

P0/P1 по коду агента (§3) остаётся отдельным backlog и **не** входит в закрытие Wave C.

#### C.1 Карта KPI (две оси)

| Ось | Источник | Что меряем |
|-----|----------|------------|
| **Engineering health** | `trace-review-v1` / acceptance артефакты, [`agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) | `tool_loop_repeat_max`, `latency_p95_ms` (или эквивалент из summary), `final_answer_missing_count`, `missing_span_count`, регрессии trace/SSE/Phoenix |
| **Product delta (pairwise vs ReAct)** | `agent_v3_quality_judge_v1` JSON `summary` + per-case rows | `mean_weighted_score_baseline` / `mean_weighted_score_candidate`, `mean_delta`, `pairwise_*_rate`, `hard_fail_count_*`, `cases_with_any_branch_non_ok`, `all_passed`, при необходимости `latency_ms` / `usage_total_tokens` по веткам |

**Draft promotion thresholds (до calibration / стабилизации judge — ориентиры, не merge-blocking):**

| Метрика (pilot, live subprocess, heuristic или согласованный LLM-judge) | Ориентир |
|------------------------------------------------------------------------|----------|
| `cases_with_any_branch_non_ok` | 0 на frozen `judge_pilot` для promotion-кандидата |
| `all_passed` | `true` |
| `mean_delta` | ≥ 0 (не хуже baseline по среднему weighted score) |
| `pairwise_candidate_win_rate` | ≥ `pairwise_baseline_win_rate` или явное обоснование, если baseline выигрывает чаще при лучшем groundedness |
| Judge variance | Нет «ломающего» расхождения heuristic vs LLM на calibration subset без смены промпта/модели (см. `scripts/run_agent_v3_quality_llm_calibration_subset.py`) |
| Stabilization window | Серия pilot-прогонов без деградации branch outcomes и без роста hard-fail у candidate vs baseline (детали — checklist в `benchmark-family-promotion-review.md`) |

Числа в **`benchmark-decision-gate.md` / `_decision_gate`** переносятся **только** после promotion review и явного PR (как для других advisory → core).

#### C.2 Cadence (ритм прогонов)

| Tier | Назначение | Типичный режим |
|------|------------|----------------|
| `judge_mini` | Быстрый контур; merge-safe **mock** (`--mock-agent`) | CI / без стека |
| `judge_mini` | Контракт + stack smoke | live `subprocess`, при необходимости `--progress`, timeout по умолчанию |
| `judge_pilot` | Основной **advisory KPI** для качества ответа vs ReAct | live `subprocess`, `--subprocess-timeout-s 600` (или выше), `--progress` |
| `judge_holdout` | Защита от overfit на pilot | **weekly** или **только на promotion review**; не подбирать промпты под holdout |
| Compare | Регрессия между снимками | `science-graphrag-agent-v3-quality-compare` → `current-agent-v3-quality-judge-compare.{json,md}` |

#### C.3 Baseline / compare / fingerprint

- **Frozen baseline:** хранить эталонный JSON (и MD) с фиксацией provenance: `run_metadata` (`tier`, `baseline_runtime`, `candidate_runtime`, `transport`, `mock_agent`, `judge_prompt_fingerprint`, `judge_prompt_sha256` / version).
- **Compare:** каждый значимый PR по агенту — diff текущего `judge_pilot` (или release snapshot) против baseline; артефакт compare — часть promotion evidence.
- **Judge fingerprint:** смена `judge_prompt_v1.md` или модели судьи → новый fingerprint → **сброс** stabilization window (как в checklist promotion review).
- **HTTP:** pairwise на **двух** API base; `--allow-http-single-base` только для smoke, **не** для promotion evidence.

#### C.4 Promotion review flow

1. Engineering gate зелёный (`trace-review-v1` / acceptance на ветке).
2. Прогон `judge_pilot` + зафиксированный compare vs baseline; при подготовке к усилению gate — `judge_holdout`.
3. Заполнить checklist в [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) (раздел Agent v3 quality judge).
4. **Exit:** запись outcome в promotion review + обновление [`benchmark-program-status.md`](../runbooks/benchmark-program-status.md); включение в `_decision_gate` / изменение `GO/NO-GO` — **отдельный** PR в [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) + [`benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) по решению мейнтейнеров.

#### C.5 Advisory visibility

Сводка [`aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) включает блок **`agent_v3_quality_family`** (если лежат canonical `eval/results/current-agent-v3-quality-judge-*.json`) — **только наблюдаемость**, без участия в `decision_gate`, пока политика не изменена явно.

#### C.6 ReAct baseline policy (зафиксировано для Wave C)

**По умолчанию:** pairwise baseline остаётся **`langgraph_research_v1` (ReAct)** как в контракте lane; полный `judge_pilot` / `judge_holdout` compare-run **обязателен для release train и для promotion review**, не обязателен на каждый мелкий PR (достаточно `judge_mini` mock + при необходимости узкий live smoke). Крупная волна по агенту (runtime / graph / writer) — **рекомендуется** полный pilot + compare к baseline snapshot.

---

## 7. Как этим пользоваться каждую неделю

Если вопрос звучит как:

**“Что делать по агенту дальше?”**
- начать с этого документа;
- затем смотреть backlog + `agent-runtime-tools-context-roadmap`.

**“Что сейчас является benchmark/gate truth?”**
- смотреть `benchmark-program-status.md` и `benchmark-decision-gate.md`.

**“Что уже закрыто по оркестрации?”**
- смотреть `orchestration-stabilization-closeout-2026-05-08.md`.

**“Что меряет качество `v3` как продукта?”**
- engineering gates + live trace-review;
- advisory pairwise lane `agent_v3_quality_judge_v1` + сводка `agent_v3_quality_family` в `benchmark-metrics-summary` (Wave C observability);
- promotion thresholds и усиление gate — только после checklist в `benchmark-family-promotion-review.md`.

---

## 8. Статус старых документов

| Документ | Новый статус |
|----------|--------------|
| [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) | детальный runtime roadmap |
| [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md) | historical rationale / design doc закрытой программы |
| [`orchestration-stabilization-closeout-2026-05-08.md`](./orchestration-stabilization-closeout-2026-05-08.md) | closeout evidence и acceptance artifacts |
| [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md) | entrypoint по benchmark/extraction оси |
| [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) | живая BT/trust очередь |

Этот документ должен использоваться как **верхнеуровневый master-plan**, а перечисленные файлы — как специализированные приложения и источники деталей.
