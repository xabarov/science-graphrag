# Orchestration stabilization plan — структурный долг и план работ (2026-05-07)

**Связано с** [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) и backlog [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md) (`[OPEN] Reduce supervisor route churn before writer handoff`, `[OPEN] Simplify writer_agent into terminal synthesis seam`, `[OPEN] Split permission / validation phase out of build_tool_execution_node`, `[OPEN] Split oversized tool_search.py`).

**Зачем этот документ.** Точечные фиксы маршрутизации на v3 acceptance-промптах (`v3_cv_fanout_dual_evidence`, ложный graph-intent на «citations», force first-hop, handoff-rule после `2× find_works + 2× paper_profile`) закрыли симптомы, но **не корневые причины** нестабильности. Здесь зафиксированы:

- результаты разбора (что именно нестабильно и почему — архитектурно vs операционно),
- целевая модель оркестрации (RoutePlan/Executor + типизация сигналов),
- план работ — **сначала архитектурные шаги**, затем «дожимающие».

Документ — `docs/analysis/`-уровня (ADR-light), не заменяет ADR; конкретные решения по API-контракту и feature-flag-ам должны переехать в ADR при сужении scope каждого шага.

> Терминология: «архитектурные» — меняют форму модулей или контракты между ними; «дожимающие» — закрываются точечной правкой без миграции вызывающих сторон.

---

## 1. Симптомы нестабильности (наблюдения за 2026-04 — 2026-05-07)

| Симптом | Где видно | Тип |
|---------|-----------|-----|
| Первый hop уходит в `graph_agent` на acceptance-промптах с подстрокой «citations» | live `tool_trace` v3, до фикса 2026-05-07 | архитектурный |
| `route_to_specialist → retrieval_agent` повторяется до writer (`tool_loop_repeat_max=11` в `trace-review-live-default-dev-v3-18787-postfix`) | trace-review default dev-v3 | архитектурный |
| `AgentGraphDeadlineExceeded` 240 s на полном dual-evidence пробе → успех на 420 s | in-container `agent.run` 2026-05-07 | операционный + структурный |
| `hybrid_v1` LLM может выставить `route_hint=graph_agent` на fuzzy `default_research_assumption`; first-hop force нужен поверх него | `coordination/turn_policy.py` + `supervisor.py` | архитектурный |
| HTTP `/v2/agent/query` в dev отдаёт `single_agent_research_v1` (`tool_trace` без `route_to_specialist`), acceptance — `langgraph_supervisor_v3`. Smoke на `:18787` показывает не тот режим, что тесты | `.env` + `agent_v2.py` | архитектурный (feature-flag fragmentation) |
| pylint R0911 (9 returns) / R0912 (13 branches) / R0915 (57 statements) в одной inner closure `supervisor_node` | `science_graphrag/agent/graph/supervisor.py:237` | структурный (size/responsibility) |

См. live-rollout note [`eval/results/runtime-v3-rollout-decision-2026-05-07.md`](../../eval/results/runtime-v3-rollout-decision-2026-05-07.md).

---

## 2. Анализ причин

### 2.1. Архитектурные

#### A. Конкурирующие источники истины для маршрута
В одном turn-е роль «куда первый hop» сейчас исполняют **четыре** независимых решения:

1. **Coordinator gate** ([`coordination/deterministic.py`](../../science_graphrag/agent/coordination/deterministic.py)): `narrow_deterministic_classify` / `rules_v0_classify` → `RouteHint`.
2. **TurnPolicy** ([`coordination/turn_policy.py`](../../science_graphrag/agent/coordination/turn_policy.py)): `rules_v0` / `hybrid_v1` / `llm_v1`. В режиме `hybrid_v1` LLM может **переопределить** `route_hint` для fuzzy-причин (`default_research_assumption`, `vague_scope_question`, `short_message_with_workspace`).
3. **LLM-роутер супервизора** ([`graph/supervisor.py:404-468`](../../science_graphrag/agent/graph/supervisor.py)): на каждом hop читает `specialist_results` и принимает решение «retrieval/graph/writer/FINISH».
4. **Эвристики паттернов вопроса** в `supervisor_node`: `_should_force_retrieval_first_hop_workspace_dual_evidence`, `_maybe_force_writer_after_retrieval`, и далее по мере появления acceptance-кейсов.

