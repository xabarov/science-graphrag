# Frontend Phase 6 bridge backlog

Backlog is split into two synchronized tracks: frontend shell and backend bridge endpoints.

**Референс по форме (osint-gr):** страница просмотра и запуска бенчмарков и сопутствующий контур — `frontend/src/pages/BenchmarkPage/` (UI), `backend/tests/bench/` (фикстуры/генерация вокруг кейсов), `backend/osint_graphrag/utils/bench/` (утилиты). В science-graphrag аналог — маршрут `/benchmark` в `ui/`, HTTP-слой `science_graphrag/api/benchmark.py`, исполнение прогонов `science_graphrag/api/task_store.py`, эталонные кейсы под CLI — `tests/fixtures/benchmarks/` и `eval/README.md`.

## Track A: frontend shell backlog

## A1. App bootstrap and shell

- [x] Initialize standalone frontend app in repo root `ui/` (or agreed package path).
- [x] Set route map for `Workspace`, `Reader`, `Graph`, `Ask`, `Evidence`, **`Benchmarks`** (`/benchmark`).
- [x] Implement reusable layout shell (sidebar, header, content outlet).
- [x] Add base theme tokens matching current design constraints.

Definition of done:

- app runs locally;
- all routes accessible with placeholder state;
- shell does not depend on missing backend endpoints.

## A2. Query-first integration

- [x] Create typed API adapter for `POST /v1/query`.
- [x] Build `Ask` screen with request state, citations panel, graph-context chips.
- [x] Render retrieval trace (resolved work id, hit count, embedding model label).
- [x] Add degraded-state UX for empty hits / backend unavailable.

Definition of done:

- user can issue a query and inspect citations + trace end-to-end.

## A3. Mock-driven research surfaces

- [x] Build `Workspace` with mocked works list/search.
- [x] Build `Reader` with mocked metadata + chunks.
- [x] Build `Graph` with mocked neighborhood payload.
- [x] Build `Evidence` screen focused on citation provenance.
- [x] Add fixture packs for "semantic available" and "semantic missing" states (`ui/src/fixtures/researchSemanticSamples.js`; covered in `researchApi.test.js`).

Definition of done:

- all screens are usable with fixtures;
- navigation and IA validated before full API integration.

## A4. Frontend quality gates

- [x] Add unit tests for API adapters (`researchApi`); route guards / reducers — backlog.
- [x] Add integration tests for `Ask` flow (`POST /v1/query` success/failure) — API-level: `test_mandatory_happy_path_sequence_smoke` + existing `test_query_endpoint_smoke` in `tests/test_api_smoke.py`.
- [x] Add basic lint + test checks to CI for frontend package.

## A5. Benchmark console (developer / QA)

Цель: как в osint-gr — **список кейсов**, **запуск подмножества**, **история прогонов** и **просмотр результатов** без обязательного SSH/CLI (CLI и decision gate остаются эталоном Phase 4).

- [x] Страница `/benchmark` (`ui/src/pages/BenchmarkPage/`), пункт навигации в shell.
- [x] Вкладки: кейсы (фильтр по tier / поиск), запуск (выбор кейсов), история прогонов, диалоги деталей.
- [x] Клиент `ui/src/services/benchmarkApi.js` к `/v1/benchmark/*`.
- [x] **Layer-2 + graph catalog в том же UI:** layer-2 прогоны через API; **graph-v1** — семейство `family=graph` в списке кейсов, колонка/флаг `graph_expectations`, вкладка ожиданий в деталях кейса; запуск graph-прогона **только CLI/CI** (`POST` → `graph_benchmark_use_cli`).
- [x] **Semantic / graph diff (MVP):** layer-2 — нормализованное сравнение methods/datasets в `SemanticComparisonTable`; graph — просмотр `graph_expectations` в JSON (полный side-by-side выход раннера vs gold в UI — backlog при необходимости).
- [x] **Целевая аудитория:** зафиксировано для текущей версии — **dev/QA-консоль** (см. [roadmap](../roadmap.md)); отдельный **пилот** для иной аудитории — будущее product/UX-решение, не блокер для консоли.
- **Note (2026-04-08):** Реализация `/benchmark` и API не блокируется отсутствием пилотного scope. Обновление 2026-04-08: чекбокс закрыт с явным дефолтом dev/QA.
- [x] Smoke на `GET /v1/benchmark/cases` в `tests/test_api_smoke.py` (`test_benchmark_cases_list_smoke`).

## Track B: backend bridge backlog

## B1. Endpoint set for first live UI wave

- [x] Implement `GET /v1/works` (search/list + pagination).
- [x] Implement `GET /v1/works/{work_id}` (work card for reader header).
- [x] Implement `GET /v1/works/{work_id}/graph` (graph neighborhood payload).
- [x] Implement `GET /v1/works/{work_id}/chunks` (reader/evidence payload).

Definition of done:

- endpoints match `docs/specs/frontend-ui-api-contracts-v1.md` (including **Mandatory API happy-path**).

**Mandatory happy-path:** см. [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) — раздел *Mandatory API happy-path*. Расширение `tests/test_api_smoke.py` под маршруты `/v1/*` — backlog при наличии моков сторов или интеграционной среды.

## B2. Observability and degraded behavior

- [x] Ensure explicit degraded flags for missing semantic layer.
- [x] Return stable ids for traceability (`work_id`, `document_id`, `chunk_fingerprint`).
- [x] Add response examples to docs and API tests.

## B3. Query payload enrichment (incremental)

- [x] Extend `/v1/query` trace metadata where cheap and deterministic.
- [x] Keep backward compatibility for `answer/citations/graph_context/retrieval_trace`.

## B4. Benchmark UI API (layer-1 MVP)

Эндпоинты для страницы Benchmarks; не входят в обязательный research happy-path Wave C, но зафиксированы как контракт UI ↔ API (см. [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md)).

- [x] `GET /v1/benchmark/cases` — список кейсов layer-1 (опционально `tier`, `q`, пагинация).
- [x] `GET /v1/benchmark/cases/{case_id}` — тело кейса (`article.md`, `gold`) для превью.
- [x] `POST /v1/benchmark/runs` — постановка прогона (выбранные `case_ids` или ярлыки вроде `merge_safe`).
- [x] `GET /v1/benchmark/runs`, `GET /v1/benchmark/runs/{run_id}`, `DELETE /v1/benchmark/runs/{run_id}`.
- [x] Явно задокументировать ограничения: run store **file-backed** (`data/benchmark_runs/*.json`, восстановление после рестарта; см. §6 контрактов), in-memory только активные записи + пул; **layer-1** и **layer-2** runner в task pool — [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) §6.
- [ ] Backlog: durable runs (файл/БД); graph runner остаётся CLI-first — см. [eval/README.md](../../eval/README.md).

## Sequencing

1. `A1` and `A2` can start immediately.
2. `A3` runs in parallel with `B1`.
3. `B2` finalization blocks full switch from mocks to live data.
4. `A4` lands before broader pilot usage.
5. `A5` / `B4` могут идти параллельно с `B1` (не блокируют research happy-path); расширение семейств — после стабилизации CLI Phase 4.
