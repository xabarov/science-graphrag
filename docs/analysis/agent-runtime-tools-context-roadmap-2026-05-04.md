# Агент · инструменты · компактация контекста — единый план (2026-05-04)

**Doc status:** `reference`

**Read hint:** deep runtime/tools/compaction reference; weekly planning — [`ACTIVE.md`](./ACTIVE.md) + [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) + [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md).

**Статус:** detailed runtime roadmap by axis *agent orchestration — tools catalog — context compaction/memory*. For default weekly planning start from [`ACTIVE.md`](./ACTIVE.md) and [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md); this file is a deep reference with extensive historical/operational notes. Replaces root slim file `chat-agent-system-roadmap-2026-04-26.md` (removed as duplicate; full CH-wave history: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md)).

**Итог на 2026-05-06:** текущая волна плана выполнена (BT8/BT9, P2 trace-review, L3/L4, prompt-after-compact matrix, trust/runtime updates).  
**Подтверждение:** live `trace-review`/regression-gate — pass; выполнен полноценный LLM-judge по live-трейсам (`eval/results/habr-window-2026-06-agent-tools-mini-band-1.35-live-llm-judge.json`); full L4 LLM compact подтверждён live-smoke с audit trail.

**Дополнение 2026-05-07 (Train T2 — §10.4 / §10.5):** закрыт срез *prompt discipline + compaction hardening* (writer/final_answer контракт, microcompact по idle, restore paper sources после compact, pre-compact sanitizers); телеметрия `debug_events` вынесена в [`science_graphrag/agent/debug_events_telemetry.py`](../../science_graphrag/agent/debug_events_telemetry.py), sync JSON получает те же агрегаты, что SSE (`payloads.response_from_run`). Детали — комментарии под §11.2.

**Дополнение 2026-05-07 (live/eval hardening — §11.2–§11.5, §10.10):** зафиксированы repeatable сценарии и политики сравнения с baseline: `scripts/live_check/agent_trace_review.py --suite acceptance` + `acceptance_summary_v1` в артефакте, OD `agent_od_workspace_e2e_audit.py --suite acceptance`, B4 HTTP-пробы `agent_v2_fanout_probe` / `agent_v2_malicious_deny` в [`http_suite.py`](../../scripts/live_check/http_suite.py), расширение [`trace_regression_compare.py`](../../scripts/live_check/trace_regression_compare.py) и [`README_trace_review.md`](../../scripts/live_check/README_trace_review.md), rollout-заметка [`eval/results/runtime-v3-rollout-decision-2026-05-07.md`](../../eval/results/runtime-v3-rollout-decision-2026-05-07.md). **Quality-pass:** `malicious_deny` поверх общего `check_agent_v2_sync_json` + поля `answer_stripped`/`answer_len` в `CheckResult.data`; dedupe `live_proven` в `build_acceptance_summary`; unit [`tests/scripts/live_check/test_http_suite_safety.py`](../../tests/scripts/live_check/test_http_suite_safety.py).

**Дополнение 2026-05-07 (Train T4 — §11.4 / §10.3 / §10.9):** под `langgraph_supervisor_v3` добавлены read-only **corpus_explore** и декомпозиция **research_plan** (флаги `agent_corpus_explore_enabled`, `agent_research_plan_subagent_enabled`; рантаймы [`corpus_explore_runtime.py`](../../science_graphrag/agent/subagents/corpus_explore_runtime.py), [`research_plan_runtime.py`](../../science_graphrag/agent/subagents/research_plan_runtime.py)); изоляция child — [`isolated_subagent_state.py`](../../science_graphrag/agent/subagents/isolated_subagent_state.py); merge ног в [`specialist_results_v3.py`](../../science_graphrag/agent/subagents/specialist_results_v3.py) + хуки в [`retrieval_agent.py`](../../science_graphrag/agent/graph/nodes/retrieval_agent.py); **tool_use_summary** — [`tool_use_summary.py`](../../science_graphrag/agent/tool_use_summary.py) + [`tool_execution_pipeline.py`](../../science_graphrag/agent/tool_execution_pipeline.py), side-LLM через `forked_runtime.run_side_llm_chat`, телеметрия `tool_use_summary_*` в [`debug_events_telemetry.py`](../../science_graphrag/agent/debug_events_telemetry.py). Тесты: [`tests/agent/test_t4_subagents_and_tool_summary.py`](../../tests/agent/test_t4_subagents_and_tool_summary.py), расширение [`test_subagent_output_contract.py`](../../tests/agent/test_subagent_output_contract.py). **Quality-pass (тот же день):** corpus-explore не стартует без полного набора whitelist-инструментов (`issues: corpus_explore_missing_tools:…`); research-plan — fail только при пустом tool-list; предупреждения envelope для неуспешных child (`corpus_explore_child_*`, `research_plan_child_*`) в [`runtime.py`](../../science_graphrag/agent/runtime.py); санитизация side-LLM JSON summary; один проход по `ToolMessage` после батча (summary → `sse_hint`); struct debt — **[OPEN] Deduplicate subagent runtime micro-helpers** в [`refactor-backend.md`](../backlog/refactor-backend.md).

**Операционный guardrail 2026-05-07 (agent live/heavy e2e):** запускать тяжёлые live/e2e проверки только с явным `AGENT_LIVE_BASE=http://...` (обычно `http://127.0.0.1:18787` для stable live-check или `http://127.0.0.1:8787` для web/dev proxy), чтобы исключить ошибки неверного base URL.

**Дополнение 2026-05-07 (orchestration efficiency — `v3_cv_fanout_dual_evidence`):** в [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) добавлен узкий deterministic handoff `retrieval_completion_dual_evidence_compare` после `2× find_works + 2× paper_profile` на compare/dual-evidence промптах (с guard’ами против обязательного GOST/quote-path). Отдельно сужена `_graph_intent_heuristic` в [`deterministic.py`](../../science_graphrag/agent/coordination/deterministic.py): больше не считаем boilerplate `citations` / `Finish with … citations` за graph-intent (ложный первый hop в `graph_agent` на OD acceptance-промпте). Дополнительно в `supervisor_node` добавлен first-hop force `workspace_dual_evidence_first_hop`, перекрывающий ложный `route_hint=graph_agent` от `hybrid_v1` LLM на OD compare-промптах. Регрессии: `tests/agent/test_supervisor_routing.py`, `tests/agent/test_graph_intent_heuristic.py`.

