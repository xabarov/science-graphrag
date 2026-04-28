# Frontend UI API contracts v1 (Phase 6 MVP)

## Scope

This document defines the minimum backend contracts required to move frontend from mock-driven shell to live data integration.

Status by endpoint:

- `POST /v1/query`: implemented (source of truth in `science_graphrag/api/main.py`)
- `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks`, `GET /v1/works/{work_id}/extracted-body`: implemented (same module; Neo4j + Qdrant + ingest artifacts under `artifact_root`)
- **`/v1/benchmark/*`:** benchmark console UI (`science_graphrag/api/benchmark.py`, runs via `science_graphrag/api/task_store.py`) — **layer-1** и **layer-2** (`family` query/body); не часть обязательного research happy-path ниже. Если задан `SCIENCE_GRAPHRAG_ADMIN_API_KEY`, клиент должен слать заголовок **`X-Admin-Key`** (см. [admin-policy.md](./admin-policy.md)).
- other niceties below: optional backlog (filters, richer graph projection)

## Mandatory API happy-path (Wave C)

Один обязательный сквозной сценарий для Phase 5/6 bridge и пилота (после ingest хотя бы одной работы в Neo4j/Qdrant):

1. **Ingest** одного документа: `science-graphrag ingest path/to/paper.pdf` (или корпус — см. [runbooks/deploy.md](../runbooks/deploy.md)).
2. **`GET /v1/works`** — список не пустой, выбрать `work_id`.
3. **`GET /v1/works/{work_id}`** — 200, стабильные поля `work_id`, `ingestion` (в т.ч. `has_extracted_body`, `work_provenance`; см. §3).
4. **`POST /v1/query`** — ответ с `citations` и `retrieval_trace` (допустимы пустые hits при пустом Qdrant, но не 5xx).
5. **`GET /v1/works/{work_id}/chunks`** — при наличии чанков: ненулевой `total` или согласованный degraded UX в UI.
6. **`GET /v1/works/{work_id}/extracted-body`** — при успешном ingest: тело текста из артефактов (`normalized.md` / `article.md`) даже если Qdrant пуст (см. ADR 022).

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

When **`workspace_id` is set** and **`work_id` is omitted**, retrieval first filters Qdrant vector search by payload `workspace_ids` containing that workspace id. Unknown workspace → HTTP 200 with empty hits and `retrieval_trace.workspace_missing: true`. **`work_id` wins** when both are provided (single-paper scope). For workspace-scoped calls, the request `workspace_id` is echoed on `retrieval_trace.workspace_id` together with `workspace_scope_work_count` (and `workspace_missing` when the workspace is unknown). Neo4j workspaces marked **unbounded** (full-corpus scope, e.g. benchmark `corpus_work_ids: "*"`) set `retrieval_trace.workspace_unbounded: true` and use `workspace_scope_work_count: 0` while still filtering Qdrant by `workspace_ids` after `scripts/backfill_workspace_payloads.py` has tagged all chunk points. If the payload-filtered search returns **no hits** but Neo4j still lists member works, the API performs **one retry** using `work_id IN (workspace members)` and sets `retrieval_trace.workspace_scope_payload_miss = "work_ids_payload"` (log warning) — run `scripts/backfill_workspace_payloads.py` if this appears after ingest migrations.

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
    "has_semantic_layer": true,
    "has_extracted_body": true,
    "extracted_body_bytes": 120000,
    "work_provenance": "ingested_document | graph_stub"
  }
}
```

- **`document_id`**: Postgres `documents.id` when this work is linked to an ingested file; otherwise `null` (graph-only / citation stub).
- **`has_extracted_body`**: `true` when `artifact_root/ingestion/{document_id}/normalized.md` or `article.md` (or legacy slug path) exists on the API host.
- **`work_provenance`**: `ingested_document` if a document row exists; `graph_stub` if the work exists only in Neo4j without a linked ingest document.

### `GET /v1/works/{work_id}/extracted-body`

Returns JSON (not raw `text/markdown` stream in v1):

| Field | Meaning |
|-------|---------|
| `available` | Whether readable body text was found |
| `reason` | When `available` is false: `no_ingested_document` (no SQL document) or `no_extracted_body` (document exists but no artifact files) |
| `text` | Full extracted markdown/text (may be truncated) |
| `source` | `normalized` \| `article` \| `article_legacy` — which file was read |
| `truncated` | `true` if response hit the server character cap (~1.5M) |
| `file_bytes` | On-disk file size when `available` |

### `GET /v1/works/{work_id}/sources` and `GET /v1/works/{work_id}/pdf`

- **`/sources`:** JSON inventory (`pdf`, `markdown` availability) for Reader UI. The `markdown` entry’s **`available`** reflects **on-disk ingest artifacts** (canonical paths under `ingestion/{document_id}/`), not Qdrant chunk count. Optional field **`indexed_chunks`** (integer) reports how many chunk points exist in Qdrant for observability.
- **`/pdf`:** Streams `application/pdf` from the blob store (`StreamingResponse`). Supports **`Range: bytes=…`** → **206 Partial Content** with `Content-Range` and `Content-Length` for the slice; full file → **200** with `Content-Length`. **`ETag`** + `Accept-Ranges: bytes`; **`If-None-Match`** → **304**. Malformed or unsatisfiable range → **416** with `Content-Range: bytes */{size}`.

## 4) Work graph neighborhood (implemented)

### `GET /v1/works/{work_id}/graph`

**Authorship / reader vs raw:** In **`view=reader`** (default), the API **collapses** `:Authorship` reification into reader-facing **`AUTHORED`** edges from the center `Work` to **`Author`** nodes (native ids when linked in Neo4j, otherwise stable synthetic ids with prefix **`va:`**). In **`view=raw`**, topology keeps **`HAS_AUTHORSHIP`** / `:Authorship` as returned from the neighborhood scan; **`author_entity_id`** is **not** exposed on `Authorship.properties` in raw (enrichment is stripped after use). Full rationale and history: [`docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md). Maintainer-oriented pipeline summary: [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md).

