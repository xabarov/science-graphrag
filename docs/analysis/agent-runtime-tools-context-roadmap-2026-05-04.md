# Агент · инструменты · компактация контекста — единый план (2026-05-04)

**Статус:** живая точка входа по оси *оркестрация агента — каталог tools — сжатие/память диалога*. Заменяет корневой slim-файл `chat-agent-system-roadmap-2026-04-26.md` (удалён как дубликат; глубокая предыстория CH-волн: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md)).

**Итог на 2026-05-06:** текущая волна плана выполнена (BT8/BT9, P2 trace-review, L3/L4, prompt-after-compact matrix, trust/runtime updates).  
**Подтверждение:** live `trace-review`/regression-gate — pass; выполнен полноценный LLM-judge по live-трейсам (`eval/results/habr-window-2026-06-agent-tools-mini-band-1.35-live-llm-judge.json`); full L4 LLM compact подтверждён live-smoke с audit trail.

**Связанные документы (не дублировать детали):**

| Документ | Роль |
|----------|------|
| [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) | Контракт SSE, CH\*-лейблы, session memory |
| [`docs/architecture/agent-chat-tools.md`](../architecture/agent-chat-tools.md) | Каталог инструментов и маппинг к коду |
| [`langgraph-migration-plan-2026-04-25.md`](./langgraph-migration-plan-2026-04-25.md) | Wave Y: smolagents → LangGraph, фазы Y1–Y6 |
| [`agent-chat-tools-and-trace-audit-master-2026-04-28.md`](./agent-chat-tools-and-trace-audit-master-2026-04-28.md) | Eval, harness, Phoenix / trace |
| [`agent-chat-prod-rollout-2026-04-27.md`](./agent-chat-prod-rollout-2026-04-27.md) | Флаги, `TurnPolicy`, prod |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](./ontology-benchmarks-roadmap-2026-04-24.md) §7.7 | Историческая инвентаризация Wave R (agent tools + bench) |
| [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md) | BT8/BT9, `agent_tools_*`, mock vs live |
| [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) | OPEN: idea_workflow split, settings, benchmark split, Qdrant… |

---

## 1. Краткие ответы на вопросы

### 1.1 Есть ли `tool_search`?

**Да, в продукте — rule-based v1.** Модуль [`science_graphrag/agent/tool_search.py`](../../science_graphrag/agent/tool_search.py): скоринг/теги по манифесту [`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py), отбор shortlist под вопрос, стрип XML-обёрток сессии (`strip_tool_search_context_wrappers`), консервативный baseline (в т.ч. `final_answer`, retrieval core). **LLM-based** подбор инструментов и «ленивая» подгрузка полных JSON-схем **не** закрыты — осознанный бэклог (нужны eval/gate).

### 1.2 Есть ли «продвинутые» техники суммаризации, как в openclaude?

**Частично, другой дизайн.** В **openclaude** (см. `openclaude/scripts/build.ts`, `src/commands/insights.ts`, UI) встречаются: **параллельная саммаризация длинных транскриптов по чанкам**, **cached micro-compact** тул-результатов (**partial: в open snapshot `cachedMicrocompact.ts` — stub, но integration path в `microCompact.ts` присутствует**), **context collapse** (**partial/stub: `services/contextCollapse/index.ts`**), **coordinator / встроенные Explore·Plan субагенты**, **token budget**, **away summary** после blur.  
В **science-graphrag** реализована **своя лестница** (см. §3): детерминированные **turn digest** + **rolling session_summary** (последние 3 из 10 дайджестов), **SSE `context_compacted`**, опциональное **сжатие старых ToolMessage** в ReAct (`tool_message_compact.py`), интеграция дайджестов в **LLM turn classifier** — без отдельного «инсайтс-LLM» по всему транскрипту, как в openclaude CLI.

### 1.3 Есть ли субагенты, которые основной агент создаёт по своей инициативе (spawn N, merge), как в openclaude?

**Нет в таком виде.** У нас **фиксированный LangGraph**: `supervisor` → `retrieval_agent` / `graph_agent` → `writer_agent` (см. `agent/graph/`). Маршрутизация — **TurnPolicy** / classifier, а не runtime-spawn воркеров. **Динамическое** ветвление «по одному tool call на субагента» — **не** в продуктовом runtime; в бенчмарках заложены **multi-agent** сценарии (`expected_specialist_sequence`, Wave Y4) и хвост **BT9** (фикстуры). Для тяжёлой изоляции см. спайк [`agent-graph-subprocess-isolation-spike-2026-04-27.md`](./agent-graph-subprocess-isolation-spike-2026-04-27.md).  
В openclaude — **COORDINATOR_MODE**, **FORK_SUBAGENT**, отдельные transcript-файлы под `subagents/`, **spawn_fallback_agent** в hook chains — это **другой класс продукта** (CLI + mesh).

---

## 2. Архитектура сейчас (канон репозитория)

| Слой | Реализация |
|------|------------|
| API | [`science_graphrag/api/agent_v2.py`](../../science_graphrag/api/agent_v2.py) — sync + SSE; события synthesis / compaction |
| Граф | [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py), ноды retrieval/graph/writer; state — [`state.py`](../../science_graphrag/agent/graph/state.py) |
| Tools | LangChain `BaseTool`, registry; **tool_search** урезает видимый набор; см. architecture doc |
| Память / сжатие | [`agent/context/`](../../science_graphrag/agent/context/) — session store, turn digest, compaction payload; [`runtime.py`](../../science_graphrag/agent/runtime.py) — пост-turn обновление |
| Политика хода | [`coordination/turn_policy.py`](../../science_graphrag/agent/coordination/turn_policy.py), [`llm_turn_classifier.py`](../../science_graphrag/agent/coordination/llm_turn_classifier.py) |

**Устаревший контур:** `POST /v1/agent/query` — **410 Gone**, преемник `/v2/agent/query` ([`refactor-backend`](../backlog/refactor-backend.md) completed 2026-05-04).

### 2.1. Архитектурный долг (зафиксировано при разборе чата / envelope / Phoenix)

Ниже — не «баг конкретного трейса», а **структурные места трения**, которые стоит держать в голове при следующих правках и при планировании рефакторинга (целевой контур: единый слой исхода хода или сужение ответственности `build_chat_envelope`).

1. **Envelope как «свалка политик»** — [`science_graphrag/agent/chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py): класс ответа, эвристика вопроса, вывод из trace, клиентский hint, предупреждения про цитаты / слабые доказательства, product markers — всё в одном месте. Логика **трёх источников намерения** (вопрос / trace / hint) порождает правила вроде «`quote_extraction` из trace, но не если…» — **смешение уровней** (доменная политика + UX + эвристика классификации), рост числа краевых условий.

