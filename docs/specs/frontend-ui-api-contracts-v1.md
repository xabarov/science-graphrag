# Frontend UI API contracts v1 (Phase 6 MVP)

## Scope

This document defines the minimum backend contracts required to move frontend from mock-driven shell to live data integration.

Status by endpoint:

- `POST /v1/query`: implemented (source of truth in `science_graphrag/api/main.py`)
- `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks`: implemented (same module; Neo4j + Qdrant)
- **`/v1/benchmark/*`:** benchmark console UI (`science_graphrag/api/benchmark.py`, runs via `science_graphrag/api/task_store.py`) — **layer-1** и **layer-2** (`family` query/body); не часть обязательного research happy-path ниже. Если задан `SCIENCE_GRAPHRAG_ADMIN_API_KEY`, клиент должен слать заголовок **`X-Admin-Key`** (см. [admin-policy.md](./admin-policy.md)).
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
  "workspace_id": "string | null",
  "top_k": "int [1..24], default 5"
}
```

When **`workspace_id` is set** and **`work_id` is omitted**, retrieval first filters Qdrant vector search by payload `workspace_ids` containing that workspace id. Unknown workspace → HTTP 200 with empty hits and `retrieval_trace.workspace_missing: true`. **`work_id` wins** when both are provided (single-paper scope). For workspace-scoped calls, the request `workspace_id` is echoed on `retrieval_trace.workspace_id` together with `workspace_scope_work_count` (and `workspace_missing` when the workspace is unknown). If the payload-filtered search returns **no hits** but Neo4j still lists member works, the API performs **one retry** using `work_id IN (workspace members)` and sets `retrieval_trace.workspace_scope_payload_miss = "work_ids_payload"` (log warning) — run `scripts/backfill_workspace_payloads.py` if this appears after ingest migrations.

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
    "workspace_id": "string | null",
    "workspace_scope_work_count": "number | omitted",
    "workspace_missing": "boolean | omitted",
    "workspace_scope_payload_miss": "string | omitted",
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

- `q` (optional text search — title substring, case-insensitive)
- `year_min` / `year_max` (optional int — only works with a non-null `publication_year` in range)
- `has_semantic` (optional bool — `true`: only works with Method/Dataset edges; `false`: only works without them)
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

## 2b) Ask sessions — server persistence (optional, implemented)

File-backed store under `data/ask_sessions/<scope>.json` on the API host. Scope is a short ASCII identifier (e.g. `standalone`, `workspace:work-123`).

| Method | Path | Notes |
|--------|------|-------|
| `GET` | `/v1/ask-sessions?scope=...` | Returns `{ scope, sessions[], active_session_id }`. |
| `POST` | `/v1/ask-sessions` | Body `{ "scope": "...", "title": "..." }` → `{ session }`. |
| `PATCH` | `/v1/ask-sessions/{session_id}?scope=...` | Body `{ "title"?, "turns"?, "active"?: bool }`. |
| `DELETE` | `/v1/ask-sessions/{session_id}?scope=...` | Removes one session. |

The React UI may keep using `localStorage` sessions ([ask-sessions.md](./ask-sessions.md)); these endpoints are for pilot / multi-device follow-up.

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

### `GET /v1/works/{work_id}/sources` and `GET /v1/works/{work_id}/pdf`

- **`/sources`:** JSON inventory (`pdf`, `markdown` availability) for Reader UI.
- **`/pdf`:** Streams `application/pdf` from the blob store (`StreamingResponse`). Supports **`Range: bytes=…`** → **206 Partial Content** with `Content-Range` and `Content-Length` for the slice; full file → **200** with `Content-Length`. **`ETag`** + `Accept-Ranges: bytes`; **`If-None-Match`** → **304**. Malformed or unsatisfiable range → **416** with `Content-Range: bytes */{size}`.

## 4) Work graph neighborhood (implemented)

### `GET /v1/works/{work_id}/graph`

Optional query (server contract):

| Query | Meaning |
|-------|---------|
| `neighbor_limit` | Integer **1–2000** (default **200**). Caps rows from the 1-hop `MATCH (w)-[r]-(n)` scan. |
| `depth` | Integer **1–3** (default **1**). Reserved for future multi-hop; **effective hop is still 1** until implemented. |
| `prioritize` | CSV list of preferred neighbor kinds (default **`Method,Dataset,Work`**). Server preserves these kinds first when `neighbor_limit` truncates dense neighborhoods. |

Response (backward compatible: `id`, `type`, `label` on nodes and `source`, `target`, `type` on edges remain; extra fields are optional for older clients):

```json
{
  "work_id": "string",
  "nodes": [
    {
      "id": "string",
      "type": "Work|Method|Dataset|Author|Authorship|Institution|...",
      "label": "string",
      "display_label": "string",
      "subtitle": "string",
      "node_kind": "Work|WorkInternal|WorkExternal|AuthorshipReification|string",
      "properties": { "publication_year": 2016, "doi": "..." }
    }
  ],
  "edges": [
    {
      "id": "e_stablehash",
      "source": "string",
      "target": "string",
      "type": "CITES",
      "display_type": "CITES",
      "source_label": "string",
      "target_label": "string",
      "summary": "Source —[CITES]→ Target",
      "direction": "outgoing|incoming|lateral"
    }
  ],
  "meta": {
    "semantic_available": true,
    "graph_scope": "work_1hop",
    "graph_depth_requested": 1,
    "graph_depth_effective": 1,
    "neighbor_match_count": 42,
    "neighbor_limit_applied": 200,
    "nodes_returned": 15,
    "edges_returned": 28,
    "is_truncated": false,
    "skipped_by_kind": { "Author": 12, "Authorship": 8 },
    "available_expansions": []
  }
}
```

`source` / `target` follow the **Neo4j relationship orientation** (`startNode(rel)` → `source`, `endNode(rel)` → `target`) for the matched hop between the requested work and each neighbor. Incoming vs outgoing edges therefore differ by which endpoint is the work id.

Degraded mode:

- if semantic extraction missing, return backbone-only neighborhood and `semantic_available=false`.

### UI route `/graph` (client-only query flags)

The standalone graph page is implemented in [`ui/src/pages/GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx). Query parameters (in addition to traceability fields from [`traceabilityState.js`](../../ui/src/components/work/traceabilityState.js), e.g. `node`, `edge`, chunk/section/citation context):

