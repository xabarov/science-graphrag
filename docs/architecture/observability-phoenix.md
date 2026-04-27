# Phoenix Observability Contract

## Span naming

- Root ingest span: `ingest_document`
- Stage spans: `ingest.<stage>`
- Substep spans inside stage: `ingest.<stage>.<substep>`
- Fallback spans: `ingest.<stage>.fallback.<reason>`
- LLM spans: `llm.<call_name>`
- API-level ingest root (job envelope): `api.ingest_job`

### Agent chat (`POST /v2/agent/query`)

- Root per user turn: `agent.query` (CHAIN)
- Turn policy / routing: `agent.turn_policy` (CHAIN), optional child `llm.agent.turn_policy` (LLM)
- Supervisor routing: `agent.supervisor.route` (CHAIN), optional child `llm.agent.supervisor_route` (LLM)
- Specialist subgraphs (optional): `agent.specialist.<name>` (CHAIN), e.g. `retrieval`, `graph`, `writer`
- Finalize / summary: `agent.finalize` (CHAIN) — short output summary only (no full answer text)
- Domain tools: `tool.<tool_name>` (TOOL), e.g. `tool.idea_search`, `tool.workspace_list_papers`
- Query embedding inside tools: `embedding.agent.<tool_name>` (EMBEDDING)
- Vector search (Qdrant hits): `retrieval.qdrant.<tool_name>` (RETRIEVER)
- Specialist ReAct LLM calls: `llm.agent.retrieval_specialist`, `llm.agent.graph_specialist` (LLM)
- Writer LLM: `llm.agent.writer` (LLM)

**Scope:** `PHOENIX_TRACE_SCOPE=full` records everything. `extraction_llm` records allowlisted ingest CHAIN/LLM spans **and** product-agent spans whose names start with `agent.`, `llm.agent.`, or `retrieval.qdrant.` (see `science_graphrag/observability/spans/decorators.py`), so `/v2/agent/query` can still emit a non-empty `phoenix_trace_id` while noisy non-agent spans stay suppressed. The live eval harness may still force `full` for historical harness parity; regression coverage lives in `tests/observability/test_extraction_llm_scope.py`.

### Verification order (research chat + Benchmark Lab)

When validating chat traceability after changes:

1. **Runtime:** padded tool names still execute (`tests/agent/test_tool_call_normalization.py`).
2. **Traceability:** with `PHOENIX_TRACE_SCOPE=extraction_llm`, `chain_span("agent.query")` is recorded (same test module as above + `test_extraction_llm_scope`).
3. **UI:** Inspect run — set `VITE_PHOENIX_UI_BASE_URL` and **`VITE_PHOENIX_PROJECT_ID`** (Phoenix UI project id / GlobalID, e.g. from the browser URL) for a working “Open in Phoenix” link; otherwise the UI shows a trace id hint only.
4. **Docs:** keep analysis docs aligned with this contract (`docs/analysis/benchmark-panel-research-redesign-plan-2026-04-27.md` shared path).

## Manual vs automatic instrumentation (LangChain / LangGraph)

- **Automatic:** `LangChainInstrumentor` (via `science_graphrag.observability.init.init_tracer_provider`) attaches spans around LangChain / LangGraph runnable invocations. Keep it enabled so framework-level visibility stays available.
- **Manual (contract):** `chain_span("agent.query", …)`, `llm_span("llm.agent.*", …)`, `run_tool_result_with_span` / `retriever_span` / `embeddings_span` implement the **named** OpenInference contract used in CI (`tests/observability/`) and in product docs above.
- **Policy:** Prefer manual spans for anything that gates quality or must match `tool_trace` / roadmap observability checks. If OpenAI auto-instrumentation duplicates LLM children, set `PHOENIX_OPENAI_AUTO_INSTRUMENTATION=0` rather than removing `llm_span` blindly.
- **Context propagation:** Any `ThreadPoolExecutor` / `asyncio.to_thread` boundary must attach the parent OTel context (see `agent/graph/invoke_timeout.py`, `api/agent_v2.py` sync-stream fallback) so Phoenix shows a **single** trace tree.

## Live Phoenix 13.x (eval / UI)

- REST: `GET /v1/projects/{project_identifier}/spans?trace_id=…` and/or `GET /v1/projects/{project_identifier}/traces?include_spans=true` (see `eval/chat_agent/phoenix_export.py`).
- Project id: `PHOENIX_PROJECT_ID` or `PHOENIX_PROJECT_NAME` (default **`science-graphrag`**, aligned with `init_tracer_provider`).
- UI deep link: `/projects/{project}/traces/{traceId}` with `PHOENIX_UI_BASE_URL` (eval harness) / `VITE_PHOENIX_UI_BASE_URL` + **`VITE_PHOENIX_PROJECT_ID`** (web UI). Do not assume the OTLP project **name** (`science-graphrag`) is a valid Phoenix UI route segment; many installs need the UI’s **project id** (GlobalID from the URL). Without `VITE_PHOENIX_PROJECT_ID`, the product UI intentionally avoids a broken deep link and shows a trace id hint instead.

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

### LLM runtime policy (timeouts, pools, contracts)

Production LLM spans SHOULD include the following **runtime policy** attributes (Phase 0 truthfulness; see `docs/analysis/llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md` §Phase 0):