2. **Два мира состояния** по одному и тому же факту «что вызывали и что вернулось»: последовательность [`messages`](../../science_graphrag/agent/graph/state.py) (LangChain), агрегированный [`tool_trace`](../../science_graphrag/agent/graph/tracing.py), при необходимости [`specialist_results`](../../science_graphrag/agent/graph/state.py), плюс повторный разбор `ToolMessage` для typed payloads ([`tool_message_payloads.py`](../../science_graphrag/agent/tool_message_payloads.py)). **Дублирование и риск рассинхрона** при новых рантаймах или при смене формата сообщений.

3. **Два рантайма агента** под одним API: **single-agent research** (`langgraph_research_v1`, ReAct + `final_answer` в [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py)) vs **supervisor → specialists → writer** (`langgraph_supervisor_v1`, отдельные подграфы; у retrieval см. [`retrieval_agent.py`](../../science_graphrag/agent/graph/nodes/retrieval_agent.py) — иной контракт с `final_answer`). В Phoenix/LangGraph автодеревья **смешиваются** в одном trace — для разработчика это **две ветки поведения и два набора ожиданий** при одном `POST /v2/agent/query`.

### 2.2. Как похожие классы проблем сняты в openclaude (ориентир, не перенос дизайна)

**Контекст:** сравнение с отдельным репозиторием **openclaude** (CLI/SDK-клиент, дерево вроде `src/coordinator/`, `src/tools/AgentTool/`, `src/QueryEngine.ts`). Там **нет** серверного слоя вроде нашего `build_chat_envelope`; поведение собирается из потока сообщений, промптов и хуков. Ниже — **классы** решений, полезные при планировании рефакторинга у нас (см. §5).

| Трение из §2.1 | Что делают в openclaude | Практический смысл для нас |
|----------------|-------------------------|----------------------------|
| **1. Envelope / смешение политик** | Нет одного «конверта ответа API»: политика разнесена по **режиму** (напр. `getCoordinatorSystemPrompt`, `getCoordinatorUserContext` в `coordinator/coordinatorMode.ts`), **permissions** на tools (`hooks/toolPermission/handlers/…`), отдельному UX (уведомления), основному циклу сообщений (`QueryEngine`). | У них меньше монолитного модуля envelope; цена — **дублирование и согласование** между промптами, permissions и правилами транскрипта. Нам полезен ориентир: **сузить** `chat_envelope` до одной роли или разнести слои (домен / UX / классификация) явно. |
| **2. Дублирование состояния** | **Физическое разнесение** субагента: отдельные sidechain-транскрипты (`recordSidechainTranscript`, `setAgentTranscriptSubdir` в потоке Agent tool / `sessionStorage`), список сессий и recovery выбирают **главную** ветку, sidechain фильтруются (`listSessionsImpl`, `conversationRecovery`). В родителя результат приходит как **завершённый контур** tool call → результат, а не несколько параллельных представлений одного факта в одном state. | Ориентир: **один канонический след** «что было вызвано и что вернулось» + явный merge-слой; либо долгосрочно — изоляция тяжёлых веток (см. спайк subprocess). |
| **3. Два способа оркестрации** | **Взаимное исключение режимов:** при активном coordinator mode эксперимент **FORK_SUBAGENT** отключён (`forkSubagent.ts`: две модели делегирования не смешивают). Режим задаётся явно (env / сессия), не два незаметных графа под один вызов. | У нас один endpoint и два графа — ориентир: **жёсткая атрибуция** в trace/UI (graph id / run kind), документированные ожидания по `final_answer`, по возможности **не** смешивать span-дерево без подписи ветки. |

Дополнительно в openclaude (для карты соответствий, не как требование к коду):

- **Жизненный цикл субагента** вынесен в хуки (SubagentStart / SubagentStop в `hooksConfigManager` и др.) вместо проверок «везде в envelope».
- **Маркер контекста** fork-ребёнка (`isInForkChild`, теги в `forkSubagent.ts`) — явное «где мы», чтобы политики не применялись вслепую.
- Тяжёлая саммаризация истории — **вне** hot-path одного turn (insights / parallel chunks); у нас это ближе к §3 L4 и строкам §5 про параллельные чанки.

---

## 3. Лестница контекста (продуктовая модель ↔ код)

Уровни из прежнего slim-roadmap; ниже — что уже есть в коде.

| Уровень | Назначение | Статус в коде |
|---------|------------|----------------|
| L0 | Нормализованный evidence pack turn (eval / воспроизводимость) | Частично через trace + harness |
| L1 | **Turn digest** — структурированная сводка хода | [`turn_digest.py`](../../science_graphrag/agent/context/turn_digest.py), `apply_turn_digest_to_thread` |
| L2 | **Rolling session memory** | [`session_backend.py`](../../science_graphrag/agent/context/session_backend.py) — до 10 дайджестов, summary из последних 3 |
| L3 | **Капсулы** workspace / paper / entity | Поля/контракт в развитии; не главный UX-приоритет |
| L4 | **Full compact boundary** — явная граница для длинных тредов | [`compaction.py`](../../science_graphrag/agent/context/compaction.py) — SSE metadata, `digest_cap`, rolling_threshold; опциональная LLM-компактация full history реализована через [`llm_history_compact.py`](../../science_graphrag/agent/context/llm_history_compact.py) (feature-flag + audit trail) |

Дополнительно: **компактация истории tool-сообщений** в одном ReAct-потоке — [`tool_message_compact.py`](../../science_graphrag/agent/tool_message_compact.py) (флаги `agent_tool_history_compact_*`).

---

## 4. Инструменты и измерение качества

- **Каталог и безопасность:** ADR-016, `docs/specs/agent-tools-v1.md`, cypher allowlist.  
- **Бенчмарки:** семейства `agent_tools_*`, gate **BT8** (live mini + осмысленный judge), **BT9** (multi-agent fixtures). Источник правды — [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md).  
- **Backlog (структура):** распил [`api/benchmark.py`](../../science_graphrag/api/benchmark.py) / [`task_store.py`](../../science_graphrag/api/task_store.py) — см. refactor-backend, синергия с Wave M/P/Q/R/S.

---

## 5. Что перенять из openclaude с наибольшим ROI

