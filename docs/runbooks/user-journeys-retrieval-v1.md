# User journeys — retrieval and grounded answers (Phase 5)

Operational companion to [roadmap Phase 5](../roadmap.md). Each journey should be reproducible with a **fixed corpus** and produce a **non-empty `retrieval_trace`** (and citations when Qdrant has chunks).

## Preconditions

- Stack: `docker compose up -d` ([deploy.md](deploy.md)).
- At least one ingested work with chunks in Qdrant and a row in Neo4j `Work`.
- Optional: `SCIENCE_GRAPHRAG_QUERY_ANSWER_LLM_ENABLED=true` with LLM credentials for second-stage paraphrase ([`.env.example`](../../.env.example)).

## Journey 1 — Browse corpus, pick a work, ask inside scope

1. `GET /v1/works?limit=20` (optional `q`, `year_min`, `year_max`, `has_semantic`).
2. Choose `work_id` from the list.
3. `POST /v1/query` with `{ "query": "<plain question about the paper>", "work_id": "<id>", "top_k": 5 }`.
4. Verify: `citations[].chunk_fingerprint` or `document_id` present when chunks exist; `retrieval_trace.hit_count` ≥ 0; `retrieval_trace.answer_synthesis` describes deterministic vs LLM second stage.

## Journey 2 — Open reader evidence path

1. `GET /v1/works/{work_id}` — confirm title and ingestion flags.
2. `GET /v1/works/{work_id}/chunks?limit=10` — confirm chunk text aligns with citation excerpts from Journey 1.
3. `GET /v1/works/{work_id}/graph` — confirm `semantic_available` matches expectations after semantic ingest.

## Journey 3 — Cross-work discovery (no work filter)

1. `POST /v1/query` with `work_id: null` and a broad factual question that should hit multiple papers in the pilot corpus.
2. Verify: `retrieval_trace.resolved_work_id` populated when hits agree on a dominant work; citations span expected works.

## Journey 4 — Pilot automation hooks

1. `BASE=http://127.0.0.1:8787 ./scripts/pilot_spot_check.sh` — structural citation checks.
2. `BASE=… N=40 ./scripts/pilot_measure_latency.sh` — latency snapshot for `/v1/query` and `/v1/works`.

## Journey 5 — Ask sessions (server-side, optional)

1. `POST /v1/ask-sessions` `{ "scope": "standalone", "title": "Pilot notes" }`.
2. `PATCH /v1/ask-sessions/{id}?scope=standalone` with `{ "turns": [ { "query": "…", "answer": "…" } ], "active": true }`.
3. `GET /v1/ask-sessions?scope=standalone` — list persisted sessions (file-backed under `data/ask_sessions/` on the API host).

## Trace checklist (for sign-off)

| Field | Expected |
|-------|----------|
| `retrieval_trace.embedding.embedding_model` | Stable label (hash or sentence-transformers name). |
| `retrieval_trace.retrieval_policy` | Present (section boost policy string). |
| `retrieval_trace.answer_synthesis.second_stage_llm` | `true` only when second stage succeeded; otherwise `false` with optional `second_stage_skipped` / `second_stage_error`. |
| `graph_context.semantic_available` | Consistent with Neo4j Method/Dataset edges for the resolved work. |

---

## Appendix A — Example `retrieval_trace` shapes (Wave F3)

Illustrative JSON only; numeric fields and collection names vary with your `.env` and corpus. Capture **real** traces from your compose-backed API when closing the pilot.

### A.1 Corpus-scoped query (`work_id: null`)

```json
{
  "hit_count": 12,
  "top_hit_scores": [0.82, 0.79, 0.76],
  "query_preview": "What is focal loss used for in object detection?",
  "retrieval_policy": "vector_oversample_section_boost",
  "filter_work_id": null,
  "resolved_work_id": "work_abc123",
  "qdrant_collection": "science_chunks_v1",
  "top_k_requested": 5,
  "citations_returned": 5,
  "embedding": { "embedding_model": "hash-deterministic", "vector_dim": 256 },
  "answer_synthesis": {
    "mode": "deterministic_snippets",
    "second_stage_llm": false,
    "second_stage_skipped": "disabled"
  },
  "degraded": []
}
```

### A.2 Paper-scoped query (`work_id` set)

```json
{
  "hit_count": 6,
  "top_hit_scores": [0.91, 0.88],
  "query_preview": "Summarize the backbone architecture.",
  "retrieval_policy": "vector_oversample_section_boost",
  "filter_work_id": "work_abc123",
  "resolved_work_id": "work_abc123",
  "qdrant_collection": "science_chunks_v1",
  "top_k_requested": 5,
  "citations_returned": 5,
  "embedding": { "embedding_model": "sentence-transformers/all-MiniLM-L6-v2", "vector_dim": 384 },
  "answer_synthesis": {
    "mode": "grounded_llm_paraphrase",
    "second_stage_llm": true,
    "model": "mistralai/mistral-small-3.2-24b-instruct"
  },
  "degraded": []
}
```