| Query | Meaning |
|-------|---------|
| `work_id` | Required to load a graph; persisted client-side when set. |
| `lab=1` | Graph Lab: diagnostics JSON expanded by default. |
| `compact=1` | Denser standalone layout: compact panel defaults (e.g. Graph/canvas mode), collapsed chrome-friendly defaults. |
| `focus=1` | **Max canvas:** implies compact panel behavior and starts with page chrome collapsed, workspace links collapsed, and panel secondary blocks (title block, legend, alerts, details) hidden until the user expands them. Preserved on **Load** with `compact` / `lab`. |

Implementation helpers: [`ui/src/pages/graphPageUrl.js`](../../ui/src/pages/graphPageUrl.js).

**Client-only layout (not in URL):** The standalone graph/detail **split width** is stored in `localStorage` under key `graphStandaloneDetailMinPx` (pixel width of the detail column track, clamped **260–480**). The toolbar slider and the **`md+` drag gutter** between graph and detail update the same value; see [`graphDetailColumnWidth.js`](../../ui/src/components/graph/graphDetailColumnWidth.js) and *Wave 7* in [`graph-ui-plan.md`](./graph-ui-plan.md). No backend or URL contract.

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

## 5b) Workspace graph v2 (implemented)

### `GET /v1/workspaces/{workspace_id}/graph`

Query params:

| Param | Default | Notes |
|-------|---------|--------|
| `mode` | `inner_only` | `inner_only` \| `union_1hop` \| `semantic_layer` \| `full` |
| `depth` | `1` | `1` or `2` (capped server-side) |
| `include_external` | `false` | When `true`, may include cited `:Work` nodes outside the workspace |
| `node_types` | *(all)* | Comma-separated: `Work`, `Author`, `Method`, `Dataset`, `Venue`, `Institution`, `Authorship` |
| `prioritize` | `Method,Dataset,Work` | CSV list of preferred kinds for truncation-aware neighbor selection. |
| `neighbor_limit` | `200` | Clamped with global cap (300 for multi-hop) |
| `external_min_internal_citers` | `0` | When &gt; 0 and `include_external=true`, keep external works only if at least N distinct internal works cite them |

