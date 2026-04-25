# Master roadmap & refactor plan — 2026-04-25

> Единый план развития science-graphrag, который связывает шесть активных роадмапов из `docs/analysis/` с обновлённым бэклогом рефакторинга из `docs/backlog/`. Цель — параллельная работа над **продуктовыми волнами** и **структурным долгом** без блокировок и переписывания одних и тех же файлов разными агентами одновременно.

## 1. Принципы

1. **Рефакторинг следует за продуктом.** Каждый структурный пункт ссылается на ту волну, которой он расчищает дорогу (synergy). Чистый рефакторинг ради рефакторинга не запускаем.
2. **Маленькие срезы.** Один split-PR — один god-файл. Один продуктовый PR — одна волна, один контракт.
3. **Контракт раньше реализации.** Меняя API/payload (ingest events, agent v2, GR2/GR4 graph payload, новые семейства бенчмарков) — сначала фиксируем контракт в `docs/specs/*.md`, потом backend, потом UI.
4. **Параллелизм по файлам, не по фичам.** Параллельные агенты могут идти, только если их файловые скоупы не пересекаются (см. матрицу параллельности §6).
5. **`Phoenix` обязателен на каждой новой LLM-стадии.** Любая новая LLM-операция (агент, idea-assist, claims, semantic) идёт через `llm_span` с полным контрактом из `docs/architecture/observability-phoenix.md`.
6. **Ссылки на бэклог в каждом продуктовом PR.** При добавлении кода в god-файл — открыть/обновить запись в `docs/backlog/refactor-{backend,frontend}.md`.

## 2. Картина треков

