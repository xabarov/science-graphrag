# Frontend UI API contracts v1 (Phase 6 MVP)

## Scope

This document defines the minimum backend contracts required to move frontend from mock-driven shell to live data integration.

Status by endpoint:

- `POST /v1/query`: implemented (source of truth in `science_graphrag/api/main.py`)
- `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks`: implemented (same module; Neo4j + Qdrant)
- **`/v1/benchmark/*`:** benchmark console UI (`science_graphrag/api/benchmark.py`, runs via `science_graphrag/api/task_store.py`) — **layer-1** и **layer-2** (`family` query/body); не часть обязательного research happy-path ниже
- other niceties below: optional backlog (filters, richer graph projection)

## Mandatory API happy-path (Wave C)

Один обязательный сквозной сценарий для Phase 5/6 bridge и пилота (после ingest хотя бы одной работы в Neo4j/Qdrant):

1. **Ingest** одного документа: `science-graphrag ingest path/to/paper.pdf` (или корпус — см. [runbooks/deploy.md](../runbooks/deploy.md)).
2. **`GET /v1/works`** — список не пустой, выбрать `work_id`.
3. **`GET /v1/works/{work_id}`** — 200, стабильные поля `work_id`, `ingestion`.
4. **`POST /v1/query`** — ответ с `citations` и `retrieval_trace` (допустимы пустые hits при пустом Qdrant, но не 5xx).
5. **`GET /v1/works/{work_id}/chunks`** — при наличии чанков: ненулевой `total` или согласованный degraded UX в UI.

Опционально для полной трассируемости: **`GET /v1/works/{work_id}/graph`** — 200, `semantic_available` согласован с фактом semantic ingest.

**Автоматическая проверка (merge CI):** `tests/test_api_smoke.py` проверяет `/health` и API-контракты `/v1/*` на моках (без живых сторов). Полный happy-path с живыми Neo4j/Qdrant — ручной или через `pytest -m integration` после поднятия compose; см. [roadmap Phase 5](../roadmap.md).  
**Snapshot (2026-03-31):** `pytest tests -m integration` прошёл (`3 passed`) на compose-стеке.

## Contract principles

- Stable identifiers in all responses: `work_id`, `document_id`, `chunk_fingerprint` where applicable.
- Traceability first: UI can always show "where this came from".
- Degraded modes are explicit in payloads (no hidden semantics).
- Missing semantic extraction is a valid state, not an exception.

## 1) Query endpoint (implemented)

### `POST /v1/query`

Request:

```json
{
  "query": "string, required",
  "work_id": "string | null",
  "top_k": "int [1..24], default 5"
}
```

Response shape:

```json
{
  "answer": "string",
  "citations": [
    {
      "rank": 1,
      "score": 0.0,
      "work_id": "string | null",
      "document_id": "string | null",
      "chunk_fingerprint": "string | null",
      "section_path": "string | null",
      "excerpt": "string"
    }
  ],
  "graph_context": {
    "methods": ["string"],
    "datasets": ["string"],
    "semantic_available": true,
    "context_work_id": "string | null",
    "degraded": ["string"],
    "error": "string | null"
  },
  "retrieval_trace": {
    "embedding": {
      "embedding_model": "string",
      "vector_dim": 0
    },
    "hit_count": 0,
    "filter_work_id": "string | null",
    "resolved_work_id": "string | null",
    "qdrant_collection": "string",
    "top_k_requested": 0,
    "citations_returned": 0,
    "degraded": ["string"]
  }
}
```

Degraded mode expectations:

- **No retrieval hits** → answer explains empty retrieval; citations empty; `retrieval_trace.degraded` contains `no_retrieval_hits`. Compare `retrieval_trace.hit_count`, `top_k_requested`, and `citations_returned` in the UI (e.g. hits present but empty excerpts should be rare; trace should still explain the outcome).
- **No work id resolved** from filter or top hits → `graph_context.degraded` contains `no_resolved_work`; `context_work_id` null; `semantic_available` false until a work is resolved.
- **Unknown work id** (resolved id not in Neo4j) → `graph_context.degraded` contains `work_not_in_graph`.
- **Neo4j unavailable** → `graph_context.error = "neo4j_unavailable"`; `graph_context.degraded` contains `neo4j_unavailable`; methods/datasets empty; UI should surface the error string and avoid implying semantic validation.
- **Semantic edges absent** (valid state after ingest without LLM or failed semantic stage) → `semantic_available=false`; `graph_context.degraded` may be empty (not an error). Chips/panels should not claim methods/datasets were extracted.
- **Qdrant / embedding failures** → expect HTTP 5xx or upstream error from the API client; not represented as a successful `degraded` payload. UI should treat transport errors separately from semantic degradation.

## 2) Works list/search (implemented)

### `GET /v1/works`

Query params:

- `q` (optional text search)
- `limit` (optional int, default 20, max 100)
- `offset` (optional int, default 0)