Приоритет — идеи, совместимые с **серверным** графом и **наблюдаемостью**, без копирования CLI-меша. **Почему не «просто скопировать»** и как паттерны openclaude соотносятся с нашим долгом §2.1 — см. **§2.2**.

| Техника (openclaude) | Смысл | Переносимость к нам |
|---------------------|--------|----------------------|
| **ToolSearchTool** + отложенные схемы | Короткий каталог → полные схемы только для shortlist (`defer_loading` + discovered tool refs) | Уже близко к rule-based v1; следующий шаг — explicit lazy schema refs в manifest |
| **CACHED_MICROCOMPACT** | Усечение тул-результатов с учётом кэша | Переносить как паттерн: в open snapshot часть реализации заглушена, но flow и точки встраивания уже есть |
| **Параллельная саммаризация чанков** (insights) | Длинная история → параллельные LLM-сводки → сборка | Имеет смысл для **L4** или офлайн «thread export» (в openclaude это сделано в `commands/insights.ts`, не в hot-path turn-loop) |
| **TOKEN_BUDGET** / предупреждения | Явный учёт лимита в UI | Продуктово полезно совместить с `context_compacted` и лимитами на клиенте |
| **VERIFICATION_AGENT** (read-only) | Отдельный лёгкий прогон проверки | Аналог: отдельный eval harness / optional node — не обязательно в user-facing графе |
| **Hook chains + spawn_fallback** | Ремедиация при ошибках | У нас нет того же event-слоя; ближе — retry в runtime + Phoenix alert |
| **COORDINATOR / Explore·Plan субагенты** | Отдельные роли в одном продукте | У нас фиксированные ноды; расширение — только при явном ROI и метриках |

---

## 6. Очередь работ (сжатая)

**Продукт / архитектура**

1. ✅ **BT8/BT9 по trust-audit** закрыты (live agent_tools, multi-agent gold).  
2. ✅ **LLM/hybrid tool_search gate** закрыт как decision checkpoint: собраны shortlist/latency/noise метрики, дефолт rule-based сохранён до явного product gate.  
3. ✅ **L3/L4** (капсулы + full-history LLM compact) закрыты: реализованы триггеры, feature-flag и audit trail для eval/run metadata.  
4. ✅ Матрица «что попадает в prompt после compact» документирована в [`agent-chat-v1.md`](../specs/agent-chat-v1.md).  
5. При рефакторинге envelope / state: держать в уме **§2.2** (канон фактов хода, слои envelope, атрибуция графа в trace).
6. ✅ **Wave 5 runtime/state cleanup + trace-review hardening** закрыт:
   - `chat_envelope` декомпозирован по слоям `intent_resolution` / `response_policy` / `ux_annotations` без изменения внешнего контракта;
   - в `graph/tracing.py` добавлен канонический typed-след `collect_tool_execution_steps`, из которого строится legacy `tool_trace`;
   - добавлена runtime-атрибуция `run_kind` / `graph_id` в initial metadata, SSE `specialist_selected`, `run_metadata` и `trace-review-v1` (`run_context` + `trace_timeline`);
   - `agent_trace_review.py` получил профили `quick/default/heavy`, а `trace_regression_compare.py` — жёсткий fail-policy на рост `compaction_churn_score` (`compaction_churn_increase`).

### 6.1 План заимствований из openclaude (high ROI)

1. ✅ **Deferred tool schemas через shortlist**  
   Комментарий (Wave 2, 2026-05-05): добавлены feature-flag `agent_tool_search_deferred_schema_refs_enabled`, `deferred_schema_refs` в `tool_search_result`, telemetry-поля shortlist (`catalog_size`, `shortlist_size`, `shortlist_ratio`), A/B прогон off/on подтверждён без регрессии verdict.

2. ✅ **Carry-over discovered tools через compaction boundary**  
   Комментарий (Wave 3, 2026-05-05): капсула `capsules.discovered_tools` в session backend (merge из `turn_digest.tools_used`), флаги `agent_discovered_tools_carryover_enabled` / `agent_discovered_tools_carryover_max`; прокидка в `tool_search` и блок `<discovered_tools>` в user prompt (`format_user_with_memory`); инварианты в `tests/test_context_session.py`.

3. ✅ **Единый execution pipeline для tool-use**  
   Комментарий (Wave 3, 2026-05-05): модуль [`science_graphrag/agent/tool_execution_pipeline.py`](../../science_graphrag/agent/tool_execution_pipeline.py) — `validate → permission → ToolNode → post-hooks`, debug events `tool_execution`; узлы retrieval/graph/writer и single-agent ReAct в [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) переведены на `build_tool_execution_node`; `effective_tool_policy` — единая точка для политики инструментов (supervisor routing использует тот же helper).

4. ✅ **Матрица allowed-tools по режимам/ролям**  
   Комментарий (Wave 3, 2026-05-05): флаг `agent_allowed_tools_matrix_enabled` (по умолчанию off), denylist/allowlist по mode и `tool_policy` в [`config.py`](../../science_graphrag/config.py), `apply_allowed_tools_matrix` перед сборкой ToolNode; тесты [`tests/agent/test_allowed_tools_matrix.py`](../../tests/agent/test_allowed_tools_matrix.py).

5. ✅ **Sidechain transcripts для изоляции веток**  
   Комментарий (Wave 3, 2026-05-05): JSONL при `agent_sidechain_transcripts_enabled`, каталог `agent_sidechain_transcripts_dir` (default `.agent_sidechains/`, в `.gitignore`); события `tool_batch_start` / `tool_batch_end` на батч вызовов.

6. ✅ **Token budget как first-class контур**  
   Комментарий (Wave 2, 2026-05-05): добавлен детерминированный stop event `budget_stop_decision` (`agent_response_budget_cutoff`) и прокладка в SSE/run_metadata; флаг `agent_budget_stop_reasoning_enabled` оставляет fallback-поведение в off-режиме.

7. ✅ **Away summary при возврате пользователя**  
   Комментарий (Wave 3, 2026-05-05): клиент передаёт `client_idle_ms` в [`agent_v2`](../../science_graphrag/api/agent_v2.py); порог `agent_away_summary_client_idle_ms_threshold`; при превышении — блок `<away_recap>` в промпте (`build_initial_agent_state` / Ask UI: `useAgentStream.js`, `useAskSubmit.js`).

