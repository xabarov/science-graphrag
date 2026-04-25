# [HISTORICAL] Completed Cursor agent rounds — 2026-04-25

> **[HISTORICAL] Архив раундов 1–5.** Все четыре параллельных слота в каждом раунде завершены и приняты. Документ создан 2026-04-25 в рамках уборки `docs/analysis/`, чтобы вынести подробные ретроспективы из активного [`../master-roadmap-and-refactor-plan-2026-04-25.md`](../master-roadmap-and-refactor-plan-2026-04-25.md). Используется только как ссылка для контекста.

**Дата создания:** 2026-04-25  
**Источник:** ранние версии `master-roadmap-and-refactor-plan-2026-04-25.md` §7 «Запуск Cursor-агентов параллельно».  
**Активные раунды (6+):** см. [`../master-roadmap-and-refactor-plan-2026-04-25.md`](../master-roadmap-and-refactor-plan-2026-04-25.md) §6.

---

## Сводная таблица

| Раунд | Дата DONE | Что сделано (4 параллельных слота) | Результат |
|-------|-----------|------------------------------------|-----------|
| **Раунд 1** (Sprint S1 ядро) | 2026-04-25 | A1: G-IngestSlim · A2: G-PipelineFacade · A3: G-PhoenixSplit · A4: H-i18n-fixes + H-Cursor*-buttons in dedup | Все 4 split-PR'а; backlog обновлён |
| **Раунд 1.5** (закрытие долгов S1) | 2026-04-25 | A1: G-PipelineFacade завершить (`pipeline.py` = 53 строки фасад) · A2: split `observability/spans.py` (410→3 модуля) · A3: фикс регрессии `IngestJobRegistry` | 375 тестов зелёные; Wave Y1 foundation выполнен полностью |
| **Раунд 2** (после 1.5 + Y1) | 2026-04-25 | A1: G-StoreFactory (`api/deps.py` + `StoreRegistry`) · A2: G-WorkspaceGraphSplit (1214→пакет) · A3: G-WorksSplit (817→пакет) · A4: H-GraphWorkspacePanelSplit (1164→shell + hooks) | 9 тестов исправлено в review; pylint 8.78/10; 383 passed, 2 skipped |
| **Раунд 3** (Wave W + Y2 + X2 + Neo4jSplit + AskPanelSplit) | 2026-04-25 | A1: Wave W backend (Dramatiq + Redis) · A2: Wave Y2 + X2 комбинированный · A3: G-Neo4jSplit (1022→11 модулей) · A4: H-AskPanelSplit (670→4 файла, 487 строк) | 390 passed, 2 skipped; pylint 8.92/10 |
| **Раунд 4** (Wave Y3 + GR2 + G-RetrievalCore + H-AskV2SSE) | 2026-04-25 | A1: Wave Y3 backend (`/v2/agent/query` SSE+sync, spec, deprecation) · A2: Wave GR2 backend (`node_kind`, `display_type`, prioritized LIMIT) · A3: G-RetrievalCore (`api/retrieval.py` 54 строки) · A4: H-AskV2SSE (`useAgentStream.js`) | 406 passed, 2 skipped, 0 failures; pylint 9.34–9.50/10; GR2 defect fixed (`skipped_by_kind`) |
| **Раунд 5** (Wave T + GR3 + Y4 + G-StageExtractionSplit) | 2026-04-25 | A1: Wave T backend (entity dedup Institution/Venue/Method/Dataset + ADR 019) · A2: Wave GR3 backend + frontend (H-GraphCanvasMvpSplit + aggregator + expand) · A3: Wave Y4 backend (multi-agent supervisor + ADR 020) · A4: G-StageExtractionSplit (ingestion/llm split) | 421 passed, 2 skipped, 0 stable failures; pylint 9.03/10; vitest 135 passed; D1 (flaky smoke test) исправлен |

---

## Подробности по раундам

### Раунд 1 (Sprint S1 ядро) — DONE 2026-04-25

- **Agent 1: G-IngestSlim** — `api/ingest_jobs.py` (846 строк) → `api/ingest/{router,registry,dispatcher,dto}.py`. Закрывает запись в `docs/backlog/refactor-backend.md`.
- **Agent 2: G-PipelineFacade** — `ingestion/pipeline.py` (976 строк) → `ingestion/stages/` + `IngestRunContext`. Воркер сразу получает один и тот же контекст без копипасты сторов.
- **Agent 3: G-PhoenixSplit** — `observability/phoenix_tracer.py` (492 строки) → `observability/{__init__.py, spans.py, instrumentation.py}` + тесты `test_span_contract.py`.
- **Agent 4: H-i18n-fixes + H-Cursor*-buttons-in-dedup** — `HypothesisPanel.jsx`, `IngestionSettingsPanel.jsx`, `WorkspacePage.jsx` (литералы), `WorkspaceDedupSection.jsx`, `WorkDedupReviewDialog.jsx`. Закрывает 2 записи backlog.