Response matches work graph shape (`work_id`, `nodes`, `edges`, `meta`). Each node may include:

- `workspace_membership`: `internal` \| `external` (for `:Work`, membership in the workspace collection; for other labels, adjacency to internal works).
- `internal_cite_count` / `external_cite_count` on `:Work` (outgoing `CITES` targets split by membership).

**`mode=full`:** same hop depth as `inner_only` / depth-2 paths, but **ignores** the `node_types` query filter so every 1-hop (or 2-hop) neighbor label reachable from internal `:Work` nodes is eligible (still respects `include_external` for non-member `:Work` nodes). Use when you need Methods/Datasets/Authors even after narrowing `node_types` in the UI.

`meta.graph_scope` is `workspace_v2` (or `workspace_union_1hop` inside legacy union mode until merged into v2 meta). `meta` also includes `gds_runtime_available`, `gds_used`, `cap_applied`, `source_work_ids`, `internal_node_count`, `external_node_count`.

### `GET /v1/workspaces/{workspace_id}/graph/stats`

Lightweight counts: `works_count`, `authors_count`, `internal_citations`, `external_citations`, `external_works_count`.

### `GET /v1/workspaces/{workspace_id}/graph/neighbors`

Query: `node_id` (required), `depth` (1–2), `limit` (1–200). Returns a subgraph slice for lazy UI merge.
Optional: `prioritize=Method,Dataset,Work` (same semantics as workspace root graph endpoint).

Implementation: [`science_graphrag/api/workspace_graph.py`](../../science_graphrag/api/workspace_graph.py), routes in [`science_graphrag/api/workspaces.py`](../../science_graphrag/api/workspaces.py). ADR: [`docs/adr/012-workspace-graph-projection.md`](../adr/012-workspace-graph-projection.md).

## 6) Benchmark console API (implemented, layer-1 + layer-2 + graph catalog)

Назначение: страница **`/benchmark`** в `ui/` — просмотр кейсов и запуск прогонов **без обязательного CLI**, по идее как dev/QA-консоль в референсе [osint-gr](/home/roman/pyprojects/ML/Prod/osint-gr) (`frontend/src/pages/BenchmarkPage/` и связанные сервисы). Фикстуры: `tests/fixtures/benchmarks/layer1/` и `tests/fixtures/benchmarks/layer2/`; полный suite и decision gate остаются в [eval/README.md](../../eval/README.md) и [runbooks/benchmark-decision-gate.md](../runbooks/benchmark-decision-gate.md).

| Method | Path | Role |
|--------|------|------|
| GET | `/v1/benchmark/cases` | Список кейсов (`family=layer1\|layer2\|graph`, `tier`, `q`, `limit`, `offset`). Для `graph` — только layer-1 кейсы, у которых в `gold.json` есть `graph_expectations` (каталог для UI, без запуска Neo4j из API). |
| GET | `/v1/benchmark/models` | Каталог model presets для UI launcher: `profile_id`, `label`, `role`, `model_id`, `family_support`, `default_gold_source`, `default_threshold_profile`. |
| GET | `/v1/benchmark/decision-gate-summary` | **BT1 read-only:** срез из `eval/results/benchmark-metrics-summary.json` — `decision`, `reason`, `criteria` (включая `advisory_phantom_*`, `hard_block_individual_failures`), `trust_by_family` (per-member `trust_signal` без сырых `cases`). **404** `benchmark_metrics_summary_not_found` если файл не сгенерирован. Реализация: `science_graphrag/api/benchmark_decision_gate.py`. Клиент: `fetchDecisionGateSummary` в `ui/src/services/benchmarkApi.js`. |
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
- `Graph`: `GET /v1/works/{work_id}/graph` or workspace mode `GET /v1/workspaces/{workspace_id}/graph` (§5b)
- `Ask`: `POST /v1/query`
- `Evidence`: query citations + chunks lookup by `chunk_fingerprint`
- `Benchmarks`: `/v1/benchmark/*` (см. §6)