Любой слой может переопределить предыдущий, и каждая регрессия закрывается **новой защёлкой**, а не уточнением одной модели. Это **policy fragmentation**: добавление нового acceptance-кейса = +1 локальное правило в supervisor + +1 фикс в `_graph_intent_heuristic` + +1 тест.

**Следствие:** rate отказов на edge-промптах не сходится к нулю — он движется по «кротовой норе».

#### B. Хрупкие текстовые эвристики
Маркеры вида

```python
_DUAL_EVIDENCE_CATALOG_COMPARE_MARKERS = (
    "compare evidence", "compare two", "two different",
    "different title keywords", "distinct work_ids",
    "disagree on any factual point",
)
```

фактически биндят маршрут к **тексту acceptance-промпта**. То же со `_GRAPH_INTENT_HINTS` / `_GRAPH_CITATION_RELATIONISH`. Любая перефразировка в продакшене (или локализация в RU) уйдёт в graph по `hybrid_v1` LLM.

**Следствие:** долг не проходит в backlog отдельной строкой; накапливается как «скрытое поведение, спрятанное в substring-проверках».

#### C. Раздутые узлы графа со смешанными ответственностями

| Файл | LoC | Pylint claims |
|------|-----|----------------|
| `science_graphrag/agent/graph/supervisor.py` | 634 | R0911/R0912/R0915 в одной closure |
| `science_graphrag/agent/runtime.py` | 889 | R0914 (22 locals) в `_run_langgraph` |
| `science_graphrag/agent/graph/nodes/retrieval_agent.py` | 574 | смешано: prompts + ReAct edges + sidechain |
| `science_graphrag/agent/coordination/deterministic.py` | 240 | regex-паттерны вместе с классификатором |
| `science_graphrag/agent/coordination/turn_policy.py` | 194 | 3 классификатора + fallback |

`supervisor_node` сейчас держит: gating по `tool_policy`, force-handoff правила, чтение `route_hint`, semantic_fast_route, round cap, LLM-routing call, post-LLM normalization. **Любая правка маршрута трогает место, где живёт ещё пять других вещей.**

#### D. Несовместимые runtime-режимы под одним endpoint
Сейчас `/v2/agent/query` отдаёт два графа в зависимости от `Settings.agent_runtime`:

- `langgraph_research_v1` / `single_agent_research_v1` — ReAct, `final_answer` напрямую, **нет `route_to_specialist`** в trace,
- `langgraph_supervisor_v1` / `langgraph_supervisor_v3` — supervisor → specialists → writer.

Dev по `.env` стоит на одном, acceptance кейсы пишутся под другой. Smoke к `:18787` — не показатель того, что маршрут v3 действительно работает (что мы и наблюдали 2026-05-07: HTTP вернул `single_agent_research_v1` без `route_to_specialist`, in-container `agent.run` с явным `SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3` показал ожидаемый first-hop).

Roadmap §2.1.3 уже фиксирует этот долг — но как наблюдение, без плана сведения.

#### E. Long-tail latency как часть «нестабильности» оркестрации
Один зависший LLM-вызов в любом узле графа гарантированно «съедает» весь turn deadline (`agent_step_timeout_seconds`). 2026-05-07: 240 s — fail, 420 s — успех ~27 s. Нет:

- per-tool-call deadline (только глобальный),
- early-completion signals из retrieval («у меня уже есть минимальный bundle»),
- partial answer salvage за пределами writer (он есть, но активируется только если writer успел).

См. также `.cursor/rules/long-running-ops.mdc` (правило сформулировано после Wave 4 hang ровно про эту проблему на ingest-side).

### 2.2. «Дожимающие»

| Долг | Где | Усилие |
|------|-----|--------|
| `tool_loop_repeat_max` writer handoff (`catalog_resolution`) | `supervisor.py` | малое (one rule + test) |
| Writer simplification → terminal synthesis seam | `nodes/writer_agent.py` | малое-среднее |
| Pylint R0911/R0912/R0915 в supervisor closure | `supervisor.py` | малое (вынести `_compute_first_hop_decision`) |
| Dev runtime alignment (`SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3` в dev `.env` или явный flag в smoke-runner) | `.env*`, smoke-скрипты | малое |
| `[OPEN] Split permission/validation phase out of build_tool_execution_node` | `tool_execution_pipeline.py` | малое |