| Трек | Заголовок | Источник | Status | Текущая волна / next |
|------|-----------|----------|--------|----------------------|
| **A** | Ingest async pipeline | [`ingestion-async-pipeline-roadmap-2026-04-25.md`](ingestion-async-pipeline-roadmap-2026-04-25.md) | Wave U done, V done, W done | **Wave W done** → Round 4 |
| **B** | LangGraph migration | [`langgraph-migration-plan-2026-04-25.md`](langgraph-migration-plan-2026-04-25.md) + ADR 016/017 | Wave R/S done, Y1/Y2 done, Y3 done | **Wave Y4** (multi-agent supervisor) |
| **C** | Phoenix tracing coverage | [`phoenix-tracing-coverage-2026-04-25.md`](phoenix-tracing-coverage-2026-04-25.md) | Wave X1 done, X2 done | **Wave X2 done** → X3 (worker OTel propagation) |
| **D** | Ontology + Benchmarks + IR | [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) | M/N/O/P/Q/R/S done, T open | **Wave T** (entity dedup), continuation of Q (multihop), R (multi-agent metrics — ждёт Y4) |
| **E** | Graph UX aggregation | [`graph-ux-aggregation-roadmap-2026-04-25.md`](graph-ux-aggregation-roadmap-2026-04-25.md) + ADR 011/012 | GR1 done, GR2 done, GR3..GR5 open | **Wave GR3** (aggregator + lazy expand) |
| **F** | Workspace experience | [`workspace-experience-gap-2026-04-24.md`](workspace-experience-gap-2026-04-24.md) | Wave I/J/K1/K2/K3/L1/L2 done, L3 gated | **Wave L3** stub, Wave M (PDF page citations, optional) |
| **G** | Backend refactor | [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md) | mixed | см. §4 |
| **H** | Frontend refactor | [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | mixed | см. §4 |

> **Важно:** треки G/H — не отдельная команда людей, а отдельные PR'ы, которые перемежаются с продуктовыми. Каждая запись бэклога расчищает дорогу для конкретного **продуктового** трека.

## 3. Граф зависимостей (волны и рефакторинг)

```
                    ┌──── X1 (done) ─────┐
                    │                    │
       Wave U (done) ── Wave V (done) ── Wave W (Redis+Dramatiq)
                                      │
                                      └── G-IngestSlim (api/ingest_jobs split)
                                               │
                                               └── G-PipelineFacade (ingestion/pipeline)
                                                        │
                                                        └── G-Neo4jStoreSplit (storage/neo4j_store)


       Wave Y1 (foundation) ── Wave Y2 (single-agent LG) ── Wave Y3 (/v2 SSE) ── Wave Y4 (multi-agent)
                │                       │                       │                       │
                │                       └── X2 (Phoenix retrieval agent)                │
                │                       │                       │                       │
                │                       └── G-StoreFactory (DI stores)                  │
                │                       │                       │                       │
                │                       │                       └── H-AskV2SSE (frontend)│
                │                       │                                               │
                │                       └── Wave Y5 (smolagents → LG) ──────────────── Wave Y6 (cleanup)
                │
                └── G-PhoenixSplit (observability/phoenix_tracer)


       Wave M (M done) ── Wave N (done) ── Wave O (done, claims production)
                                                      │
                                                      └── Wave Q (hybrid + indexes done) ── Wave R (agent done) ── Wave S (done)
                                                                                                                       │
                                                                                                                       └── G-IdeaAssistSplit (Wave S follow-up)
                                                                                                                       │
                                                                       Wave T (entity dedup) ── G-Neo4jStoreSplit ──── │
                                                                       │
                                                                       └── ADR 018 + spec
                                                      │
                                                      └── G-RetrievalCore (api/retrieval split)
                                                                  │
                                                                  └── G-StageExtractionSplit (ingestion/llm)


       Wave GR1 (done) ── Wave GR2 (display_type/node_kind) ── Wave GR3 (aggregator) ── Wave GR4 (reader view) ── Wave GR5 (counters)
                                            │
                                            └── G-WorkspaceGraphSplit (api/workspace_graph)
                                            │
                                            └── G-WorksSplit (api/works)
                                            │
                                            └── H-GraphWorkspacePanelSplit (frontend)
                                            │
                                            └── H-GraphCanvasMvpSplit (frontend, already in backlog)


       Wave I/J/K1/K2/K3/L1/L2 (done) ── Wave L3 (gated stub) ── Wave T (entity dedup, продолжение)
                                                                       │
                                                                       └── G-WorkspaceDedupSplit (api/workspace_dedup)
                                                                       │
                                                                       └── H-WorkspacePageSlim
```

> Стрелки показывают **рекомендованный** порядок. Параллельные треки между уровнями независимы по файлам.

## 4. Roadmap-волны и связанный рефакторинг (детально)

### 4.1 Track A — Ingest async (продолжение)

**Цель:** убрать `threading.Thread` из API, унести ingest в Dramatiq actor поверх Redis, оставить SSE контракт неизменным.

**Шаги:**

1. **Wave W backend (продукт):** `docker-compose.yml` (+ dev), `science_graphrag/worker/`, `dramatiq` actor `ingest_document_actor`, `IngestEventBus` v2 (Redis pub/sub), удаление `mark_stale_running_jobs_failed`. Артефакт: ADR `0XX-ingest-worker-redis.md`, spec `docs/specs/ingest-worker-v1.md`.
2. **G-IngestSlim (рефактор, обязателен в этой же фазе):** [Slim `api/ingest_jobs.py` → `api/ingest/{router,registry,dispatcher,dto}.py`](../backlog/refactor-backend.md#open-slim-apiingest_jobspy-846-lines--registryworker-vs-httpsse). Wave W меняет только `dispatcher.py` и реализацию `IngestEventBus`.
3. **G-PipelineFacade (рефактор, тот же кластер):** [фасад `ingestion/pipeline.py` + `IngestRunContext`](../backlog/refactor-backend.md#open-refactor-ingestionpipelinepy-976-lines-into-stages-with-context-facade). Воркер сразу получает один и тот же контекст, без копипасты сторов.
4. **CLI правка:** `cli/main.py` команда `worker` (см. [G-CLISplit](../backlog/refactor-backend.md#open-split-climainpy-361-by-command-groups)).
5. **Frontend:** изменений UI **не нужно** (Wave V уже доставила SSE; контракт сохраняется). Рекомендуется только добавить ссылку на Phoenix trace из job-карточки (X1.6 уже доставила `phoenix_trace_id`).

**Acceptance уровня трека:** API падает/перезапускается без потери ingest; `tests/integration/test_full_ingest_integration.py` зелёный с воркером; runbook `deploy.md`/`backup.md` обновлены под Redis.

### 4.2 Track B — LangGraph migration

1. **Wave Y1 (foundation):** dependencies, smoke `ChatOpenAI`↔OpenRouter, **LangChain instrumentation** в `phoenix_tracer.py`, `.env.example`, CI с `[agent]` extra. Без runtime-смены поведения.
2. **G-PhoenixSplit (рефактор, готовит почву):** [`observability/phoenix_tracer.py` split](../backlog/refactor-backend.md#open-split-observabilityphoenix_tracerpy-492--init-vs-spans-vs-instrumentation). Y1 затем кладёт `instrumentation.langchain` в готовое место.
3. **G-StoreFactory (рефактор, перед Y2/Y3):** [DI `StoreRegistry`](../backlog/refactor-backend.md#open-unified-bolt-access-factory--agentidea-assist-composition-root). Снимает per-request init Neo4j/Qdrant в agent-пути, который явно отмечен как pain в `phoenix-tracing-coverage`.
4. **Wave Y2:** 6 tools на `langchain_core.tools`, `StateGraph`, `runtime_legacy.py`. Тесты `tests/agent/`. Параллельно — **Wave X2** (Phoenix retrieval agent observability), они логически склеиваются.
5. **Wave X2 (трек C):** `traced_tool_span` вокруг tools, `chain_span("agent.query", ...)`, `RETRIEVER` для Qdrant idea_search, `EMBEDDING` span на query embed, `phoenix_trace_id` в `AgentQueryResponse`. Тесты — расширение `test_span_contract.py`.
6. **Wave Y3:** `POST /v2/agent/query` (SSE + sync JSON), spec `docs/specs/agent-tools-v2.md` (создать). Backend + spec — backend-агент. Frontend — отдельная задача [H-AskV2SSE](../backlog/refactor-frontend.md#open-frontend-wiring-for-v2agentquery-sse-wave-y3-follow-up).
7. **G-AskPanelSplit + H-AskV2SSE:** оба идут перед/во время Wave Y3 (см. §6 — параллельно с backend).
8. **Wave Y4:** supervisor + specialists + ADR. **Внимание:** ADR номер из плана (`017-langgraph-supervisor-multiagent.md`) **конфликтует** с уже занятым `017-hypothesis-idea-assist-advisory.md`. Перенумеровать в `019-...` (после `018-entity-dedup` из Wave T) или `020-...`. Перед Y4 — обновить [`docs/adr/README.md`](../adr/README.md) и зафиксировать соглашение.
9. **Wave Y5:** миграция research spike. Параллельна с Y4 при наличии ресурсов.
10. **Wave Y6:** удаление `smolagents`, `BaseAgentTool`, `runtime_legacy`, `POST /v1/agent/query`. **Условие:** UI на v2 (см. H-AskV2SSE) и pass `eval/agent_tools/*`.

### 4.3 Track C — Phoenix tracing (продолжение)

* **Wave X1 — done.** Все substep'ы инструментированы; `phoenix_trace_id` в job.
* **Wave X2 — open.** Полная связка с Track B (см. выше). Можно начать **сразу после Y1**: уже доступна `LangChainInstrumentor`. Файловый скоуп — `science_graphrag/agent/`, `api/agent.py`, тесты `tests/observability/`. Не пересекается с трек A (ingest) и трек D (ontology).
* **Заметка про Track A Wave W:** OTel-контекст не пересекает границу процесса в Dramatiq без `inject`/`extract`. Перед merge Wave W — добавить `tests/observability/test_worker_trace_propagation.py` и middleware в `science_graphrag/worker/`. Это **расширение X1 в воркер-направление** (X1.7?), а не часть X2.

### 4.4 Track D — Ontology / Benchmarks / IR

Уже многое доставлено (Wave M/N/O/P/Q/R/S отмечены `[x]` в роадмапе). Открытые крупные пункты:

1. **Wave T (entity dedup для Author/Institution/Venue/Method/Dataset):**
   - Backend: пакет `science_graphrag/dedup/<type>_pipeline.py`, общая Postgres-очередь `entity_dedup_conflicts` (расширение ADR 014), коллекции Qdrant `authors/institutions/...`, ADR `018-entity-dedup-pipeline.md`, supersede `work-dedup-pipeline-v2.md` → `entity-dedup-pipeline-v2.md`.
   - **Перед/параллельно:** [G-Neo4jStoreSplit](../backlog/refactor-backend.md#open-split-storageneo4j_storepy-1022-lines-by-domain-or-layer) — добавлять writes/{authors,institutions,...} проще в подмодулях.
   - Frontend: вкладки dedup по типам, `WorkDedupReviewDialog` reuse → [H-Cursor*-buttons in dedup dialogs](../backlog/refactor-frontend.md#open-switch-dedup-dialogs-to-cursor-button-family).
   - Settings: расширить snapshot полями `entity_dedup_*` ([G-SettingsSplit](../backlog/refactor-backend.md#open-settings-service-split-504)).
2. **Wave Q follow-ups (multihop / hybrid усиление):** core retrieval нужно вынести из `api/retrieval.py` ([G-RetrievalCore](../backlog/refactor-backend.md#open-corerouter-split-for-apiretrievalpy-682)) — это позволит писать unit-тесты ablation без поднятия FastAPI.
3. **Wave R follow-ups (multi-agent benchmarks):** ждут Wave Y4 (новый tier `agent_tools_multiagent` с `expected_specialist_sequence`).
4. **Wave S follow-ups:** [Split idea-assist workflow orchestration](../backlog/refactor-backend.md#open-split-idea-assist-workflow-orchestration-wave-s-follow-up). Требуется перед расширением гипотез до multi-agent (Y4 + S+).
5. **Benchmark UI рост:** [Split `BenchmarkPage/CaseDetailDialog.jsx`](../backlog/refactor-frontend.md#open-split-benchmarkpagecasedetaildialogjsx-790) и [`CompareTab/RunTab`](../backlog/refactor-frontend.md#open-split-benchmarkpagecomparetabjsx-417-and-runtabjsx-365) перед Wave M/Q/R follow-ups.
6. **Backend ingestion LLM:** [Split `ingestion/llm/stage_extraction.py`](../backlog/refactor-backend.md#open-split-ingestionllmstage_extractionpy-849--orchestrator-vs-prompts-vs-heuristics) — перед ростом семейств extractor'ов (Wave N production, Wave O claims maturation).

### 4.5 Track E — Graph UX aggregation

1. **Wave GR2 (display_type/node_kind/prioritized LIMIT):** backend в `api/works.py` + `api/workspace_graph.py`. Перед началом — **G-WorkspaceGraphSplit** ([backlog](../backlog/refactor-backend.md#open-split-apiworkspace_graphpy-1214-lines--projection-vs-cypher-vs-http)) и параллельно **G-WorksSplit** ([backlog](../backlog/refactor-backend.md#open-split-apiworkspy-817--graph-dto-vs-vector-vs-blob)).
2. **Wave GR3 (aggregator + lazy expand):** новый эндпоинт `expand`. Frontend — `GraphCanvasMvp` обработка клика по агрегатору + `GraphSidePanel` preview. Перед началом — **H-GraphWorkspacePanelSplit** и **H-GraphCanvasMvpSplit** (оба уже в бэклоге).
3. **Wave GR4 (`view=raw|reader`):** виртуальные `AUTHORED` рёбра, `via` trace; default — обсудить (ADR opt). UI: тогглер в `WorkspaceGraphToolbar`. Не блокируется рефактором, но удобнее после GR3 split.
4. **Wave GR5 (denormalized counters + weighted layout):** `cites_in_count`, `cites_out_count`, `authors_count` на `:Work`. Backend — миграция Neo4j (фон, идемпотентная) + расширение payload. Перед — **G-Neo4jStoreSplit** (опционально, но желательно).
5. **GR2/GR3/GR4/GR5 в API workspace_graph:** Все четыре волны точечно правят разные подмодули **только если** G-WorkspaceGraphSplit выполнен — иначе каждая волна правит один god-файл и блокирует другие.

### 4.6 Track F — Workspace experience (продолжение)

Большая часть Wave I/J/K/L доставлена. Открытое:

1. **Wave L3 (Institution/Venue dedup) — gated stub:** реальная работа уйдёт в Wave T (см. трек D).
2. **Wave M идея — PDF page citations / table extracts:** опционально, не приоритет.
3. **Frontend дисциплина:** [H-WorkspacePageSlim](../backlog/refactor-frontend.md#open-slim-workspacepagejsx-530--extract-papers-model--dialogs--ingest-wiring) — обязательно перед Wave T UI (новые dedup-вкладки), Wave Y3 (агент v2 в shell), Wave S+ (hypothesis modal).
4. **i18n ремонт:** [H-i18n-fixes](../backlog/refactor-frontend.md#open-i18n-hardcoded-copy-hypothesispanel-ingestionsettings-workspace-dialogs) — независимо, можно делать «фоном».

## 5. Спринты (рекомендованный темп)

> Размер спринта — субъективно ~1-2 недели; конкретный календарь подстраивается под доступность агентов и людей.

### Sprint S1 — «расчищаем воркер»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track G: **G-IngestSlim** | `science_graphrag/api/ingest_jobs.py` → `api/ingest/{router,registry,dispatcher,dto}.py`, `tests/test_ingest_jobs*` |
| P2 | Track G: **G-PipelineFacade** | `science_graphrag/ingestion/pipeline.py`, `science_graphrag/ingestion/stages/`, `tests/test_pipeline_*` |
| P3 | Track B: **Wave Y1** (foundation) | `pyproject.toml`, `science_graphrag/observability/phoenix_tracer.py` (минимально), `science_graphrag/config.py`, `Dockerfile`, `.env.example`, `.github/workflows/`, `docs/runbooks/roadmap-next-waves.md` |
| P4 | Track G: **G-PhoenixSplit** | `science_graphrag/observability/` (новый пакет), `tests/observability/test_span_contract.py` |
| P5 | Track H: **H-i18n-fixes** | `ui/src/components/work/HypothesisPanel.jsx`, `ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx`, `ui/src/pages/WorkspacePage/WorkspacePage.jsx` (только литералы), `ui/src/i18n/` |
| P6 | Track H: **H-Cursor*-buttons in dedup** | `ui/src/pages/WorkspacePage/WorkspaceDedupSection.jsx`, `ui/src/components/graph/WorkDedupReviewDialog.jsx` |

**Параллельно безопасно:** P1+P3+P4+P5+P6 по разным файлам. P2 трогает `science_graphrag/ingestion/pipeline.py` — **не пересекается** с P1, можно вместе. P3 трогает `phoenix_tracer.py` — **может конфликтовать** с P4. Решение: P4 делает split первым (1-2 часа), P3 потом добавляет LangChain instrumentation в новый `instrumentation.py`.

### Sprint S2 — «воркер живёт, агент в LangGraph»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track A: **Wave W backend** (продукт) | `docker-compose*.yml`, `science_graphrag/worker/`, `science_graphrag/api/ingest/dispatcher.py`, `science_graphrag/api/ingest_event_bus.py` v2, ADR + spec |
| P2 | Track G: **G-StoreFactory** | `science_graphrag/api/deps.py`, частичные правки `api/{agent,idea_assist,retrieval,works,workspaces,workspace_graph,workspace_dedup,ingest_jobs}.py` |
| P3 | Track B: **Wave Y2** (single-agent LG) | `science_graphrag/agent/`, `pyproject.toml` (агент уже в Y1), `tests/agent/`, `science_graphrag/api/agent.py` (без смены контракта) |
| P4 | Track C: **Wave X2** (Phoenix retrieval agent) | `science_graphrag/agent/runtime.py`, `science_graphrag/agent/tools/*`, `tests/observability/` |
| P5 | Track G: **G-WorkspaceGraphSplit** | `science_graphrag/api/workspace_graph.py` → `api/workspace_graph/`, `tests/test_workspace_graph_*` |
| P6 | Track G: **G-WorksSplit** | `science_graphrag/api/works.py` → `api/works/`, `tests/test_works*` |

**Конфликты:**
- P3 + P4 трогают одни файлы (`agent/runtime.py`, `tools/`). Делать в одном PR последовательно (Y2 → X2) либо чётко в разных подмодулях.
- P2 + P5 + P6 + P1 трогают `api/ingest_jobs.py`, `api/agent.py`, `api/workspace_graph.py`, `api/works.py`. Конфликта нет, если P2 «первый прошёл» — добавил `deps.py` и подменил композицию точечно.

### Sprint S3 — «agent v2 + graph UX волна 1»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track B: **Wave Y3** (`/v2/agent/query` SSE) | `science_graphrag/api/agent_v2.py` (новый), `science_graphrag/api/main.py` (роутер include), `docs/specs/agent-tools-v2.md` (создать), тесты v2 smoke |
| P2 | Track H: **H-AskPanelSplit** | `ui/src/components/work/AskPanel.jsx`, `ui/src/components/work/{AskAnswerPanel,AskSessionControls,useAskSubmit}.jsx`, тесты |
| P3 | Track H: **H-AskV2SSE** (после P1+P2) | `ui/src/hooks/useAgentStream.js`, `ui/src/services/research/agent.js`, интеграция в `useAskSubmit` |
| P4 | Track E: **Wave GR2** (display_type/node_kind/prioritized LIMIT) | `science_graphrag/api/works/graph_neighborhood.py`, `science_graphrag/api/workspace_graph/projection.py`, `ui/src/components/graph/GraphTypeLegend.jsx`, обновление `docs/adr/011-graph-live-ux-and-payload.md` |
| P5 | Track G: **G-Neo4jStoreSplit** (большой) | `science_graphrag/storage/neo4j_store.py` → `science_graphrag/storage/neo4j/`, осторожный набор юнит-тестов перед |
| P6 | Track H: **H-GraphWorkspacePanelSplit** | `ui/src/components/graph/GraphWorkspacePanel.jsx` → `useGraphWorkspaceData`, `GraphViewModeSwitch`, `GraphDebugInspector`, `GraphSidePanel` |

**Конфликты:**
- P1 (backend) и P2 (frontend) — независимы; P3 ждёт оба.
- P4 трогает граф-API; P5 трогает `storage/neo4j_store.py`. Не пересекаются по файлам, но GR2 импортирует `Neo4jGraphStore`. Если P5 закончен раньше, GR2 сразу пользуется новой структурой.
- P6 — frontend, не пересекается с backend.

### Sprint S4 — «graph UX волна 2 + multi-agent готовность»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track E: **Wave GR3** (aggregator + lazy expand) | `api/works/graph_neighborhood.py`, `api/workspace_graph/projection.py`, новый `expand` endpoint; UI — `GraphCanvasMvp` + `GraphSidePanel` |
| P2 | Track H: **H-GraphCanvasMvpSplit** (уже в backlog) | `ui/src/components/graph/GraphCanvasMvp.jsx` → `useGraphCanvasInput`, `graphCanvasDraw.js` |
| P3 | Track B: **Wave Y4** (multi-agent supervisor) | `science_graphrag/agent/graph/{nodes/{retrieval_agent,graph_agent,writer},supervisor.py}`, `eval/agent_tools/metrics.py`, новый ADR `019-langgraph-supervisor-multiagent.md` (см. §4.2 п.8 про номер) |
| P4 | Track D: **Wave R follow-ups** (multi-agent benchmarks) | `tests/fixtures/benchmarks/agent_tools_multiagent/`, `eval/agent_tools/*` |
| P5 | Track G: **G-StageExtractionSplit** | `science_graphrag/ingestion/llm/` → подпакет с `prompts/`, `executor.py`, `orchestrator.py`, `heuristics/` |
| P6 | Track G: **G-RetrievalCore** | `science_graphrag/retrieval/` (новый пакет), `science_graphrag/api/retrieval.py` (тонкий router), `science_graphrag/api/main.py` (cleanup `answer_query`) |

**Конфликты:** P3+P4 идут парой; P5 не трогает agent-пакеты; P6 не трогает ingestion. Высокая параллельность.

### Sprint S5 — «entity dedup + benchmark UI»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track D: **Wave T** (entity dedup) | `science_graphrag/dedup/<type>_pipeline.py`, `storage/neo4j/writes/{authors,institutions,...}.py` (после G-Neo4jStoreSplit), `api/workspace_dedup/` (после split), Postgres миграция, ADR `018-entity-dedup-pipeline.md` |
| P2 | Track G: **G-WorkspaceDedupSplit** | `science_graphrag/api/workspace_dedup.py` → `api/workspace_dedup/{router,engine_glue,dto}.py` |
| P3 | Track G: **G-BenchmarkSplit** + **G-TaskStoreSplit** | `science_graphrag/api/benchmark.py` → `api/benchmark/`, `science_graphrag/api/task_store.py` → executor/persistence/dto |
| P4 | Track H: **H-BenchmarkCaseDetailSplit** + **H-CompareTab/RunTab Split** | `ui/src/pages/BenchmarkPage/CaseDetailDialog.jsx`, `CompareTab.jsx`, `RunTab.jsx` |
| P5 | Track H: **H-WorkspacePageSlim** | `ui/src/pages/WorkspacePage/WorkspacePage.jsx`, новый `useWorkspacePapersModel`, `WorkspaceDialogs` |
| P6 | Track B: **Wave Y5** (research spike → LangGraph) | `scripts/experiment_references_*.py`, `science_graphrag/agent/graph/research/`, `eval/references_harness/`, `tests/test_agent_suite_metrics.py` |

### Sprint S6 — «cleanup + GR4/GR5»

| Параллельный поток | Задача | Файловый скоуп |
|---|---|---|
| P1 | Track E: **Wave GR4** (`view=raw|reader`) | `api/works/graph_neighborhood.py`, `api/workspace_graph/projection.py`, `ui/src/components/graph/WorkspaceGraphToolbar.jsx`, ADR opt |
| P2 | Track E: **Wave GR5** (denormalized counters + weighted layout) | `storage/neo4j/writes/works.py`, ingest backfill, `ui/src/components/graph/graphCanvasStyle.js`, миграция backfill-скрипта |
| P3 | Track B: **Wave Y6** (cleanup) | `pyproject.toml` (выпил smolagents), `science_graphrag/api/main.py`, `science_graphrag/agent/runtime_legacy.py` (удаление), доки |
| P4 | Track G: **G-CLISplit** + **G-SettingsSplit** + **G-PhoenixSplit-cleanup** | `cli/main.py`, `settings/service.py`, `observability/` follow-ups |
| P5 | Track H: **H-ServicesSplit** + **H-MoveForceSimulation** + **H-ReaderWorkBodySplit** | `ui/src/services/research*`, `ui/src/hooks/graph/`, `ui/src/components/work/ReaderWorkBody.jsx` |
| P6 | Track G: **Targeted backend test coverage** | `tests/test_ingest_jobs*`, `tests/test_retrieval*`, `tests/storage/test_neo4j_*`, `tests/agent/` (юнит-тесты к новым модулям) |

## 6. Матрица параллельности (что можно запускать одновременно агентами)

> Таблица «✅» — параллелится без конфликтов по файлам. «⚠️» — возможен мердж-конфликт, согласовать порядок. «⛔» — нельзя в один присест.

|                                  | A:Wave W | B:Y1 | B:Y2 | B:Y3 | B:Y4 | C:X2 | D:T | D:Q-fup | E:GR2 | E:GR3 | E:GR4 | E:GR5 | G:IngestSlim | G:PipelineFacade | G:Neo4jSplit | G:WorkspaceGraphSplit | G:WorksSplit | G:RetrievalCore | G:StageExtractionSplit | G:PhoenixSplit | G:StoreFactory | H:AskPanel | H:AskV2SSE | H:GraphWorkspacePanel | H:GraphCanvas |
|----------------------------------|---------|------|------|------|------|------|-----|---------|-------|-------|-------|-------|--------------|------------------|--------------|-----------------------|--------------|-----------------|------------------------|----------------|----------------|------------|------------|-----------------------|---------------|
| **A: Wave W**                   | —       | ✅   | ✅   | ✅   | ✅   | ⚠️ ¹| ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ⛔ ²         | ⚠️ ³             | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ⚠️ ⁴           | ✅         | ✅         | ✅                    | ✅            |
| **B: Y1 foundation**            | ✅      | —    | ⛔ ⁵ | ✅   | ✅   | ✅   | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ⚠️ ⁶           | ✅             | ✅         | ✅         | ✅                    | ✅            |
| **B: Y2 single-agent LG**       | ✅      | ⛔   | —    | ⛔ ⁷ | ⛔   | ⛔ ⁸ | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ⚠️ ⁹           | ✅         | ✅         | ✅                    | ✅            |
| **B: Y3 v2 SSE**                | ✅      | ✅   | ⛔   | —    | ⛔   | ✅   | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ⚠️             | ⚠️ ¹⁰      | ⛔ ¹¹      | ✅                    | ✅            |
| **B: Y4 multi-agent**           | ✅      | ✅   | ⛔   | ⛔   | —    | ✅   | ✅  | ⚠️ ¹²   | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ✅             | ✅         | ✅         | ✅                    | ✅            |
| **C: X2 Phoenix agent**         | ⚠️      | ✅   | ⛔   | ✅   | ✅   | —    | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ⚠️             | ✅             | ✅         | ✅         | ✅                    | ✅            |
| **D: Wave T**                   | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | —   | ✅      | ✅    | ✅    | ✅    | ⚠️ ¹³ | ✅           | ✅               | ⛔ ¹⁴        | ✅                    | ✅           | ✅              | ✅                     | ✅             | ✅             | ✅         | ✅         | ✅                    | ✅            |
| **E: GR2**                      | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | —     | ⛔ ¹⁵ | ⛔    | ⛔    | ✅           | ✅               | ✅           | ⛔ ¹⁶                 | ⛔ ¹⁷        | ✅              | ✅                     | ✅             | ✅             | ✅         | ✅         | ⚠️ ¹⁸                 | ⚠️             |
| **E: GR3**                      | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | ⛔    | —     | ⛔    | ⛔    | ✅           | ✅               | ✅           | ⛔                    | ⛔           | ✅              | ✅                     | ✅             | ✅             | ✅         | ✅         | ⚠️                    | ⛔ ¹⁹          |
| **G: IngestSlim**               | ⛔      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | —            | ⚠️ ²⁰            | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ⚠️             | ✅         | ✅         | ✅                    | ✅            |
| **G: Neo4jSplit**               | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ⛔  | ✅      | ✅    | ✅    | ✅    | ⚠️ ²¹ | ✅           | ⚠️ ²²            | —            | ⚠️ ²³                 | ⚠️ ²³        | ✅              | ✅                     | ✅             | ⚠️             | ✅         | ✅         | ✅                    | ✅            |
| **G: WorkspaceGraphSplit**      | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | ⛔    | ⛔    | ⛔    | ⚠️    | ✅           | ✅               | ⚠️           | —                     | ⚠️ ²⁴        | ✅              | ✅                     | ✅             | ⚠️             | ✅         | ✅         | ✅                    | ✅            |
| **H: AskPanel split**           | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | ✅    | ✅    | ✅    | ✅    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ✅             | —          | ⛔ ²⁵       | ✅                    | ✅            |
| **H: GraphCanvas split**        | ✅      | ✅   | ✅   | ✅   | ✅   | ✅   | ✅  | ✅      | ⚠️    | ⛔    | ⚠️    | ⚠️    | ✅           | ✅               | ✅           | ✅                    | ✅           | ✅              | ✅                     | ✅             | ✅             | ✅         | ✅         | ⚠️ ²⁶                 | —             |

**Сноски:**
1. ¹ Wave W в Dramatiq нуждается в propagate OTel-контекста. Согласовать с владельцем X-серии (либо включить в Wave W чеклист).
2. ² Wave W меняет диспатчер; G-IngestSlim вводит модуль `dispatcher.py`. Делать строго G-IngestSlim → Wave W.
3. ³ Wave W трогает `pipeline.py` через actor; G-PipelineFacade одновременно перепиливает структуру. Лучше PipelineFacade → Wave W.
4. ⁴ G-StoreFactory меняет `api/ingest_jobs.py` (через `deps`), а Wave W удаляет thread из этого же файла. Если оба идут в одной фазе — последовательно.
5. ⁵ Y2 строится на Y1.
6. ⁶ Y1 кладёт LangChain instrumentation в `phoenix_tracer.py`. G-PhoenixSplit перетасовывает этот файл. Делать G-PhoenixSplit → Y1 instrumentation.
7. ⁷ Y3 опирается на Y2 (готовый граф).
8. ⁸ X2 дополняет тот же `agent/runtime.py`, что и Y2. Включать X2 в Y2-PR или сразу следующий PR.
9. ⁹ Y2 точечно меняет `agent/runtime.py` и tools; G-StoreFactory меняет конструкторы. Ок параллельно по разным точкам, но желательна синхронизация (Store-фактори первой, Y2 затем).
10. ¹⁰ Y3 не трогает frontend, но AskPanel split нужен до AskV2SSE.
11. ¹¹ AskV2SSE требует, чтобы Y3 уже выкатил `/v2/agent/query`.
12. ¹² Wave R follow-ups (multi-agent benchmarks) ждут Y4 фактической реализации.
13. ¹³ GR5 расширяет поля `:Work` (counters); Wave T расширяет `:Author`/`:Institution`. По разным сущностям, но обе трогают ingest. Если оба сразу — координировать миграции.
14. ¹⁴ Wave T добавляет writes по новым типам — лучше после G-Neo4jSplit.
15. ¹⁵ GR2/GR3/GR4/GR5 идут последовательно (общий `api/workspace_graph/projection.py`).
16. ¹⁶ G-WorkspaceGraphSplit меняет структуру `api/workspace_graph.py`; делать ДО GR2.
17. ¹⁷ Аналогично для `api/works.py`.
18. ¹⁸ GR2 добавляет легенду; H-GraphWorkspacePanelSplit перетасовывает компонент. Лучше сначала split.
19. ¹⁹ GR3 кликабельный агрегатор требует уже разнесённого `GraphCanvasMvp` (input vs draw).
20. ²⁰ Оба трогают `pipeline.py`/`api/ingest_jobs.py` соседние файлы — синхронизировать.
21. ²¹ GR5 пишет в Neo4j новые поля; легче после Neo4jSplit.
22. ²² Конфликт по `storage/neo4j_store.py` (PipelineFacade использует `Neo4jGraphStore`).
23. ²³ Если разнесли `Neo4jGraphStore` — `WorkspaceGraphSplit` и `WorksSplit` импортируют из новых модулей. Согласовать порядок (Neo4jSplit раньше).
24. ²⁴ Оба трогают `graph_display.py`/общие helpers.
25. ²⁵ AskV2SSE интегрируется в `useAskSubmit` — нужен после AskPanel split.
26. ²⁶ Оба трогают `GraphCanvasMvp.jsx` — нельзя одновременно.

## 7. Запуск Cursor-агентов параллельно

> Каждый «слот» — отдельный фоновый агент в Cursor. Используем ограничения матрицы §6.

**Безопасный шаблон одного раунда (по 4 агента):**

- **Раунд 1 (Sprint S1 ядро) ✅ DONE 2026-04-25:**
  - Agent 1: G-IngestSlim (`api/ingest_jobs.py` → `api/ingest/`). ✅
  - Agent 2: G-PipelineFacade (`ingestion/pipeline.py` → stages + context). ✅
  - Agent 3: G-PhoenixSplit (`observability/`). ✅
  - Agent 4: H-i18n-fixes + H-Cursor-buttons-in-dedup (frontend, разные файлы). ✅
- **Раунд 1.5 (закрываем долги Sprint S1 перед запуском Раунда 2) ✅ DONE 2026-04-25:**

  > Раунд добавлен по итогам Sprint S1 review (2026-04-25): три задачи Sprint S1 не прошли acceptance-критерии и блокируют Раунд 2. Выполняется строго до Раунда 2.

  - Agent 1: **Завершить G-PipelineFacade** ✅ — тяжёлая логика в `_pipeline_impl.py`; `pipeline.py` = 53 строки фасад-реэкспорт (≤250 ✅). 375 тестов зелёные.
  - Agent 2: **Split `observability/spans.py` (410 строк)** ✅ — разнесено на `observability/spans/{attributes.py,decorators.py,__init__.py}`; все файлы ≤300 строк ✅; `test_span_contract.py` зелёный.
  - Agent 3: **Фикс регрессии IngestJobRegistry** ✅ — `__init__` не вызывает `init_db`/`mark_stale`; добавлен ленивый `bootstrap()`; monkeypatch-тесты перенесены на `router._registry`; все `test_api_smoke` зелёные.

  > Agent 4: нет — три задачи не пересекаются по файлам, безопасно параллельны. Wave Y1 (P3 Sprint S1) выполнен полностью: deps установлены, `instrumentation.py` наполнен, `config.py` и `.env.example` обновлены. ✅

- **Раунд 2 (после раунда 1.5 + Y1 foundation) ✅ DONE 2026-04-25:**
  - Agent 1: G-StoreFactory — `api/deps.py` с `StoreRegistry` + `get_stores()`; lifespan в `main.py`. ✅
  - Agent 2: G-WorkspaceGraphSplit — `api/workspace_graph.py` (1214 строк) → пакет `api/workspace_graph/{cypher,projection,router,__init__}.py` + helpers. ✅
  - Agent 3: G-WorksSplit — `api/works.py` (817 строк) → пакет `api/works/{dto,detail,graph_neighborhood,chunks,router,__init__}.py`. ✅
  - Agent 4: H-GraphWorkspacePanelSplit — `GraphWorkspacePanel.jsx` (1164 строк) → shell + `useGraphWorkspaceData`, `GraphViewModeSwitch`, `GraphSidePanel`, `GraphDebugInspector`. ✅

  > **Review 2026-04-25 (9 тестов исправлено):**
  >
  > Три класса дефектов обнаружены и устранены в ходе review:
  >
  > 1. **`works/__init__.py` naming-конфликт:** пакет re-экспортирует `router` (APIRouter instance), что затеняет submodule-ссылку `works.router`. Тесты использовали `api_main.works_api.*` — атрибут исчез после сплита. **Фикс:** `works_api = sys.modules["science_graphrag.api.works.router"]` shim в `main.py`. Технический долг: очистить при G-RetrievalCore (см. ниже).
  >
  > 2. **DI-ordering в `agent.py`:** `Depends(get_stores)` резолвится до тела endpoint, поэтому `agent_enabled` guard не защищал от `RuntimeError` при незаполненном `app.state.stores` в тестах. **Фикс:** оба теста теперь переопределяют `get_stores`.
  >
  > 3. **Сигнатура `work_sources_payload`:** в сплите добавился параметр `stores`, тест-fake имел старую сигнатуру. **Фикс:** обновлен fake.
  >
  > Качество: pylint 8.78/10, isort/black чисто, frontend ESLint чисто, **383 passed, 2 skipped**.
- **Раунд 3 (Wave W + Y2 + X2 + Neo4jSplit + AskPanelSplit) ✅ DONE 2026-04-25 — промпты: [`round3-agent-prompts-2026-04-25.md`](round3-agent-prompts-2026-04-25.md):**
  - Agent 1: Wave W backend (Dramatiq actor + Redis). ✅
  - Agent 2: Wave Y2 + Wave X2 (один комбинированный PR в `agent/`). ✅
  - Agent 3: G-Neo4jSplit (`neo4j_store.py` 1022 строки → 11 модулей пакета). ✅
  - Agent 4: H-AskPanelSplit (`AskPanel.jsx` → shell + `useAskSubmit`, `AskSessionControls`, `AskAnswerPanel`). ✅

  > **Review 2026-04-25:** 390 passed, 2 skipped; pylint 8.92/10; isort/black/ESLint чисто. Единственное отклонение от спецификации: `IngestEventBus` живёт в `api/ingest_event_bus.py`, а не в `api/ingest/dispatcher.py` — функционально не влияет, Round 4 не блокирует. Метрика: 23 новых модуля, neo4j_store 1022→11 файлов, AskPanel 670→4 файла 487 строк суммарно.
- **Раунд 4 (Wave Y3 + GR2 + G-RetrievalCore + H-AskV2SSE) ✅ DONE 2026-04-25 — промпты: [`round4-agent-prompts-2026-04-25.md`](round4-agent-prompts-2026-04-25.md):**
  - Agent 1: Wave Y3 backend — `api/agent_v2.py`, `/v2/agent/query` (SSE+sync), `docs/specs/agent-tools-v2.md`, deprecation header v1. ✅
  - Agent 2: Wave GR2 backend — `node_kind`, semantic `display_type`, prioritized LIMIT + `meta.skipped_by_kind`; ADR 011 updated. ✅
  - Agent 3: G-RetrievalCore — `science_graphrag/retrieval/` пакет; `api/retrieval.py` тонкий router (54 строки); `main.py` shim удалён; `works/__init__` naming fixed. ✅
  - Agent 4: H-AskV2SSE — `useAgentStream.js`; `useAskSubmit.js` SSE path; `AskAnswerPanel` stream events. ✅

  > **Review 2026-04-25:** 406 passed, 2 skipped, 0 failures; pylint 9.34–9.50/10; isort/black/ESLint чисто. Исправлен дефект GR2: `skipped_by_kind` вычислялся только из cap-overflow, но не учитывал узлы, которые не были запрошены из-за priority-ограничений — добавлен запрос kind-distribution и пересчёт `skipped_by_kind = available − fetched`. Все структурные и smoke-проверки ✓.
- **Раунд 5 (Wave T + GR3 + GR4 + Y4):**
  - Agent 1: Wave T backend (entity dedup) — требует G-Neo4jSplit.
  - Agent 2: Wave GR3 backend + frontend (последовательно внутри агента).
  - Agent 3: Wave Y4 backend (multi-agent supervisor).
  - Agent 4: G-StageExtractionSplit (в параллель безопасно).

> При каждом раунде проверять матрицу §6: если задача в строке/колонке имеет ⛔/⚠️ с другой задачей этого же раунда — переносить в следующий раунд.

## 8. Контроль и acceptance трека

После каждого спринта проверять:

- **Quality gates:** `pytest`, `pylint`, `black`, `isort`, `npm run lint`, `npm run test` зелёные на затронутых каталогах ([`pre-commit-checklist.mdc`](../../.cursor/rules/pre-commit-checklist.mdc)).
- **Contract docs:** обновлены `docs/specs/frontend-ui-api-contracts-v1.md`, `docs/architecture/observability-phoenix.md`, `docs/specs/agent-tools-{v1,v2}.md`.
- **Backlog hygiene:** все закрытые рефакторы помечены `[DONE]` с датой и одной строкой про реальный диапазон линий после распила; новые отложенные пункты добавлены тут же.
- **ADR sync:** новые продуктовые волны = новые ADR (нумерация без коллизий — см. §4.2 п.8 про 017/019).
- **Phoenix smoke:** при каждом релизе проверять, что в Phoenix UI стоимость сходится (кастомные модели), нет «голых» CHAIN с LLM-атрибутами, agent-trace виден.
- **Benchmarks:** `decision-gate` пройден для затронутых семейств; advisory не «протекают» в core без 7+ ночей.

## 9. Открытые вопросы / риски (сводно)

1. **ADR номер для multi-agent supervisor (Wave Y4):** конфликт с уже занятым 017. Решение зафиксировать до старта Y4.
2. **OTel propagation в Dramatiq:** не входит в чеклист Wave W; добавить как обязательное условие.
3. **`PHOENIX_TRACE_SCOPE`:** при переименованиях ingest stages (после G-PipelineFacade) обязательно синхронизировать `_EXTRACTION_LLM_CHAIN_NAMES`. Нужен тест регрессии.
4. **Default `view` в graph (GR4):** opt-in `reader` в UI vs default `reader` на сервере. Зафиксировать ADR 016 или дополнение к 011 до Wave GR4.
5. **`aggregator_threshold` (GR3):** числовое значение — обсудить до start.
6. **Multi-host API:** не цель Phase 1; держать в фокусе при дизайне `IngestEventBus` v2 (Redis pub/sub) — multi-host станет реальной возможностью.
7. **Settings-секции для новых волн:** Wave T (entity dedup) расширяет snapshot; Wave Y2/Y3 добавляет `agent_runtime`, `agent_max_tool_calls`, `agent_supervisor_recursion_limit`. Делать через G-SettingsSplit.

## 10. Ссылки

### Активные роадмапы

- [`docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md`](ingestion-async-pipeline-roadmap-2026-04-25.md)
- [`docs/analysis/langgraph-migration-plan-2026-04-25.md`](langgraph-migration-plan-2026-04-25.md)
- [`docs/analysis/phoenix-tracing-coverage-2026-04-25.md`](phoenix-tracing-coverage-2026-04-25.md)
- [`docs/analysis/ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md)
- [`docs/analysis/graph-ux-aggregation-roadmap-2026-04-25.md`](graph-ux-aggregation-roadmap-2026-04-25.md)
- [`docs/analysis/workspace-experience-gap-2026-04-24.md`](workspace-experience-gap-2026-04-24.md)
- [`docs/analysis/reference-extraction-llm-agent-tools.md`](reference-extraction-llm-agent-tools.md) (исторический контекст)

### Бэклог рефакторинга

- [`docs/backlog/refactor-backend.md`](../backlog/refactor-backend.md)
- [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md)

### Архитектурный канон

- [`docs/adr/README.md`](../adr/README.md) — индекс ADR
- [`docs/architecture/phase-1-backbone.md`](../architecture/phase-1-backbone.md)
- [`docs/architecture/observability-phoenix.md`](../architecture/observability-phoenix.md)
- [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md)
- [`docs/specs/route-map.md`](../specs/route-map.md), [`docs/specs/shell-layout.md`](../specs/shell-layout.md)
- [`docs/specs/agent-tools-v1.md`](../specs/agent-tools-v1.md), [`docs/specs/idea-assist-v1.md`](../specs/idea-assist-v1.md)
- [`docs/specs/ontology-claims-v1.md`](../specs/ontology-claims-v1.md), [`docs/specs/ontology-v1-mvp.md`](../specs/ontology-v1-mvp.md)

### Правила

- [`.cursor/rules/refactor-rhythm-and-backlog.mdc`](../../.cursor/rules/refactor-rhythm-and-backlog.mdc)
- [`.cursor/rules/pre-commit-checklist.mdc`](../../.cursor/rules/pre-commit-checklist.mdc)
- [`.cursor/rules/architecture.mdc`](../../.cursor/rules/architecture.mdc)
