# Frontend UI API contracts v1 (Phase 6 MVP)

## Scope

This document defines the minimum backend contracts required to move frontend from mock-driven shell to live data integration.

Status by endpoint:

- `POST /v1/query`: implemented (source of truth in `science_graphrag/api/main.py`)
- `GET /v1/works`, `GET /v1/works/{work_id}`, `GET /v1/works/{work_id}/graph`, `GET /v1/works/{work_id}/chunks`: implemented (same module; Neo4j + Qdrant)
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
    "error": "optional string"
  },
  "retrieval_trace": {
    "embedding": {
      "embedding_model": "string",
      "vector_dim": 0
    },
    "hit_count": 0,
    "filter_work_id": "string | null",
    "resolved_work_id": "string | null"
  }
}
```

Degraded mode expectations:

- no retrieval hits -> answer explains empty retrieval; citations empty;
- Neo4j unavailable -> `graph_context.error = "neo4j_unavailable"`; methods/datasets empty.

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

## Mapping to UI surfaces

- `Workspace`: `GET /v1/works`
- `Reader`: `GET /v1/works/{work_id}` + `GET /v1/works/{work_id}/chunks`
- `Graph`: `GET /v1/works/{work_id}/graph`
- `Ask`: `POST /v1/query`
- `Evidence`: query citations + chunks lookup by `chunk_fingerprint`
