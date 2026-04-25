# Phoenix Observability Contract

## Span naming

- Root ingest span: `ingest_document`
- Stage spans: `ingest.<stage>`
- Substep spans inside stage: `ingest.<stage>.<substep>`
- Fallback spans: `ingest.<stage>.fallback.<reason>`
- LLM spans: `llm.<call_name>`
- API-level ingest root (job envelope): `api.ingest_job`

## Required attributes

### Ingest root (`ingest_document`)

- `session.id` = ingest job id
- `user.id` = workspace id
- `metadata.job_id`
- `metadata.parent_job_id` (if present)
- `metadata.workspace_id`
- `metadata.source_name`
- `metadata.extraction_mode`
- `metadata.embedding_model`
- `metadata.extraction_llm_model`
- `metadata.vl_model`

### LLM spans

Every LLM span must include:

- `llm.model_name`
- `llm.provider` (when resolvable)
- `llm.token_count.prompt`
- `llm.token_count.completion`
- `llm.token_count.total`

If provider usage is missing, estimate token counts via text fallback and set `llm.usage_source=estimated`.

### DB/HTTP spans

- OpenAlex lookup: `http.request.method`, `http.url`, `openalex.doi`, `openalex.found`
- Qdrant upsert: `db.system=qdrant`, `db.collection.name`, `db.operation=upsert`, `vector.dim`, `vector.count`
- Neo4j writes: `db.system=neo4j`, `db.operation`, `writes.count`

### Embedding spans

- `openinference.span.kind=EMBEDDING`
- `embedding.model_name`
- `embedding.dim`
- `embedding.input_count`

## API correlation

- `ingest_jobs.phoenix_trace_id` stores 32-char hex trace id.
- `GET /v1/ingest/jobs/{id}` returns `phoenix_trace_id`.
- UI can build deep-link to Phoenix trace from this id.