---

## 3. Целевая модель (ADR-light)

### 3.1. RoutePlan + Executor

Сейчас «маршрут» — **императивная цепочка** решений (`if route_hint == X: return ...`). Целевое — **декларативный план**:

```
RoutePlan = {
  steps: [RouteStep],          # упорядоченные специалисты с ожидаемыми completion-сигналами
  termination: TerminationRule,# когда переходить в writer или END
  replan_signal: Optional[str] # явный маркер для повторного построения
}

RouteStep = {
  specialist: "retrieval_agent" | "graph_agent" | "writer_agent",
  expected_completion: Set[CompletionSignal],   # типизированные, не подстроки
  budget_hint: int | None,
  reason: str,
}
```

- **Coordinator gate** (детерминизм) и **TurnPolicy LLM** становятся **двумя разными плановщиками** одной и той же сущности (`RoutePlan`), а не источниками разных решений.
- **Supervisor** перестаёт быть LLM-роутером по умолчанию — он **исполнитель плана** + early-termination check. LLM `replan` вызывается только когда `replan_signal` явно поднят (например, `retrieval_agent` сообщил `evidence_insufficient + needs_graph_traversal`).
- **`_should_force_*` латки** становятся правилами планировщика, а не ветками супервизора.

**Минимальный путь миграции**, без переписывания всего сразу:

1. Ввести `RoutePlan` + `RouteStep` как datatype в [`coordination/`](../../science_graphrag/agent/coordination/), сериализовать в `metadata.turn_policy.route_plan` (рядом с существующими полями).
2. `supervisor_node` начинает **читать** план, если он есть; если нет — текущее поведение.
3. Постепенно переносим существующие force-rules (`workspace_dual_evidence_first_hop`, `retrieval_completion_dual_evidence_compare`, `retrieval_completion_workspace_stats`) в правила планировщика (`build_route_plan(question, state)`), удаляя их из `supervisor_node`.
4. LLM-роутер становится **`maybe_replan(state, plan)`** и вызывается только при `replan_signal`.

**Acceptance:** `tool_loop_repeat_max` на default dev-v3 baseline снижается материально без новых ad-hoc эвристик в `supervisor_node`.

### 3.2. Типизированные сигналы вместо substring-проверок

Сейчас:

```python
if any(needle in q_norm for needle in _DUAL_EVIDENCE_CATALOG_COMPARE_MARKERS):
    ...
```

Целевое: **семантические признаки** на уровне coordinator (вычисляются один раз и кладутся в state):

```
QuestionFeatures = {
  has_workspace: bool,
  asks_for_compare: bool,
  asks_for_relations: bool,        # paths / cited / cypher
  asks_for_quotes: bool,
  asks_for_bibliography_format: "gost" | None,
  asks_for_n_works: int | None,    # 2 для dual-evidence
  language: "en" | "ru" | "mixed",
  ...
}
```

`build_route_plan(features, settings)` → `RoutePlan`. Substring-проверки остаются только **внутри** feature-extractor (одно место), а не размазаны по supervisor / coordinator / writer.

**Бонус:** перефразировки и RU-локализация acceptance-промптов перестают быть угрозой — они режутся в один feature-extractor, а не в три модуля.

### 3.3. Сужение runtime-режимов под одним endpoint

Два пути, из которых нужен **один выбор**:

- **Опция X (рекомендуется):** один backbone (`langgraph_supervisor_v3`) с feature-flag `agent_single_agent_react_mode`, который активирует упрощённую конфигурацию плана (writer-only after retrieval) — но не отдельный граф. Trace всегда содержит `route_to_specialist` (даже если их 1).
- **Опция Y:** разделить endpoint-ы (`/v2/agent/query` для supervisor, `/v2/agent/single` для ReAct). Плохо тем, что клиенты теперь должны выбирать и поддерживать оба.

Опция X согласуется с roadmap §2.1.3 (один canonical путь) и упрощает live/eval (один формат `tool_trace`).

### 3.4. Latency / partial answer

Минимальные шаги, не требующие переписывания LangGraph:

1. **Per-tool-call deadline** в `tool_execution_pipeline.py`: cap отдельно от global step timeout, чтобы один зависший LLM-tool не съедал весь turn.
2. **Early-completion signals** из retrieval: `specialist_results["retrieval_agent"]` уже содержит `evidence_origin/partial_failure` (см. Train T4 §11.4); добавить `completion_state: "minimal_bundle_ready"` для catalog-style вопросов, чтобы планировщик мог сразу пойти в writer.
3. **Расширить salvage:** сейчас ответ salvage-ится только из писательских черновиков / quote_candidates / graph_tool. Добавить salvage из **последнего успешного `paper_profile`/`find_works` пакета** при глобальном deadline.

Это не закрывает зависание LLM, но делает **degradation graceful**: вместо «turn умер» — частичный ответ + warning.

---

## 4. План работ

### Фаза 1 (архитектурная) — RoutePlan + типизация сигналов

> Цель: устранить policy fragmentation (§2.1.A) и хрупкие substring-эвристики (§2.1.B).

| Шаг | Описание | Приёмка |
|-----|----------|---------|
| 1.1 | `science_graphrag/agent/coordination/route_plan.py`: dataclass `RoutePlan` / `RouteStep` / `CompletionSignal` + сериализатор в `metadata.turn_policy.route_plan` | unit-тесты на сериализацию |
| 1.2 | `science_graphrag/agent/coordination/question_features.py`: feature-extractor, **единственное** место substring/regex-проверок (мигрировать `_DUAL_EVIDENCE_*`, `_GRAPH_INTENT_HINTS`, `_RESEARCHISH`) | unit-тесты на 10+ acceptance-промптов EN/RU |
| 1.3 | `build_route_plan(features, settings)` в `coordination/` (детерминистическая часть) → возвращает `RoutePlan` для текущих rules_v0 / narrow паттернов; supervisor умеет **читать** план, fallback на старое поведение если плана нет | новый ключ `metadata.turn_policy.route_plan`; trace остаётся обратно совместимым |
| 1.4 | Перенос force-rules (`workspace_dual_evidence_first_hop`, `retrieval_completion_dual_evidence_compare`, `retrieval_completion_workspace_stats`, `retrieval_completion_catalog_resolution`, `retrieval_completion_quote_evidence`) из `supervisor_node` в правила планировщика | существующие тесты `tests/agent/test_supervisor_routing.py` зелёные **без** правок логики, только импортов |
| 1.5 | LLM-роутер супервизора → `maybe_replan(state, plan)`; вызывается только при `replan_signal` или явном `route_hint=replan` | live: число LLM-роутинговых вызовов на default dev-v3 trace **снижается** |

**Архитектурное приёмочное условие фазы 1:** ни один новый acceptance-кейс **не требует** правок `supervisor_node` — только нового `RouteStep`/feature.

### Фаза 2 (архитектурная) — runtime alignment

> Цель: устранить feature-flag fragmentation (§2.1.D).

| Шаг | Описание | Приёмка |
|-----|----------|---------|
| 2.1 | ADR (1–2 страницы) о выборе X vs Y из §3.3 | merged ADR + dev/staging/prod flags синхронизированы |
| 2.2 | Реализация выбранного пути; в случае X — `agent_single_agent_react_mode` flag поверх supervisor backbone | smoke `/v2/agent/query` в dev/staging/acceptance показывает один формат `tool_trace` |
| 2.3 | `scripts/live_check/agent_trace_review.py` обновлён: `acceptance_summary_v1` гарантированно содержит `route_to_specialist` (если режим — supervisor) | acceptance `--suite acceptance` зелёный без runtime-warnings |

### Фаза 3 (архитектурная) — graceful degradation

> Цель: закрыть long-tail latency как причину «нестабильности» (§2.1.E).

| Шаг | Описание | Приёмка |
|-----|----------|---------|
| 3.1 | Per-tool-call deadline в `tool_execution_pipeline.py` (cap отдельно от global) | unit-тест на симулированный hang отдельного tool |
| 3.2 | `completion_state` в `specialist_results_v3` (`minimal_bundle_ready` / `evidence_insufficient` / `partial_failure_recoverable`) | планировщик читает; live: writer вызывается раньше для catalog-промптов |
| 3.3 | Salvage из последнего успешного `paper_profile`/`find_works` при глобальном deadline | regression-тест: turn с искусственным deadline отдаёт partial answer + warning, а не пустоту |

### Фаза 4 (архитектурная-структурная) — split раздутых узлов