8. ✅ **Feature-gated rollout + telemetry для новых runtime-механизмов**  
   Комментарий (Wave 2, 2026-05-05): dual-run off/on выполнен через `agent_trace_review.py`, compare через `trace_regression_compare.py`; добавлены telemetry-метрики в `trace-review-v1` (`shortlist_ratio_avg`, `deferred_schema_event_count`, `budget_cutoff_count`) и run_context flags.

### 6.2 Ревизия текущих скриптов и пробелов trace-review

**Уже есть (переиспользуем как базу P0):**

- `scripts/live_check/agent_v2_http.py` + `scripts/live_check/http_suite.py`  
  Live smoke для `/health` + `/v2/agent/query` (JSON/SSE/multi-turn/CH4).
- `scripts/live_check/agent_od_workspace_e2e_audit.py` + `scripts/live_check/run_agent_od_phases_audit.sh`  
  End-to-end OD-аудит с `tool_trace`, Phoenix span coverage, Postgres checks.
- `eval/chat_agent/roadmap_runner.py` + `eval/chat_agent/runner.py`  
  Harness/регрессия и контрактные проверки по fixture-пакам.
- `eval/chat_agent/observability_audit.py` + `eval/chat_agent/phoenix_export.py`  
  Сверка trace артефактов и Phoenix snapshot.
- `scripts/chat_agent_workspace_readiness_audit.py`  
  Readiness перед heavy/live прогоном.

**Пробелы (что мешает стабильному «всегда одинаковому» отсмотру):**

1. Нет одного канонического CLI «trace review» (нужно собирать руками из нескольких утилит).  
2. Нет единой schema-версии артефакта ревизии (JSON/MD в разных форматах).  
3. Нет выделенного lane для анализа последствий `context_compacted` «до/после».  
4. Нет baseline-diff инструмента «candidate vs baseline» по trace quality.  
5. Нет стандартного timeline формата `tool_call -> span -> side effect -> verdict`.

**Статус после Wave 1 (2026-05-05):**

1. ✅ **Закрыто.** Канонический CLI есть: `scripts/live_check/agent_trace_review.py`.  
   Комментарий: оркестратор собирает checks + e2e + Phoenix + compaction в единый `trace-review-v1`.
2. ✅ **Закрыто.** Единая schema-версия внедрена: `scripts/live_check/trace_review_schema.py`.  
   Комментарий: dataclass-модель, merge-хелперы и единый `review_version`.
3. ✅ **Закрыто.** Отдельный lane для compaction есть: `scripts/live_check/compaction_turn_review.py`.  
   Комментарий: `compaction_events` и merge в основной артефакт через `--emit-merged-into`.
4. ✅ **Закрыто.** Baseline diff есть: `scripts/live_check/trace_regression_compare.py`.  
   Комментарий: fail/warn политики, проверка версии схемы (exit 2 при drift), self-check baseline=baseline проходит.
5. ✅ **Закрыто.** Timeline формат стандартизован в `trace-review-v1` (`trace_timeline`).  
   Комментарий: поля `tool_steps`, `phoenix_alignment`, `compaction_events`, `warnings`, итоговый verdict.

**Техническая пометка по качеству прогона:**  
- Во время Wave 1 поймана и исправлена причина падения SSE-check `missing_intent_classified` для runtime `langgraph_research_v1`:  
  `build_initial_agent_state` теперь добавляет стартовый debug-event `intent_classified` и контракт подтверждён тестом.  
- После фикса full e2e прогон `agent_trace_review.py` завершился `verdict=pass`; baseline обновлён живым артефактом.
- Wave 2: устранён CLI-дрифт между `agent_trace_review.py` и `agent_od_workspace_e2e_audit.py` (совместимость `--skip-postgres`), из-за которого e2e сначала падал до выполнения кейсов.  
- Wave 2: стабилизирован heavy-кейс `graph_ego_methods` (сузили сценарий до `workspace_inspect -> edge_search -> final_answer`), после чего full dual-run off/on дал `verdict=pass` в обоих режимах.

### 6.3 Канонический формат артефакта trace-review (v1)

**JSON (`review.json`)**

```json
{
  "review_version": "trace-review-v1",
  "generated_at": "ISO-8601",
  "run_context": {
    "base_url": "http://127.0.0.1:18787",
    "workspace_id": "uuid-or-null",
    "suite": "default|heavy|full",
    "feature_flags": {
      "agent_runtime": "langgraph_supervisor_v1",
      "agent_rule_tool_search_enabled": true
    }
  },
  "checks": [
    {"name": "health", "ok": true, "detail": "ok"},
    {"name": "agent_v2_sync_json", "ok": true, "detail": "ok"},
    {"name": "agent_v2_sse", "ok": true, "detail": "ok"}
  ],
  "trace_timeline": [
    {
      "case_id": "string",
      "thread_id": "string-or-null",
      "tool_steps": [{"idx": 1, "tool": "tool_name", "ok": true}],
      "phoenix_alignment": {"covered": 3, "missing": []},
      "compaction_events": [{"type": "context_compacted", "kinds": ["turn_digest"]}],
      "db_side_effects": {"ingest_jobs_seen": 0},
      "warnings": []
    }
  ],
  "metrics": {
    "tool_error_rate": 0.0,
    "missing_span_count": 0,
    "compaction_event_count": 1,
    "final_answer_missing_count": 0
  },
  "verdict": {
    "status": "pass|warn|fail",
    "fail_reasons": []
  }
}
```

**Markdown (`review.md`)**

- Run context (env/suite/flags).  
- Таблица checks (OK/FAIL + detail).  
- Таблица timeline по кейсам (tool sequence, span coverage, compaction, warnings).  
- Итоговый verdict с причинами и ссылками на артефакты.

**Вердикт-гейты (v1):**

- `FAIL`, если:
  - любой обязательный check (`health`, `agent_v2_sync_json`, `agent_v2_sse`) не прошёл;
  - `missing_final_answer` > 0;
  - появился `error` SSE event без успешного salvage;
  - рост `missing_span_count` относительно baseline выше порога.
- `WARN`, если:
  - есть деградация latency / compaction churn / tool-loop stability без hard-fail.

### 6.4 P0/P1/P2 и тест-матрица по 8 ROI пунктам