Optional query (server contract):

| Query | Meaning |
|-------|---------|
| `neighbor_limit` | Integer **1–2000** (default **200**). Caps rows from the 1-hop `MATCH (w)-[r]-(n)` scan. |
| `depth` | Integer **1–3** (default **1**). Reserved for future multi-hop; **effective hop is still 1** until implemented. |
| `prioritize` | CSV list of preferred neighbor kinds (default **`Method,Dataset,Work`**). Server preserves these kinds first when `neighbor_limit` truncates dense neighborhoods. |
| `view` | **`reader`** (default) or **`raw`**. Reader applies authorship collapse only; raw keeps graph-shaped authorship. **Server-side neighbor aggregation (GR8) is off** (2026-04-28): no `Aggregator` nodes in normal responses. |
| `include_claims` | Boolean (default **false**). When true, merges a capped slice of `Claim` nodes linked from the center work (`claims_limit` caps the claim query). |
| `claims_limit` | Integer **1–120** (default **24**). Used only when `include_claims=true`. |
| `aggregator_threshold` | **Ignored** (accepted for API compatibility; neighbor aggregation disabled). |
| `aggregator_disabled_kinds` | **Ignored** (accepted for API compatibility). |
| `include_authorship_debug` | Boolean (default **false**). When **true** and `view=reader`, response **`meta.authorship_projection`** is set to one of **`native`**, **`synthesized`**, **`mixed`**, **`none`** — classifies post-collapse `AUTHORED` targets from the center (no PII). See [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md). |
| `workspace_id` | Optional string (Phase 2, 2026-04-28). When set, the center work must be **`CONTAINS`**-ed by that workspace; response nodes get **`workspace_membership`** / cite split fields using the same rules as workspace graph projection. **`404`** `workspace_not_found` if the workspace does not exist; **`422`** `work_not_in_workspace` if the work is not in the collection. **`meta.graph_mode`** is **`work_workspace_context`** (still capped neighborhood, not union). |
| `include_institutions` | Boolean (default **false**, Phase 3). When **true**, attaches **`Institution`** nodes for affiliations linked from the center work’s **Authorship** rows in Neo4j (capped per request). **`view=reader`:** after authorship collapse, edges are **`Author–AFFILIATED_WITH–Institution`** (reader projection; Neo4j may only store `Authorship–Institution`). **`view=raw`:** **`Authorship–AFFILIATED_WITH–Institution`** after reader-only property strip. See **`meta.include_institutions`**, **`meta.reader_extra_hops`**, **`meta.institutions`**. |

**`meta.neighbor_aggregation`:** always **`none`** on work graph and workspace graph root payloads (2026-04-28). Dense neighborhoods are only limited by **`neighbor_limit`** / fetch ordering, not by `Aggregator` substitution.

**Reader graph `meta` contract (Phase 0–4):** Responses include **`meta.graph_contract_version`** (integer, currently **`4`** — bumped 2026-04-28 when workspace **`view=reader`** payloads adopted the same server-side authorship collapse as the work graph). Bump it when neighbor caps, membership annotation rules, reader authorship collapse semantics, workspace reader shape, or optional institution hop behavior change in a contract-visible way.