| Attribute | Meaning |
|-----------|---------|
| `llm.pool_name` | Logical concurrency pool / traffic class (e.g. `metadata`, `references`, `claims`, `semantic`, `dedup`, `agent_classifier`, `agent_chat`, `query_answer`, `idea_assist`, `vl_pdf`). Present even before real semaphore wiring. |
| `llm.transport_timeout_seconds` | Per-request HTTP / client timeout for a single provider call. |
| `llm.operation_deadline_seconds` | Wall-clock budget for the whole logical step when enforced (ingestion ``run_extraction``, shared claims fallback, semantic bundle, etc.). Omit if N/A. |
| `llm.response_deadline_seconds` | User-visible wait cap that may return without cancelling upstream work (agent graph invoke / SSE). Omit on pure ingestion LLM calls. |
| `llm.retry_budget` | Extra attempts allowed by the **caller-owned** outer retry loop (e.g. `run_extraction(retries=…)`), not inner transport retries inside `SyncInstructorExtractor`. |
| `llm.transport_max_attempts` | Optional: max inner HTTP attempts in ``SyncInstructorExtractor.extract_maybe``, or max attempts for a dedicated HTTP helper (e.g. VL `post_chat_completions_json`). |
| `llm.timeout_contract` | One of: `transport_only`, `transport_with_operation_deadline`, `transport_plus_deadline` (legacy alias), `response_deadline_only`, `unknown`. |
| `llm.per_attempt_transport_timeout_seconds` | Optional: enforced HTTP timeout for the current attempt (may be below `llm.transport_timeout_seconds` when an operation deadline caps remaining time). |

**Semantics:**

- **Transport timeout** bounds a single outbound request; retries can still extend wall time unless an operation deadline exists.
- **Response deadline** (`response_deadline_only`): the API stops waiting for the user turn; the LangGraph worker thread or provider may still run (see `science_graphrag/agent/graph/invoke_timeout.py` and `docs/runbooks/agent-chat-v2.md`). This is **not** full cancellation.

Ingest spans may keep legacy `extraction.timeout_seconds`; it MUST match the **enforced** per-attempt HTTP timeout for that span (same numeric value as `llm.per_attempt_transport_timeout_seconds` when present; may be lower than configured `llm.transport_timeout_seconds` under an active operation deadline).

### DB/HTTP spans

- OpenAlex lookup: `http.request.method`, `http.url`, `openalex.doi`, `openalex.found`
- Qdrant upsert: `db.system=qdrant`, `db.collection.name`, `db.operation=upsert`, `vector.dim`, `vector.count`
- Neo4j writes: `db.system=neo4j`, `db.operation`, `writes.count`

### Embedding spans

- `openinference.span.kind=EMBEDDING`
- `embedding.model_name`
- `embedding.dim`
- `embedding.input_count`

### Agent root (`agent.query`)

- `openinference.span.kind` = CHAIN
- `session.id` = `thread_id` when present; otherwise optional `metadata.request_id` for grouping
- `user.id` = `workspace_id` (may be empty)
- `agent.runtime`, `agent.max_tool_calls`, optional `agent.answer_class_hint`
- `agent.response_deadline_seconds` — wall-clock cap for returning a response for one turn (`Settings.agent_step_timeout_seconds`); **does not** guarantee upstream LLM/tool cancellation (`agent.response_deadline_enforces_upstream_cancel=false`).
- `input.value` — truncated user question (no full history blobs)
- Root **output** (after run): JSON summary only — `answer_class`, `tool_call_count`, `warning_codes`, `citation_count`, `budget_exhausted` — via `output.value` / safe JSON helper

### Agent TOOL spans (`tool.<name>`)

- `openinference.span.kind` = TOOL
- `tool.name`, `tool.parameters` (truncated JSON)
- Optional `tool.step` when aligned with `ToolCallTrace.step`
- `input.value` / `output.value` — truncated previews; include `row_count`, `truncated`, `error` semantics in output dict

### Agent RETRIEVER spans (`retrieval.qdrant.<tool>`)

- `openinference.span.kind` = RETRIEVER
- `db.system=qdrant`, `db.collection.name`, `retrieval.top_k`
- `metadata.workspace_id`, optional `metadata.work_id`
- `retrieval.documents.{i}.document.id`, `.document.score`, `.document.content` (snippet), metadata for `work_id` / chunk id as applicable

### Agent LLM spans (`llm.agent.*`)

Same LLM contract as ingest: `llm.model_name`, `llm.provider`, `llm.token_count.*`. **Do not** attach `llm.*` token attributes to parent CHAIN spans.

## API correlation

- `ingest_jobs.phoenix_trace_id` stores 32-char hex trace id.
- `GET /v1/ingest/jobs/{id}` returns `phoenix_trace_id`.
- UI can build deep-link to Phoenix trace from this id.

Agent chat: `AgentRunOutput.phoenix_trace_id` / API response includes the same 32-char hex for `POST /v2/agent/query` when tracing is active.

Chat-agent roadmap `--fetch-phoenix` compares span **names** to `tool_trace` only when the HTTP snapshot is **valid JSON** (not an HTML shell). If Phoenix is unreachable or returns a legacy SPA page, `observability_match_reliable` is false and `require_observability_match` does not fail the case.