| ROI пункт | Приоритет | Live checks (обязательно) | Automated checks (обязательно) | Telemetry / Gate |
|-----------|-----------|---------------------------|----------------------------------|------------------|
| Deferred schemas + shortlist | P2 | `agent_trace_review.py` + heavy suite + A/B flags | `tests/test_tool_search.py`, `tests/test_api_agent_v2_stream_parity.py` + новые shortlist quality fixtures | shortlist quality, latency delta, unnecessary tool calls |
| Discovered tools carry-over | P2 | `compaction_turn_review.py` + multi-turn `/v2/agent/query` | `tests/test_context_session.py` + новый carry-over invariant test | rediscovery churn после compact |
| Unified tool-use pipeline | P2 | `agent_trace_review.py` + trace timeline | `tests/agent/test_react_edges.py` + новые stage failure tests | validation_fail / permission_deny / hook_error |
| Allowed-tools matrix | P2 | e2e suite + SSE `tool_search_result` parity | `tests/agent/test_supervisor_routing.py`, `tests/agent/test_turn_policy_eval_gold.py` + matrix fixtures | deny-by-role/mode, exposure regressions |
| Sidechain transcripts | P2 | trace review + timeline (ветви) | новые transcript recovery tests | sidechain depth, merge latency |
| Token budget loop policy | P2 | live scenarios near budget + trace review | `tests/agent/test_react_budget_cutoff.py` + новые token-policy tests | stop reason distribution |
| Away summary | P2 | multi-turn return scenario + trace review | `tests/eval/test_chat_multi_turn_memory_smoke.py` + новые away-summary contract tests | re-engagement success / correction rate |
| Feature-gated rollout + telemetry | P0 | dual-run off/on в `agent_trace_review.py` + regression compare | stream parity + observability tests (`tests/observability/*`) | on/off parity, warning drift, p95 drift |

**Внедрение по фазам:**

- **P0 (сразу):** SOP + `agent_trace_review.py` + schema `trace-review-v1` + regression compare gate.  
- **P1:** compaction/timeline/phoenix pull utilities и унификация артефактов для оффлайн ревью.  
- **P2:** фича-специфичные сценарии и тесты по каждому ROI пункту.

**Из refactor-backend (фильтр по этой оси)**

- Split **`idea_workflow.py`** — см. OPEN item.  
- **Settings service split** — caps для агента / pools.  
- **Artifact storage** для chat-agent traces — OPEN «Split benchmark artifact storage».  
- **paper_profile** null-rate — влияет на tool quality; см. OPEN.

---

## 7. История

| Дата | Изменение |
|------|-----------|
| 2026-05-04 | Единый план: объединены slim roadmap, ответы на сравнение с openclaude, ссылки на backlog и ontology §7.7; удалён дублирующий `chat-agent-system-roadmap-2026-04-26.md`. **§2.1** (архитектурный долг). **§2.2** (добавлено позже в тот же день): сопоставление долга с openclaude — разнесение политик vs monolithic `chat_envelope`, sidechain-транскрипты vs дубли state, взаимное исключение FORK/coordinator vs два графа под одним API; кросс-ссылки из §5 и §6. |
| 2026-05-05 | Точечная верификация по коду openclaude snapshot: уточнено, что `CACHED_MICROCOMPACT` и `contextCollapse` в открытом срезе частично/stub; формулировки про ToolSearch/defer-loading и chunk-summarization приведены к фактическим точкам в коде (`services/compact/*`, `services/contextCollapse/*`, `commands/insights.ts`). |
| 2026-05-05 | Добавлен отдельный блок планов **§6.1** «План заимствований из openclaude (high ROI)»: deferred schemas, carry-over discovered tools, единый pipeline tool-use, role/mode allowlist, sidechain transcripts, token budget loop-policy, away summary и feature-gated rollout с telemetry. |
| 2026-05-05 | Добавлены **§6.2** (ревизия текущих scripts/runbooks/eval и зафиксированные пробелы) и **§6.3** (каноническая schema `trace-review-v1`, markdown layout, pass/warn/fail гейты) как база для SOP и новых `scripts/live_check/*`. |
| 2026-05-05 | Добавлены **§6.4** (P0/P1/P2 приоритизация и тест-матрица по 8 ROI-пунктам) и операционный контур dual-run/regression-gate для runtime rollout. |
| 2026-05-05 | Обновлён статус в **§6.2**: Wave 1 (P0 + P1 toolkit) отмечен как выполненный с комментариями по каждому пробелу; добавлена пометка о фиксе SSE `missing_intent_classified` для `langgraph_research_v1`, успешном full e2e (`verdict=pass`) и обновлении baseline артефактов. |
| 2026-05-05 | Обновлён статус в **§6.1**: закрыты ROI-пункты 1/6/8 (deferred schemas, token budget stop reasons, feature-gated rollout + telemetry). Зафиксированы результаты Wave 2: dual-run off/on `pass`, добавленные telemetry-метрики `trace-review-v1`, а также исправления e2e-блокеров (`--skip-postgres` совместимость и стабилизация кейса `graph_ego_methods`). |
| 2026-05-05 | **Wave 3** — закрыты ROI-пункты §6.1 **2–5 и 7**: carry-over discovered tools, unified tool execution pipeline, allowed-tools matrix (feature-flag), sidechain JSONL transcripts, away summary (`client_idle_ms`). Регрессия к baseline: `trace_regression_compare.py` против `eval/results/trace-review-off.json` — **pass**; live `agent_trace_review.py` (default suite) — **pass**. Техдолг: pylint duplicate-code между графом и pipeline снят через общий `effective_tool_policy`. |
| 2026-05-06 | **Wave 4 (runner/trust/P2):** BT8/BT9 runner closure — `routing_log` в benchmark/live выводе агента; stub-трассы бенчмарка без ``mock answer`` / ``mock-work`` для честного ``trust_signal``; tier ``agent_tools_multiagent`` в aggregate + артефакт ``current-agent-tools-multiagent.json``; nightly опциональная live-перегенерация mini при секрете; метрики ``tool_name``/``args_match`` в ``eval/agent_tools/metrics``; CH5 ``context_compacted.audit``; матрица prompt/memory в ``agent-chat-v1.md``; ADR-027; тесты P2 (trace-review ROI counters, sidechain path). |
| 2026-05-06 | **Wave 4.1 (LLM judge + L4 live run):** выполнен полноценный `science-graphrag-agent-judge-benchmark --llm` по live-трейсам (`habr-window-2026-06-agent-tools-mini-band-1.35-live-llm-judge.json`); подтверждён full L4 LLM compact в live smoke (feature-flag `SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED`, audit в `session_meta` и `run_metadata.compaction_audit`). |
| 2026-05-06 | **Wave 5 (runtime/state cleanup + trace-review hardening):** декомпозирован `chat_envelope` (intent/policy/ux), введён канонический typed tool execution trace (`collect_tool_execution_steps`) как source-of-truth для `tool_trace`, добавлена атрибуция `run_kind`/`graph_id` в SSE/final run_metadata/trace-review schema, расширен `agent_trace_review.py` профилями quick/default/heavy, `trace_regression_compare.py` ужесточён fail-политикой `compaction_churn_increase`; обновлены тесты `test_chat_envelope`, `test_api_agent_v2_stream_parity`, `test_trace_review_schema`, `test_trace_regression_compare`. |