**`meta.graph_mode`** (product-facing): derived from `graph_scope` / workspace `mode`, or overridden explicitly: **`work_capped`** (standalone neighborhood), **`work_workspace_context`** (neighborhood + optional `workspace_id` membership pass), **`workspace_union`**, **`workspace_v2`**, **`workspace_neighbors`**, plus expand-only **`work_expand_aggregator`** / **`workspace_expand_aggregator`**.

Always present on root graph responses: **`neighbor_limit`** (requested int on work graph; **`null`** on workspace root — full 1-hop union per ADR-012), **`neighbor_limit_applied`**, **`prioritize`**, **`view`**, **`is_truncated`**, **`workspace_id`** (normalized query value when provided, else **`null`**).

### `GET /v1/works/{work_id}/graph/expand`

**Status:** Legacy endpoint. Main graph responses no longer include **`Aggregator`** nodes (aggregation disabled 2026-04-28); clients should not rely on this path for normal navigation. It remains for backward compatibility and tests.

| Query | Meaning |
|-------|---------|
| `aggregator_id` | **Required** when calling. Opaque id (historically from `aggregation_hints` / `expand_endpoint`). |
| `limit` | Integer **1–300** (default **50**). Caps how many neighbor nodes are returned for that bucket. |
| `workspace_id` | Optional (Phase 2). Same validation and membership annotation as **`GET .../graph`** when expanding from a workspace-scoped work graph; echoed in **`meta.workspace_id`**. **`meta.graph_mode`** stays **`work_expand_aggregator`**. |
| `include_institutions` | Optional boolean (Phase 3). Same semantics as **`GET .../graph`** — forwarded to the underlying neighborhood rebuild. |

**Behavior:** Recomputes an enlarged neighborhood and filters edges matching the parsed **`aggregator_id`** bucket. **Author** buckets (**`AUTHORED`** in reader mode) still use an internal **`view=reader`** re-fetch path inside `expand_work_aggregator` (implementation detail).

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
    "graph_contract_version": 4,
    "graph_mode": "work_capped",
    "semantic_available": true,
    "graph_scope": "work_1hop",
    "graph_depth_requested": 1,
    "graph_depth_effective": 1,
    "neighbor_match_count": 42,
    "neighbor_limit": 200,
    "neighbor_limit_applied": 200,
    "prioritize": "Method,Dataset,Work",
    "view": "reader",
    "workspace_id": null,
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
| `work_id` | When set, loads **capped** work neighborhood via **`GET /v1/works/{work_id}/graph`** (not the workspace union). Persisted client-side when set. |
| `workspace_id` | Optional. When **`work_id`** is set, passed to the work graph API for **`workspace_membership`** on neighbor works. When **`work_id`** is omitted, the page loads **`GET /v1/workspaces/{workspace_id}/graph`** (full union). |
| `lab=1` | Graph Lab: diagnostics JSON expanded by default. |
| `compact=1` | Denser standalone layout: compact panel defaults (e.g. Graph/canvas mode), collapsed chrome-friendly defaults. |
| `focus=1` | **Max canvas:** implies compact panel behavior and starts with page chrome collapsed, workspace links collapsed, and panel secondary blocks (title block, legend, alerts, details) hidden until the user expands them. Preserved on **Load** with `compact` / `lab`. |

Implementation helpers: [`ui/src/routing/graphPageQuery.js`](../../ui/src/routing/graphPageQuery.js).

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
| `include_external` | `false` | When `true`, may include cited `:Work` nodes outside the workspace |
| `prioritize` | `Method,Dataset,Work` | CSV list of preferred kinds (ordering / display hints where applicable). |
| `external_min_internal_citers` | `0` | When &gt; 0 and `include_external=true`, keep external works only if at least N distinct internal works cite them |
| `view` | `reader` | `reader` \| `raw` |
| `include_claims` | `false` | Optional claim slice; `claims_per_work` / `claims_max_total` omit for uncapped |
| `include_authorship_debug` | `false` | When **true** and `view=reader`, **`meta.authorship_projection`** ∈ {`native`,`synthesized`,`mixed`,`none`} classifies **all** `AUTHORED` edge targets in the payload (workspace-wide; same helper family as work graph). |

**Removed (2026-04-27):** `depth`, `neighbor_limit`, `node_types` — the server always returns the **full union of 1-hop** incident edges for every internal work in the workspace (see ADR 012 addendum). **Node-type visibility** is **client-only** (`graphVisibilityFilter`).