> Цель: §2.1.C; снимает почву под повторное появление R0915/R0911 в одном файле.

| Шаг | Описание | Приёмка |
|-----|----------|---------|
| 4.1 | Вынести `_compute_first_hop_decision`, `_compute_post_retrieval_handoff`, `_compute_round_cap_decision` из `supervisor_node` в pure-функции в `graph/supervisor_decisions.py` | `supervisor.py` < 400 LoC; pylint без R0911/R0912/R0915 на module level |
| 4.2 | Закрыть backlog `[OPEN] Split permission/validation phase out of build_tool_execution_node` | tests `test_allowed_tools_matrix`, `test_agent_registry_permissions` зелёные |
| 4.3 | Закрыть backlog `[OPEN] Simplify writer_agent into terminal synthesis seam` (writer перестаёт делать tool_search/reroute в нормальных flow) | live-traces: меньше поздних writer/retrieval осцилляций |
| 4.4 | Закрыть backlog `[OPEN] Split oversized tool_search.py` (rules / discovery / hybrid → подпакет) | каждый модуль < 350 LoC, public API сохранён |

### Фаза 5 (дожимающие) — параллельно фазе 1, без блокировки

| Шаг | Описание | Приёмка |
|-----|----------|---------|
| 5.1 | Handoff rule «после `paper_profile` для одиночного title-resolution → writer» (backlog `[OPEN] Reduce supervisor route churn`) | `tool_loop_repeat_max` на default dev-v3 baseline снижен материально |
| 5.2 | Dev `.env` / smoke-runner: явный `SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v3` для acceptance-эквивалентного контура | `make dev-up` + POST на `:18787` отдают `route_to_specialist` |
| 5.3 | Pylint cleanup в `supervisor.py` (line-length, ранее — `_DUAL_EVIDENCE_CATALOG_COMPARE_MARKERS` дубль) | pylint -sn без warnings module-level в supervisor |

---

## 5. Связь с roadmap и backlog

- В шапке [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) — добавлен cross-link на этот документ.
- Backlog items, которые «уезжают» под этот план:
  - `[OPEN] Reduce supervisor route churn before writer handoff` → **Фаза 5.1** (точечно) + **Фаза 1** (структурно).
  - `[OPEN] Simplify writer_agent into terminal synthesis seam` → **Фаза 4.3**.
  - `[OPEN] Split permission / validation phase out of build_tool_execution_node` → **Фаза 4.2**.
  - `[OPEN] Split oversized tool_search.py` → **Фаза 4.4**.
- Новые backlog items, которые надо завести в [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md):
  - `[OPEN] Introduce RoutePlan + QuestionFeatures (orchestration policy unification)` — Фаза 1.
  - `[OPEN] Single supervisor backbone with single_agent_react_mode flag` — Фаза 2 (или альтернатива из ADR).
  - `[OPEN] Per-tool-call deadline + completion_state for graceful degradation` — Фаза 3.
  - `[OPEN] Split supervisor_node into supervisor_decisions module` — Фаза 4.1.

---

## 6. Что считаем «стабильной версией»

- Acceptance `agent_trace_review.py --suite acceptance` зелёный на default dev-v3 **без точечных substring-латок в `supervisor_node`** для новых вариантов промптов.
- `tool_loop_repeat_max` на default dev-v3 baseline снижен **измеримо** (целевое: ≤ 4 на acceptance-наборе).
- Один формат `tool_trace` для дев и acceptance (`route_to_specialist` всегда виден).
- При сетевых hang-ах LLM turn заканчивается **partial answer + warning**, а не дедлайном.
- Backlog не пополняется новыми «policy fragmentation» items при добавлении acceptance-кейсов.

---

## 7. Что **не** входит

- Перенос на subprocess-isolated subagents (см. отдельный спайк [`agent-graph-subprocess-isolation-spike-2026-04-27.md`](./agent-graph-subprocess-isolation-spike-2026-04-27.md)) — отдельная ось, не часть этой стабилизации.
- Реальный параллельный fanout (`Epic B`, roadmap §11.4) — этот план **совместим** с ним, но не предполагает доставку.
- Перестройка `chat_envelope.py` (roadmap §2.1.1) — отдельная задача; здесь только не ухудшаем её контракт.
- Оптимизация LLM провайдера / таймаутов — операционная ось, не архитектурная.