Response:

```json
{
  "items": [
    {
      "work_id": "string",
      "title": "string",
      "year": 2020,
      "doi": "string | null",
      "arxiv_id": "string | null",
      "venue": "string | null",
      "authors_preview": ["string"],
      "has_semantic_layer": true
    }
  ],
  "total": 0
}
```

## 3) Work detail (implemented)

### `GET /v1/works/{work_id}`

Response:

```json
{
  "work_id": "string",
  "title": "string",
  "abstract": "string | null",
  "year": 2020,
  "doi": "string | null",
  "arxiv_id": "string | null",
  "venue": "string | null",
  "authors": [
    {
      "author_id": "string",
      "name": "string",
      "institutions": ["string"]
    }
  ],
  "ingestion": {
    "document_id": "string | null",
    "has_chunks": true,
    "has_semantic_layer": true
  }
}
```

## 4) Work graph neighborhood (implemented)

### `GET /v1/works/{work_id}/graph`

Response:

```json
{
  "work_id": "string",
  "nodes": [
    {
      "id": "string",
      "type": "Work|Method|Dataset|Author|Venue|...",
      "label": "string"
    }
  ],
  "edges": [
    {
      "source": "string",
      "target": "string",
      "type": "string"
    }
  ],
  "meta": {
    "semantic_available": true
  }
}
```

`source` / `target` follow the **Neo4j relationship orientation** (`startNode(rel)` → `source`, `endNode(rel)` → `target`) for the matched hop between the requested work and each neighbor. Incoming vs outgoing edges therefore differ by which endpoint is the work id.

Degraded mode:

- if semantic extraction missing, return backbone-only neighborhood and `semantic_available=false`.

## 5) Chunks/evidence (implemented)

### `GET /v1/works/{work_id}/chunks`

Query params:

- `limit` (optional int, default 50, max 200)
- `offset` (optional int, default 0)
- `section_prefix` (optional string)

Response:

```json
{
  "items": [
    {
      "document_id": "string",
      "chunk_fingerprint": "string",
      "section_path": "string | null",
      "text": "string",
      "order": 0
    }
  ],
  "total": 0
}
```

## 6) Benchmark console API (implemented, layer-1 + layer-2 + graph catalog)

Назначение: страница **`/benchmark`** в `ui/` — просмотр кейсов и запуск прогонов **без обязательного CLI**, по идее как dev/QA-консоль в референсе [osint-gr](/home/roman/pyprojects/ML/Prod/osint-gr) (`frontend/src/pages/BenchmarkPage/` и связанные сервисы). Фикстуры: `tests/fixtures/benchmarks/layer1/` и `tests/fixtures/benchmarks/layer2/`; полный suite и decision gate остаются в [eval/README.md](../../eval/README.md) и [runbooks/benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md).

