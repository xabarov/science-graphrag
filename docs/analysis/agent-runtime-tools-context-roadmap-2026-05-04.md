# Агент · инструменты · компактация контекста — единый план (2026-05-04)

**Статус:** живая точка входа по оси *оркестрация агента — каталог tools — сжатие/память диалога*. Заменяет корневой slim-файл `chat-agent-system-roadmap-2026-04-26.md` (удалён как дубликат; глубокая предыстория CH-волн: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md)).

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

**Частично, другой дизайн.** В **openclaude** (см. `openclaude/scripts/build.ts`, `src/commands/insights.ts`, UI) встречаются: **параллельная саммаризация длинных транскриптов по чанкам**, **cached micro-compact** тул-результатов, **context collapse** (в open build **заглушка**), **coordinator / встроенные Explore·Plan субагенты**, **token budget**, **away summary** после blur.  
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

---

## 3. Лестница контекста (продуктовая модель ↔ код)

Уровни из прежнего slim-roadmap; ниже — что уже есть в коде.

| Уровень | Назначение | Статус в коде |
|---------|------------|----------------|
| L0 | Нормализованный evidence pack turn (eval / воспроизводимость) | Частично через trace + harness |
| L1 | **Turn digest** — структурированная сводка хода | [`turn_digest.py`](../../science_graphrag/agent/context/turn_digest.py), `apply_turn_digest_to_thread` |
| L2 | **Rolling session memory** | [`session_backend.py`](../../science_graphrag/agent/context/session_backend.py) — до 10 дайджестов, summary из последних 3 |
| L3 | **Капсулы** workspace / paper / entity | Поля/контракт в развитии; не главный UX-приоритет |
| L4 | **Full compact boundary** — явная граница для длинных тредов | [`compaction.py`](../../science_graphrag/agent/context/compaction.py) — SSE metadata, `digest_cap`, rolling_threshold; полная LLM-компактация истории — будущее |

Дополнительно: **компактация истории tool-сообщений** в одном ReAct-потоке — [`tool_message_compact.py`](../../science_graphrag/agent/tool_message_compact.py) (флаги `agent_tool_history_compact_*`).

---

## 4. Инструменты и измерение качества

- **Каталог и безопасность:** ADR-016, `docs/specs/agent-tools-v1.md`, cypher allowlist.  
- **Бенчмарки:** семейства `agent_tools_*`, gate **BT8** (live mini + осмысленный judge), **BT9** (multi-agent fixtures). Источник правды — [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md).  
- **Backlog (структура):** распил [`api/benchmark.py`](../../science_graphrag/api/benchmark.py) / [`task_store.py`](../../science_graphrag/api/task_store.py) — см. refactor-backend, синергия с Wave M/P/Q/R/S.

---

## 5. Что перенять из openclaude с наибольшим ROI

Приоритет — идеи, совместимые с **серверным** графом и **наблюдаемостью**, без копирования CLI-меша.

| Техника (openclaude) | Смысл | Переносимость к нам |
|---------------------|--------|----------------------|
| **ToolSearchTool** + отложенные схемы | Короткий каталог → полные схемы только для shortlist | Уже близко к rule-based v1; следующий шаг — explicit lazy schema refs в manifest |
| **CACHED_MICROCOMPACT** | Усечение тул-результатов с учётом кэша | Расширить политику рядом с `tool_message_compact` / размером чанков в trace |
| **Параллельная саммаризация чанков** (insights) | Длинная история → параллельные LLM-сводки → сборка | Имеет смысл для **L4** или офлайн «thread export», не в hot-path каждого turn без бюджета |
| **TOKEN_BUDGET** / предупреждения | Явный учёт лимита в UI | Продуктово полезно совместить с `context_compacted` и лимитами на клиенте |
| **VERIFICATION_AGENT** (read-only) | Отдельный лёгкий прогон проверки | Аналог: отдельный eval harness / optional node — не обязательно в user-facing графе |
| **Hook chains + spawn_fallback** | Ремедиация при ошибках | У нас нет того же event-слоя; ближе — retry в runtime + Phoenix alert |
| **COORDINATOR / Explore·Plan субагенты** | Отдельные роли в одном продукте | У нас фиксированные ноды; расширение — только при явном ROI и метриках |

---

## 6. Очередь работ (сжатая)

**Продукт / архитектура**

1. Завершить **BT8/BT9** по trust-audit (live agent_tools, multi-agent gold).  
2. **LLM или hybrid tool_search** — только после стабильных метрик shortlist quality + latency.  
3. **L3/L4**: капсулы и полная LLM-компактация — по триггерам (token threshold, длина треда), с сохранением audit trail для eval.  
4. Документировать матрицу «что попадает в prompt после compact» в [`agent-chat-v1.md`](../specs/agent-chat-v1.md).

**Из refactor-backend (фильтр по этой оси)**

- Split **`idea_workflow.py`** — см. OPEN item.  
- **Settings service split** — caps для агента / pools.  
- **Artifact storage** для chat-agent traces — OPEN «Split benchmark artifact storage».  
- **paper_profile** null-rate — влияет на tool quality; см. OPEN.

---

## 7. История

| Дата | Изменение |
|------|-----------|
| 2026-05-04 | Единый план: объединены slim roadmap, ответы на сравнение с openclaude, ссылки на backlog и ontology §7.7; удалён дублирующий `chat-agent-system-roadmap-2026-04-26.md`. |