### Раунд 1.5 (закрытие долгов Sprint S1 перед запуском Раунда 2) — DONE 2026-04-25

> Раунд добавлен по итогам Sprint S1 review (2026-04-25): три задачи Sprint S1 не прошли acceptance-критерии и блокировали Раунд 2. Выполнено строго до Раунда 2.

- **Agent 1: Завершить G-PipelineFacade** — тяжёлая логика в `_pipeline_impl.py`; `pipeline.py` = 53 строки фасад-реэкспорт (≤250 ✅). 375 тестов зелёные.
- **Agent 2: Split `observability/spans.py` (410 строк)** — разнесено на `observability/spans/{attributes.py,decorators.py,__init__.py}`; все файлы ≤300 строк ✅; `test_span_contract.py` зелёный.
- **Agent 3: Фикс регрессии IngestJobRegistry** — `__init__` не вызывает `init_db`/`mark_stale`; добавлен ленивый `bootstrap()`; monkeypatch-тесты перенесены на `router._registry`; все `test_api_smoke` зелёные.

> Agent 4: нет — три задачи не пересекаются по файлам, безопасно параллельны. Wave Y1 (P3 Sprint S1) выполнен полностью: deps установлены, `instrumentation.py` наполнен, `config.py` и `.env.example` обновлены.

### Раунд 2 (после раунда 1.5 + Y1 foundation) — DONE 2026-04-25

- **Agent 1: G-StoreFactory** — `api/deps.py` с `StoreRegistry` + `get_stores()`; lifespan в `main.py`.
- **Agent 2: G-WorkspaceGraphSplit** — `api/workspace_graph.py` (1214 строк) → пакет `api/workspace_graph/{cypher,projection,router,__init__}.py` + helpers.
- **Agent 3: G-WorksSplit** — `api/works.py` (817 строк) → пакет `api/works/{dto,detail,graph_neighborhood,chunks,router,__init__}.py`.
- **Agent 4: H-GraphWorkspacePanelSplit** — `GraphWorkspacePanel.jsx` (1164 строк) → shell + `useGraphWorkspaceData`, `GraphViewModeSwitch`, `GraphSidePanel`, `GraphDebugInspector`.

> **Review 2026-04-25 (9 тестов исправлено):**
>
> Три класса дефектов обнаружены и устранены в ходе review:
>
> 1. **`works/__init__.py` naming-конфликт:** пакет re-экспортирует `router` (APIRouter instance), что затеняет submodule-ссылку `works.router`. Тесты использовали `api_main.works_api.*` — атрибут исчез после сплита. **Фикс:** `works_api = sys.modules["science_graphrag.api.works.router"]` shim в `main.py`. Технический долг закрыт в Раунде 4 (G-RetrievalCore).
>
> 2. **DI-ordering в `agent.py`:** `Depends(get_stores)` резолвится до тела endpoint, поэтому `agent_enabled` guard не защищал от `RuntimeError` при незаполненном `app.state.stores` в тестах. **Фикс:** оба теста теперь переопределяют `get_stores`.
>
> 3. **Сигнатура `work_sources_payload`:** в сплите добавился параметр `stores`, тест-fake имел старую сигнатуру. **Фикс:** обновлен fake.
>
> Качество: pylint 8.78/10, isort/black чисто, frontend ESLint чисто, **383 passed, 2 skipped**.

### Раунд 3 (Wave W + Y2 + X2 + Neo4jSplit + AskPanelSplit) — DONE 2026-04-25

- **Agent 1: Wave W backend** — Dramatiq actor + Redis pub/sub `IngestEventBus` v2; `science_graphrag/worker/`; ADR + spec.
- **Agent 2: Wave Y2 + Wave X2** — один комбинированный PR в `agent/`. LangGraph `StateGraph`, 6 tools на `langchain_core.tools`, Phoenix `traced_tool_span` + `chain_span("agent.query")` + `RETRIEVER` для Qdrant + `EMBEDDING` span на query.
- **Agent 3: G-Neo4jSplit** — `neo4j_store.py` (1022 строки) → 11 модулей пакета `storage/neo4j/`.
- **Agent 4: H-AskPanelSplit** — `AskPanel.jsx` (670 строк) → shell + `useAskSubmit`, `AskSessionControls`, `AskAnswerPanel` (4 файла, 487 строк суммарно).

