# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Queue

### [DONE] Graph readability — Wave GR1 display labels (Authorship/Author/Institution/Venue)
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Graph projections leaked technical UUID-like node ids (notably `:Authorship` ids like `...:ash:1`) into `display_label`/`subtitle`, reducing readability.
- **Proposal:** Introduce shared display helper and enrich Authorship labels from `OF_AUTHOR`/`AFFILIATED_WITH`; apply in all graph endpoints.
- **Acceptance:** no UUID-like labels in graph node titles/subtitles for core node types; integration + unit tests cover Authorship rendering.
- **Raised:** 2026-04-25
- **Note (done):** 2026-04-25 — implemented in GR1 pass with tests for `/v1/works/{id}/graph`, `/v1/workspaces/{id}/graph`, and `/v1/workspaces/{id}/graph/neighbors`.

### [OPEN] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** `node_kind` is still equal to Neo4j `type`; edge labels remain technical (`HAS_AUTHORSHIP`, etc.); `LIMIT` truncation is not priority-aware.
- **Proposal:** Add `node_kind` projection semantics, relation `display_type` mapping, and limit prioritization with `meta.skipped_by_kind`.
- **Acceptance:** priority kinds (`Method`,`Dataset`,`Work`) survive truncation reliably and UI legend can render semantic edge labels.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR3 aggregator nodes + lazy expand endpoint
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`
- **Issue:** Dense one-kind neighbor stars (authors/cites/institutions) overload graph readability at default limits.
- **Proposal:** Add `node_kind: Aggregator` projection with `aggregation_hints` and expand endpoint for lazy unfolding.
- **Acceptance:** oversized neighbor groups collapse into one aggregator node with count/preview and expand on demand.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR4 reader view with virtual AUTHORED edges
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/workspace_graph.py`, `science_graphrag/api/graph_snapshot_diff.py`
- **Issue:** Raw `Authorship` reification is useful for ontology/debug but too verbose for default reader UX.
- **Proposal:** Add `view=raw|reader`; in reader view project virtual `AUTHORED` edges with `via` trace fields, keep raw mode for snapshots/tests.
- **Acceptance:** reader view hides `Authorship` nodes by default while preserving traceability and raw compatibility.
- **Raised:** 2026-04-25

### [OPEN] Graph readability — Wave GR5 denormalized Work counters for weighted layout
- **Area:** `science_graphrag/storage/neo4j_store.py`, ingestion pipelines, graph API payload properties
- **Issue:** Work importance signals (`cites_in/out`, `authors_count`) are recomputed ad hoc and not consistently available for graph styling.
- **Proposal:** Persist denormalized counters on `:Work` and expose them in graph payload properties.
- **Acceptance:** graph payload includes stable counter properties enabling weighted radius/ranking without extra query passes.
- **Raised:** 2026-04-25

### [PARTIAL] Ingest pipeline async-redesign (Wave U–W)

- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/ingestion/pipeline.py`, `ui/src/hooks/usePollJob.js`, `docker/nginx-web.conf`, `docker-compose.yml`
- **Issue:** ingest исполняется `threading.Thread` внутри API → рестарт убивает работу; UI поллит `GET /v1/ingest/jobs/{id}` каждые 2 с → access-лог зашумлён; пайплайн не размечен на стадии → видимость нулевая (`message: "Running pipeline (Neo4j / vectors / SQL)…"` минутами).
- **Proposal:** план в [docs/analysis/ingestion-async-pipeline-roadmap-2026-04-25.md](../analysis/ingestion-async-pipeline-roadmap-2026-04-25.md):
  - **Wave U** — фильтр polling из uvicorn access-лога; ORM `IngestJobStageOrm` + enum `IngestStage`; контекст-менеджер `stage(...)` с OTel-спанами; UI `IngestStageStepper`.
  - **Wave V** — `sse-starlette` + `GET /v1/ingest/jobs/{id}/events` с `Last-Event-ID`; nginx SSE-friendly `location`; UI `useJobStream` с graceful fallback на polling.
  - **Wave W** — ADR + `redis` и `worker` в compose; `dramatiq` actor `ingest_document_actor`; API только enqueue; `IngestEventBus` v2 поверх Redis pub/sub; идемпотентность + compensation sweep; `mark_stale_running_jobs_failed` удаляется.
- **Acceptance:** см. чеклисты Wave U/V/W в роадмапе. Закрывается тремя независимыми проходами; до Wave W можно держать `[PARTIAL]` после прохождения U или V.
- **Raised:** 2026-04-25
- **Note (Wave U done):** 2026-04-25 — stage timeline, OTel stage spans, `IngestStageStepper`, и filtering polling access-log доставлены; Wave V/W остаются открытыми.

### [OPEN] Split idea-assist workflow orchestration (Wave S follow-up)
- **Area:** `science_graphrag/agent/idea_workflow.py`
- **Issue:** `idea_workflow.py` reached ~270 lines and now mixes retrieval orchestration, claim querying, LLM prompting, and output normalization in one module.
- **Proposal:** Extract (1) claim/context collector, (2) LLM schema+prompt builder, and (3) result normalizer into separate modules under `science_graphrag/agent/idea_assist/`.
- **Acceptance:** orchestrator file <= 180 lines, prompt/schema logic isolated, and unit tests target each submodule independently.
- **Raised:** 2026-04-25

### [OPEN] Split `api/workspace_graph.py` (1214 lines) — projection vs Cypher vs HTTP
- **Area:** `science_graphrag/api/workspace_graph.py`, `science_graphrag/api/graph_display.py`, `science_graphrag/storage/neo4j_store.py`
- **Issue:** Файл вырос до ≈1214 строк и совмещает: (1) собственный `GraphDatabase.driver` (раз дополнительный путь к Bolt мимо `Neo4jGraphStore`), (2) Cypher для neighbors/stats/projection, (3) merge member vs external и аннотации membership/cites, (4) FastAPI router + DTO. Сильный hub: импорты сходятся со всех граф-эндпоинтов.
- **Proposal:** разнести на пакет `api/workspace_graph/`: `cypher.py` (запросы/проекция), `projection.py` (склейка member/external, membership annotations), `router.py` (тонкие хендлеры FastAPI). Доступ к Bolt — только через `Neo4jGraphStore` (или общий driver-фабрику в `storage/`).
- **Acceptance:** ни один файл в `api/workspace_graph/` не превышает ≈400 строк; нет прямого `GraphDatabase.driver(...)` за пределами `storage/`; тесты `test_workspace_graph_*.py` зелёные без правок поведения.
- **Synergy:** разблокирует **Wave GR2/GR3/GR4** (агрегаторы, `view=reader`, prioritized LIMIT) — каждой волне нужно отдельно править маленькие модули вместо god-файла.
- **Raised:** 2026-04-25

### [OPEN] Split `storage/neo4j_store.py` (1022 lines) by domain or layer
- **Area:** `science_graphrag/storage/neo4j_store.py`
- **Issue:** `Neo4jGraphStore` совмещает schema/init, write-операции (works/authorships/semantic/claims/workspace), reads, merge и wipe; сильная связность всех ingest-стадий и API-роутеров.
- **Proposal:** разнести на пакет `storage/neo4j/`: `client.py` (driver + sessions), `schema.py` (constraints/indexes), `writes/{works,authorships,semantic,claims,workspace}.py`, `reads.py`. Сохранить публичный класс `Neo4jGraphStore` как фасад с прежним API.
- **Acceptance:** ни один модуль > ≈400 строк; интеграционные тесты `tests/integration/test_full_ingest_integration.py` и юнит-тесты Neo4j зелёные; импорты из `api/*` и `ingestion/*` не меняются.
- **Synergy:** **Wave GR5** (denormalized counters), **Wave Q** (Neo4j vector index, fulltext indexes, миграции) — независимые модули проще тестировать; **Wave T** (entity dedup) добавляет writes/{authors,institutions,...} без расширения god-файла.
- **Raised:** 2026-04-25

### [OPEN] Refactor `ingestion/pipeline.py` (976 lines) into stages-with-context facade
- **Area:** `science_graphrag/ingestion/pipeline.py`, `science_graphrag/ingestion/stages/`, `science_graphrag/ingestion/stage_context.py`
- **Issue:** Один файл оркеструет OpenAlex, normalization, chunking, embeddings, claims, semantic, references, Neo4j upsert, Qdrant upsert, workspace attach, Phoenix spans и CLI entrypoints. Каждый ingest-route (CLI, batch, API job, Wave W actor) копирует инициализацию stores. Затрудняет per-stage error handling и blast radius.
- **Proposal:** ввести `IngestRunContext` (создаёт и переиспользует `Neo4jGraphStore`, `QdrantChunkStore`, `BlobStore`, `PhoenixTracer`); переписать `run_ingest_*` как тонкий фасад, последовательно вызывающий модули `stages/{vl_pdf,metadata,chunking,embeddings,semantic,claims,references,authorships,neo4j_upsert,qdrant_upsert,workspace_attach}.py`; каждый stage — изолированная функция с входным/выходным DTO и обёрткой `with stage(...)`. CLI остаётся одним entrypoint, но без копипасты сторов.
- **Acceptance:** `pipeline.py` <= 250 строк; есть отдельный модуль на каждую stage, покрытый юнит-тестом с моками `stores`; интеграционный тест end-to-end зелёный; маршрут A (CLI) и маршрут B (`api/ingest_jobs._execute_single_ingest`) повторно используют один и тот же контекст.
- **Synergy:** **Wave U** уже добавил `stage_context` — продолжение в эту сторону; **Wave W** (Dramatiq actor) сразу получает один и тот же `IngestRunContext` без копипасты. **Wave X1** (Phoenix) — уже отметил «слипшийся `neo4j_graph_persistence`», эта работа закрывает структурную часть. **Wave Q** (hybrid retrieval) добавит Neo4j-индексацию work post-upsert одной новой стадией без god-файла.
- **Raised:** 2026-04-25

### [OPEN] Slim `api/ingest_jobs.py` (846 lines) — registry/worker vs HTTP/SSE
- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/api/ingest_event_bus.py`, будущий `science_graphrag/worker/`
- **Issue:** Файл совмещает HTTP-роутер, `IngestJobRegistry` с прямым SQLAlchemy/ORM, in-process `threading.Thread` воркер, SSE endpoint, маппинг ORM↔DTO и intermix с `chain_span`. Wave W удалит `threading.Thread`, но без структурного разделения регистр/SSE/HTTP останутся в одной куче.
- **Proposal:** разделить на (1) `api/ingest/router.py` (HTTP + SSE, тонко), (2) `api/ingest/registry.py` (Postgres-стор jobs/stages/events, маппинг DTO), (3) `api/ingest/dispatcher.py` (in-process до Wave W, `enqueue` к Dramatiq после), (4) `api/ingest/dto.py` (`IngestJobView`, `IngestStageView`, `IngestJobEvent`). `IngestEventBus` остаётся отдельным модулем — менять только реализацию (in-process → Redis pub/sub).
- **Acceptance:** ни один файл > ≈400 строк; тесты `test_api_smoke` + новые юниты на registry зелёные; **Wave W** меняет только `dispatcher.py` и реализацию `IngestEventBus`.
- **Synergy:** **Wave V** (SSE done) — уже отделил event bus; **Wave W** (Dramatiq+Redis) — сядет на готовую границу dispatcher. Тонкая schema под `phoenix_trace_id` (Wave X1.6) тоже изолирована.
- **Raised:** 2026-04-25

### [OPEN] Split `api/benchmark.py` (1027) + `api/task_store.py` (908)
- **Area:** `science_graphrag/api/benchmark.py`, `science_graphrag/api/task_store.py`, `science_graphrag/api/benchmark_profiles.py`
- **Issue:** Двa самых крупных hub-модуля для UI бенчмарка. `benchmark.py` — каталог фикстур, детали кейсов, сравнение, связь с `task_store`/`graph_snapshot_diff`/`eval/*`. `task_store.py` — in-memory `ThreadPoolExecutor` исполнитель + JSON guards + persist + сериализация. Сильная связность с `eval/`; рост блокирует продвижение **Wave M/P/Q/R/S** (новые семейства бенчмарков добавляются в один большой роутер).
- **Proposal:** разнести `benchmark.py` на `api/benchmark/{router.py,catalog.py,case_detail.py,compare.py,profiles.py}`. Из `task_store.py` выделить: `runs_executor.py` (планировщик/пул), `runs_persistence.py` (snapshots, sidecar JSON, гварды), `runs_dto.py` (сериализация для API). Сохранить публичные эндпоинты.
- **Acceptance:** ни один модуль > ≈400 строк; новые семейства бенчмарков (`workspace_scoped`, `hybrid_ablation`, `multihop_v1`, `agent_tools_*`, `idea_assist_v1`) добавляются точечно в `catalog.py` без редактирования router/persistence; тесты `test_benchmark_*` зелёные.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap-2026-04-24.md` — каждое семейство не упирается в god-файл.
- **Raised:** 2026-04-25

### [OPEN] Split `ingestion/llm/stage_extraction.py` (849) — orchestrator vs prompts vs heuristics
- **Area:** `science_graphrag/ingestion/llm/stage_extraction.py`, `science_graphrag/ingestion/llm/semantic_extraction.py`, `science_graphrag/ingestion/llm/extractor.py`
- **Issue:** LLM-first путь смешивает orchestration (`ThreadPoolExecutor`), Pydantic-схемы, промпты, heuristic fallback и связку со stage-модулями metadata/authorships/references. Дубли регексов/промптов с `semantic_extraction.py`. Перепиливается каждый раз при новом extractor (claims, concept/topic — Wave N/O).
- **Proposal:** ввести `science_graphrag/ingestion/llm/` подпакет с: `prompts/<call_name>.py` (текстовые промпты + Pydantic-схема), `executor.py` (общий вызов через instructor/LangChain, span-discipline), `orchestrator.py` (LLM + heuristics + fallback политика), `heuristics/<call_name>.py`. `semantic_extraction.py` использует тот же executor и тот же стиль `prompts/`.
- **Acceptance:** ни один файл > ≈300 строк; новые extractor'ы (Wave N concept/topic gold→production, Wave O claims promotion) добавляются как `prompts/<name>.py` + `heuristics/<name>.py`; юнит-тесты на промпт-схемы.
- **Synergy:** **Wave N/O** (онтология), **Wave Y2** (LangGraph tool-граф) — общий executor можно потом переключить на `langchain_core` LLM-калл без сноса orchestrator.
- **Raised:** 2026-04-25

### [OPEN] Core/router split for `api/retrieval.py` (682)
- **Area:** `science_graphrag/api/retrieval.py`, `science_graphrag/api/main.py` (`answer_query`/`GroundedAnswer`)
- **Issue:** Один файл собирает: query embedding (OpenAI), Qdrant search, Neo4j semantic context, second-stage answer, payload фильтры. Тестировать фрагменты без поднятия всего стека сложно. `api/main.py` отдельно импортирует `answer_query` для собственных хендлеров — двойной entry point.
- **Proposal:** выделить `science_graphrag/retrieval/` пакет: `query_embedder.py`, `qdrant_search.py`, `neo4j_context.py`, `hybrid_combiner.py` (под Wave Q), `answer.py`. `api/retrieval.py` — тонкий router; `api/main.py` импортирует только из `science_graphrag/retrieval/`.
- **Acceptance:** core retrieval тестируется юнитами с заглушенными stores; ни один модуль не превышает ≈300 строк.
- **Synergy:** **Wave Q** (hybrid + RRF + multihop) — добавление новых mode не растягивает router. **Wave R** (`idea_search` как tool) и **Wave Y2** (LangGraph) переиспользуют core напрямую без обхода API. **Wave P** (workspace-scoped + judge) — вынесение фильтра `workspace_ids` в `qdrant_search.py`.
- **Raised:** 2026-04-25

### [OPEN] Split `api/works.py` (817) — graph DTO vs vector vs blob
- **Area:** `science_graphrag/api/works.py`, `science_graphrag/api/graph_display.py`
- **Issue:** Совмещает list/detail работ, neighborhood payload, чанки из Qdrant, blob/PDF entry, semantic context. Параллельно с `workspace_graph.py` участвует в **Wave GR1–GR5**.
- **Proposal:** разнести на `api/works/`: `router.py`, `detail.py`, `graph_neighborhood.py` (использует общий `graph_display`), `chunks.py`. Wave GR работает только в `graph_neighborhood.py`.
- **Acceptance:** ни один файл > ≈400 строк; тесты `tests/test_works_graph_display.py` и smoke зелёные.
- **Synergy:** **Wave GR2/GR4** — `node_kind`, `view=reader` на одном work правится в одном модуле.
- **Raised:** 2026-04-25

### [OPEN] Unified Bolt access factory + agent/idea-assist composition root
- **Area:** `science_graphrag/api/deps.py` (новый, или существующий), `science_graphrag/storage/neo4j_store.py`, `science_graphrag/api/agent.py`, `science_graphrag/api/idea_assist.py`, `science_graphrag/agent/`
- **Issue:** Паттерн `Neo4jGraphStore(settings.neo4j_uri, ...)` вручную поднимается в десятке мест (`retrieval`, `works`, `idea_assist`, `agent`, `ingest_jobs`, `workspaces`, `workspace_dedup`, `cli`, `pipeline`); `api/workspace_graph.py` дополнительно использует raw `GraphDatabase.driver(...)`. Каждый запрос к agent-эндпоинтам пересоздаёт stores (отмечено в `phoenix-tracing-coverage` как pain). Composition root для idea-assist дублирует agent.
- **Proposal:** ввести FastAPI dependency `get_stores()` → singleton-фасад `StoreRegistry` (`neo4j`, `qdrant_chunks`, `qdrant_works`, `qdrant_claims`, `blobs`, `postgres_session`); все API роуты и agent/idea-assist берут stores через DI. CLI — через сервис-фабрику. Убрать прямой `GraphDatabase.driver` из `workspace_graph`.
- **Acceptance:** один источник создания клиентов; тесты могут подменять `StoreRegistry` фикстурой; per-request init Neo4j/Qdrant исчезает в agent-пути.
- **Synergy:** **Wave Y2/Y3** (LangGraph) — supervisor + tools получают stores через `build_tool_registry(stores)`; **Wave X2** (Phoenix retrieval agent) — единая точка для `init_tracer_provider` lifespan; **Wave W** (Dramatiq worker) — один `StoreRegistry` в воркере.
- **Raised:** 2026-04-25

### [OPEN] Split `observability/phoenix_tracer.py` (492) — init vs spans vs instrumentation
- **Area:** `science_graphrag/observability/phoenix_tracer.py`, `science_graphrag/ingestion/stage_context.py`
- **Issue:** В одном файле — init Phoenix/OTel + конфигурация scope (`PHOENIX_TRACE_SCOPE`) + helpers `chain_span`/`llm_span` + обёртка OpenAI auto-instrumentation. Ветвления по scope разрастаются с каждой волной (`extraction_llm`, перспективный `agent_only`).
- **Proposal:** пакет `science_graphrag/observability/`: `init.py` (`init_tracer_provider`, lifespan helper), `spans.py` (`chain_span`, `llm_span`, `embeddings_span`, `traced_tool_span`), `scope.py` (политика `PHOENIX_TRACE_SCOPE`, синхронизация имён `_EXTRACTION_LLM_CHAIN_NAMES`), `instrumentation.py` (OpenAI/LangChain hooks).
- **Acceptance:** контракт-тесты `test_span_contract.py` без изменений поведения; добавление нового scope (`agent_only` после X2) не требует трогать `init.py`.
- **Synergy:** **Wave X2** (retrieval agent observability) — `traced_tool_span` уже в плане; **Wave Y1** (LangChain instrumentation) — `instrumentation.py` место для openinference-langchain.
- **Raised:** 2026-04-25

### [OPEN] Split `api/task_store.py` see «benchmark.py + task_store.py»
*(объединено выше, см. пункт «Split `api/benchmark.py` + `api/task_store.py`»).*

### [OPEN] Settings service split (504)
- **Area:** `science_graphrag/settings/service.py`, `science_graphrag/api/settings.py`
- **Issue:** Сервис настроек смешивает работу с секретами/OpenAI client и сборку DTO для security/diagnostics snapshot.
- **Proposal:** `settings/secrets.py` (KMS/env interaction), `settings/llm_clients.py` (OpenAI/OpenRouter clients), `settings/service.py` (DTO/CRUD), `settings/snapshots.py` (security/diagnostics).
- **Acceptance:** ни один файл > ≈300 строк; добавление новых секций settings (Wave L work_dedup, Wave R agent caps, Wave Y2 LangChain creds) — точечная правка в `secrets.py`.
- **Raised:** 2026-04-25

### [OPEN] Split `cli/main.py` (361) by command groups
- **Area:** `science_graphrag/cli/main.py`
- **Issue:** Typer-приложение фактически — оркестратор offline-операций (`neo4j-wipe`, `ingest`, `merge-work`, `repoint-qdrant-work-ids` и т.п.); по мере Wave Q/T/W будет расти.
- **Proposal:** `cli/{ingest,neo4j,qdrant,dedup,worker}.py`, тонкий `cli/main.py` собирает Typer-app из подкоманд.
- **Acceptance:** ни один файл > ≈200 строк; запуск `science-graphrag --help` идентичен.
- **Synergy:** **Wave W** добавит `cli/worker.py` (запуск Dramatiq) без раздувания main.
- **Raised:** 2026-04-25

### [OPEN] Targeted backend test coverage for hot modules
- **Area:** `tests/test_ingest_jobs*`, `tests/test_retrieval*`, `tests/storage/test_neo4j_*`, `tests/agent/`
- **Issue:** На фоне распилов (registry, retrieval core, neo4j writes) текущее покрытие — преимущественно smoke + интеграционные. Юнит-тестов на error paths и DTO-маппинги мало; рискуют регрессии при разнесении god-файлов.
- **Proposal:** перед каждым крупным split добавить характерные unit-тесты (registry transitions, ORM↔DTO, retrieval core с mocked stores, neo4j writes по доменам). Перед Wave Y2 — `tests/agent/` под LangGraph state.
- **Acceptance:** для затронутых split-PR'ов покрытие новых модулей юнит-тестами > 70 % строк (без интеграционных).
- **Raised:** 2026-04-25

### [OPEN] DB-backed benchmark run store (deferred)

- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** File-backed snapshots suffice for single-host dev/QA; a DB would add ops cost without a clear trigger today.
- **Proposal:** Stay on disk until **multi-host** API or **large-volume** retained run history becomes a product requirement; then design migrations, retention, and export parity with current JSON snapshots.
- **Acceptance:** No DB migration started without an operational signal captured in a pilot/ops note; file-backed path remains documented as the default.
- **Raised:** 2026-04-19

<!-- Example:
### [OPEN] Example — tighten retrieval module boundaries
- **Area:** `science_graphrag/api/retrieval.py`, related services
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->

### [DONE] Audit teacher-gold benchmark fixtures
- **Area:** `eval/teacher_gold/layer1/`, generation scripts in `scripts/`, benchmark run persistence in `science_graphrag/api/benchmark.py`
- **Issue:** `teacher_gold` fixtures are partially sparse and can drift from curated gold or persisted run payloads; this creates false negatives in benchmark analysis and makes UI triage harder.
- **Proposal:** follow [benchmarks/teacher-gold-audit-v1.md](../benchmarks/teacher-gold-audit-v1.md): inventory fields, diff fixtures vs `data/benchmark_runs/*.json` gold payloads, triage, remediation.
- **Acceptance:** documented audit checklist, prioritized list of suspect cases, and an agreed remediation path for fixture refresh vs. post-processing repair.
- **Raised:** 2026-04-07
- **Note (done):** 2026-04-19 — Wave E1 baseline: [teacher-gold-audit-checklist.md](../benchmarks/teacher-gold-audit-checklist.md) extended with layer-2 table + **Audit exit** block; ongoing row-by-row review stays in that checklist until all phases CLOSED.

### [DONE] Durable benchmark run snapshots (UI API)
- **Area:** `science_graphrag/api/task_store.py`, `data/benchmark_runs/`
- **Issue:** Earlier bridge backlog called out “durable runs”; runs must survive API restart for dev/QA.
- **Proposal:** Implemented: `_persist_run_snapshot`, `_load_persisted_runs`, `.summary.json` sidecars; see `BenchmarkTaskStore` docstring.
- **Acceptance:** Restart API → run list/history still lists completed runs from disk; documented in Phase 6 bridge backlog.
- **Raised:** 2026-04-06
- **Note (done):** 2026-04-19 — backlog row closed; optional future work is DB-backed store if file volume becomes a bottleneck.
