# План работ по инструментам чат-агента (research chat)

**Статус плана:** рабочий (приоритизация и приёмка для фаз B–D). **Фаза A:** реализована в коде — детали и оговорки в разделе [«Статус выполнения фазы A»](#статус-выполнения-фазы-a).  
**Связанные документы:** [`docs/architecture/agent-chat-tools.md`](../architecture/agent-chat-tools.md) (каталог, §5.1 heavy-audit), [`docs/architecture/agent-tools-best-practices.md`](../architecture/agent-tools-best-practices.md), slim-roadmap [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md) (`tool_search`, compaction).  
**Скрипты проверки:** [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) (`--suite default|heavy`, `--trace-audit`), [`scripts/prompt_audit/build_research_chat_prompt_bundle.py`](../../scripts/prompt_audit/build_research_chat_prompt_bundle.py) (`--evaluate`).

Ниже фазы упорядочены от **критичных** (надёжность ответа и отсутствие ложных отказов) к **менее критичным** (стоимость, DX, масштаб). Внутри фазы пункты тоже идут по убыванию критичности.

---

## Архитектурная тяжесть и связность работ

**Уровни:** *архитектура* — меняется граф оркестрации, контракт состояния или граница LLM↔тулов; *серьёзная доработка* — новый тул / заметное API поведение без смены всего графа; *умеренная* — глубокая правка одного домена (retrieval, один тул); *инкремент* — промпты, доки, тесты, метрики CI.

| Пункт | Уровень | С чем связано (сквозные связи) |
|-------|----------|----------------------------------|
| **A1** `final_answer` обязателен | **Архитектура** | LangGraph single-agent (`supervisor` / `chat`→`tools`→`after_tools`→маршрут; бюджет после тулов), политика остановки; предупреждение в [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py); см. **статус фазы A**. |
| **A2** типы рёбер / `edge_search` | **Серьёзная доработка** (или архитектура, если вводится отдельный сервис обзора графа) | Реализован тул `workspace_graph_reltypes` (+10-й в реестре), см. **статус фазы A**; Phoenix по имени тула без отдельной доработки. |
| **A3** `paper_profile` / null | **Архитектура** (ветка данных) + **умеренная** (ветка тул) | Тул + промпт по плану сделаны; ветка данных / OD-метрики — см. **статус фазы A** (частично). |
| **B1** guided Cypher | **Инкремент** (docstring + тесты) **или серьёзная** (`cypher_query_template` / enum) | Безопасность [`cypher_safety`](../../science_graphrag/agent/cypher_safety.py), снижение ошибок модели; вторая опция трогает реестр и промпт-бандл. |
| **B2** fan-out / дубликаты | **Инкремент** (промпт) **или архитектура** (hash аргументов в state + budget) | Состояние графа, риск взаимодействия с CH4 session memory; observability `tool_trace`. |
| **B3** `paper_quote_search` | **Умеренная** | Qdrant payload, пороги score, выравнивание с `idea_search`; предупреждения в [`chat_envelope`](../../science_graphrag/agent/chat_envelope.py). |
| **C1** `tool_search` | **Архитектура** | Поверхность `bind_tools`, возможно два этапа LLM, манифест, eval harness, UI «какие тулзы доступны». |
| **C2** compaction / капсулы | **Архитектура** | CH4/CH5 память, API `history_digest` / `session_summary`, размер контекста и стоимость; задел под multi-turn. |
| **C3** E2E / CI | **Инкремент** (часто) | Инфраструктура CI при обязательном live API — **серьёзная** по процессу, не по коду репозитория. |
| **D1–D4** | **Умеренная** / **инкремент** | Продуктовая полировка, документация Phoenix, UI без смены ядра графа. |

Детализация по пунктам — в таблицах ниже; у каждого пункта добавлено поле **Масштаб**.

---

## Фаза A — критично (корректность завершения и доверие к графу)

### A1. Гарантия завершения через `final_answer`

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Архитектура** (ядро LangGraph + опционально слой API). |
| **Проблема** | В heavy-сценарии `multi_evidence_speed_accuracy` цепочка тулов оборвалась **без** вызова `final_answer` при непустом тексте ответа и предупреждениях `no_quote_found` / `no_citations` (см. §5.1 в `agent-chat-tools.md`). Пользователь и API-контракт ожидают структурированный финал с `citations`. |
| **Цель** | Любой успешный HTTP-ответ по `/v2/agent/query` в нормальном режиме должен иметь в `tool_trace` последним шагом **`final_answer`**, либо явную **ошибку** уровня API (не «тихий обрыв»). |
| **Направления** | (1) Политика в **budget** / conditional edges: при приближении к `agent_max_tool_calls` принудительно предлагать только `final_answer` или вызывать обёртку «собрать ответ из последних payload». (2) Системный промпт: «если цитат нет — всё равно один `final_answer` с явным gap». (3) Опционально: отдельный **recovery**-путь в графе после таймаута LLM. |
| **Файлы (ориентир)** | [`science_graphrag/agent/graph/supervisor.py`](../../science_graphrag/agent/graph/supervisor.py), ноды `chat` / `budget`, [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), [`agent_v2.py`](../../science_graphrag/api/agent_v2.py) (нормализация ответа при обрыве). |
| **Приёмка** | Повтор `agent_od_workspace_e2e_audit.py --suite heavy`: кейс `multi_evidence_speed_accuracy` с **`final_answer_reached: true`**; добавить **pytest** или live-gate на «последний тул = final_answer» для синтетического короткого графа. |
| **Зависимости** | Нет жёстких; желательно не поднимать `agent_max_tool_calls` «вслепую» до решения политики обрыва. |

### A2. Граф: реальные типы рёбер и пустой `edge_search`

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Серьёзная доработка** (новый тул или режим + Neo4j + реестр + дока); при выделении отдельного «graph introspection» API — **архитектура**. |
| **Проблема** | Модель подставляет **несуществующие** `rel_types` (`MENTIONS_METHOD`, …) → 0 строк, лишние шаги и переход к «тяжёлому» Cypher. |
| **Цель** | Модель может узнать **какие типы рёбер** встречаются рядом с `Work` в workspace (или глобально) без свободного write-Cypher. |
| **Направления** | (1) Новый read-only тул **`workspace_graph_reltypes`** или режим расширения **`workspace_inspect`** (например `mode=graph_reltype_sample`) — ограниченный DISTINCT `type(r)` + лимит. (2) Либо зашить в системный промпт **канонический список** типов из схемы Neo4j проекта (обновлять при смене схемы). (3) В описании `edge_search`: примеры **только** из реальной схемы. |
| **Файлы** | [`edge_search.py`](../../science_graphrag/agent/tools/edge_search.py), [`workspace_catalog_tools.py`](../../science_graphrag/agent/tools/workspace_catalog_tools.py) / Neo4j reads, [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), [`agent-chat-tools.md`](../architecture/agent-chat-tools.md). |
| **Приёмка** | Heavy `graph_ego_methods`: после A2 либо **ненулевой** `edge_search` при осмысленном запросе, либо один явный ответ «типов нет» без серии пустых вызовов; метрика «число нулевых edge_search подряд ≤ 1» в trace-audit (расширение скрипта). |

### A3. Качество карточки работы (`paper_profile`) и null-поля

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Архитектура** по ветке ingestion / graph population; **умеренная** по ветке расширения ответа `paper_profile` + промпт. |
| **Проблема** | `year` / `venue` часто **null** — модель вынуждена угадывать или честно говорить «нет данных», сценарии сравнения слабеют. |
| **Цель** | Либо заполнение полей на ingest/merge, либо явная семантика в payload («not ingested», «source: openalex») и промпт «не заполнять null из головы». |
| **Направления** | (1) Дорожка **данных**: сверка с OpenAlex / PDF front-matter в pipeline (не только тул). (2) **Тул:** в ответе `paper_profile` добавить флаги `metadata_completeness` / `sources`. (3) Промпт: ссылка на `find_works` + вторую работу при пустых полях. |
| **Файлы** | Ingestion / graph writers (вне одного PR), [`workspace_catalog_tools.py`](../../science_graphrag/agent/tools/workspace_catalog_tools.py), промпт. |
| **Приёмка** | Доля null в venue/year снижается на OD-воркспейсе **или** в 100% кейсов модель не галлюцинирует год (eval с teacher judge / rule: year ∈ payload \| null). |

---

## Статус выполнения фазы A

Ниже — что уже сделано в репозитории по пунктам A1–A3, с комментариями (чтобы не путать «план» и «факт в коде»). Фазы B–D в этом разделе **не** отмечаются как выполненные.

### A1. Гарантия завершения через `final_answer`

| Статус | Комментарий |
|--------|-------------|
| **Граф (ядро)** | Выполнено. Узел «budget» между `chat` и `tools` **убран** из single-agent и из subgraph retrieval / graph / writer: бюджет уменьшается **после** выполнения батча тулов (`react_after_tools_decrement_budget` в [`react_edges.py`](../../science_graphrag/agent/graph/react_edges.py)). Маршрут из `chat`: [`route_react_chat_to_tools`](../../science_graphrag/agent/graph/react_edges.py) — при `budget_remaining >= 0` отложенный батч `tool_calls` всё ещё исполняется (исправлен обрыв на последнем шаге). При `budget_remaining < 0` допускается ещё один батч **только** из вызовов `final_answer` (`tool_calls_batch_is_only_final_answer`). |
| **Промпт** | Выполнено. В [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py): явная обязанность закончить `final_answer` даже при пустых цитатах / gap; не вызывать повторно `paper_profile` для того же `work_id` без новой цели. |
| **Слой API / контракт** | Частично в духе плана. Синтетическая запись `final_answer` в `tool_trace` **не** добавлялась (осознанно: честность трассы). Вместо этого в [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) при `tool_policy=allow_tools`, непустом ответе и последнем инструменте в trace ≠ `final_answer` добавляется предупреждение `agent_finished_without_final_answer_tool`. |
| **Тесты** | Выполнено. [`tests/agent/test_react_edges.py`](../../tests/agent/test_react_edges.py), расширение [`tests/test_chat_envelope.py`](../../tests/test_chat_envelope.py). |
| **Приёмка heavy E2E** | Не зафиксирована в этом документе как прогон; рекомендуется повторить `agent_od_workspace_e2e_audit.py --suite heavy` на живом стенде и убедиться, что `multi_evidence_speed_accuracy` даёт `final_answer_reached: true`. |
| **Опциональный recovery после таймаута LLM** | Не реализовывался отдельно; salvage по-прежнему в [`agent_v2.py`](../../science_graphrag/api/agent_v2.py) при deadline. |

**Замечание к таблице «Файлы» выше по A1:** ориентир `chat` / `budget` для актуального кода — см. `chat` → `route_react_chat_to_tools` → `tools` → `after_tools` → `route_react_tools_next` в [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) и одноимённые subgraph-файлы в `agent/graph/nodes/`.

### A2. Реальные типы рёбер и пустой `edge_search`

| Статус | Комментарий |
|--------|-------------|
| **Новый read-only тул** | Выполнено. `workspace_graph_reltypes` (LangChain в [`workspace_paper_tools.py`](../../science_graphrag/agent/tools/workspace_paper_tools.py), логика Neo4j в [`workspace_catalog_tools.py`](../../science_graphrag/agent/tools/workspace_catalog_tools.py) — класс `WorkspaceGraphReltypesTool`). |
| **Канонические подсказки** | Выполнено. Модуль [`work_graph_schema.py`](../../science_graphrag/agent/tools/work_graph_schema.py): `KNOWN_WORK_NEIGHBOR_REL_TYPES` + `WORK_EDGE_REL_TYPES_HINT` для описания `edge_search.rel_types`; в payload тула поле `canonical_hints` (глобальные примеры) vs измеренные `rel_types` по workspace. |
| **Промпт и каталог** | Выполнено. [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), [`agent-chat-tools.md`](../architecture/agent-chat-tools.md) (10 инструментов), [`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py), `EXPECTED_TOOL_NAMES` в [`build_research_chat_prompt_bundle.py`](../../scripts/prompt_audit/build_research_chat_prompt_bundle.py). |
| **UI** | Выполнено. Подписи чата: `chat.run.toolLabel.workspace_graph_reltypes` в `ui/src/i18n/messages/en|ru/partChat.js`. |
| **Trace-audit** | Выполнено. В [`agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py): `edge_search_zero_row_max_streak` и эвристика в `trace_audit` при серии `edge_search` с `row_count == 0`. |
| **Режим `workspace_inspect`** | Не выбирался: вместо расширения `workspace_inspect` взят отдельный тул (как «путь 1» в плане). |

### A3. `paper_profile` и null-поля

| Статус | Комментарий |
|--------|-------------|
| **Тул / семантика в payload** | Выполнено. В ответе `paper_profile`: `metadata_completeness`, `venue_resolution` (`graph_linked` / `no_venue_linked`), `metadata_source`; для `work_not_found` — пустые/нейтральные поля. Pydantic-описания и docstring тула согласованы с [`agent-tools-best-practices.md`](../architecture/agent-tools-best-practices.md). |
| **Промпт** | Выполнено. Явное правило не выдумывать year/venue при null в [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py). |
| **Дорожка данных (ingest / merge)** | Частично. В pipeline уже используется `merge_draft_prefer_enriched` после OpenAlex ([`_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py)); добавлен регрессионный тест [`tests/ingestion/test_merge_draft_openalex.py`](../../tests/ingestion/test_merge_draft_openalex.py). Целевая приёмка плана («доля null на OD» / teacher eval) **не** закрыта одним PR — требует измерений на воркспейсе или отдельной доработки writers/pipeline. |

---

## Фаза B — высокий приоритет (меньше лишних шагов и ложных Cypher)

### B1. «Guided» Cypher и снижение когнитивной нагрузки на модель

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Инкремент** (примеры, тесты) **или серьёзная** (новый шаблонный тул / enum — реестр, промпт-бандл, eval). |
| **Контекст** | Ложное срабатывание `SET` внутри `:Dataset` **исправлено** (word-boundary в [`cypher_safety.py`](../../science_graphrag/agent/cypher_safety.py)); остаётся риск других шаблонов и сложных запросов. |
| **Направления** | (1) Расширить **позитивные** примеры в docstring `cypher_query`. (2) Каталог **2–4 шаблонов** «ego-graph / two-hop / co-citation» как готовые строки в доке или вспомогательный тул **`cypher_query_template`** с enum сценария + параметрами (без свободного текста). (3) Юнит-тесты на граничные лейблы (`:Reset` если появится — не конфликт с `SET` и т.д.). |
| **Приёмка** | Heavy `graph_ego_methods`: ≤ **1** неуспешный `cypher_query` при валидном графе; 0 — при пустом графе с явным объяснением. |

### B2. Дисциплина fan-out и «дубликаты» тулов

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Инкремент** (только промпт) **или архитектура** (учёт истории вызовов / дедуп в state на стороне budget — связь с графом состояний и тестами CH4). |
| **Проблема** | Два `find_works` подряд для **разных** запросов — норма; два `paper_profile` подряд без нового `work_id` — часто лишнее. `trace_audit` уже считает вызовы — использовать в eval. |
| **Направления** | (1) Промпт: явно разрешить многократный `find_works` при сравнении; ограничить повторный `paper_profile` без новой цели. (2) В **budget**-ноде: мягкий штраф / предупреждение в state при повторе того же тула с теми же аргументами (если доступно сравнение args hash). |
| **Файлы** | [`research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), [`supervisor.py`](../../science_graphrag/agent/graph/supervisor.py), при необходимости [`tracing.py`](../../science_graphrag/agent/graph/tracing.py). |
| **Приёмка** | Метрика на OD-heavy: среднее число шагов на успешный сценарий не растёт; нет цепочек `paper_profile`→`paper_profile` с идентичным `work_id` в golden cases. |

### B3. `paper_quote_search` и предупреждение `no_quote_found`

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Умеренная** (retrieval + контракт предупреждений); без смены графа агента, но возможны изменения индексации/пейлоада Qdrant в связке с ingestion. |
| **Проблема** | Частые `no_quote_found` при том что `idea_search` находит чанки — рассинхрон порогов / запросов. |
| **Направления** | (1) Согласовать **top_k**, порог score, нормализацию запроса между тулом и Qdrant. (2) Промпт: порядок «сначала `idea_search` / узкий work_id, потом quote». (3) Возврат тулу структурированного «почему пусто» (нет чанков vs низкий score). |
| **Файлы** | [`paper_quote_search_tool.py`](../../science_graphrag/agent/tools/paper_quote_search_tool.py), промпт, при необходимости [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) для `warnings`. |
| **Приёмка** | Доля `no_quote_found` на фиксированном OD-наборе вопросов снижается на X% или документированно объясняется (thin corpus). |

---

## Фаза C — средний приоритет (стоимость контекста и масштаб каталога)

### C1. `tool_search` и отложенные полные схемы

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Архитектура** (новый этап маршрутизации тулов, изменение поверхности `bind_tools` или двухфазный вызов LLM). Связано с slim-roadmap §6.1 и стоимостью промпт-бандла. |
| **Ссылка** | Roadmap §6.1 / [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md). |
| **Направления** | Короткий каталог в промпте + тул `tool_search` + eval-ворота до LLM-маршрутизации; синхронизация с [`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py). |
| **Приёмка** | Снижение `approx_input_tokens_bundle_total` в `build_research_chat_prompt_bundle.py --json` при сохранении качества на OD-eval. |

### C2. Компактация и «капсулы» evidence

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Архитектура** (память сессии, формат сообщений в графе, API CH4/CH5). Связано с размером контекста, multi-turn и стоимостью, не с одним тулом. |
| **Ссылка** | Roadmap L0–L4, API `context_compacted`, `session_summary`. |
| **Направления** | Не раздувать повторяющиеся payload тулов в истории ReAct; капсулы для повторно используемых work_id / chunk ids. |
| **Приёмка** | Меньше токенов на multi-turn + те же heavy-сценарии без деградации. |

### C3. Расширение E2E-аудита и CI

| Поле | Содержание |
|------|------------|
| **Масштаб** | **Инкремент** по коду скриптов/тестов; **серьёзная** по процессу, если job становится обязательным и требует стабильного live-стенда и секретов в CI. |
| **Направления** | (1) Nightly или optional job: `agent_od_workspace_e2e_audit.py --suite heavy --trace-audit` с `AGENT_LIVE_BASE`. (2) Жёсткий gate: «последний тул = `final_answer`». (3) Расширить `trace_audit`: нулевые `edge_search` подряд, ошибки Cypher. |
| **Файлы** | CI yaml (если есть), скрипт, [`chat-agent-roadmap-trace-audit-2026-04-27.md`](./chat-agent-roadmap-trace-audit-2026-04-27.md) — ссылка на этот план. |

---

## Фаза D — ниже приоритета (полировка и продукт)

### D1. `format_bibliography_gost`

**Масштаб:** **Умеренная** (логика тул + контракт ошибок). Валидация `work_ids` ⊆ workspace, понятные ошибки в payload для модели; примеры в промпте для 3+ работ.

### D2. Чёткая матрица «когда какой retrieval-тул»

**Масштаб:** **Инкремент** (промпт + архитектурная дока). Короткая таблица в `research_chat_system`: `idea_search` vs `paper_quote_search` vs `workspace_inspect` vs `find_works` (1 экран, без дублирования длинных docstring).

### D3. Phoenix / корреляция

**Масштаб:** **Архитектура** при смене propagation / resource атрибутов между процессами; **инкремент** при ограничении документацией и операторскими практиками. Развести визуально или по атрибутам **ingest** vs **agent** (см. §5.1 — смешение спанов в одном trace); документировать для операторов в [`observability-phoenix.md`](../architecture/observability-phoenix.md).

### D4. UI / манифест

**Масштаб:** **Инкремент** (ui + константы манифеста). Синхронизация подсказок в UI с реестром после каждого изменения тулов ([`tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py), [`chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py)).

---

## Сводная таблица фаз и ориентировочный порядок внедрения

| Фаза | Темы | Ориентир последовательности |
|------|------|------------------------------|
| **A** | A1 → A2 → A3 (A1 и A2 можно параллелить разным людям) | 1–2 спринта |
| **B** | B1 → B2 → B3 | после или частично вместе с A |
| **C** | C1 → C2 → C3 | когда каталог/стоимость станут узким местом |
| **D** | D1–D4 | по мере касания UX и observability |

---

## Риски и что не смешивать

- **Не** подменять A1 только ростом `agent_max_tool_calls` без политики финала — это маскирует симптом и дороже по токенам.
- Изменения **схемы Neo4j** и ingest должны сопровождаться обновлением A2/B1 и архитектурной доки.
- Любой новый тул: чеклист из [`agent-tools-best-practices.md`](../architecture/agent-tools-best-practices.md) + обновление `EXPECTED_TOOL_NAMES` в [`build_research_chat_prompt_bundle.py`](../../scripts/prompt_audit/build_research_chat_prompt_bundle.py).

---

## История правок документа

| Дата | Изменение |
|------|-----------|
| 2026-04-28 | Первая версия плана после heavy E2E и фикса `cypher_safety` (Dataset vs SET). |
| 2026-04-28 | Добавлены раздел «Архитектурная тяжесть и связность», поле **Масштаб** у пунктов A–D. |
| 2026-04-28 | Раздел **«Статус выполнения фазы A»**: отметка выполненного в коде (A1–A3) с комментариями; уточнена строка таблицы про A1/A2 под фактическую реализацию. |
