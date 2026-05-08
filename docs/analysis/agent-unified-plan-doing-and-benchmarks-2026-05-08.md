# Agent unified plan — доработки и бенчмарки (2026-05-08)

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

### Wave A — structural hardening after stabilisation

1. `writer_agent` -> terminal synthesis seam.
2. `runtime.py` split.
3. `retrieval_agent.py` split.
4. `tool_search.py` deeper split.
5. Проверка новых seam'ов через `tests/agent/` + live `trace-review-v1`.

### Wave B — v3 quality benchmark

1. Собрать frozen prompt set для `v3-quality`.
2. Определить JSON schema judge output.
3. Запустить advisory `LLM-as-a-judge` lane для `react` vs `v3`.
4. Добавить compare script / summary artifact.
5. Вписать lane в `benchmark-program-status.md` как advisory family.

### Wave C — promotion / rollout discipline

1. Определить KPI для `v3`:
   - `tool_loop_repeat_max`
   - `latency_p95_ms`
   - `final_answer_missing_count`
   - `missing_span_count`
   - judge score deltas vs ReAct
2. Обновить decision-gate / benchmark-program-status при готовности promotion.
3. После стабилизации judge lane решить, остаётся ли ReAct baseline обязательным compare-run'ом для каждой крупной волны.

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
- пока: engineering gates + live trace-review;
- next wave: advisory `LLM-as-a-judge` benchmark для `v3-quality`.

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