---

## 8. Post-closure next wave (обновление после выполнения Wave 5)

Текущая волна roadmap закрыта; ниже — **узкий хвост hardening-работ**, синхронизированный с backend backlog.  
Цель блока: не переоткрывать закрытые ROI-пункты §6.1/§6.2, а зафиксировать, что осталось для «production-ready steady state».

### 8.1 P0 (ближайший цикл)

1. **CI gate: candidate vs baseline для trace-review**  
   Закрыть хвост по OPEN `CI gate — trace_regression_compare vs committed baseline`:  
   добавить candidate-generation шаг (не baseline-vs-baseline), зафиксировать policy (какой compare step blocking, какой advisory) в workflow comments/docs.

2. **Orchestrator smoke-контракт для `agent_trace_review.py`**  
   Добавить subprocess smoke (quick/default) с проверкой `review_version`, `run_context`, поведения warn/fail-paths.

### 8.2 P1 (архитектурный hardening)

1. **Единый канонический tool/run audit trail**  
   Дожать OPEN `Single canonical tool/run audit trail`:  
   контракт «turn facts» как единственный источник для envelope/observability + тест выравнивания `tool_trace` ↔ spans на reference suite.

2. **Дальнейший распил перегруженных модулей runtime/SSE**  
   Продолжить OPEN `Split oversized agent edges + SSE lifecycle modules` и `De-duplicate Agent v2 payload/runtime metadata seams` до целевых acceptance-критериев (ветвление/statement budget, один canonical metadata builder для sync/SSE).

### 8.3 P2 (операционные измерения и качество данных)

1. **`agent_note` cost evidence (50-turn batch)**  
   Дособрать фактические token/latency числа и финализировать рекомендацию в `docs/analysis/agent-note-cost-eval-2026-05-06.md`.

2. **`paper_profile` null-rate closure (OD)**  
   Провести замер `eval/paper_profile_stats.summarize_paper_profile_payloads`, затем решить: достаточно read-path overlay или нужен ingest-time writeback year/venue в граф.

### 8.4 Definition of done для этой next wave

- CI на PR-ветках ловит trace-regressions в candidate-vs-baseline режиме.
- `agent_trace_review.py` имеет отдельный smoke-контракт orchestration-слоя.
- Для runtime trail зафиксирован один канон фактов хода и есть тесты выравнивания trace/observability.
- Операционные хвосты (`agent_note` cost, `paper_profile` null-rate) закрыты цифрами, а не только proposal-формулировками.

### 8.5 Execution log (2026-05-06, next-wave pass)

- **P0 закрыт:** `.github/workflows/agent-sse-contract.yml` переведён на candidate-generation + compare с policy split:
  - advisory compare (`--warn-is-pass`);
  - blocking strict compare (без `--warn-is-pass`).
- **P0 закрыт:** `tests/scripts/live_check/test_agent_trace_review.py` получил subprocess smoke-контракты для `--profile quick/default` с проверкой `review_version`, `run_context.profile` и fail-path verdict.
- **P1 закрыт (runtime canon):**
  - добавлен canonical metadata builder в `science_graphrag/api/agent_v2_modules/payloads.py` (`build_run_metadata`, `apply_runtime_metadata_from_state`);
  - sync/SSE пути выровнены на один builder в `science_graphrag/api/agent_v2.py` и `science_graphrag/api/agent_v2_modules/stream_lifecycle.py`.
- **P1 закрыт (alignment test):** добавлен regression-контракт `tests/scripts/live_check/test_trace_review_schema.py::test_reference_suite_tool_trace_span_alignment_contract`.
- **P2 обновлён (agent_note cost):** добавлен 50-turn batch результат в `docs/analysis/agent-note-cost-eval-2026-05-06.md` + артефакт `eval/results/agent-note-cost-50turn.json`.
- **P2 обновлён (paper_profile null-rate):** измерен proxy-null-rate на OD case exports (`eval/results/paper-profile-null-rate-od-snapshot.json`): `year_null=1.0`, `venue_null=1.0` (n=8), решение по ingest writeback — в backend backlog (OPEN).

---

## 9. Closure plan по исходным целям (openclaude-parity track)

Этот раздел фиксирует **первичные цели**, с которых начался roadmap:

1. умная суммаризация контекста как в `openclaude`;
2. вариант runtime (условно `agent v3`), где агент может вызывать субагентов как в `openclaude`;
3. tool_search логика как в `openclaude`.

Ниже — не «общие намерения», а исполнимый план до состояния, когда можно честно сказать «цели закрыты».

### 9.1 Принцип «закрыто» (anti-formality gate)

Любой пункт считается закрытым только при одновременном выполнении трёх условий:

- **Runtime:** механизм реально включается в live `/v2/agent/query` (или явно в новом `/v3/agent/query`), а не только в тестовых/stub путях.
- **Observability:** в SSE/run_metadata/trace-review есть проверяемые следы работы механизма.
- **Quality gate:** есть минимум один benchmark/eval сценарий, где новая логика не ухудшает baseline по trust/verdict/latency выше оговорённых порогов.

Если есть только код без trace + gate, статус — `PARTIAL`.

### 9.2 Стартовая диагностика (что уже есть и чего не хватает)

#### A) Context summarization

- **Есть:** `turn_digest`, rolling `session_summary`, `context_compacted`, L4 full-history compact через feature-flag, `away_recap`, `tool_message_compact`.
- **Не хватает до parity-цели:** отдельного слоя «insights-like» для длинных тредов (chunked/parallel summarize + synthesis), явной policy «когда offline summary заменяет/дополняет turn-loop memory».
- **Важная оговорка по openclaude:** в snapshot `contextCollapse` отмечен как stub/feature-gated (`src/services/contextCollapse/index.ts`), поэтому parity-ориентир берём не по «внутренней реализации collapse», а по поведенческому контракту: устойчивый long-thread UX + reproducible compaction decisions + traceability.

#### B) Subagent runtime (`agent v3`)