| Method | Path | Role |
|--------|------|------|
| GET | `/v1/benchmark/cases` | Список кейсов (`family=layer1\|layer2\|graph`, `tier`, `q`, `limit`, `offset`). Для `graph` — только layer-1 кейсы, у которых в `gold.json` есть `graph_expectations` (каталог для UI, без запуска Neo4j из API). |
| GET | `/v1/benchmark/models` | Каталог model presets для UI launcher: `profile_id`, `label`, `role`, `model_id`, `family_support`, `default_gold_source`, `default_threshold_profile`. |
| GET | `/v1/benchmark/cases/{case_id}` | Превью fixture: `article_md`, `article_sections`, `gold`, `artifacts`; для layer-1 поддержан `gold_source=curated_gold\\|teacher_gold`, для layer-2 `gold` = содержимое `semantic_gold.json`. |
| GET | `/v1/benchmark/cases/{case_id}/artifacts` | Инвентарь файлов кейса: `family` query (`layer1` / `layer2` / `graph`), пути относительно корня репозитория, `gold_variants` (curated/teacher) для layer-1, `semantic_gold` / `semantic_gold_teacher` для layer-2, `graph_expectations` для graph. Поле `last_run_hints`: при наличии — `{ run_id, completed_at, status }` для последнего **completed** run с тем же `benchmark_family`, где встречается `case_id` (скан до 200 самых новых по mtime JSON в `data/benchmark_runs/` и legacy dir), иначе `null`. |
| POST | `/v1/benchmark/cases/{case_id}/graph-snapshot-preview` | Тело JSON: `{ "graph_snapshot": { ... } }` (как вывод graph-benchmark CLI). Query `family` (`graph` по умолчанию или `layer1` при `graph_expectations` в gold). Ответ `data`: `rows`, `arxiv_notes`, `opened_case_id`, `snapshot_case_id`, `case_id_mismatch` (серверный diff, зеркало логики UI `graphSnapshotCompare.js`). Лимит сырого тела **3 MiB** — **413** `graph_snapshot_body_too_large`. **422**: `invalid_json_body`, `graph_snapshot_required`. **404**: `case_has_no_graph_expectations` / `case_not_found`. |
| POST | `/v1/benchmark/runs` | Старт прогона (`case_ids` или ярлыки `all` / `merge_safe` / `nightly_heavy` / `nightly_semantic`; тело: `family`, `label`, `model_profile`, `model_id`, `gold_source`, `threshold_profile`, optional `base_url_override`, `api_key_env_name`). Для `family=graph` — **400** с `detail: "graph_benchmark_use_cli"` (исполнение через `science-graphrag-graph-benchmark` / CI, не через API). |
| GET | `/v1/benchmark/runs` | История прогонов. Опциональные query: `family` (точное совпадение `benchmark_family`, без учёта регистра), `status` (точное совпадение статуса run-а), `q` (подстрока в `run_id` или `label`, без учёта регистра). |
| GET | `/v1/benchmark/runs/compare` | Сравнение двух прогонов: query `baseline_run_id`, `current_run_id` (оба из store). Одинаковый `benchmark_family`; ответ `data` — результат `compare_reports` (регрессии/улучшения/unchanged по плоским метрикам) плюс `skipped_baseline` / `skipped_current`, `baseline_run_id`, `current_run_id`, строка **`markdown`** (готовый отчёт через `compare_result_to_markdown`). **400**: `same_run_id`, `benchmark_family_mismatch`, `compare_case_limit_exceeded` (если в любом из run-ов `cases.length` > 2000). **404**: `baseline_run_not_found` / `current_run_not_found`. |
| GET | `/v1/benchmark/runs/{run_id}` | Детали/метрики прогона (полный JSON, включая `result` по кейсам). **413** `run_payload_too_large_use_cases_api`, если run в памяти превышает лимит числа кейсов (**2000**) или снимок `{run_id}.json` на диске > **50 MiB** — использовать summary + `GET .../cases` или CLI. |
| GET | `/v1/benchmark/runs/{run_id}/summary` | Компактный прогон: те же верхнеуровневые поля и обычно `cases[]` с `case_id`, `status`, `summary`, `error_message`, `finished_at`, без тяжёлого `result`. Если кейсов больше внутреннего порога (~100), `cases` может быть `[]`, тогда заданы `cases_paginated: true` и `cases_total` — список подгружать через `GET .../cases`. При persist пишется sidecar `data/benchmark_runs/{run_id}.summary.json`; при наличии читается без полной загрузки основного JSON. Поля **`full_run_blocked`** (bool) и **`full_run_block_reason`** (строка или `null`) подсказывают UI, можно ли безопасно вызывать полный `GET .../runs/{run_id}`. |
| GET | `/v1/benchmark/runs/{run_id}/cases` | Пагинация slim-строк кейсов (без `result`): query `offset` (≥0), `limit` (1–500). Ответ `data`: `items`, `total`, `offset`, `limit`, `run_id`, `benchmark_family`. Маршрут объявлен **до** `.../cases/{case_id}`. |
| GET | `/v1/benchmark/runs/{run_id}/cases/{case_id}` | Workbench drill-down: `article`, `gold`, `predicted`, `comparison`, `metrics`, `diagnostics`, `run_config` для одного кейса в рамках run-а. |
| DELETE | `/v1/benchmark/runs/{run_id}` | Удалить запись прогона |

**Ограничения (зафиксировать в UX):** run history file-backed: `data/benchmark_runs/{run_id}.json` + опционально `{run_id}.summary.json`; при restore из glob игнорируются `*.summary.json`. Если API был перезапущен посреди выполнения, незавершённый run при restore помечается как interrupted/failed. `api_key_env_name` разрешает только ссылку на переменную окружения на backend, UI не передаёт raw secret. **Graph-v1 прогоны** из UI не запускаются (ингест + Neo4j); вкладка «graph» в Benchmarks — каталог кейсов и просмотр `graph_expectations`, ссылка на CLI. Deep-link: `/benchmark?tab=workbench|launch|results|compare|cases` или `tab=0..4`, плюс `run`, `case`. Детали — [architecture/frontend-phase6-bridge-backlog.md](../architecture/frontend-phase6-bridge-backlog.md) `A5` / `B4`.

**Ответ прогона:** layer-1 — `ComparisonTable`; layer-2 — semantic methods/datasets (`SemanticComparisonTable` в UI).

Клиент: `ui/src/services/benchmarkApi.js` (`getBenchmarkRunSummary`, `getBenchmarkCaseArtifacts`, `compareBenchmarkRuns`, …).

## Mapping to UI surfaces

- `Workspace`: `GET /v1/works`
- `Reader`: `GET /v1/works/{work_id}` + `GET /v1/works/{work_id}/chunks`
- `Graph`: `GET /v1/works/{work_id}/graph`
- `Ask`: `POST /v1/query`
- `Evidence`: query citations + chunks lookup by `chunk_fingerprint`
- `Benchmarks`: `/v1/benchmark/*` (см. §6)