> **Review 2026-04-25:** 390 passed, 2 skipped; pylint 8.92/10; isort/black/ESLint чисто. Единственное отклонение от спецификации: `IngestEventBus` живёт в `api/ingest_event_bus.py`, а не в `api/ingest/dispatcher.py` — функционально не влияет, Round 4 не блокирует. Метрика: 23 новых модуля, neo4j_store 1022→11 файлов, AskPanel 670→4 файла 487 строк суммарно.

### Раунд 4 (Wave Y3 + GR2 + G-RetrievalCore + H-AskV2SSE) — DONE 2026-04-25

- **Agent 1: Wave Y3 backend** — `api/agent_v2.py`, `/v2/agent/query` (SSE+sync), `docs/specs/agent-tools-v2.md`, deprecation header v1.
- **Agent 2: Wave GR2 backend** — `node_kind`, semantic `display_type`, prioritized LIMIT + `meta.skipped_by_kind`; ADR 011 updated.
- **Agent 3: G-RetrievalCore** — `science_graphrag/retrieval/` пакет; `api/retrieval.py` тонкий router (54 строки); `main.py` shim удалён; `works/__init__` naming fixed (закрытие долга Раунда 2).
- **Agent 4: H-AskV2SSE** — `useAgentStream.js`; `useAskSubmit.js` SSE path; `AskAnswerPanel` stream events.

> **Review 2026-04-25:** 406 passed, 2 skipped, 0 failures; pylint 9.34–9.50/10; isort/black/ESLint чисто. Исправлен дефект GR2: `skipped_by_kind` вычислялся только из cap-overflow, но не учитывал узлы, которые не были запрошены из-за priority-ограничений — добавлен запрос kind-distribution и пересчёт `skipped_by_kind = available − fetched`. Все структурные и smoke-проверки ✓.

### Раунд 5 (Wave T + GR3 + Y4 + G-StageExtractionSplit) — DONE 2026-04-25

- **Agent 1: Wave T backend** (entity dedup Institution/Venue/Method/Dataset + ADR 019) — требует G-Neo4jSplit (Раунд 3).
- **Agent 2: Wave GR3 backend + frontend** (H-GraphCanvasMvpSplit → aggregator → expand endpoint) — последовательно внутри агента.
- **Agent 3: Wave Y4 backend** (multi-agent supervisor: retrieval/graph/writer specialists + ADR 020).
- **Agent 4: G-StageExtractionSplit** (ingestion/llm → prompts/ + heuristics/ + executor + orchestrator).

> **Review 2026-04-25:** 421 passed, 2 skipped, 0 stable failures; pylint 9.03/10; ESLint чисто, vitest 135 passed.
> Дефект D1 (`test_build_agent_and_run_smoke` flaky — реальный LLM в smoke тесте) исправлен: fake LLM через `monkeypatch`.
> isort/black нарушения в `ingest_jobs.py` и `idea_workflow.py` — pre-existing, зафиксированы в бэклоге.

---

## Чему научились (мета-выводы)

- **Comb split-PR раньше продуктовой волны.** Раунд 2 (G-WorkspaceGraphSplit, G-WorksSplit) → Раунд 4 (Wave GR2 правит подмодули): split первым = меньше merge-боли.
- **Round 1.5 («закрытие долгов») как практика.** Если acceptance не пройден в раунде N, не «двигаем дальше», а устраняем долг до раунда N+1 — иначе долг копится и ловит дефектами.
- **Naming conflicts при пакетировании (`__init__.py` re-export shadows submodule).** Раунд 2 поймал в `works/`, Раунд 4 закрыл общий шаблон через прямой `sys.modules` shim в `main.py` или (предпочтительно) через переименование re-export'а.
- **Phoenix-инструментация — рядом с продуктовой волной (Wave Y2 + X2 одним PR).** Иначе LLM-стадия попадает в production без полного `chain_span`/`RETRIEVER`/`EMBEDDING`-разметки.
- **Smoke-тесты через `monkeypatch` для LLM.** Real LLM в smoke = flaky на CI; всегда `fake_chat_model` фабрика через fixture.