**Дополнение 2026-05-07 (orchestration stabilization plan — структурный):** разбор причин нестабильности маршрутизации (architectural vs «дожать») и план работ — отдельный документ [`orchestration-stabilization-plan-2026-05-07.md`](./orchestration-stabilization-plan-2026-05-07.md). Ключевые архитектурные оси: **RoutePlan + типизированные `QuestionFeatures`** (вместо substring-латок в `supervisor_node`), **single supervisor backbone** под `/v2/agent/query` (устранение feature-flag fragmentation между `langgraph_research_v1` и `langgraph_supervisor_v3`), **graceful degradation** при LLM-hang (per-tool deadline + расширенный salvage). Связано с backlog [`refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN] Reduce supervisor route churn`, `[OPEN] Simplify writer_agent into terminal synthesis seam`, `[OPEN] Split permission/validation phase out of build_tool_execution_node`, `[OPEN] Split oversized tool_search.py`.

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

**Уточнение по openclaude (важно для §9.4 / §10.1):** в openclaude реализованы **два взаимоисключающих** режима субагентов, не один:
- **Coordinator** (`src/coordinator/coordinatorMode.ts`, `workerAgent.ts`): явная диспетчеризация через `AgentTool` + `SendMessageTool` + `TaskStopTool`, отдельный `getCoordinatorSystemPrompt`, типизированные `worker`-результаты, async-by-default.
- **Fork** (`src/tools/AgentTool/forkSubagent.ts`, `runForkedAgent`): неявное наследование `system+tools+messages prefix` (cache-share!), text-only / no-tools контракт у форка, recursive-fork guard.

Они **взаимоисключающие** (если активен coordinator — fork-эксперимент отключён). Это критично при выборе runtime для нашего Epic B — см. §10.1 (детальный contrast) и §9.4 B0 (выбор траектории).

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
| **Cache-safe forked-agent pattern** (`runForkedAgent`) | Все side-LLM вызовы (compact/away/memory/dream/agent_summary) идут с identical cache key (system+tools+messages prefix), ради 70–95% read-token reuse | **Высокий ROI** для нашей экономики LLM. См. §10.2 — обязательное условие production-ready Epic A1 (`thread_insights`) и L4 LLM compact. Маппинг: обернуть `thread_insights.py` и `llm_history_compact.py` в общий cache-safe payload, измерить `side_llm_cache_read_ratio`. |
| **Agent definitions on disk + frontmatter** (`.claude/agents/*.md`) | Декларативные роли (tools/disallowedTools/model/permissionMode/whenToUse) без правки кода | См. §10.7 — точка расширения SciGraph для пользовательских ролей (`librarian`, `bibliographer`, `methodology-checker`); расширяет матрицу из §6.1.4 без жёсткого вшивания в config. |
| **Subagent prompt discipline** (synthesize-not-delegate, Scope/Result/VERDICT) | Жёсткий output contract субагентов: «echo scope → result → key findings → VERDICT» + запрет на handoff-фразы | См. §10.4 — берём в наш supervisor → specialist промпт сразу в B2 (writer contract). Контракт-тест на regex выхода. |
| **Per-call `canUseTool` callback** | Permission policy на уровне вызова, не только режима (per-fork: `createMemoryFileCanUseTool(path)`, `createCompactCanUseTool()` deny-all, etc.) | См. §10.7 — расширение текущего `effective_tool_policy` опциональным callback'ом для finer control в Epic B (например, claim-verifier deny-write на cypher_query). |
| **Microcompaction time-trigger** | Если gap > N min между ходами — server cache cold анyway → content-clear старых tool results | См. §10.5 — простой портируемый паттерн в `tool_message_compact.py` (без зависимости от Anthropic-specific `cache_edits`). |
| **PTL retry + group-by-API-round** | Структурный примитив `groupMessagesByApiRound` + `truncateHeadForPTLRetry` | См. §10.5 — вводим как first-class в `compaction.py` (детерминированное urезание по группам, retry до 3). |

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
| 2026-05-06 | **Deep-dive openclaude vs план (повторный проход):** уточнён §1.3 (две взаимоисключающие модели субагентов: coordinator vs fork); расширена таблица §5 (cache-safe forked-agent pattern, agent definitions on disk, subagent prompt discipline, per-call canUseTool, microcompact time-trigger, PTL retry + group-by-round); §9.4 B0 получил явную развилку coordinator vs fork с recommendation `fork-mode as baseline`; §9.4 B1 расширен `<task-notification>` envelope и periodic progress label (AgentSummary-pattern); §9.5.1 пополнен P0.3 (web_search/web_fetch с academic allowlist), P0.4 (DOI/OpenAlex resolver), P1.3 (research_plan_write), P1.4 (ask_user_question), P1.5 (claim_verification subagent), P2.3 (plan mode), P2.4 (brief). Добавлен **§10** — deep-dive по паттернам, не закрытым ранее: coordinator/fork contrast, cache-safe side-LLM, built-in subagent catalog → SciGraph mapping, prompt discipline, compaction hardening (microcompact triggers / post-compact restoration / PTL retry / sanitizers), hook surface, agent registry + per-call canUseTool, `<task-notification>` envelope, обновлённый release train (T1–T5) и cross-refs. |
| 2026-05-06 | Добавлен **§11**: сводный actionable чеклист по Train T1–T5 (`[x] / [~] / [ ]` статусы), отдельный pool §11.6 для tool-parity backlog, §11.0 — закрытое, §11.7 — stop-conditions reminder. Источник правды по прогрессу для §9.3/§9.4/§9.5/§9.5.1/§10. |
| 2026-05-07 | **Train T2 (§11.2):** зафиксированы комментарии к закрытому срезу §10.4 (writer prompt + `subagent_output_contract`, guard в `FinalAnswerTool.run`) и §10.5.1–§10.5.2 / §10.5.4 (microcompact по `client_idle_ms`, post-compact paper sources + `runtime.py` после digest, pre-compact sanitizers); агрегация `extract_runtime_telemetry_from_debug_events` перенесена в `agent/debug_events_telemetry.py` (SSE + sync parity в `payloads.py`). Тесты: `test_subagent_output_contract`, `test_final_answer_args`, `test_tool_message_compact`, `test_message_sanitizers`, `test_context_session`, `test_debug_events_telemetry`. |
| 2026-05-07 | **Tool surfaces T2 (§11.6 / §9.5.1):** gated MCP quartet (`SCIENCE_GRAPHRAG_AGENT_MCP_TOOLS_ENABLED` + `agent_mcp_http_base_url` / denylist / SSE `mcp_audit`), bounded `lsp_tool` (`agent_lsp_server_argv`, stdio **Content-Length** framing + timeout/budget), `runtime_monitor_get` + in-proc registry, `research_plan_write` → `session_meta.research_plan` + SSE `research_plan_updated`, `ask_user_question` + API `user_structured_answer` + debug `user_answered`, `brief` → `run_metadata.brief`; `thread_id` для session tools через `runtime_context` в `tool_execution_pipeline`. Тесты: `tests/agent/test_product_surfaces.py`, обновлены `test_tool_manifest_sync`. |
| 2026-05-07 | **Train T3 §11.3 (B0/B1 lifecycle + observability) — зафиксировано в чеклисте:** ADR `docs/adr/028-agent-runtime-v3-subagents.md`, `notification.py` / `lifecycle.py` / `sidechain_transcript.py`, интеграция в `supervisor.py`, `writer_agent.py` (terminal task-notification), `stream_lifecycle.py` + sync `runtime.py`/`payloads.py`, trace-review (`subagent_lifecycle_missing_count`, …), bench `eval/chat_agent/subagent_runtime_fork_vs_coordinator_bench.py` + регрессия по missing. **Quality-pass (тот же день):** без дублирования sidechain-событий успешного завершения ноги (`routing_leg_finished` в stream только если lifecycle enhanced выключен — иначе канон JSONL `routing_leg_completed` из `lifecycle.py`); при ошибке сборки envelope — JSONL `task_notification_rollback`; SSE `subagent_task_notification` всегда с каноническим `type` поверх зеркалируемого payload; мелкие правки pylint (`anext`, locals). |
| 2026-05-07 | **Quality pass / verification:** локально зелёные таргетные pytest-наборы по runtime/SSE/registry/hooks/tool-surfaces (`49 passed` + отдельно `test_api_agent_v2_stream_parity.py`, `test_allowed_tools_matrix.py`), quick live `agent_trace_review.py --profile quick --skip-e2e` на dev-контуре `http://127.0.0.1:18787` — **pass** (`eval/results/trace-review-t3-quality-pass.json`), baseline compare — **pass** (`eval/results/trace-regression-t3-quality-pass.json`). В ходе добивки: нормализация single-string `tools/disallowedTools` в registry, stricter validation для `ask_user_question` (>=2 options, unique ids), framed stdio для `lsp_tool`. |
| 2026-05-07 | **Live/eval hardening (§11.2–§11.5 / §10.10):** `agent_trace_review.py --suite acceptance` + `acceptance_summary_v1`; OD E2E `--suite acceptance`; `http_suite` probes `agent_v2_fanout_probe` / `agent_v2_malicious_deny`; `trace_regression_compare.py` — `--max-latency-p95-regress-ratio`, `--min-live-trust-signal-delta`, fail `subagent_lifecycle_missing_increase`; rollout note `eval/results/runtime-v3-rollout-decision-2026-05-07.md`; обновлены `README_trace_review.md`, §11 чеклист, тесты `test_trace_review_schema` / `test_trace_regression_compare`. |
| 2026-05-07 | **Train T4 (§11.4 / §10.3 / §10.9) — закрыт кодовый срез + quality-pass:** см. шапку документа («Дополнение 2026-05-07 (Train T4…)») и обновлённые комментарии в **§11.4** (B3, corpus_explore, research_plan, tool_use_summary). Live-gate «строгий token ceiling для child» по-прежнему `[~]` в §11.4 B3. |
| 2026-05-08 | **Tool-parity acceptance (§11.6 / §9.5.1) — доводка до product/trace parity:** `runtime_monitor_get` — адаптеры ingest + benchmark task store, поля `source`/`timeout_hit`, телеметрия `runtime_monitor_audit` в `run_metadata`, проекция в `trace_review_schema` / live-check; `research_plan` — снимок в `run_metadata` (sync + final SSE), Ask UI **`AskResearchPlanPanel`** + `stream_events` hint; **`ask_user_question`** — SSE-hint с массивом `questions`, Ask **`AskUserQuestionForm`**, `user_structured_answer` в stream и **JSON** `/v2/agent/query`, `open_structured_question` в turn `details`, server sync через `compactAskTurnDetailsForSync` / `entriesToApiTurns`; **`brief`** — превью в **`ChatSessionSidebar`**; MCP — `test_mcp_call_tool_json_rpc_ok`, `docs/agent/mcp_runtime_acceptance.md`, rollup-тесты `mcp_audit_summary` в `test_debug_events_telemetry.py`; LSP — tier **`agent_tools_lsp`** (`lsp_nav_symbol_stub`), mock-runner для `lsp_tool`, `docs/agent/lsp_tool_compatibility.md`. UI-тесты: `askStreamArtifacts`, `askSessionServerBridge.details`, `useAgentStream` / `useAskSubmit`. *Вне этого среза остаются: полноценный live MCP e2e, Playwright product E2E ask-user, зеркалирование в `agentRunViewModel`.* |
| 2026-05-08 | **§11 чеклист — синхронизация с выполненным live/eval hardening:** в §11.2 пункт gate claim_verification → `[x]` + комментарий (операторский nightly/compare vs baseline, acceptance `min_claim_verification_parse_rate`); §11.3 B0 — уточнён live export (`--suite acceptance`, §7); §11.4 B2/B3 — комментарии machine-checkable vs LLM-judge и тесты `test_trace_review_schema`; §11.5 B4/C3/§10.10 — комментарии quality-pass (`http_suite`, `test_http_suite_safety.py`, compare-флаги); §11.7 — bullet про `AGENT_LIVE_WORKSPACE_ID`; шапка документа — блок **live/eval hardening + quality-pass**; строка **«Текущий счёт»** — оценка ~57/~59 + примечание 05-08 по §11.6. |

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

- **Status (2026-05-06): DONE (Train T1 slice).**
- Выполнено:
  - в `docs/specs/agent-chat-v1.md` добавлен раздел `Summarization modes`;
  - зафиксированы `turn_loop_memory` / `thread_insights_compact` / `hybrid`;
  - добавлены негативные кейсы и пометка о том, что prompt precedence остаётся в A2.

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

- **Status (2026-05-06): A1 hardening delivered in-repo (server-side artifact + resilience); A2 remains prompt path.**
- **Scope split:** A1 = `thread_insight` snapshot, persistence, post-turn refresh policy, audit/control telemetry, compaction boundary, circuit-breaker, L4 PTL retry + `message_groups` integrity helpers. **A2** = `<thread_insight>` injection, precedence matrix, `insight_fallback_reason` / conflict markers in prompt + run_metadata. **A3** = full long-thread eval lane + numeric SLO gate (beyond minimal synthetic harness).
- Выполнено:
  - добавлен `science_graphrag/agent/context/thread_insights.py` (deterministic chunking + bounded parallel workers + synthesis);
  - persistence в `session_meta.thread_insight` через `apply_thread_insight_snapshot` (memory + redis backend);
  - post-turn refresh под feature-flag `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED`;
  - `run_metadata.thread_insight_audit` в sync/SSE;
  - freshness (`turn_delta`, optional TTL, `high_churn`), `thread_insight_control`, `stale_reason` / `refresh_decision` в audit/control;
  - `compaction_lock` + insight circuit-breaker; L4 PTL retry (`agent_llm_full_history_compact_ptl_max_retries`); `science_graphrag/agent/context/message_groups.py` + `science_graphrag/agent/forked_runtime.py` seam stub.
- Осталось до полного **A2**:
  - prompt injection `<thread_insight>` и precedence matrix.

- Добавить модуль `agent/context/thread_insights.py`:
  - windowing длинного треда на semantic chunks;
  - parallel summarize workers (bounded concurrency, timeout/cancel-safe);
  - final synthesis в единый `thread_insight`.
- Роли memory-слоёв разделить явно:
  - `thread_insight` = long-thread synthesis и anchor для recall/consistency;
  - `session_summary` = rolling continuity для короткого turn-loop.
- Добавить `session_backend` поля:
  - `thread_insight.current`,
  - `thread_insight.version`,
  - `thread_insight.sources` (chunk ids / turn range),
  - `thread_insight.generated_at`,
  - `thread_insight.section_budgets`,
  - `thread_insight.compaction_boundary`.
- Добавить policy freshness:
  - invalidation на N новых turn-ов + TTL;
  - forced refresh при high-churn tool traces;
  - в audit писать `stale_reason` (`turn_delta|ttl|high_churn|manual`).
- Добавить runtime hardening паттерны из openclaude:
  - circuit breaker для repeated compaction failures (`max_consecutive_failures`);
  - PTL retry policy с bounded head truncation (`max_ptl_retries`);
  - инварианты целостности `tool_use/tool_result` при chunk/drop/rebuild;
  - явный compaction boundary artifact (`trigger`, `pre_tokens`, `source_range`, `preserved_segment`).

**Acceptance A1:** на длинном synthetic треде строится `thread_insight` с воспроизводимым audit trail (`chunk_count`, `worker_count`, `generation_ms`, `source_range`, `stale_reason`, `boundary_trigger`) и детерминированной section-budget policy.

#### A2. Prompt integration + fallback policy

- Расширить `format_user_with_memory`:
  - при наличии свежего `thread_insight` инжектить компактный `<thread_insight>` блок;
  - при stale/failed insight откат к текущему `session_summary`;
  - при circuit-breaker open сразу принудительный fallback в `session_summary`.
- Добавить deterministic precedence matrix:
  - `turn_digest` (latest) > `thread_insight` (fresh) > `session_summary`;
  - если insight конфликтует с последним `turn_digest`, приоритет у свежих turn facts;
  - конфликтные claim-ы помечать как `conflicted` до следующего refresh.
- В run_metadata писать:
  - `insight_conflict_resolved=true/false`,
  - `insight_fallback_reason`,
  - `ptl_retry_count`.

**Acceptance A2:** deterministic precedence policy покрыта тестами; нет silent override свежих фактов старым insight.

#### A3. Eval + gate

- Новый набор в `eval/chat_agent`:
  - long-thread retrieval,
  - context drift detection,
  - summary hallucination rejection,
  - claim-level grounding checks (claim -> source chunk/tool evidence).
- Метрики:
  - `insight_recall@k`,
  - `stale_summary_error_rate`,
  - `compaction_churn_delta`,
  - latency overhead p50/p95,
  - `insight_stale_reason_rate`,
  - `insight_conflict_resolved_rate`,
  - `ptl_retry_rate`,
  - `compaction_circuit_breaker_trips`.
- Gate:
  - trust/verdict не хуже baseline,
  - p95 latency рост в пределах согласованного бюджета,
  - claim grounding precision/recall не ниже согласованного SLO.

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
- **Развилка subagent runtime** (см. §10.1): выбрать одну из траекторий или поддержать обе под флагами:
  - **(а) Coordinator-mode** — явный `spawn_subagent(role, task)` + `send_message(subagent_id)` + `task_stop` (как `coordinatorMode.ts` в openclaude). Чистая observability через `subagent_id`/`task_id`, async-by-default, явные лейблы лайфцикла. Цена: дополнительный state machine для tasks + ToolUse-обёртка.
  - **(б) Fork-mode** — неявное наследование `system + tools + messages prefix` родителя (`runForkedAgent`/`forkSubagent.ts`). **Cache-share** на 70–95% read-tokens (соответствует §10.2). text-only output контракт + recursive-fork guard. Цена: меньше явных API-границ, сложнее различать в trace, нельзя continue-talk-back.
  - **Рекомендация:** для SciGraph экономика LLM критична → **fork-mode как baseline** для side-LLM (thread_insights, away_summary, claim verification), **coordinator-mode** добавить только при явном продукт-сценарии длинного research-турна с пользовательской возможностью «продолжи специалиста». Эту дихотомию закрепить в ADR.
- В ADR явно зафиксировать:
  - prompt-cache контракт fork-режима (что и почему НЕ меняется в child системно: тот же tool array, без `maxOutputTokens`, тот же thinking config — см. §10.2);
  - изоляция subagent transcript'а (sidechain, как в §6.1.5) — обязательна;
  - pull-back-to-parent контракт (что именно из child carry-back, как избежать flooding — см. B3).

**Acceptance B0:** ADR с финальным вариантом API/compatibility и rollback strategy + benchmark на одинаковом сценарии (latency, cache hit, missing-state events) для двух траекторий перед фиксацией.

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
- **Periodic progress label** (UX-паттерн `AgentSummary` в openclaude, `services/AgentSummary/agentSummary.ts`): для долгих background subagents запускать **каждые ~30 сек** lightweight cache-safe forked-агент, который выдаёт **одну фразу** прогресса (например, `«читает paper_quote_search для PMID:12345»`, `«проверяет цитату [3] в claim-verifier»`). Печатается в SSE как `subagent_progress_label`. **Контракт:** ride на parent prompt cache (см. §10.2), отдельная gating через `agent_subagent_progress_label_enabled`, throttle ≥ 30s, drop при отсутствии нового прогресса.
- **`<task-notification>` envelope для completion** (см. §10.10): когда child завершается, в parent message stream вставляется **user-role** message с XML конвертом `<task-notification task-id=… status=… subagent=…><summary/><result/><usage/></task-notification>`. Это унифицирует «событие завершения» как часть transcript'а, не как боковой канал; делает следующий ход родителя tractable для классификатора и trace-review.
- **Promptless spawn rules** (как в openclaude `prompt.ts` для AgentTool):
  - read-only задачи (corpus_explore, claim_verification, paper_profile fanout) — в параллель;
  - write-heavy / state-mutating — последовательно;
  - verification — независимо от основного потока, всегда fresh fork.

**Acceptance B1:** live run с 2+ параллельными subagents даёт полный lifecycle в SSE + trace-review без missing states; `subagent_progress_label` появляется минимум 1 раз для child длительностью > 30s; `<task-notification>` присутствует в parent transcript на каждый завершившийся child.

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

- **Status (2026-05-06): PARTIAL (Train T1 rules-first increment).**
- Выполнено:
  - `tool_search` учитывает discovered tools из message history (`AIMessage.tool_calls` / `ToolMessage`);
  - merge discovered names происходит детерминированно перед session carry-over;
  - в `tool_search_result` добавлены `message_discovery_tools` / `message_discovery_merged`.
- Осталось до полного C0/C2 контракта:
  - strict deferred activation policy (`only-on-discovery`) как отдельный runtime contract;
  - расширенная telemetry по activation/miss на lane-уровне.

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

> **Синхронизация с §11.6 (2026-05-07, уточнение 2026-05-08):** пункты P0.1–P0.2, P1.2–P1.4, P2.4 в **§11.6** отмечены `[x]` как **seam + заявленный acceptance-slice**; блоки **«Статус SciGraph»** ниже обновлены **2026-05-08** — зафиксировано, что закрыто в коде/тестах/UI и что остаётся **rollout / optional e2e** (real MCP server, Playwright ask-flow, `agentRunViewModel`).

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
   - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` **seam + CI-acceptance** — то же, что выше, плюс: агрегат **`mcp_audit_summary`** в `run_metadata` (тест `test_debug_events_telemetry.py`), интеграционный тест **`test_mcp_call_tool_json_rpc_ok`** (stub `httpx`), документ **`docs/agent/mcp_runtime_acceptance.md`** (unconfigured/deny/success + граница `mcp_auth`). **Live e2e с реальным MCP server** по-прежнему **rollout / staging**, не гейт CI.

2. **LSP tool (read-only, bounded)**
   - Scope:
     - symbol lookup / references / go-to-definition в sandboxed read-only режиме.
   - Why:
     - улучшает code-aware retrieval и уменьшает ложные tool hops в codebase workflows.
   - Acceptance:
     - есть bounded latency/timeout policy;
     - trace фиксирует тип LSP операции и payload budget;
     - benchmark lane показывает не хуже baseline по verdict/trust при code-navigation вопросах.
  - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` **seam + eval lane (mini)** — read-only stdio JSON-RPC, framing, `lsp_audit`, `lsp_unconfigured` без argv. Добавлены: tier **`agent_tools_lsp`** (`tests/fixtures/benchmarks/agent_tools_v1/lsp_nav_symbol_stub`), mock-ветка **`eval/agent_tools/runner.py`** для честного `args_match` по `lsp_tool`, документ **`docs/agent/lsp_tool_compatibility.md`** (границы совместимости). Универсальная совместимость со **всеми** LSP-серверами — по-прежнему **не обещается**.

3. **Web research tools (`web_search`, `web_fetch`)** — для research-flow поверх корпуса
   - Scope:
     - `web_search(query, allowed_domains?, blocked_domains?, max_results)` — с поддержкой domain allowlist/denylist (как `WebSearchTool` в openclaude);
     - `web_fetch(url, prompt)` — load + summarize через small/fast model (как `WebFetchTool`), с redirect handling, allow/deny на хосты, cache на 10–15 мин по URL;
     - адаптеры под provider (Tavily/Serper/Brave/native MCP) с `transient_error → fallback` policy (как `isTransientError` в openclaude).
   - Why:
     - SciGraph — research product; пользователю часто нужно найти **новые** статьи/preprints вне локального корпуса; сейчас этот сценарий не закрыт;
     - дополняет `find_works`/`paper_quote_search` (локальный корпус) внешним каналом;
     - даёт основу для будущего «дополни корпус по DOI/url» workflow.
   - Acceptance:
     - tools видны в `tool_search` shortlist под feature-flag `agent_web_research_tools_enabled`;
     - SSE event `web_fetched` с url/status/bytes/cache-hit;
     - trust-audit lane не деградирует (важно: web-source ≠ corpus-grounded; маркировать в `evidence_origin`);
     - allowlist по умолчанию academic-only (arxiv.org, pubmed.ncbi.nlm.nih.gov, semanticscholar.org, doi.org, openreview.net, biorxiv.org).
   - **Статус SciGraph:** см. **§11.6 P0.3** — закрыто в продуктовом срезе под feature flag; детали acceptance (trust-audit lane, `evidence_origin`) — в Wave/Train логах и тестах web-fetch path.

4. **DOI / OpenAlex resolver tool** — bridge между web и graph корпусом
   - Scope:
     - `doi_resolver(doi_or_url)` — нормализация → metadata (title/authors/year/venue/abstract) + canonical paper_id попытка mapping в локальный workspace;
     - source: OpenAlex API + Crossref как fallback.
   - Why:
     - закрывает разрыв «у пользователя ссылка/DOI — нет в нашем graph»;
     - пред-этап для решения «можно ли импортировать в workspace» (out-of-scope для tool, in-scope для UX);
     - удобный complement к `web_fetch` (fetch — content, doi_resolver — structured metadata).
   - Acceptance:
     - SSE `doi_resolved` с `paper_id_in_workspace` (если найдено);
     - `paper_profile` вызывается автоматически если paper_id найден;
     - rate-limit policy по OpenAlex (документировать).
   - **Статус SciGraph:** см. **§11.6 P0.4** — `doi_resolver` + SSE `doi_resolved`; workspace/graph mapping — по текущему контракту в коде (см. комментарий в §11.6).

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
   - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` **seam + SoT-адаптеры + trace** — `runtime_monitor_get`: fallback на **ingest job registry** и **benchmark task store** (`runtime_monitor_sources.py`), in-proc snapshot для unit-тестов; в payload/SSE — **`source`**, **`timeout_hit`**; телеметрия **`runtime_monitor_audit`** в `run_metadata`; поля в **`scripts/live_check/trace_review_schema.py`** и регрессионных тестах схемы. *Дальнейшее:* расширение покрытия live-case'ами под конкретные ingest/benchmark SKU — по мере появления сценариев.

3. **`research_plan_write` (TodoWrite-аналог)** — структурированный progress checklist
   - Scope:
     - агент создаёт/обновляет JSON-список TODO для длинных multi-step research turn'ов;
     - формат: `{id, content, status: pending|in_progress|completed|cancelled}` (как `TodoWriteTool` в openclaude);
     - persistence в `session_meta.research_plan`.
   - Why:
     - пользователь видит план хода → меньше «чёрного ящика» в долгих ходах;
     - агент сам себе structured memory для multi-hop reasoning (что уже сделано / что осталось).
   - Acceptance:
     - SSE `research_plan_updated` event;
     - UI рендерит чеклист в side-panel чата;
     - после `context_compacted` план сохраняется (re-attach как §10.5).
   - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` **backend + Ask UI** — persistence / reinject / SSE без изменений по смыслу; добавлены: зеркало плана в **`run_metadata.research_plan`** при sync/final (`payloads.py` / `stream_lifecycle.py`), панель **`AskResearchPlanPanel`** в **`AskPanel`**, подсказка из **`research_plan_updated`** в `stream_events` (`askStreamArtifacts.js`). Post-compact re-attach — см. §10.5 / `post_compact`.

4. **`ask_user_question` (structured multi-choice)** — снижение ambiguity
   - Scope:
     - tool с аргументами `{questions: [{id, prompt, options: [{id, label}], allow_multiple?}]}` (как `AskUserQuestionTool` в openclaude);
     - SSE `user_question_asked`, ожидание structured `user_answered` payload.
   - Why:
     - текущий способ задать вопрос — простая assistant message; UI/UX выигрывают от детерминированных вариантов;
     - снижает неоднозначность в сценариях «хочешь по PMC ID или по названию?», «какой год / какой журнал?».
   - Acceptance:
     - frontend получает structured payload и рендерит UI-форму;
     - ответ возвращается обратно как tool-result в transcript;
     - тест E2E: agent → ask → user picks → continue.
  - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` **backend + Ask UI + transport** — tool + pending + API + debug без изменений по смыслу; добавлены: **SSE-hint `user_question_asked` с массивом `questions`** (без доп. round-trip), **`AskUserQuestionForm`** в **`ChatMessageThread`**, отправка **`user_structured_answer`** в **`useAgentStream`** (SSE) и **`useAskSubmit`** (JSON `/v2/agent/query`), сохранение **`open_structured_question`** в turn `details` + приоритет разрешения из **`stream_events`**, server sync **`compactAskTurnDetailsForSync` / `apiTurnToEntry`**, unit-тесты **`askStreamArtifacts`**, **`askSessionServerBridge.details`**, **`useAskSubmit` / `useAgentStream`**, `test_ask_user_question_sse_hint_lists_questions`. **Playwright / полный product E2E** «клик по UI» — опционально; **`agentRunViewModel`** не дублировал consumption — при необходимости отдельный малый PR.

5. **`claim_verification` subagent** (read-only adversarial probe)
   - Scope:
     - lightweight forked subagent (см. §10.2 cache-safe pattern) с deny-write tool policy: только `paper_quote_search`, `paper_profile`, `find_works`;
     - запускается на финальный writer ответ, проверяет цитаты/grounding, выдаёт `VERDICT: PASS|FAIL|PARTIAL` + список конкретных проблем (см. §10.4 prompt discipline).
   - Why:
     - это **наша** версия `verification` агента из openclaude built-ins, специализированная под citation grounding;
     - закрывает CH-trust audit на уровне runtime (а не только offline benchmark);
     - дешёвый ход (cache-share, малая модель).
   - Acceptance:
     - SSE `claim_verification_result` с verdict + issues;
     - feature-flag `agent_claim_verification_enabled`;
     - trust-audit lane показывает рост trust_signal без latency регрессии > 15%.

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

3. **Plan mode (`enter_plan_mode` / `exit_plan_mode`)**
   - Scope:
     - режим «agent только планирует, не действует» (read-only): корпус читать можно, граф писать нельзя, никаких side-effect tool calls;
     - exit-flow: пользователь approve plan → переключение в act-mode (как `EnterPlanMode`/`ExitPlanMode` в openclaude).
   - Why:
     - для долгих research-сессий: сначала approve plan (research outline), потом execute;
     - снижает риск долгого «не туда»;
     - синергия с `research_plan_write` (P1.3).
   - Acceptance:
     - SSE `plan_mode_entered`/`plan_mode_exited`;
     - в plan-mode tool policy жёстко ограничивает — нет `cypher_query` write, нет ingestion endpoints;
     - eval lane: на длинных вопросах plan-mode дешевле в latency на ≥ 30% при сохранении trust.

4. **`brief` (synthetic output / commit-style summary)**
   - Scope:
     - дополнительный финальный краткий summary хода для habr-export / UI (1–3 предложения, без ссылок-плумбинга);
     - отдельно от `final_answer` (которое для пользователя), `brief` — для downstream (sharing, history index, mini-card).
   - Why:
     - UX-улучшение для history-list / sharing;
     - снижает повторное чтение пользователем длинных ответов когда нужен только overview.
   - Acceptance:
     - в `run_metadata.brief` (≤ 240 chars);
     - используется в Ask history side-panel.
   - **Статус SciGraph (2026-05-07, 2026-05-08):** `[x]` — tool + `run_metadata.brief` без изменений по смыслу; **Ask:** превью **`run_metadata.brief`** в списке сессий (**`ChatSessionSidebar`**, вторичная строка), синхронизация slim-`details` на `/v1/ask-sessions`. Полноценный «rich turn» для всех полей истории — по мере необходимости (сейчас — brief + plan + structured + хвост `stream_events`).

#### Out-of-scope до отдельного ADR

- `team_create` / `team_delete`,
- remote triggers,
- REPL-like execution surfaces.

Причина: высокий security/ops overhead при низком краткосрочном эффекте для текущего parity-трека.

### 9.6 Порядок внедрения (release train)

1. **Train T1 (2 недели):** A0/A1/C0 — schema/freshness/telemetry contracts + thread-insights skeleton + discovery-aware tool loading.
2. **Train T2 (2 недели):** A2/A3/C1 — fallback/preference policy, prompt integration, claim-grounding eval gates, hybrid selector.
3. **Train T3 (2-3 недели):** B0/B1 + A-advanced — ADR + runtime spawn primitive + lifecycle observability + advanced summarization optimizations (incremental insight updates, contradiction-aware synthesis).
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
| 2026-05-06 | Отмечен фактический статус Train T1 implementation slice: `A0=DONE`, `A1=PARTIAL (skeleton)`, `C0=PARTIAL (rules-first message discovery)`; добавлены явные remaining до A2/C2. |
| 2026-05-06 | Deep-dive дополнение по заимствованиям из `openclaude` для **Epic A**: добавлены circuit-breaker/PTL-retry/invariant-guards/compaction-boundary, freshness+precedence contract, claim-level grounding eval и расширенные telemetry метрики; обновлён release train `§9.6` (T1/T2/T3). |
| 2026-05-06 | Добавлен **§9.5.1**: `Tool parity backlog (openclaude-reference)` с приоритетами P0/P1/P2, acceptance-критериями и out-of-scope списком. |
| 2026-05-06 | Добавлен **§9**: closure plan по исходным целям (smart summarization parity, real subagent runtime v3, tool search parity), с epic-структурой, acceptance/gates, release train и stop-conditions против формального закрытия. |
| 2026-05-06 | **Второй deep-dive проход openclaude → план:** уточнены §1.3 (coordinator vs fork — две взаимоисключающие модели), §5 (расширена таблица переноса), §9.4 B0/B1 (явная развилка subagent runtime + `<task-notification>` envelope + periodic progress label), §9.5.1 (добавлены P0.3 web tools, P0.4 DOI resolver, P1.3 research_plan_write, P1.4 ask_user_question, P1.5 claim_verification subagent, P2.3 plan mode, P2.4 brief). Добавлен **§10** — паттерны openclaude, не покрытые ранее: cache-safe side-LLM (`runForkedAgent`), built-in subagent catalog (corpus-explore / research-plan / claim-verification), strict prompt discipline (Scope/Result/VERDICT, anti-handoff guard), compaction hardening (microcompact time-trigger, post-compact paper sources restore, PTL retry + group-by-API-round, sanitizers), hook surface (PreCompact/PostCompact/SubagentStart/Stop), agent registry на диске + per-call canUseTool callback, `<task-notification>` envelope. Обновлены acceptance gates §10.10 и release train (§10.11) без сдвига существующих T1–T5. |
| 2026-05-06 | Добавлен **§11**: сводный actionable чеклист по Train T1–T5 со статусами `[x] / [~] / [ ]`, pool §11.6 для §9.5.1 tool-parity backlog, §11.0 (контекст «уже закрыто»), §11.7 (stop-conditions). Этот раздел становится точкой синхронизации статусов с §9.3/§9.4/§9.5/§9.5.1/§10. |
| 2026-05-07 | См. §7: комментарии к §11.2 §10.4–§10.5 (реализация + тесты + `debug_events_telemetry` / sync metadata parity). |
| 2026-05-07 | **§9.5.1:** у пунктов P0.1–P0.2, P1.2–P1.4, P2.4 добавлены блоки **«Статус SciGraph»** (что закрыто как backend/SSE seam vs что остаётся aspirational: real MCP e2e, LSP benchmark lane, UI для research plan / ask-user, Ask history для `brief`); вводный callout на **§11.6** как канон чеклиста. |
| 2026-05-08 | **§9.5.1 / §11.6:** обновлены **«Статус SciGraph»** и комментарии под `[x]` (см. также changelog в шапке §1 и строка **2026-05-08** там же) — зафиксирован tool-parity **acceptance closure**: monitor SoT, trace-review, Ask UI (plan / structured / brief preview), MCP/LSP тесты+доки+mini lane; явный хвост: live MCP e2e, Playwright, `agentRunViewModel`. |

---

## 10. Глубокая сверка с openclaude (паттерны, ещё не закрытые в плане)

Этот раздел — итог второго сравнительного прохода по дереву `openclaude/src/{coordinator,tools/AgentTool,services/{compact,SessionMemory,AgentSummary,extractMemories,autoDream,awaySummary,toolUseSummary,contextCollapse}}/` с прицелом на то, что **ещё не зафиксировано** в §1–§9. Каждый подраздел имеет конкретный SciGraph-маппинг и ссылки на place в наш план (Epic A/B/C / §6.1 / §9.5.1).

### 10.1 Subagent runtime: coordinator vs fork (детальный contrast)

В openclaude **две независимые** модели субагентов, и они **взаимоисключающие** — это критичный architectural fact для §9.4 B0:

| Свойство | Coordinator (`coordinatorMode.ts`, `workerAgent.ts`) | Fork (`forkSubagent.ts`, `runForkedAgent`) |
|---|---|---|
| Триггер | Явный tool call: `AgentTool({subagent_type, prompt})` | Неявный: `AgentTool` без `subagent_type` или `runForkedAgent` из любого места рантайма |
| System prompt child'а | **Свой** (`getCoordinatorWorkerSystemPrompt`), типизирован под role | **Тот же** что у parent (cache-share!) |
| Tools child'а | **Свои** (фильтрованный набор для role) | **Тот же tool array** (canUseTool callback ставит фактическую политику) |
| Messages prefix | **Свой** (минимальный context) | **Идентичный parent prefix** до точки fork → cache hit на 70–95% read tokens |
| Continuation | **Да** — `SendMessageTool(subagent_id, msg)` | **Нет** — fork работает один turn, output `text-only`, никаких tool calls |
| Stop | **Да** — `TaskStopTool(subagent_id)` | Только timeout / completion |
| Recursive nesting | Разрешено (с ограничениями) | **Запрещено** (`isInForkChild` guard, ошибка при попытке fork внутри fork) |
| Output format | Свободный (последний assistant message) | Strict text-only, обычно с разметкой `Scope:/Result:/VERDICT:` |
| Observability | Явный `task_id` lifecycle (start / progress / done / failed) | Sidechain transcript, имплицитный |
| Use case | «Делегируй задачу specialist'у и продолжи беседу с ним» | «Прогони лёгкий side-LLM на тёплом кэше» |

**Что это значит для SciGraph (Epic B0):**

- **Fork-mode** — это **базовый** паттерн для всех «внутренних LLM-вызовов» (thread_insights, away_summary, tool_use_summary, claim verification, full L4 compact). Дешёвый, простой, ride на тёплом кэше. Выбираем как **default**.
- **Coordinator-mode** — добавляем **только** под явный продукт-сценарий: «пользователь хочет вести беседу со specialist'ом» (например, "продолжи с librarian, найди ещё 3 источника"). Имеет смысл только в Epic B Train T4+, после того как fork-mode и merge contract стабилизированы.
- В ADR §9.4 B0 эту дихотомию закрепить: **fork-mode** обязательно; **coordinator-mode** — опционально с явным продукт-обоснованием.

### 10.2 Cache-safe side-LLM pattern (runForkedAgent)

Это центральный экономический паттерн openclaude. Все «вторичные» LLM-вызовы (compact summary, away summary, session memory update, extract memories, auto-dream, periodic AgentSummary, tool_use_summary) идут через `runForkedAgent` с **identical cache key** к parent ходу.

**Контракт cache-safe fork** (нарушение → cache invalidation → 5–10× стоимость):

1. **Тот же `system_prompt`** что у parent (даже если child делает другую задачу — cache принимает только идентичные префиксы).
2. **Тот же `tools` array** — даже если все будут отвергнуты через `canUseTool` callback.
3. **Тот же `model` и `thinking config`** — нельзя ставить `maxOutputTokens` (clамп `budget_tokens` → cache miss).
4. `forkContextMessages` — общий префикс messages с parent (до точки fork).
5. `promptMessages` — задание fork'а как отдельный suffix; именно он оплачивается полностью, всё остальное — cached read.
6. **Per-call `canUseTool` callback** — фактическая политика на уровне выполнения каждого tool call, без изменения tools array.

**SciGraph mapping (план):**

- **Train T1 hardening (Epic A1):**
  - обернуть `science_graphrag/agent/context/thread_insights.py` в общий `science_graphrag/agent/forked_runtime.py` helper, который:
    - принимает `parent_system`, `parent_tools`, `parent_messages_prefix`, `fork_prompt`, `fork_can_use_tool`;
    - возвращает completion, метрики кэша (cache_creation_tokens, cache_read_tokens), latency;
    - логирует `side_llm_cache_read_ratio`.
  - метрика `side_llm_cache_read_ratio` появляется в `trace-review-v1`.
  - gate: `>= 0.6` для `thread_insights`, `>= 0.8` для full L4 compact (когда вызывается через тот же helper).

- **Train T2 (Epic A2/A3):**
  - перевести `away_summary` (§6.1.7) и `agent_note` на тот же helper;
  - перевести L4 LLM compact (`llm_history_compact.py`) на тот же helper.

- **Train T3+ (Epic B):**
  - все subagent runs (verification, claim_check, corpus_explore из §10.3) — через тот же helper.

**Acceptance §10.2:** в trace-review-v1 каждый side-LLM call помечен `forked: true | false`; при `forked=true` гейт `side_llm_cache_read_ratio >= configured_threshold`.

### 10.3 Built-in subagent catalog → SciGraph projection

openclaude имеет каталог встроенных subagent ролей в `src/tools/AgentTool/built-in/*.ts`. Перенести **дословно** не имеет смысла (продукт другой), но мапятся в наши research-roles:

| openclaude built-in | Назначение | SciGraph аналог | Приоритет |
|---|---|---|---|
| `general-purpose` (full tools) | универсальный воркер | текущий `retrieval_agent` (workspace_inspect/find_works/paper_quote_search/idea_search) | already-done |
| `Explore` (read-only поиск, малая модель) | дешёвый fanout по поиску | новый **`corpus-explore`** subagent: read-only fanout `workspace_inspect` → `find_works` → `paper_quote_search` → `idea_search` на дешёвой модели | Train T3 (Epic B Train) |
| `Plan` (read-only архитектурное планирование) | декомпозиция сложного запроса на подзадачи | новый **`research-plan`** subagent: декомпозирует пользовательский вопрос на (а) sub-queries по корпусу, (б) sub-queries по графу, (в) writer-spec | Train T3 |
| `verification` (adversarial PASS/FAIL/PARTIAL) | проверка сделанного | новый **`claim-verification`** subagent: re-read цитат, проверка grounding, adversarial probes (см. §9.5.1 P1.5) | Train T2 (быстрый ROI) |
| `claude-code-guide` | продуктовая помощь | n/a | — |
| `worker` (coordinator-spawned typed) | универсальный coordinator-воркер | (опционально, только если Epic B B0 выбирает coordinator-режим) | Train T4+ |

**Контракт каждого SciGraph-subagent'а:**

1. **Self-contained prompt** (см. §10.4): всё, что нужно child'у, — в его prompt; родитель невидим.
2. **Cache-safe fork** (см. §10.2): system+tools+messages prefix общие с parent.
3. **Sidechain transcript** (§6.1.5): JSONL, не засоряет основной transcript.
4. **Strict output format** (§10.4): Scope/Result/Key sources/VERDICT.
5. **Per-call permission policy** (§10.7): `canUseTool` callback с deny-write для read-only ролей.

### 10.4 Subagent prompt discipline (что брать в промпты дословно)

openclaude в `src/tools/AgentTool/prompt.ts`, `coordinator/coordinatorMode.ts`, `services/*/prompts.ts` использует устойчивый набор директив, которые надо ставить в наши supervisor → specialist промпты:

1. **Synthesize, don't delegate.**
   > «Никогда не пиши "based on your findings" в адрес parent'а. Выпиши конкретику: что нашёл, какие источники, какой verdict.»
   
   У нас сейчас в supervisor → writer контракт это явно не прописано. **Action:** добавить в `science_graphrag/agent/graph/nodes/writer_agent.py` system prompt блок:
   
   > `Если specialist вернул резюме без конкретики — синтезируй сам, не просто пересказывай.`

2. **Self-contained scope.**
   Каждый subagent prompt должен включать всё нужное (workspace_id, paper_ids, claim_text, expected output format), parent context недоступен.

3. **Purpose statement.**
   > «Это нужно для bibliography / для quote-extraction / для adversarial claim check.»
   
   Помогает subagent'у настроить inline reasoning.

4. **Output format directive (strict):**
   ```
   Scope: <one-line echo задачи>
   Result: <тело ответа>
   Key sources: [paper_id, paper_id, ...]
   VERDICT: PASS | FAIL | PARTIAL  (только для verification subagent'ов)
   ```
   
   **Action:** контракт-тест в `tests/agent/test_subagent_output_contract.py`: regex match на `Scope:` и (для verification) `VERDICT:`.

5. **Concurrency rule (для §10.3 corpus-explore + research-plan):**
   - read-only задачи → параллельно;
   - write-heavy / state-mutating → последовательно;
   - verification — независимо.

6. **Continuation vs spawn-fresh (для Epic B B1):**
   - research → implementation continuation: тот же subagent;
   - research → narrow follow-up: spawn fresh (child наследует cache, не state);
   - verification: всегда fresh (защита от сговора).

7. **Anti-handoff guard (`classifyHandoffIfNeeded` в openclaude):**
   classifier на выходе subagent'а проверяет фразы вроде «please continue from here», «I leave the rest to you». При обнаружении — **prepend warning** к result. Защищает от ленивого handoff'а.
   
   **Action:** в Epic B Train T2 — добавить regex-detector + warning injection.

### 10.5 Compaction hardening (что усилить поверх §6.1 / §9.3)

**5.1 Microcompaction time-trigger** (`microCompact.ts` в openclaude):

Если gap между last assistant message и current request > N min — server cache cold anyway → content-clear все tool results кроме последних K. Простой, портируемый, без зависимости от Anthropic-specific `cache_edits` (который и так stub в open snapshot).

**SciGraph action:** добавить в `science_graphrag/agent/tool_message_compact.py`:
- параметры: `microcompact_time_gap_minutes` (default 10), `microcompact_keep_last_k_tool_results` (default 3);
- feature-flag `agent_tool_message_microcompact_time_trigger_enabled`;
- метрика `tool_message_microcompact_triggered_count` в trace-review.

**5.2 Post-compact restoration** (после `context_compacted`):

openclaude после compaction re-инжектит:
- Recently read files (top N by recency, capped by token budget)
- Plan file (`getPlan(agentId)`)
- Invoked skills (truncated)
- Discovered tools delta

**SciGraph mapping** (мы уже частично делаем discovered_tools §6.1.2; нужно расширить):
- (а) **Recent paper sources**: top N последних `paper_quote_search` / `idea_search` results (paper_id + краткий quote head) — capped budget;
- (б) **Active research_plan** (если §9.5.1 P1.3 имплементирован) — re-attach целиком;
- (в) **Discovered tools delta** — уже есть.

**Action:** добавить `science_graphrag/agent/context/post_compact_attachments.py` builder + integration в `format_user_with_memory`. Acceptance: `post_compact_paper_sources_restored_count` в trace-review.

**5.3 PTL retry + group-by-API-round** (`compact.ts` в openclaude — `truncateHeadForPTLRetry`, `groupMessagesByApiRound`):

Когда сама compaction request hits PTL → drop oldest API-round groups и retry. **API-round** = preamble (group 0) + каждый assistant turn + следующие до next assistant.

**SciGraph action:**
- ввести `science_graphrag/agent/context/message_groups.py` с `group_messages_by_api_round`;
- расширить `compaction.py` PTL retry policy (already mentioned в §9.3 A1) с использованием этого примитива;
- метрика `ptl_retry_count_per_compaction` в trace-review.

**5.4 Pre-compact sanitizers** (`stripImagesFromMessages`, `stripReinjectedAttachments`):

Перед summarize-LLM:
- drop images (для нашего кейса — почти не используются, но потенциально может появиться через `web_fetch`);
- drop tool attachments которые и так re-инжектятся после compact (избегать double-inclusion в summary).

**Action:** утилита `sanitize_messages_for_summary` в `compaction.py`.

**5.5 Mutual exclusion с session-memory compact:**

В openclaude `sessionMemoryCompact.ts` имеет lock-mechanism: при активной session-memory компактации полный compact отключается до её завершения (избегаем race + double-compact). Нам это тоже понадобится при появлении thread_insights refresh + L4 compact в одном ходе.

**Action:** ввести `compaction_lock` flag в session_meta; circuit-breaker (3 consecutive failures → skip compact на N turns).

### 10.6 Hook surface (расширение over current Phoenix-trace)

openclaude имеет полноценный hook chain (`src/services/hooks/`):

| Hook | Назначение | SciGraph mapping |
|---|---|---|
| `PreCompactHooks` (trigger='auto'\|'manual') | custom instructions injection перед compact | будущая точка для thread_insights freshness check + custom system prompt overrides |
| `PostCompactHooks` | действия после compact | re-inject recent papers / plan / discovered tools (см. §10.5.2) |
| `SessionStartHooks` | после session resume / compact | re-load workspace metrics, paper_profile freshness, capsules invalidation |
| `PostSamplingHooks` | после assistant LLM call | trigger thread_insights refresh, extract durable memories, prompt coaching |
| `PromptSubmitHooks` | до отправки запроса в LLM | inject `<away_recap>`, `<thread_insight>`, `<discovered_tools>` |
| `SubagentStartHooks` / `SubagentStopHooks` | lifecycle subagent | для §9.4 B1 — обязательны как explicit observability events |

**SciGraph action (Train T3 — параллельно с Epic B0):**
- вынести в новый модуль `science_graphrag/agent/hooks/` с явным contract'ом, не размазывать по `runtime.py`/`stream_lifecycle.py`/`post_turn.py`;
- начать с **PostCompact** (re-inject) и **SubagentStart/Stop** (для Epic B observability) — остальное по мере необходимости;
- avoid hooks-as-monkey-patch — каждый hook принимает immutable context, возвращает diff/decision; собирается в trace-review как `hook_chain_events`.

### 10.7 Agent registry & per-fork permission policy

**7.1 Disk-loaded agent definitions** (`loadAgentsDir.ts` в openclaude):

openclaude читает `~/.claude/agents/*.md` и `<project>/.claude/agents/*.md` с YAML frontmatter:

```yaml
---
name: librarian
model: claude-haiku-4
tools: [paper_quote_search, paper_profile, find_works]
disallowedTools: [cypher_query]
permissionMode: read_only
requiredMcpServers: []
isolation: sidechain
background: true
whenToUse: |
  When the user asks for academic references or wants to compose a bibliography section.
color: blue
---

You are an academic librarian. Read `<paper>` blocks carefully and produce GOST-formatted entries.
```

**Расширение для SciGraph:**

- `~/.scigraph/agents/<name>.md` + `<workspace>/.scigraph/agents/<name>.md` — позволяет пользователю/проекту определять собственные роли (`librarian`, `bibliographer`, `methodology-checker`, `dataset-explorer`) **без правки кода**.
- Frontmatter маппится в нашу tool policy matrix (§6.1.4) + system prompt builder.
- Subagent invocation: `AgentTool(subagent_type='librarian', prompt='...')` находит definition, применяет canUseTool, runs as cache-safe fork (§10.2).

**Acceptance:**
- registry loader + frontmatter parser + system prompt builder + permission filter;
- integration test: загрузка `tests/fixtures/agents/librarian.md`, вызов через AgentTool, контракт verification.
- В Epic B B0 ADR — фиксируем регистр как часть архитектуры.

**7.2 Per-call `canUseTool` callback** (см. §10.2):

Текущий `effective_tool_policy` (§6.1.3) — **per-mode**. Нужен дополнительный **per-call** layer:

- `createMemoryFileCanUseTool(path)` — только Edit на конкретный путь;
- `createCompactCanUseTool()` — **deny ALL** (compact subagent работает text-only);
- `createClaimVerificationCanUseTool(paper_ids)` — Read-only `paper_quote_search` / `paper_profile`, deny `cypher_query` write.

**Action:** добавить optional `can_use_tool: Callable[[Tool, ToolInput], Decision]` в `tool_execution_pipeline.py` (на верх effective_tool_policy). Контракт: если callback возвращает `Decision.DENY`, инструмент не вызывается, agent получает structured error (`tool_denied_by_policy: <reason>`).

### 10.8 `<task-notification>` envelope для subagent completion

В openclaude когда coordinator-spawned worker завершается, parent получает **user-role** message с XML конвертом (см. `coordinator/notifications.ts`):

```xml
<task-notification>
  <task-id>5f3a-...</task-id>
  <subagent>corpus-explore</subagent>
  <status>completed</status>
  <usage>
    <tokens-input>12345</tokens-input>
    <tokens-output>234</tokens-output>
    <duration-ms>8400</duration-ms>
  </usage>
  <summary>Found 3 candidate papers for the query.</summary>
  <result>
    <!-- worker's final assistant message -->
  </result>
</task-notification>
```

**Зачем:** унифицирует «событие завершения child'а» как **часть transcript'а** (а не только SSE боковой канал). Делает следующий ход parent'а tractable для:
- LLM turn classifier;
- trace-review (видит lifecycle прямо в messages);
- compaction (`<task-notification>` сжимается как обычный tool result, structure preserved).

**SciGraph action для Epic B B1:**
- ввести `<task-notification>` envelope в `science_graphrag/agent/subagents/notification.py`;
- emit как `HumanMessage` с `additional_kwargs={'kind': 'task_notification'}` после child'а;
- SSE event `subagent_task_notification` зеркалит payload для UI;
- compaction-friendly: при сжатии `<task-notification>` сохраняем `<status>`, `<summary>`, `<task-id>`, дропаем `<result>`.

### 10.9 Дополнительные паттерны (короткий список)

| Паттерн | Источник в openclaude | SciGraph value | Куда положить |
|---|---|---|---|
| **`extractMemories` / autoMem** — durable memories per-project | `services/extractMemories/` | низкий приоритет: у нас memory — per-session; но при появлении user accounts может пригодиться | Backlog (отдельный ADR) |
| **`autoDream`** — periodic memory consolidation across sessions | `services/autoDream/` | низкий приоритет, требует cross-session aggregation | Backlog |
| **`tool_use_summary`** — компрессия больших tool results | `services/toolUseSummary/` | **средний** приоритет; complement к §6.1.4 token budget; может работать на cache-safe fork (§10.2) | Train T4 (post-Epic B B1) |
| **`agent_listing_delta` attachment** | `tools/AgentTool/AgentTool.tsx` | избежать busting cache при изменении MCP/plugin list — выносить agent listing в delta-attachment | Train T4 (нужен только когда §10.7 disk agents появятся) |
| **`PromptCoaching` post-sampling** | `services/promptCoaching/` | UX touch — suggest follow-up prompts | Backlog (UI feature) |
| **`stripReinjectedAttachments` pre-compact** | `services/compact/compact.ts` | санитайзер перед compaction LLM — экономия | Train T2 (вместе с §10.5.4) |

### 10.10 Acceptance / observability layer для §10

| Подраздел | Acceptance gate |
|---|---|
| §10.1 (coordinator vs fork) | ADR Epic B0 содержит решение + benchmark на одинаковом сценарии (latency, cache hit, missing-state events) |
| §10.2 (cache-safe side-LLM) | metric `side_llm_cache_read_ratio` в trace-review-v1; gate `>= 0.6` для thread_insights, `>= 0.8` для full L4 compact |
| §10.3 (subagent catalog) | benchmark lane `subagent_specialist_routing`; verification subagent VERDICT regex parse rate ≥ 95% |
| §10.4 (prompt discipline) | contract test на subagent output: `Scope:` regex required, `VERDICT:` для verification subagents |
| §10.5 (compaction hardening) | существующий `compaction_churn_increase` + новый `post_compact_paper_sources_restored_count` + `ptl_retry_count_per_compaction` |
| §10.6 (hooks) | `hook_chain_events` в trace-review с порядком вызовов (PostCompact обязателен после context_compacted) |
| §10.7 (agent registry) | integration test на `~/.scigraph/agents/*.md` loading + per-call canUseTool callback test |
| §10.8 (`<task-notification>`) | обязательный envelope на каждый завершённый child в Epic B B1 acceptance |

### 10.11 Привязка §10 к release train (§9.6)

Обновлённый порядок (без сдвига существующих trains, только добавление точек):

- **Train T1** (текущий, A0/A1/C0): + **§10.2 helper** `forked_runtime.py` + первый side-LLM helper consumer = `thread_insights.py` (cache-safe).
- **Train T2** (A2/A3/C1): + **§10.4 prompt discipline** в supervisor → writer; + **§10.5.1/§10.5.2** microcompact time-trigger + post-compact paper sources; + **§10.5.4** sanitizers; + **§10.3 claim-verification** subagent (быстрый ROI поверх cache-safe helper).
- **Train T3** (B0/B1): + **§10.1 ADR-решение** (fork-mode default); + **§10.6 hooks** layer (Pre/Post compact + Subagent start/stop); + **§10.7 agent registry** baseline (disk loader + per-call canUseTool); + **§10.8 `<task-notification>`** envelope.
- **Train T4** (B2/B3/C2): + **§10.3 corpus-explore / research-plan** subagents; + **§10.9 tool_use_summary** на cache-safe helper.
- **Train T5** (B4/C3): + **§10.5.3 PTL retry + group-by-round** primitives; финальный hardening §10.10 acceptance.

### 10.12 Cross-references (где §10 пересекается с §1–§9)

- **§10.1** уточняет **§1.3** и **§9.4 B0** (выбор fork vs coordinator).
- **§10.2** — обязательное предусловие для **§9.3 A1** production-ready (без cache-safe — экономика side-LLM не выдержит) и для всех будущих subagent runs (§9.4 B*).
- **§10.3** — конкретные субагенты для **§9.4 B0/B1** + новый item в **§9.5.1 P1** (claim-verification).
- **§10.4** — input для **§9.4 B2** (writer contract) и **§9.3 A2** (precedence prompt).
- **§10.5** — уточняет **§9.3 A1/A2** hardening + **§6.1** (микрокомпакт + post-compact).
- **§10.6** — связан с **§6.1.4** matrix prompt после compact; явный hook layer закроет «smoeshing» политик из §2.1.1.
- **§10.7** — расширение **§6.1.4** allowed-tools matrix (per-mode → per-call).
- **§10.8** — обязательный envelope для **§9.4 B1**.
- **§10.9 / §10.11** — дополняют **§9.5.1** и **§9.6**.

---

## 11. Сводный чеклист по Trains (T1–T5)

**Назначение:** один actionable checklist по подэтапам, чтобы прогресс был виден одним взглядом. Детали (acceptance / gates / observability) — в §9.3 / §9.4 / §9.5 / §9.5.1 / §10.

**Легенда:**
- `[x]` — DONE: реализовано + покрыто тестами + есть запись в Wave/Train log.
- `[ ]` — PENDING: не начато.
- `[~]` — PARTIAL: использовать только для эпика, который не декомпозирован на подзадачи прямо здесь. Если эпик декомпозирован (как A1 ниже) — статус выражается смесью `[x]` и `[ ]` среди подпунктов, без `[~]` на уровне эпика.

**Текущий счёт (2026-05-07, уточнение 2026-05-08):** ~57 DONE / ~59 PENDING (без §11.0 контекста и §11.7 reminder'а). *Оценка после live/eval hardening (§11.2 claim gate CLI, §10.10, B4 HTTP); перед релизом пересчитать grep'ом по `[x]` / `[ ]` в §11.1–§11.6.* **2026-05-08:** в §11.6 новые `[x]` не добавлялись — расширены **комментарии** и блоки **«Статус SciGraph»** в §9.5.1 (см. строку **2026-05-08** в таблице **§7. История** и §9.8).

> Этот чеклист — **производный**: при движении по пунктам обновлять и здесь, и в исходных секциях (§9.3/§9.4/§9.5/§10), чтобы не возникало дрейфа.

### 11.0 Уже закрыто (контекст «зачёта», не входит в Train T1–T5)

- **§6.1 (8 ROI пунктов из openclaude):** все DONE — deferred schemas, carry-over discovered tools, unified tool-execution pipeline, allowed-tools matrix, sidechain transcripts, token budget loop policy, away summary, feature-gated rollout + telemetry.
- **§8 Post-closure next wave:** P0 (CI gate trace_regression, orchestrator smoke), P1 (canonical tool/run audit trail + alignment test, runtime metadata builder unify), P2 (`agent_note` 50-turn cost, `paper_profile` null-rate snapshot) — DONE per `§8.5 Execution log`.
- **Wave 5:** `chat_envelope` декомпозирован, canonical typed tool-execution trace, `run_kind`/`graph_id` атрибуция, profiles `quick/default/heavy` в `agent_trace_review.py`, `compaction_churn_increase` fail-policy в `trace_regression_compare.py` — DONE.

### 11.1 Train T1 (2 недели) — A0 / A1 / C0 + cache-safe helper

**Цель:** schema/freshness/telemetry contracts + thread-insights skeleton + discovery-aware tool loading + общий cache-safe helper для side-LLM.

- **A0. Summarization modes spec** (§9.3 A0)
  - [x] раздел `Summarization modes` в `docs/specs/agent-chat-v1.md`
  - [x] зафиксированы `turn_loop_memory` / `thread_insights_compact` / `hybrid`
  - [x] негативные кейсы + пометка о precedence (откладывается в A2)

- **A1. Thread-insights pipeline** (§9.3 A1, §10.5)
  - [x] `science_graphrag/agent/context/thread_insights.py` (skeleton: chunking + bounded parallel + synthesis)
  - [x] persistence в `session_meta.thread_insight` (memory + redis backend)
  - [x] post-turn refresh под `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED`
  - [x] `run_metadata.thread_insight_audit` в sync/SSE
  - [x] freshness policy: TTL / turn_delta / high_churn (§9.3 A1)
  - [x] circuit-breaker (`max_consecutive_failures`) (§9.3 A1, §10.5.5)
  - [x] PTL retry policy (`max_ptl_retries`) — L4 digest path + `message_groups` for LC history (§9.3 A1, §10.5.3)
  - [x] integrity guards `tool_use/tool_result` при chunk/drop/rebuild (`message_groups.py`) (§9.3 A1)
  - [x] explicit compaction boundary artifact (`trigger`/`pre_tokens`/`source_range`/`preserved_segment`) (§9.3 A1)
  - [x] gate: `insight_recall@k` measurable, `stale_summary_error_rate` baseline — synthetic harness only (§9.3 A3 ref; full A3 eval still T2+)

- **C0. Discovery-aware tool loading** (§9.5 C0)
  - [x] `tool_search` учитывает discovered tools из message history (`AIMessage.tool_calls` / `ToolMessage`)
  - [x] детерминированный merge перед session carry-over
  - [x] `message_discovery_tools` / `message_discovery_merged` в `tool_search_result`
  - [x] strict deferred activation policy (`only-on-discovery`) как runtime contract
  - [x] расширенная telemetry на lane-уровне (`activation_rate` / `miss_due_to_no_discovery`)

- **§10.2 Cache-safe side-LLM helper** (новое в Train T1)
  - [x] `science_graphrag/agent/forked_runtime.py` **stub** (`side_llm_fork_metadata` + audit merge; full fork helper deferred)
  - [x] `thread_insights.py` пишет fork/cache telemetry fields в audit через stub
  - [x] метрика `side_llm_cache_read_ratio` в `trace-review-v1` (non-stub)
  - [x] gate: `side_llm_cache_read_ratio >= 0.6` для `thread_insights` (CLI `--min-side-llm-cache-read-ratio`, nightly / live когда forked audit присутствует)
  - [x] dual-run regression compare on/off через `trace_regression_compare.py` (два артефакта + compare; feature_flags в `run_context` для A/B; см. `agent-runtime-train-t1-acceptance-2026-05-06.md`)

### 11.2 Train T2 (2 недели) — A2 / A3 / C1 + claim_verification + compaction hardening

**Цель:** prompt integration thread_insight'а с precedence policy, long-thread eval gates, hybrid LLM-selector, первый production subagent (claim_verification) на cache-safe helper'е, hardening компактации.

- **A2. Prompt integration + fallback policy** (§9.3 A2)
  - [x] `<thread_insight>` блок в `format_user_with_memory` при свежем insight'е
  - [x] fallback к `session_summary` при stale/failed/circuit-breaker open
  - [x] precedence: `turn_digest` (latest) > `thread_insight` (fresh) > `session_summary`
  - [x] conflict detection: `turn_digest` vs `thread_insight` claim mismatch → label `conflicted`
  - [x] `insight_conflict_resolved` / `insight_fallback_reason` / `ptl_retry_count` в `run_metadata`
  - [x] контракт-тесты на детерминизм precedence (no silent override свежих фактов)

- **A3. Eval + gate** (§9.3 A3)
  - [x] eval lane `eval/chat_agent/long_thread_*`: long-thread retrieval / context drift / summary hallucination / claim grounding
  - [x] метрики `insight_recall@k` / `stale_summary_error_rate` / `compaction_churn_delta` / latency p50/p95 / `insight_stale_reason_rate` / `insight_conflict_resolved_rate` / `ptl_retry_rate` / `compaction_circuit_breaker_trips`
  - [x] gate: trust/verdict не хуже baseline + p95 latency в бюджете + claim grounding precision/recall ≥ SLO

- **C1. Hybrid selector (rules + LLM judge)** (§9.5 C1)
  - [x] LLM rerank поверх rule-based shortlist (`tool_selector_hybrid.py`, `SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_LLM_RERANK_ENABLED`)
  - [x] confidence score + reason codes (`selector_confidence`, `selector_reason_codes` в `tool_search_result` / meta)
  - [x] guardrails: deny unsafe tools до LLM решения, `final_answer` всегда доступен (pre-LLM denylist + `_ensure_final_answer_in_picked`)
  - [x] benchmark lane: метрика `unnecessary_tool_calls` + `trace-review` / `trace_regression_compare` политики (verdict/trust gates без изменений)
  - Комментарий: C1 закрыт в hybrid-срезе без смены базового runtime-контракта `(tools, meta)`; fallback rules-only path сохранён.
  - Комментарий (post-fix, 2026-05-07): ветка `llm_rerank_skipped_no_api_key` теперь тоже проходит pre-LLM deny фильтр (без возврата сырого `picked`), поэтому guardrail консистентен во всех fallback path.
  - Комментарий: regression покрыт тестами `tests/test_tool_search.py`, `tests/eval/test_agent_tools_metrics.py`, `tests/scripts/live_check/test_trace_*`.

- **§10.3 `claim_verification` subagent** (быстрый ROI, §9.5.1 P1.5)
  - [x] subagent на `forked_runtime.py` helper с deny-write policy (`create_claim_verification_can_use_tool` + `run_claim_verification_fork_bundle` в `forked_runtime.py`)
  - [x] system prompt с strict output format `Scope/Result/Key sources/VERDICT` (§10.4) в `claim_verification_runtime.py`
  - [x] feature-flag `agent_claim_verification_enabled` (+ таймауты/бюджет/fanout caps в Settings)
  - [x] SSE `claim_verification_result` с verdict + issues + sync `run_metadata.claim_verification_results`
  - [x] gate: trust + latency vs baseline для claim_verification — **repeatable nightly / операторский compare** (не обязательный PR CI): в [`trace_regression_compare.py`](../../scripts/live_check/trace_regression_compare.py) — `--max-latency-p95-regress-ratio` (кап +15% к baseline `latency_p95_ms` при обоих > 0), `--min-live-trust-signal-delta` на дельту `live_trust_signal_avg`, опция `subagent_lifecycle_missing_increase` в `--fail-on`; в `trace-review-v1` метрики `claim_verification_verdict_parse_rate`, `live_trust_signal_avg` (см. [`trace_review_schema.py`](../../scripts/live_check/trace_review_schema.py)). На **`--suite acceptance`**: дефолт `min_claim_verification_parse_rate=0.95` в [`agent_trace_review.py`](../../scripts/live_check/agent_trace_review.py). См. [`README_trace_review.md`](../../scripts/live_check/README_trace_review.md) §4–§4.1.
  - Комментарий (2026-05-07): полноценный «зелёный» прогон остаётся за оператором (нужны live API + workspace + baseline JSON); инструменты и тесты compare/schema — закрыты.

- **§10.4 Subagent prompt discipline** (writer/specialist promptы)
  - [x] директива «synthesize-not-delegate» в `writer_agent.py` system prompt
  - [x] strict output format `Scope:` / `Result:` / `Key sources:` / `VERDICT:` (для verification)
  - [x] anti-handoff guard (regex detector «please continue» / «I leave the rest to you» → warning prepend)
  - [x] контракт-тест `tests/agent/test_subagent_output_contract.py`
  - Комментарий (2026-05-07): единый контракт в [`science_graphrag/agent/subagent_output_contract.py`](../../science_graphrag/agent/subagent_output_contract.py) (`SYNTHESIZE_NOT_DELEGATE_DIRECTIVE`, `writer_system_prompt_suffix`, `maybe_prepend_handoff_warning`). Strict блок `Scope/Result/Key sources/VERDICT` подключается только при `SCIENCE_GRAPHRAG_AGENT_WRITER_VERIFICATION_OUTPUT_FORMAT_ENABLED=1` и writer-режиме `normal` (см. `writer_agent.py`). Тот же handoff-regex применяется в **`FinalAnswerTool.run`** (не только в `@tool`-обёртке), чтобы guard не обходился прямым вызовом `run`. Регрессия: `tests/agent/test_subagent_output_contract.py`, `tests/test_final_answer_args.py`.
  - Комментарий (architecture note, 2026-05-07): **`writer_agent` пока оставляем**, но трактуем его как **узкий terminal synthesis seam**, а не как ещё одного «исследователя». Почему не переносим это обратно в `supervisor`: нам нужен стабильный последний hop для `final_answer`, единая точка для synthesis/citation-normalization/merge-directive, и изоляция user-facing phrasing от retrieval/graph orchestration. Направление следующего шага: **упростить** writer (меньше ReAct-поведения, без самостоятельного tool-discovery/reroute), а не удалять его; см. backlog item **[OPEN] Simplify writer_agent into terminal synthesis seam** в `docs/backlog/refactor-backend.md`.

- **§10.5 Compaction hardening (часть 1)**
  - [x] §10.5.1 microcompact time-trigger в `tool_message_compact.py` (gap > N min → clear all but last K) + flag + метрика
  - [x] §10.5.2 post-compact paper sources restore (`science_graphrag/agent/context/post_compact_attachments.py` + integration в `format_user_with_memory`) + метрика `post_compact_paper_sources_restored_count`
  - [x] §10.5.4 pre-compact sanitizers (`stripImagesFromMessages` + `stripReinjectedAttachments` равнозначные функции)
  - Комментарий (2026-05-07, §10.5.1): триггер по **`client_idle_ms`** из клиента (прокидывается через `supervisor` → compact path); флаги `SCIENCE_GRAPHRAG_AGENT_TOOL_MESSAGE_MICROCOMPACT_TIME_TRIGGER_ENABLED`, `…_TIME_GAP_MINUTES`, `…_KEEP_LAST_K_TOOL_RESULTS`; в audit/debug — `tool_message_microcompact_triggered_count`. Агрегация в `run_metadata`: [`science_graphrag/agent/debug_events_telemetry.py`](../../science_graphrag/agent/debug_events_telemetry.py) — `extract_runtime_telemetry_from_debug_events` (используется и в SSE [`stream_lifecycle.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle.py), и в sync [`payloads.py`](../../science_graphrag/api/agent_v2_modules/payloads.py) для parity). Тесты: `tests/agent/test_tool_message_compact.py`, `tests/agent/test_debug_events_telemetry.py`.
  - Комментарий (2026-05-07, §10.5.2): капсула recent paper sources в `session_meta`, one-shot reinject через `<paper_sources_restored>` в user-памяти, счётчик в metadata; после `apply_turn_digest_to_thread` в [`runtime.py`](../../science_graphrag/agent/runtime.py) вызывается `persist_post_compact_paper_sources` (в дополнение к пути после `context_compacted` в stream). Тесты: `tests/test_context_session.py`.
  - Комментарий (2026-05-07, §10.5.4): [`science_graphrag/agent/context/message_sanitizers.py`](../../science_graphrag/agent/context/message_sanitizers.py) + вызовы из `tool_message_compact` и [`llm_history_compact.py`](../../science_graphrag/agent/context/llm_history_compact.py); флаг `SCIENCE_GRAPHRAG_AGENT_PRE_COMPACT_SANITIZERS_ENABLED`. Тесты: `tests/agent/test_message_sanitizers.py`.

### 11.3 Train T3 (2–3 недели) — B0 / B1 + advanced summarization + hooks/registry/envelope

**Цель:** ADR по subagent runtime v3, базовый spawn primitive, hooks layer, agent registry, `<task-notification>` envelope, advanced summarization optimizations.

- **B0. ADR `agent-runtime-v3-subagents`** (§9.4 B0, §10.1)
  - [x] decision policy «когда нужен spawn» + sync vs background + merge contract + failure taxonomy
  - [x] выбор API: `/v3/agent/query` ИЛИ `run_kind=langgraph_supervisor_v3` под `/v2`
  - [x] §10.1 решение: **fork-mode default**, coordinator-mode только при явном продукт-сценарии
  - [x] benchmark fork vs coordinator на одинаковом сценарии (latency / cache hit / missing-state events) — **synthetic lanes** в `eval/chat_agent/subagent_runtime_fork_vs_coordinator_bench.py` + delta `subagent_lifecycle_missing_count` в `trace_regression_compare.py`; **live export** — `agent_trace_review.py` / `agent_od_workspace_e2e_audit.py` с **`--suite acceptance`** (см. B1 gate ниже и changelog §7).
  - [x] prompt-cache контракт fork-режима зафиксирован в ADR (та же tools array, без `maxOutputTokens`, тот же thinking config)
  - [x] sidechain transcript обязателен для каждого subagent run (§6.1.5 ref) — JSONL `subagent/<parent_turn_id>/<subagent_id>.jsonl` при `agent_sidechain_transcripts_enabled`
  - [x] pull-back-to-parent контракт (избегаем flooding) — `SubagentCarryBack` + `<task-notification>` без полного child dump
  - [x] rollback strategy — `agent_subagent_lifecycle_enhanced_enabled` + `run_metadata.subagent_observability_lane`
  - Комментарий (2026-05-07): lifecycle/observability wave — `notification.py`, `lifecycle.py`, `sidechain_transcript.py`, `stream_lifecycle.py`, `supervisor.py`, `writer_agent.py`, `runtime.py`, `trace_review_schema.py`.
  - Комментарий (2026-05-07, quality-pass): успешное завершение routing-ноги в sidechain не дублируется: при включённом `agent_subagent_lifecycle_enhanced` JSONL пишет `routing_leg_completed` из `lifecycle.py`, а `stream_lifecycle.py` не добавляет второй ряд `routing_leg_finished` на success (исключения — timeout/recursion и режим без enhanced). При сбое `task_notification_human_message` в JSONL пишется `task_notification_rollback`; в SSE payload для `subagent_task_notification` поле `type` защищено от перезаписи из вложенного dict.

- **B1. Runtime primitive: spawn / track / collect** (§9.4 B1, §10.8)
  - [x] `science_graphrag/agent/subagents/runtime.py` с `spawn_subagent(task_spec) -> subagent_id`
  - [x] heartbeat / progress channel — SSE `subagent_heartbeat` + `subagent_progress` (существующий) + `subagent_progress_label` (throttle)
  - [x] terminal states (`succeeded|failed|cancelled|timed_out`) + bounded fanout (`max_parallel_subagents`)
  - [x] observability: `parent_turn_id` / `subagent_id` / `spawn_reason` / `cost/tokens/latency` per child
  - [x] §10.8 `<task-notification>` envelope как user-role message в parent transcript
  - [x] SSE `subagent_task_notification` зеркалит payload для UI
  - [x] periodic `subagent_progress_label` (≥ 30s throttle; **deterministic** label от последнего tool progress — LLM AgentSummary fork отложен)
  - [x] gate: live run с 2+ child legs → trace completeness в SSE + trace-review — **`agent_trace_review.py --suite acceptance`** (strict `subagent_lifecycle_missing_count`, E2E pack `agent_od_workspace_e2e_audit.py --suite acceptance`); не заявляется «настоящий параллельный mesh», только observability completeness
  - Комментарий (2026-05-07): foundation + v3 lifecycle extras; explicit parallel spawn graph всё ещё sequential routing — gate формулировать как trace completeness, не как настоящий параллельный mesh.

- **A-advanced** (§9.6 Train T3)
  - [x] incremental insight updates: append-only refresh path в `thread_insights.py` (`try_build_thread_insight_snapshot_incremental`) с `refresh_mode=incremental`, fingerprint окна и bounded tail-only synthesis
  - [x] contradiction-aware synthesis: `synthesis_conflicts` / `synthesis_conflict` в audit при конфликте нового tail digest с prior insight; покрыто `tests/test_thread_insights.py`

- **§10.6 Hooks layer baseline**
  - [x] `science_graphrag/agent/hooks/` модуль (immutable context → diff/decision контракт)
  - [x] `PostCompactHooks` (re-inject paper sources / plan / discovered tools — синхронизировано с §11.2 §10.5.2)
  - [x] `SubagentStartHooks` / `SubagentStopHooks` (для §11.3 B1 observability)
  - [x] `hook_chain_events` в `trace-review-v1`
  - Комментарий (2026-05-07): реализация в [`science_graphrag/agent/hooks/`](../../science_graphrag/agent/hooks/), `run_post_compact_hooks` + `hook_chain_event` debug rows; subagent ledger/runtime пишет start/stop; `run_metadata.hook_chain_events` + `Metrics.hook_chain_event_count` в [`scripts/live_check/trace_review_schema.py`](../../scripts/live_check/trace_review_schema.py); sync path [`science_graphrag/agent/runtime.py`](../../science_graphrag/agent/runtime.py), SSE [`stream_lifecycle.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle.py).
  - Комментарий (2026-05-07, quality-pass): `merge_hook_chain_events_into_run_metadata` сохраняет уже присутствующие события из `run_metadata` и дедуплицирует объединение (`type/hook/phase/ok/detail`), чтобы sync/SSE merge не терял события и не плодил дубли; покрыто тестами `tests/agent/test_hooks_post_compact.py`.

- **§10.7 Agent registry & per-fork permissions baseline**
  - [x] disk loader: `~/.scigraph/agents/*.md` + `<workspace>/.scigraph/agents/*.md` с YAML frontmatter (`name`, `model`, `tools`, `disallowedTools`, `permissionMode`, `whenToUse`, `color`, `isolation`, `background`)
  - [x] frontmatter parser → tool policy matrix mapping (§6.1.4 ref) + system prompt builder
  - [x] per-call `canUseTool` callback в `tool_execution_pipeline.py` (поверх `effective_tool_policy`)
  - [x] integration test: `tests/fixtures/agents/librarian.md` загрузка → AgentTool вызов → permission filter
  - Комментарий (2026-05-07): [`science_graphrag/agent/agent_registry.py`](../../science_graphrag/agent/agent_registry.py) + `disk_agent_definition_to_can_use_tool`; single-agent bound surface: `metadata.react_bound_tool_names` в [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) + gating в [`tool_execution_pipeline.py`](../../science_graphrag/agent/tool_execution_pipeline.py); тесты `tests/agent/test_agent_registry_permissions.py`, `tests/agent/test_allowed_tools_matrix.py`.
  - Комментарий (2026-05-07, quality-pass): hardened permission path — исключения в `can_use_tool` теперь конвертируются в явный deny (`can_use_tool_callback_error:<ExceptionName>`), убран неверный implicit deny `cypher_query` для `permissionMode=read_only` (политика задаётся `tools/disallowedTools`), parser корректно обрабатывает не-UTF8 файлы, добавлен общий контракт `CanUseTool` в `science_graphrag/agent/can_use_tool_contract.py`; регрессии закрыты в `tests/agent/test_agent_registry_permissions.py`.

### 11.4 Train T4 (2–3 недели) — B2 / B3 / C2 + corpus-explore / research-plan + tool_use_summary

**Цель:** merge node + writer contract, subagent isolation policies, dynamic schema transport, второй и третий production-subagent, компрессия больших tool results.

- **B2. Merge node + writer contract** (§9.4 B2)
  - [x] merge-узел (library): child/parent legs → typed `specialist_results_v3` (`specialist_results_v3.py` + append из `retrieval_agent` / `graph_agent`)
  - [x] confidence ranking + provenance (`evidence_origin`: `parent_tool` / `subagent:<id>` / `mixed`) + `merge.conflict` при расходящихся VERDICT
  - [x] writer context: `serialize_for_writer` + `merge.writer_directive` (явный конфликт / partial_failure)
  - [ ] gate: при конфликтующих ответах финальный answer объяснимо выбирает/синтезирует, provenance виден — **LLM-judge live**, не закрыто автотестом
  - Комментарий (live/eval hardening, 2026-05-07): **machine-checkable слой закрыт** — в `trace_timeline` поля `specialist_v3_merge_conflict` / `specialist_v3_evidence_origin`, в OD acceptance кейс `b2_merge_provenance_probe` (`agent_od_workspace_e2e_audit.py`), в `acceptance_summary_v1` — `specialist_v3_merge_conflict_observed_live` и `residual_open` про LLM-judge, если конфликт в конкретном прогоне не воспроизвёлся.
  - Комментарий (Train T4, 2026-05-07): в typed merge добавлены ноги **`corpus_explore`** и **`research_plan`** (`append_corpus_explore_leg` / `append_research_plan_leg`, `evidence_origin` / `partial_failure` для смешанных источников); writer видит тот же v3-контракт через существующий `serialize_for_writer`.

- **B3. Tool/search/memory subagent isolation** (§9.4 B3)
  - [x] изолированный tool policy на `claim_verification` child run (`build_claim_verification_tools` + `can_use_tool`)
  - [x] локальный short-term memory (не carry-over в parent если не явно) — `science_graphrag/agent/subagents/isolated_subagent_state.py` (`subagent_short_term_memory`, пустые child `messages`, явный carry-back)
  - [x] controlled carry-back: transcript — только `HumanMessage` markers + `specialist_results["claim_verification"]` excerpts (без полного child dump)
  - [x] квоты: `agent_claim_verification_max_tool_calls`, `agent_claim_verification_step_timeout_seconds`, `agent_claim_verification_fanout_max`, `agent_claim_verification_recursion_limit`
  - [x] зеркальная политика для **corpus_explore** / **research_plan**: отдельные `canUseTool` whitelist (`create_corpus_explore_can_use_tool`, `create_research_plan_can_use_tool`), те же квоты/таймауты через Settings-префиксы `agent_corpus_explore_*` / `agent_research_plan_subagent_*`, carry-back через markers + `specialist_results` bucket'ы (без merge child `messages` в parent)
  - [~] gate: subagent mode vs token budget — **live профиль**: `acceptance_summary_v1` gate `§11.4_B3_budget_usage_timeline` + `budget_cutoff_count` / `agent_usage_total_tokens_sum` в `trace-review-v1` (`suite=acceptance`); строгий token ceiling — advisory без отдельного лимитера в compare
  - Комментарий (live/eval hardening, 2026-05-07): B3 gate и dedupe `live_proven` в `build_acceptance_summary` — unit-тесты в [`tests/scripts/live_check/test_trace_review_schema.py`](../../tests/scripts/live_check/test_trace_review_schema.py).
  - Комментарий (Train T4 + quality-pass, 2026-05-07): **corpus_explore** не стартует, пока не собран **полный** набор из 4 read-only tools (`workspace_inspect`, `find_works`, `paper_quote_search`, `idea_search`); иначе fast-fail с `issues: corpus_explore_missing_tools:<names>`. **research_plan** — отказ только при **пустом** списке tools после фильтрации (раньше ложный fail при `len(tools)==2`). Разбор JSON в research-plan helpers — только `(TypeError, ValueError, JSONDecodeError)`, без bare `Exception`. В `_run_langgraph` добавлены предупреждения **`corpus_explore_child_non_success` / `corpus_explore_child_issues`** и **`research_plan_child_*`** по аналогии с claim_verification (см. `runtime.py`). Дублирующийся проход по `ToolMessage` в `tool_execution_pipeline` после summary убран (один цикл: summary → `sse_hint`).

- **C2. Dynamic schema transport** (§9.5 C2)
  - [x] компактные refs для deferred tools by default (`deferred_schema_refs`)
  - [x] полная схема only-on-discovery (`deferred_schema_full_tools`, gated full transport)
  - [x] метрики: `tool_schema_bytes_saved` / `deferred_tool_activation_rate` / `tool_search_miss_due_to_no_discovery` в `tool_search`, telemetry merge и `trace-review-v1`
  - Комментарий (2026-05-07): контракт и telemetry покрыты `tests/test_tool_search.py`, `tests/test_tool_manifest_sync.py`, `tests/scripts/live_check/test_trace_review_schema.py`; rollout-policy lane остаётся в T5 C3.

- **§10.3 corpus-explore subagent** (read-only fanout)
  - [x] system prompt: read-only `workspace_inspect` → `find_works` → `paper_quote_search` → `idea_search` на дешёвой модели (`corpus_explore_runtime.py`, опциональный `agent_corpus_explore_chat_llm_model`)
  - [x] `canUseTool` deny-write (`create_corpus_explore_can_use_tool`)
  - [x] strict output format (§10.4) — Scope/Result/Key sources без VERDICT + `read_only_subagent_answer_matches_contract`
  - [x] интеграция supervisor v3: `run_corpus_explore_fork_bundle` / fanout из `retrieval_agent.py`, `HumanMessage` marker `corpus_explore_result`, SSE + `run_metadata.corpus_explore_results` (`notification.py`, `stream_lifecycle.py`, `payloads.py`, `runtime.py`)
  - [x] regression: `tests/agent/test_t4_subagents_and_tool_summary.py` (policy, изоляция, v3 merge), контракт — `test_subagent_output_contract.py`

- **§10.3 research-plan subagent** (декомпозиция запроса)
  - [x] system prompt: декомпозиция вопроса на (а) corpus sub-queries, (б) graph sub-queries, (в) writer-spec (`research_plan_runtime.py`)
  - [x] integration с `research_plan_write` при `SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_TOOL_ENABLED` + общий `thread_id` (reinject через session как у основного агента)
  - [x] strict output contract — `research_plan_subagent_answer_matches_contract` (заголовки Corpus/Graph/Writer + Key sources, без VERDICT)
  - [x] интеграция v3: `run_research_plan_fork_bundle`, marker `research_plan_result`, `research_plan_write_ok` в outcome dict, `run_metadata.research_plan_results`
  - Комментарий (2026-05-07): docstrings на `clear_research_plan_subgraph_cache` / `_cache_key` / `run_research_plan_fanout` для pylint; struct debt duplicate-code vs corpus runtime — см. **[OPEN] Deduplicate subagent runtime micro-helpers** в `refactor-backend.md`.

- **§10.9 tool_use_summary** на cache-safe helper
  - [x] компрессия больших tool results в structured summary через `science_graphrag/agent/tool_use_summary.py` (`summarize_tool_result_payload_dict`, side-LLM через `forked_runtime.run_side_llm_chat`) + применение в `tool_execution_pipeline`
  - [x] complement к §6.1.6 token budget — флаги `agent_tool_use_summary_*`, telemetry `tool_use_summary_*` в `debug_events_telemetry`
  - [x] debug/SSE тип `tool_use_summary_batch` в `debug_streamable_types.py`; цикл импорта `forked_runtime` ↔ `tool_execution_pipeline` разорван выносом логики в `tool_use_summary.py`
  - Комментарий (quality-pass, 2026-05-07): после парса side-LLM — **`_sanitize_llm_tool_summary_v1`** (кап строк, каноническое поле `tool` = фактический tool name, `numeric_facts` только JSON-safe скаляры); при превышении `agent_tool_use_summary_max_output_chars` — `_tool_use_summary_overflow_drop` + усечённый payload; один проход по `ToolMessage` в pipeline после батча (сначала summary, затем извлечение `sse_hint` из уже обновлённого `content`).

### 11.5 Train T5 (1–2 недели) — B4 / C3 + PTL retry + финальный hardening

**Цель:** safety/eval gate multi-agent, eval lanes для tool search, PTL retry primitives, финальный rollout decision.

- **B4. Safety/eval gate multi-agent** (§9.4 B4)
  - [x] eval scenarios: synthetic unit coverage + **live HTTP** `agent_v2_fanout_probe` / `agent_v2_malicious_deny` при `suite=acceptance` (`http_suite.py`); timeout-ish path — `b4_timeout_or_deadline_warning_in_e2e_timeline` в `acceptance_summary` при warning'ах E2E
  - [~] gate: partial-failure → `warnings` + lifecycle metrics в trace-review; **100% completeness** — только вместе с полным acceptance прогоном, не в unit-only CI
  - Комментарий (quality-pass, 2026-05-07): `malicious_deny` унифицирован с `check_agent_v2_sync_json` (один POST, общий контракт ответа); mock-тесты — [`tests/scripts/live_check/test_http_suite_safety.py`](../../tests/scripts/live_check/test_http_suite_safety.py).

- **C3. Eval + policy gate** (§9.5 C3)
  - [x] lanes: canonical fixture `eval/chat_agent/epic_c_eval_lanes.v1.json` + regression contract `tests/eval/test_epic_c_eval_lanes.py` (`sparse-query` / `ambiguous_intent` / `graph-heavy` / `bibliography-quote`)
  - [x] policy: `trace_regression_compare.py` поддерживает `c3_latency_without_error_regress` (warn) и `c3_tool_loop_instability` (fail); покрыто `tests/scripts/live_check/test_trace_regression_compare.py`
  - Комментарий (2026-05-07): это offline/policy baseline; corpus-populated live suite для этих lane'ов остаётся отдельным follow-up перед итоговым default-on решением.
  - Комментарий (live/eval hardening, 2026-05-07): к compare добавлены nightly-опции `subagent_lifecycle_missing_increase`, `--max-latency-p95-regress-ratio`, `--min-live-trust-signal-delta` и дельты trust/CV-parse в JSON-артефакте; регрессия в `test_trace_regression_compare.py`.

- **§10.5.3 PTL retry + group-by-API-round** (compaction hardening финал)
  - [x] `science_graphrag/agent/context/message_groups.py` с `group_messages_by_api_round` + helpers для digest API-round mapping
  - [x] PTL retry policy в `llm_history_compact.py` (drop oldest API-round digest groups, retry до лимита)
  - [x] метрика `ptl_retry_count_per_compaction` в `run_metadata` / `trace-review-v1`
  - Комментарий (2026-05-07): regression покрыт `tests/test_message_groups.py`, `tests/agent/test_llm_history_compact.py`, `tests/scripts/live_check/test_trace_review_schema.py`.

- **§10.10 финальный acceptance check**
  - [x] reference suite: `acceptance_summary_v1` в JSON + секция в MD (`agent_trace_review.py`), тесты `tests/scripts/live_check/test_trace_review_schema.py`
  - [x] dual-run: политики `trace_regression_compare.py` (`--max-latency-p95-regress-ratio`, `subagent_lifecycle_missing_increase`, `--min-live-trust-signal-delta`) + пример команд в `README_trace_review.md`
  - [x] rollout decision: `eval/results/runtime-v3-rollout-decision-2026-05-07.md` (default-on vs gated по evidence)
  - Комментарий (quality-pass, 2026-05-07): MD-вывод `_write_markdown` защищён от не-dict в `checks`; заглушка в `test_agent_trace_review.py` дополнена `build_acceptance_summary`; dedupe `live_proven` в `build_acceptance_summary`.

### 11.6 Tool parity backlog (§9.5.1) — мапинг к Trains

Не все tool-parity items жёстко привязаны к Train acceptance — отслеживаем отдельным чеклистом, выбираем в Train по capacity.

**P0 (целевой Train T1–T2):**
- [x] §9.5.1 P0.1 MCP runtime trio + auth (`call_mcp_tool` / `list_mcp_resources` / `fetch_mcp_resource` / `mcp_auth`) — **gated seam:** `SCIENCE_GRAPHRAG_AGENT_MCP_TOOLS_ENABLED`, HTTP JSON-RPC на `agent_mcp_http_base_url`, denylist `agent_mcp_server_denylist`, SSE `mcp_audit`; без base URL — typed `mcp_unconfigured`.
  - *Комментарий (2026-05-08):* **`mcp_audit_summary`** в `run_metadata`, тест **`test_mcp_call_tool_json_rpc_ok`**, док **`docs/agent/mcp_runtime_acceptance.md`**; live MCP server — вне CI.
- [x] §9.5.1 P0.2 LSP tool (read-only, bounded) — `lsp_tool` + `agent_lsp_server_argv`, timeouts / `lsp_audit`; без argv — `lsp_unconfigured`.
  - *Комментарий (2026-05-08):* tier **`agent_tools_lsp`** + fixture **`lsp_nav_symbol_stub`**, mock trace в **`eval/agent_tools/runner.py`**, док **`docs/agent/lsp_tool_compatibility.md`**; live LSP — по конфигу хоста.
- [x] §9.5.1 P0.3 Web research tools (`web_search` + `web_fetch`, academic allowlist by default; `SCIENCE_GRAPHRAG_AGENT_WEB_RESEARCH_TOOLS_ENABLED`)
- [x] §9.5.1 P0.4 DOI / OpenAlex resolver (`doi_resolver`; `SCIENCE_GRAPHRAG_AGENT_DOI_RESOLVER_TOOL_ENABLED`)
- Комментарий: web-инструменты запускаются только под feature flag; allowlist/redirect-guard + bounded fetch включены, SSE: `web_fetched`.
- Комментарий: DOI bridge переиспользует `normalize_doi` + OpenAlex/Crossref fallback и workspace mapping, SSE: `doi_resolved`; post-fix: `paper_id_in_workspace` заполняется только для реального workspace-match, общий graph fallback отражается в `graph_work_id`.

**P1 (целевой Train T2–T3):**
- [x] §9.5.1 P1.1 Worktree isolation tools — `enter_worktree` / `exit_worktree`, bounded sandbox root `agent_worktree_base_dir`, session meta + SSE `worktree_entered` / `worktree_exited`; regression `tests/agent/test_plan_worktree_surfaces.py`
- [x] §9.5.1 P1.2 Runtime monitor tool — `runtime_monitor_get` + `SCIENCE_GRAPHRAG_AGENT_RUNTIME_MONITOR_TOOL_ENABLED`, единый status contract; snapshot через `register_runtime_monitor_snapshot` (tests) / дальнейший job-store seam.
  - *Комментарий (2026-05-08):* **ingest + benchmark** SoT в **`runtime_monitor_sources.py`**, поля **`source`/`timeout_hit`**, **`runtime_monitor_audit`** + **trace-review schema** — закрыто для заявленного acceptance-slice.
- [x] §9.5.1 P1.3 `research_plan_write` (TodoWrite-аналог) — `session_meta.research_plan`, reinject `<research_plan>`, SSE `research_plan_updated`; flag `SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_TOOL_ENABLED`.
  - *Комментарий (2026-05-08):* **`run_metadata.research_plan`** в API final/sync; UI **`AskResearchPlanPanel`** + hint из stream.
- [x] §9.5.1 P1.4 `ask_user_question` (structured multi-choice) — pending в `session_meta`, SSE `user_question_asked`, клиентский roundtrip поля `user_structured_answer` + debug `user_answered`; flag `SCIENCE_GRAPHRAG_AGENT_ASK_USER_QUESTION_TOOL_ENABLED`.
  - *Комментарий (2026-05-08):* SSE с **`questions`** в hint; **`AskUserQuestionForm`**, **`open_structured_question`** в `details`, JSON+SSE **`user_structured_answer`**; Playwright — опционально.
- [x] §9.5.1 P1.5 `claim_verification` subagent — **дублируется с §11.2 (Train T2)**, отслеживается там

**P2 (только при явном продукт-сценарии):**
- [ ] §9.5.1 P2.1 Task orchestration primitives (`task_create` / `task_get` / etc) — только если Epic B0 выбирает coordinator-mode
- [ ] §9.5.1 P2.2 Scheduled automation (`cron_*`) — требует business case
- [x] §9.5.1 P2.3 Plan mode (`enter_plan_mode` / `exit_plan_mode`) — session toggle + SSE `plan_mode_entered` / `plan_mode_exited`, enforcement через deny high-risk tools в `tool_execution_pipeline.py`; regression `tests/agent/test_plan_worktree_surfaces.py`
- [x] §9.5.1 P2.4 `brief` synthetic output — tool `brief` + `run_metadata.brief` (≤240 chars); `SCIENCE_GRAPHRAG_AGENT_BRIEF_OUTPUT_ENABLED`.
  - *Комментарий (2026-05-08):* превью в **`ChatSessionSidebar`** (вторичная строка сессии) + slim sync `details.run_metadata.brief`.

- Комментарий (2026-05-07): детальное разделение **«seam закрыт» vs aspirational acceptance** (real MCP e2e, LSP eval lane, UI чеклиста/формы, Ask history для `brief`) — в **§9.5.1** под каждым пунктом (**«Статус SciGraph»**); quality-pass: Redis `patch_session_meta` без ключа = seed пустой сессии; sidechain JSONL не падает при `OSError`; `science_graphrag/agent/debug_streamable_types.py` — единый набор типов для SSE/debug; quick live `agent_trace_review.py` на `http://127.0.0.1:18787` + baseline compare — **pass**.
- Комментарий (2026-05-08): aspirational слой **сужен** — для P0.1/P0.2/P1.2–P1.4/P2.4 см. changelog-строку **2026-05-08** и обновлённые **«Статус SciGraph»** в §9.5.1; остаётся осознанный хвост: **live MCP e2e**, **Playwright ask-user**, **agentRunViewModel** (при product-нужде).

**Out-of-scope до отдельного ADR:** `team_create`/`team_delete`, remote triggers, REPL-like execution surfaces (§9.5.1).

### 11.7 Stop-conditions reminder (§9.7)

- ❌ Нельзя пометить Epic B как done, пока `subagent_*` события не подтверждены реальными child runtimes в trace artifacts.
- ❌ Нельзя пометить Epic A как done без long-thread eval с цифрами (не только «pass smoke»).
- ❌ Нельзя пометить Epic C как done, если нет отдельного lane с ambiguous/sparse queries и зафиксированной policy `warn/fail`.
- Train T1 cache gate: `trace_regression_compare.py --min-side-llm-cache-read-ratio 0.6` на кандидате с непустым `metrics.side_llm_cache_read_ratio_avg` (forked `thread_insight_audit` в E2E); PR CI остаётся без этого порога, nightly/live — по желанию (§11.1).
- Train T5 acceptance lane: `agent_trace_review.py --suite acceptance` обязателен **`AGENT_LIVE_WORKSPACE_ID`** (fanout-probe) и доступный API; B4 HTTP-пробы входят в `required` checks только для этого suite — см. [`README_trace_review.md`](../../scripts/live_check/README_trace_review.md) §4.1.