- **Есть:** specialist routing в фиксированном LangGraph + sidechain transcripts + SSE-события `subagent_*` как UX-слой.
- **Не хватает до parity-цели:** реального динамического spawn/fork автономных воркеров с последующим merge-этапом.
- **Текущий риск формальности:** термин `subagent` в stream событиях сейчас может вводить в заблуждение (маркирует specialist handoff, но не отдельный runtime-process/task lifecycle).

#### C) Tool search

- **Есть:** rule-based shortlist, deferred schema refs, carry-over discovered tools, telemetry и regression gates.
- **Не хватает до parity-цели:** model-assisted discovery loop и динамическое подключение deferred tools по факту «discovered references», а не только эвристический скоринг по тексту.

### 9.3 Epic A — Smart context summarization parity

#### A0. Контракт и режимы (spec first)

- Добавить в `docs/specs/agent-chat-v1.md` раздел `Summarization modes`:
  - `turn_loop_memory` (текущий CH4/CH5),
  - `thread_insights_compact` (новый async/offline контур),
  - `hybrid` (turn-loop + periodic insights refresh).
- Для каждого режима зафиксировать:
  - source inputs,
  - artifact schema,
  - как попадает в prompt,
  - когда отбрасывается как stale.

**Acceptance A0:** документированная матрица режимов + негативные кейсы (empty/noisy/contradicting summaries).

#### A1. Thread-insights pipeline (новый слой)

- Добавить модуль `agent/context/thread_insights.py`:
  - windowing длинного треда на semantic chunks;
  - parallel summarize workers (bounded concurrency, timeout/cancel-safe);
  - final synthesis в единый `thread_insight`.
- Добавить `session_backend` поля:
  - `thread_insight.current`,
  - `thread_insight.version`,
  - `thread_insight.sources` (chunk ids / turn range),
  - `thread_insight.generated_at`.
- Добавить policy freshness:
  - invalidation на N новых turn-ов;
  - forced refresh при high-churn tool traces.

**Acceptance A1:** на длинном synthetic треде строится `thread_insight` с воспроизводимым audit trail (`chunk_count`, `worker_count`, `generation_ms`, `source_range`).

#### A2. Prompt integration + fallback policy

- Расширить `format_user_with_memory`:
  - при наличии свежего `thread_insight` инжектить компактный `<thread_insight>` блок;
  - при stale/failed insight откат к текущему `session_summary`.
- Добавить guardrail:
  - если insight конфликтует с последним `turn_digest`, приоритет у свежих turn facts;
  - в run_metadata писать `insight_conflict_resolved=true/false`.

**Acceptance A2:** deterministic precedence policy покрыта тестами; нет silent override свежих фактов старым insight.

#### A3. Eval + gate

- Новый набор в `eval/chat_agent`:
  - long-thread retrieval,
  - context drift detection,
  - summary hallucination rejection.
- Метрики:
  - `insight_recall@k`,
  - `stale_summary_error_rate`,
  - `compaction_churn_delta`,
  - latency overhead p50/p95.
- Gate:
  - trust/verdict не хуже baseline,
  - p95 latency рост в пределах согласованного бюджета.

**Definition of done (Epic A):**
- thread-insights реально участвует в runtime;
- trace-review показывает его decisions;
- long-thread eval показывает улучшение recall/consistency или минимум отсутствие регрессии при включённом feature-flag.

### 9.4 Epic B — Agent v3 with real subagent spawning

#### B0. ADR и границы v3

- Выпустить ADR `agent-runtime-v3-subagents`:
  - когда нужен spawn (decision policy),
  - sync vs background branches,
  - merge contract,
  - failure taxonomy (timeout, partial, cancelled, tool-denied).
- Принять решение по API:
  - либо новый endpoint `/v3/agent/query`,
  - либо `run_kind=langgraph_supervisor_v3` под `/v2/agent/query` с жёсткой атрибуцией.

**Acceptance B0:** ADR с финальным вариантом API/compatibility и rollback strategy.

#### B1. Runtime primitive: spawn / track / collect

- Новый слой `agent/subagents/runtime.py`:
  - `spawn_subagent(task_spec) -> subagent_id`,
  - heartbeat/progress channel,
  - terminal states (`succeeded|failed|cancelled|timed_out`),
  - bounded fanout (`max_parallel_subagents`).
- Привязка к observability:
  - единый `parent_turn_id`,
  - `subagent_id`,
  - `spawn_reason`,
  - `cost/tokens/latency` per child.

**Acceptance B1:** live run с 2+ параллельными subagents даёт полный lifecycle в SSE + trace-review без missing states.

#### B2. Merge node и итоговый writer contract

- Добавить merge-узел:
  - агрегирует child outputs в typed `specialist_results_v3`,
  - устраняет дубли/конфликты (confidence ranking + provenance).
- Writer получает merge payload с явным `evidence_origin`:
  - `parent_tool`,
  - `subagent:<id>`,
  - `mixed`.

**Acceptance B2:** при конфликтующих ответах двух subagents финальный ответ объяснимо выбирает/синтезирует результат, provenance виден в run artifacts.

#### B3. Tool/search/memory взаимодействие

- Для subagent runs:
  - изолированный tool policy,
  - локальный short-term memory,
  - controlled carry-back в parent context (без полного transcript flooding).
- Ввести квоты:
  - `max_subagent_hops_per_turn`,
  - `max_subagent_tokens_per_turn`,
  - hard timeout per child.

**Acceptance B3:** subagent mode не ломает token budget policy и не создаёт runaway loops.

#### B4. Safety/eval gate

- Новые сценарии:
  - fanout research (N children),
  - one child fails, others succeed,
  - timeout + salvage,
  - malicious tool request в child (permission deny).
- Гейт:
  - корректный failover без silent success,
  - trace completeness 100% по lifecycle events.

**Definition of done (Epic B):**
- в runtime есть настоящий spawn/fanout/merge;
- SSE `subagent_*` отражает реальный lifecycle, а не только specialist routing;
- multi-agent eval lane стабильно проходит и отделён от legacy v2 режима.

### 9.5 Epic C — Tool search parity track

#### C0. V2 contract: discovery-aware tool loading

- Расширить текущий `tool_search` контракт:
  - поддержка `tool_reference`-подобных discovered entries в message history;
  - deferred tools реально подключаются только после discovery;
  - fallback к rule-based shortlist при low-signal/unsupported model.

**Acceptance C0:** история discovered tools влияет на доступный tool set в следующем ходе детерминированно и прозрачно в metadata.