**Workspace reader (Phase 4):** For `view=reader`, the server applies **`collapse_authorship_for_reader_multicenter`** after `enrich_authorship_nodes` and before edge display enrichment — same GR9 contract as `GET /v1/works/{id}/graph`: **no `:Authorship` nodes** in the JSON; **`Work–AUTHORED–Author`** with `via` metadata; **`Authorship–AFFILIATED_WITH–Institution`** rewritten to **`Author–AFFILIATED_WITH–Institution`** when institutions are present. **`view=raw`** keeps authorship-shaped nodes and skips collapse.

Response matches work graph shape (`work_id`, `nodes`, `edges`, `meta`). Each node may include:

**When is `workspace_membership` present?**

| API | Present? | Notes |
|-----|------------|--------|
| `GET /v1/workspaces/{workspace_id}/graph` | **Yes** (when projection runs) | Set by server membership pass on `Work` and related nodes; values **`internal`** \| **`external`**. |
| `GET /v1/workspaces/{workspace_id}/graph/neighbors` | **Yes** | Same annotation rules for the lazy neighbor slice. |
| `GET /v1/works/{work_id}/graph` | **Yes** iff query **`workspace_id`** is set and valid (center work ∈ workspace) | Same **`internal`** / **`external`** rules as workspace projection (`annotate_membership_and_cites`). Without **`workspace_id`**, omit membership fields — UI must not treat missing membership as “internal”. |

- `workspace_membership`: `internal` \| `external` (for `:Work`, membership in the workspace collection; for other labels, adjacency to internal works).
- `internal_cite_count` / `external_cite_count` on `:Work` (outgoing `CITES` targets split by membership).

**`:Method` node `properties` (ADR 023, when present on Neo4j):** `aliases`, `description_short`, `description_markdown`, `description_plaintext`, `method_kind`, `description_source`, `description_confidence` — surfaced for the graph inspector; rich Markdown is rendered client-side (`GraphDetailPanel` + `MarkdownViewCore`).

**`mode=full`:** full semantic adjacency from internal works (same **1-hop union** engine as other modes, with semantic edge filter disabled); still respects `include_external` / `external_min_internal_citers`.

`meta.graph_scope` is `workspace_v2` (or `workspace_union_1hop` inside legacy union mode until merged into v2 meta). `meta` may include projection diagnostics (`gds_runtime_available`, `gds_used`, `cap_applied`, `source_work_ids`, `internal_node_count`, `external_node_count`) where relevant; **`gds_used`** is not used for the main workspace canvas path after 2026-04-27.

Workspace root graph **`meta`** also includes the same Phase 0 keys as work graph: **`graph_contract_version`**, **`graph_mode`** (typically **`workspace_v2`** or **`workspace_union`** when `mode=union_1hop`), **`neighbor_limit`: `null`**, **`neighbor_limit_applied`: `null`**, **`prioritize`**, **`view`**, **`workspace_id`** (always the path id), **`is_truncated`**.

### `GET /v1/workspaces/{workspace_id}/graph/stats`

Lightweight counts: `works_count`, `authors_count`, `internal_citations`, `external_citations`, `external_works_count`.

### `GET /v1/workspaces/{workspace_id}/graph/neighbors`

Query: `node_id` (**required**). Returns **all** relationships incident to that node for lazy UI merge (**1 hop**, no `limit` / `depth` query contract).

Optional: `prioritize=Method,Dataset,Work` (same CSV shape as workspace root graph).

Implementation: [`science_graphrag/api/workspace_graph/router.py`](../../science_graphrag/api/workspace_graph/router.py) (included from [`science_graphrag/api/main.py`](../../science_graphrag/api/main.py)). ADR: [`docs/adr/012-workspace-graph-projection.md`](../adr/012-workspace-graph-projection.md) + addendum (2026-04-27).

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
- `Graph`: capped neighborhood `GET /v1/works/{work_id}/graph` (optional `workspace_id` for membership, §4); full union `GET /v1/workspaces/{workspace_id}/graph` when no work scope (§5b)
- `Ask`: `POST /v1/query`
- `Evidence`: query citations + chunks lookup by `chunk_fingerprint`
- `Benchmarks`: `/v1/benchmark/*` (см. §6)

## Ingest job view (WX2-BE)

`GET /v1/ingest/jobs/{job_id}` (`IngestJobView`) дополнительно к `progress_current` / `progress_total` может содержать:

- **`progress_pct`**: `float | null` (0..1) — взвешенный прогресс по стадиям (running = 0.5 веса), чтобы UI рисовал общий бар без «рваных» процентов.
- **`stages[i].expected_duration_ms`**: `int | null` — средняя длительность стадии по последним успешным jobs (Postgres), подсказка для ETA на фронте.