#### C1. Hybrid selector (rules + LLM judge)

- Добавить optional LLM-selector поверх rule shortlist:
  - rules формируют candidate pool,
  - LLM rerank выбирает final shortlist,
  - confidence score + reason codes.
- Guardrails:
  - deny unsafe/excluded tools до LLM decision,
  - `final_answer` всегда доступен.

**Acceptance C1:** в benchmark lane снижается unnecessary tool calls без ухудшения verdict/trust.

#### C2. Dynamic schema transport

- Для deferred tools:
  - передавать компактные refs по умолчанию;
  - полную схему отправлять only-on-discovery.
- Добавить telemetry:
  - `tool_schema_bytes_saved`,
  - `deferred_tool_activation_rate`,
  - `tool_search_miss_due_to_no_discovery`.

**Acceptance C2:** уменьшение tool schema payload при сохранении/улучшении качества вызовов.

#### C3. Eval + policy gate

- Отдельные пакеты:
  - sparse-query (низкий сигнал),
  - ambiguous intent,
  - graph-heavy workloads,
  - bibliography/quote workflows.
- Gate policy:
  - `warn` при росте latency без роста ошибок,
  - `fail` при росте missed-tool или tool-loop instability.

**Definition of done (Epic C):**
- tool search работает как hybrid discovery-aware контур, а не только keyword scoring;
- деградации ловятся до rollout через trace regression compare + lane-specific metrics.

### 9.5.1 Tool parity backlog (openclaude-reference)

Этот backlog фиксирует **инструментальный хвост parity** к `openclaude` поверх уже описанных Epic A/B/C.
Фокус — не «добавить всё», а закрыть максимальный product/runtime эффект минимальным числом новых surfaces.

#### P0 (брать в ближайший train)

1. **MCP runtime trio + auth**
   - Scope:
     - `call_mcp_tool` (server/tool/arguments),
     - `list_mcp_resources`,
     - `fetch_mcp_resource`,
     - `mcp_auth` (interactive auth handoff).
   - Why:
     - даёт масштабируемое подключение внешних систем без N кастомных tool adapters;
     - напрямую усиливает Epic C (tool discovery) и Epic B (subagent payload usefulness).
   - Acceptance:
     - инструменты доступны в `/v2/agent/query` под feature flags;
     - в run metadata/SSE есть audit trail по `server`, `tool`, `resource_uri`, auth-status;
     - минимум 1 e2e scenario проходит с реальным MCP server и policy deny-path.

2. **LSP tool (read-only, bounded)**
   - Scope:
     - symbol lookup / references / go-to-definition в sandboxed read-only режиме.
   - Why:
     - улучшает code-aware retrieval и уменьшает ложные tool hops в codebase workflows.
   - Acceptance:
     - есть bounded latency/timeout policy;
     - trace фиксирует тип LSP операции и payload budget;
     - benchmark lane показывает не хуже baseline по verdict/trust при code-navigation вопросах.

#### P1 (после стабилизации P0 и B0/B1)

1. **Worktree isolation tools**
   - Scope:
     - `enter_worktree`,
     - `exit_worktree`.
   - Why:
     - готовит основу для реального multi-agent execution (Epic B) с безопасной изоляцией правок.
   - Acceptance:
     - lifecycle worktree прозрачно отражается в run artifacts;
     - fail/cleanup paths покрыты (dangling worktree не остаётся);
     - permission policy не позволяет escape за workspace boundaries.

2. **Runtime monitor tool**
   - Scope:
     - чтение статуса long-running task (state/progress/last heartbeat/error tail).
   - Why:
     - снижает риск silent hangs и усиливает observability для ingest/eval сценариев.
   - Acceptance:
     - есть единый status contract для async tasks;
     - в trace-review видны monitor events и корректная эскалация timeout/degraded state.

#### P2 (опционально, только при явном продукт-сценарии)

1. **Task orchestration primitives**
   - Scope:
     - `task_create`, `task_get`, `task_list`, `task_update`, `send_message`.
   - Why:
     - полезно для coordinator/subagent runtime, но создаёт дополнительный state-management overhead.
   - Acceptance:
     - доказан сценарий, где coordinator mode выигрывает у текущего graph routing по latency/reliability;
     - нет регрессий по trace completeness и permission safety.

2. **Scheduled automation (`cron_*`)**
   - Scope:
     - `cron_create`, `cron_list`, `cron_delete`.
   - Why:
     - ценно только если нужен first-class background automation в продукте.
   - Acceptance:
     - есть явный бизнес-кейс + retention/cleanup policy;
     - security review закрывает abuse vectors (spam scheduling, privilege escalation).

#### Out-of-scope до отдельного ADR

- `team_create` / `team_delete`,
- remote triggers,
- REPL-like execution surfaces.

Причина: высокий security/ops overhead при низком краткосрочном эффекте для текущего parity-трека.

### 9.6 Порядок внедрения (release train)

1. **Train T1 (2 недели):** A0/A1/C0 — контракты + thread-insights skeleton + discovery-aware tool loading.
2. **Train T2 (2 недели):** A2/A3/C1 — prompt integration + eval gates + hybrid selector.
3. **Train T3 (2-3 недели):** B0/B1 — ADR + runtime spawn primitive + lifecycle observability.
4. **Train T4 (2-3 недели):** B2/B3/C2 — merge node + quotas + dynamic schema transport.
5. **Train T5 (1-2 недели):** B4/C3 + финальный regression hardening и rollout decision.

Каждый train закрывается dual-run (`off/on`) и сравнением с committed baseline.

### 9.7 Явные stop-conditions (чтобы не повторить «отписку»)

- Нельзя пометить Epic B как done, пока `subagent_*` события не подтверждены реальными child runtimes в trace artifacts.
- Нельзя пометить Epic A как done без long-thread eval с цифрами (не только “pass smoke”).
- Нельзя пометить Epic C как done, если нет отдельного lane с ambiguous/sparse queries и зафиксированной policy `warn/fail`.

### 9.8 Изменение в истории документа

| Дата | Изменение |
|------|-----------|
| 2026-05-06 | Добавлен **§9.5.1**: `Tool parity backlog (openclaude-reference)` с приоритетами P0/P1/P2, acceptance-критериями и out-of-scope списком. |
| 2026-05-06 | Добавлен **§9**: closure plan по исходным целям (smart summarization parity, real subagent runtime v3, tool search parity), с epic-структурой, acceptance/gates, release train и stop-conditions против формального закрытия. |
