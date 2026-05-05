# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Completed (archive)

Summaries only; details lived in prior revisions / runbooks / ADRs.

| When | Theme |
|------|--------|
| 2026-05-05 | **Wave Next (ingest stability) — partial delivery:** вынесены `ingestion/{orchestrator,progress_store,cache_policy,document_runtime}.py`; batch ingest переведён на orchestrator seam; `claims` path переведён на shared runtime envelope (`ingestion/llm/claims_runtime.py` + обновление `claims/extractor.py`); добавлены регрессионные тесты `tests/ingestion/test_progress_store_and_cache_policy.py` + прогоны `tests/ingestion`, `test_ingest_checkpoint`, `test_ingest_sha_dedup`, `test_full_ingest_integration`. |
| 2026-05-05 | **CLI `config-check` delivered:** `science-graphrag config-check` exists in `science_graphrag/cli/main.py`, prints masked config diagnostics (`SET`/`UNSET` for keys), supports preflights, and is wired in ops docs/rules as the canonical pre-flight gate. |
| 2026-05-05 | **Wave Next+1 (ingest stability completion) — partial:** selective `ingest-resume --stages` (references/claims/embed) + Neo4j outgoing `CITES` prune before refs rebuild; `--no-cache` / `bypass_markdown_cache` plumbed through ingest + WARN-level cache hit logs; citations persistence extracted to `science_graphrag/ingestion/reference_citations.py`; `ingestion/pipeline.py` slim public facade; added `tests/ingestion/test_resume_stages_csv.py`. |
| 2026-05-05 | **Wave Next+1 — quality/completion sweep (references + resume):** `persist_reference_citation` логирует `warning` при падении OpenAlex `fetch_work_by_doi` (продолжение без `openalex_id`); `normalized_title_for_fingerprint` учитывает буквы не только Latin-1 (NFKC+casefold+`isalnum`/`isspace` — кириллица не обнуляется); `resume_document_ingest_stages` при ошибках стадий `references`/`claims` пишет `mark_stage_failed` + commit статуса `failed_retryable`/`failed_terminal` (паритет с веткой embed) через `_persist_resume_stage_failure` / `_resume_failure_retryable`; тесты: `tests/test_citation_persist.py` (кириллица, лог OpenAlex), расширен `tests/ingestion/test_resume_stages_csv.py` (эвристика retryable). |
| 2026-05-05 | **LLM stage extraction split delivered:** former `ingestion/llm/stage_extraction.py` god-module was reduced to a thin compatibility facade; orchestration moved to `ingestion/llm/orchestrator.py`, transport to `ingestion/llm/executor.py`, prompts/heuristics into dedicated modules. |
| 2026-05-04 | **Retire `POST /v1/agent/query`:** route returns **410 Gone** + JSON `replacement: /v2/agent/query` and `Link: </v2/agent/query>; rel="successor-version"` ([`science_graphrag/api/agent.py`](../../science_graphrag/api/agent.py)); smoke tests updated (`tests/test_api_agent_smoke.py`, `tests/test_api_agent_v2_smoke.py`). |
| 2026-04-28 | **Graph work vs workspace DRY (Phases 0–5):** `collapse_authorship_for_reader_multicenter` + workspace pipeline in `workspace_graph/cypher.py`; `GRAPH_CONTRACT_VERSION=4`; workspace `include_authorship_debug`; `Authorship–AFFILIATED_WITH–Institution` → `Author–…` in collapse; UI `projectAuthorSemanticGraph` pass-through; i18n + `work_workspace_context` subtitle; spec §5b. Plan: [`docs/analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](../analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md). |
| 2026-04-26 | **Wave 6 — benchmarks quality closure:** `decision_gate` **GO** with ≤2 design-only phantom families (`merge_safe_contract_mock`, `strict_pilot_mock`); agent LLM `ensure_messages_safe_for_generation` (OpenRouter `add_generation_prompt` fix); `agent_tools` metrics (subsequence match, ignore `route_to_specialist`); multihop_v2 pilot gold thresholds + `current-retrieval-multihop-mini.json` refresh; `eval/results/benchmark-trust-baseline.json` via `scripts/refresh_benchmark_metrics.sh`. Write-up: [`docs/analysis/_archive/wave6-benchmarks-quality-2026-04-26.md`](../analysis/_archive/wave6-benchmarks-quality-2026-04-26.md). |
| 2026-04-26 | **ADR-021 Phase 0 (ops slice):** runbook [`docs/runbooks/phase0-bge-m3-qdrant-cutover.md`](../runbooks/phase0-bge-m3-qdrant-cutover.md); `science-graphrag qdrant-recreate-embedding-collections --dry-run`; `describe_embedding_collections_cutover` / `qdrant_embedding_collection_names` in `recreate_embedding_collections.py`. **Operator:** `qdrant-recreate-embedding-collections` (1024) + **`ingest-corpus` завершён** (`ingest-progress-phase0-bge-m3.jsonl`). Дальше: см. OPEN «Switch Qdrant…» — BT2/BT4/BT5 + baseline. |
| 2026-04-27 | **BT12 — contradictions benchmark in trust rollup:** committed `eval/results/current-contradictions-v1-mini.json` (``python -m eval.contradictions.runner …/contradictions_v1 --suite --materialize`` against a graph with corpus works); `scripts/aggregate_benchmark_metrics.py` + `contradictions_family` / `trust_signal` member `contradictions_v1_mini` (`detect_runtime_mode` → `live`). Ingest-time auto-write of `:CONTRADICTS` remains a separate product decision. |
| 2026-04-27 | **BT8 slice — `agent_tools_judge` artifact:** committed `eval/results/current-agent-tools-judge-pilot.json` (heuristic `science-graphrag-agent-judge-benchmark` over `current-agent-tools-mini.json`); `.github/workflows/integration-nightly.yml` regenerates before aggregate; `benchmark-trust-baseline.json` refreshed (`advisory_phantom_count` −1 vs missing_file). |
| 2026-04-27 | **Wave X3 (Dramatiq OTel — producer inject):** `science_graphrag/worker/trace_options.py` (`propagate.inject` → Dramatiq message `options`); `enqueue_ingest_job` + compensation sweep use `send_with_options` when carrier non-empty; tests `tests/observability/test_worker_trace_propagation.py` (incl. `test_dramatiq_otel_options_injects_traceparent_under_span`). |
| 2026-04-27 | **LX1 (partial — settings only):** `Settings.merge_runtime_env_overrides` mirrors `extraction_llm_references_max_concurrency` ↔ `llm_concurrency_extraction_references`; test `tests/test_llm_concurrency_config.py`. |
| 2026-04-27 | **Phase 2 LLM pools:** `science_graphrag/llm/concurrency.py` (threading gates + `run_extraction(settings=…)`), new `llm_concurrency_*` fields; translation SSE uses cached `get_llm_async_semaphore_map`; tests `tests/llm/test_pool_concurrency.py`. |
| 2026-04-27 | **ADR-021 config bridge (pre–drop/recreate):** hub-style value in `embedding_model` (`org/model`) promoted to `openrouter_embedding_model` in merge validator so `resolve_embedder` can pick OpenRouter without mis-typing the sentence-transformers slot; test `tests/test_embedding_model_promotion.py`. **Does not** replace Qdrant recreate + corpus re-ingest — см. OPEN «Switch Qdrant…». |
| 2026-04-27 | **BT6 trust_signal slice (pre–barrier 2 gold):** `eval/claims/paraphrase_runner.py` emits per-case `runtime_mode`; `science_graphrag/benchmarks/trust_signal.py` prefers homogeneous explicit `runtime_mode` on `claims_paraphrase_*` cases; test `tests/benchmarks/test_trust_signal.py::test_detect_runtime_mode_claims_paraphrase_explicit_live`. |
| 2026-04-26 | **Reader full text vs Qdrant (ADR 022):** canonical artifacts `ingestion/{document_id}/article.md` + `normalized.md`; removed orphan `blob_store.write_text("extracted.txt")`; API `GET /v1/works/{id}/extracted-body`, `ingestion.has_extracted_body` / `work_provenance`, `sources.markdown` + `indexed_chunks`; optional `DocumentRecord.extracted_body_path` deferred. |
| 2026-04-26 | **BT6 P0 quote tolerance (barrier 1):** `science_graphrag/ingestion/claims/quote_match.py` (NFKC / dashes / nbsp / `×`→`x` / letter–digit spacing + `find_fuzzy_substring`); 4-level `_quote_accepted` + chunk pre-normalize in `extract_claims_llm`; `eval/claims/article_source.read_claims_article`; tests `tests/ingestion/claims/`. Write-up: [`docs/analysis/_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](../analysis/_archive/wave5-bt6-quote-tolerance-2026-04-26.md). Barrier 2 (gold semantics, `trust_signal live`) — OPEN item ниже. |
| 2026-04-26 | **Ingest robustness:** per-file timeout, JSONL checkpoint + `--resume`, flush logging, OpenRouter/instructor retries; test + runbook. VL-specific timeout deferred (per-file covers batch). |
| 2026-04-26 | **Unbounded workspaces:** `ws.unbounded`, scope + Qdrant `add_workspace_to_all_chunks`, backfill + runbooks. |
| 2026-04-26 | **CI:** nightly `aggregate_benchmark_metrics` + trust-baseline regression guard. |
| 2026-04-25 | **Corpus Gold v1 + dual_validate:** Phases 1–5 gold fixtures; 6.A–6.E + 6.B/D/C infrastructure (extractors, matcher, embeddings cascade, triple-vote); Phase 1–4 gold summaries folded into fixtures + `eval/dual_validate/`. |
| 2026-04-25 | **Graph readability GR1/GR3:** display labels; aggregator nodes + expand endpoints (caveats → GR8). |
| 2026-04-25 | **Ingest async roadmap:** stage timeline / OTel / stepper; Redis + Dramatiq worker; ADR-018 + worker spec (see roadmap for Wave V nuance). |
| 2026-04-25 | **API/storage splits:** `workspace_graph/`, `neo4j/` package, `ingest/*`, slim `ingest_jobs` shim, `works/`, retrieval core → `science_graphrag/retrieval/`, `pipeline` facade + `_pipeline_impl`, `IngestJobRegistry` lazy bootstrap. |
| 2026-04-25 | **Observability:** `spans/` split, `phoenix_tracer` modules, span contract preserved. |
| 2026-04-25 | **DI:** `StoreRegistry` + `get_stores()`; removed `main.py` works shim; `works_router` naming. |
| 2026-04-25 | **Product waves:** T entity dedup API; Y2 LangGraph ReAct + tests; Y4 multi-agent supervisor + ADR-020. |
| 2026-04-19 | **Benchmarks:** teacher-gold audit baseline checklist; durable file-backed run snapshots in `task_store`. |
| 2026-04-26 | **Big plan partial + quality gates:** ingest CLI timeout/resume/checkpoint (см. «Ingest robustness»); `scripts/benchmark_aggregator/paths.py`; `EDGE_DISPLAY_TYPE_READER` + test; `ExtractorBase._safe_parse_json` + `claims_v2`; **isort/black** зелёные на `science_graphrag/api/ingest_jobs.py` и `science_graphrag/agent/idea_workflow.py` (не весь пакет `science_graphrag/` — отдельный глобальный проход при необходимости). |
| 2026-04-26 | **Wave A LangChain tools:** split into `workspace_catalog_tools.py`, `paper_quote_search_tool.py`, `format_bibliography_gost_tool.py`; facade `workspace_paper_tools.py` (`build_workspace_paper_langchain_tools` + re-exports). |

## Queue

Closed items live only in **Completed (archive)** above (no `### [DONE]` bodies here).

### [OPEN] Stable error_class enum on `error` SSE — extend coverage
- **Area:** `science_graphrag/api/agent_v2.py` (`_classify_agent_stream_error`), `docs/specs/agent-chat-v1.md`
- **Issue:** Initial classifier covers OpenRouter-shaped `ValueError({code, message})`, generic timeouts, connection errors, and a catch-all `internal_error`. Real-world failures (LangChain validation, langgraph deadline before tool call, instructor parse failures) currently still collapse to `internal_error`.
- **Proposal:** Walk recent traces (`eval/results/trace-review-*.json`) and add discriminator branches for the most common opaque error kinds; keep the small enum (`provider_*`, `internal_error`) and document each new code in `chat-errors.md` / spec.
- **Acceptance:** ≥80% of `error` events from a recent live run land on a non-`internal_error` class; UI ships a localized message for each new class via `chat.errors.<error_class>`.
- **Raised:** 2026-05-05 (readable-stream-events plan)

### [OPEN] paper_profile year/venue — OD null-rate closure (ingest + graph)
- **Area:** `science_graphrag/ingestion/_pipeline_impl.py`, Neo4j writers / OpenAlex merge, `workspace_catalog_tools.py` (`paper_profile`)
- **Issue:** Phase A3 acceptance («доля null на OD») not closed by tool+prompt alone; `eval/paper_profile_stats.summarize_paper_profile_payloads` can measure saved payloads but pipeline may still omit venue/year.
- **Proposal:** Run aggregator on OD workspace exports; extend merge/writers for venue/year from OpenAlex or PDF front-matter; re-measure with the same helper.
- **Acceptance:** Documented null-rate baseline drops or stays stable with explicit «thin corpus» rationale in `docs/architecture/agent-chat-tools.md`.
- **Raised:** 2026-04-28 (agent tools plan phase A3)

### [OPEN] Phase 5B — per-model / tenant-fairness quota (post–Redis ZSET v1)
- **Area:** `science_graphrag/llm/redis_quota.py`, `pool_limits.py`, `config.py`, settings schema
- **Issue:** Phase 5 v1 enforces one global cap per logical pool; no per-model keys, no tenant/workspace fairness, no lease heartbeat (see `docs/analysis/llm-distributed-quota-phase5b-advanced-scope.md`).
- **Proposal:** Separate ADR + Redis key design if product requires it; optional lease refresh task; avoid hot-key regressions.
- **Acceptance:** Documented policy + integration tests for chosen fairness model; no silent over-cap beyond documented v1 lease semantics.
- **Raised:** 2026-04-27

### [PARTIAL] Ingest resume — claims + Neo4j selective rebuild
- **Area:** `science_graphrag/ingestion/resume_ingest.py`, `science_graphrag/storage/neo4j/writes/works.py`
- **Issue:** `ingest-resume-embed` only repopulates chunk + work-summary vectors in Qdrant; it does not re-extract claims or refresh `CITES` titles when those stages were skipped or half-written.
- **Proposal:** Add optional `--stages claims,references` (or separate CLI) that reuses `normalized.md` + Neo4j `work_id`, re-runs LLM stages with idempotent upserts, and aligns checkpoint keys. **Interim operator path:** `scripts/backfill_workspace_claims.py` (chunks in Qdrant → LLM claims → Neo4j + Qdrant claims collection; JSONL progress).
- **Acceptance:** Integration test on a fixture document that forces embed failure then resumes claims+embed without duplicating layer1 Work nodes.
- **Done in Wave Next+1 (2026-05-05):** CLI `science-graphrag ingest-resume --stages …` → `resume_document_ingest_stages`; references resume deletes outgoing `CITES` before rebuild; claims resume refreshes Qdrant claim vectors **only when embed is not part of the same resume run** (avoid double-embedding); checkpoint keys updated via `mark_stage_completed` for resumed stages.
- **Done in follow-up (2026-05-05):** паритет checkpoint при падении **не-embed** стадий: обёртка `references`/`claims` в `resume_document_ingest_stages` вызывает `_persist_resume_stage_failure` (сериализация checkpoint, `IngestionRunRecord` `failed_retryable` / `failed_terminal`); эвристика `_resume_failure_retryable` + unit-тесты в `tests/ingestion/test_resume_stages_csv.py`.
- **Done in follow-up (2026-05-05) — citations path:** в `reference_citations.py` — лог при ошибке OpenAlex по DOI; нормализация заголовка для fingerprint без выкидывания нелатинских букв; регрессии в `tests/test_citation_persist.py`.
- **Remaining:** integration fixture test «embed fail → resume claims+embed without duplicate layer1 Works» (end-to-end, не покрыт юнитами выше).
- **Raised:** 2026-04-27 (stage-safe ingest follow-up)

### [OPEN] Work dedup hygiene — drift detection after ingest
- **Area:** `science_graphrag/cli/main.py` (`merge-work`, `repoint-qdrant-work-ids`), ingest pipeline, optional nightly job
- **Issue:** Title-level duplicate `Work` nodes can reappear after bulk ingest; manual merge was required for BT2 (`scripts/merge_duplicate_works_by_title.py` + audit JSON under `eval/results/`).
- **Proposal:** Post-ingest Cypher report (dup titles) + WARN metric or CI step when `size(ws)>1` for canonical pilot titles; link runbook from `docs/runbooks/benchmark-decision-gate.md`.
- **Acceptance:** Documented operator path + either automated alert or weekly scheduled report with non-zero exit when new dup clusters appear.
- **Raised:** 2026-04-26 (Wave 6 benchmarks roadmap)

### [OPEN] Split benchmark artifact storage: canonical vs runtime diagnostics
- **Area:** `eval/results/`, `eval/chat_agent/`, `scripts/benchmark_aggregator/paths.py`, benchmark/chat-agent runners
- **Issue:** `eval/results/` mixes canonical committed artifacts (`current-*`, baselines), heavy live traces (`case_result.json`, `trace_audit.json`), repair progress JSONL, and local runtime snapshots with absolute paths / workspace ids. This hurts repo hygiene, agent navigation/search, and creates a shallow file-name-driven seam where storage role is inferred from naming conventions.
- **Proposal:** Introduce explicit artifact classes and roots: keep only small reviewable canonical artifacts in git; move live/debug/repair outputs to ignored storage (`data/diagnostics/`, MinIO/S3, or equivalent) behind a small manifest/index layer with stable pointers + checksums. Update runners/docs so `--out` defaults reflect the class (canonical vs runtime), and sanitize exported JSON that still needs to be committed.
- **Acceptance:** `eval/results/` contains only canonical/report-facing artifacts; live chat-agent traces and OD repair snapshots no longer commit absolute local paths; aggregator reads canonical inputs through a single registry/manifest seam rather than ad-hoc filename conventions.
- **Raised:** 2026-04-27 (artifact hygiene audit)

### [PARTIAL] VL JSON parse error for DN-DETR.pdf (reproducible)
- **Area:** `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/ingestion/llm/raw_openai_transport.py`
- **Issue:** `DN-DETR.pdf` (13 pages, `doc_id=dff05d47`) fails VL 3/3 times with `Expecting value: line 585 column 1 (char 3212)` — OpenRouter/chat-completions wrappers occasionally return **non-JSON bodies** despite HTTP 200, which breaks `response.json()` parsing.
- **Proposal:** (1) Normalize transport errors + raise a typed error for non-JSON bodies. (2) Harden VL response parsing (`message.content` variants, markdown fences). (3) Provide clean fallback + structured diagnostics.
- **Acceptance:** Stable operator behavior: non-JSON VL responses do not explode with opaque tracebacks; fallback path emits structured ingest diagnostics suitable for auditing.
- **Done in Wave Next+1 (2026-05-05):** `raw_openai_transport` raises `ChatCompletionsNonJsonResponseError` on HTTP 200 non-JSON bodies; `vl_pdf` parses `message.content` variants + strips markdown fences; markdown fallback records structured diagnostics (`markdown_fallback_*`, `ingest_transport`).
- **Remaining:** DN-DETR acceptance case (“VL processes all pages, `markdown_source=vl`”) is still provider/model dependent — track separately if we still want 100% VL markdown for this PDF family.
- **Raised:** 2026-04-26

### [PARTIAL] reuse_cached_markdown cache-collision: too many fallback paths
- **Area:** `science_graphrag/ingestion/cache_policy.py`, `science_graphrag/ingestion/orchestrator.py`, `science_graphrag/cli/main.py`
- **Issue:** legacy markdown cache lookups can silently reuse unexpected on-disk artifacts (slug-based copies / multiple roots), causing `cached-normalized` skips when operators expect a forced re-extract.
- **Proposal:** (1) explicit operator bypass for cache reuse; (2) louder logging for cache hits; (3) long-term: single canonical cache keying by `document_id` only.
- **Acceptance:** Re-ingest of any document with `--no-cache` always runs VL/pypdf regardless of what's on disk; no `cached-normalized` in diagnostics after explicit force-re-ingest.
- **Done in Wave Next+1 (2026-05-05):** `--no-cache` on `ingest` / `ingest-corpus` forces `bypass_markdown_cache`; cache hits log at WARNING with rel path + document_id + mode.
- **Remaining:** consolidate legacy slug-based cache paths (migration-only), reduce ambiguous fallbacks beyond operator bypass.
- **Raised:** 2026-04-26

### [OPEN] VL OCR truncation for long PDFs (>16 pages)
- **Area:** `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/config.py`
- **Issue:** `vl_max_pages = 16` (hardcoded default) silently truncates any PDF beyond 16 pages. Confirmed case: Falcon-H1 paper (`work_id=739b528f-f8f1-42b4-b185-35c114986e9d`), 81 pages total — markdown stops at section 2.4.1 (~page 16). Additionally, `max_tokens=12000` is hardcoded in `VLPDFProcessor.pdf_to_markdown()` — even if `vl_max_pages` is raised, the response may be output-truncated. The root architecture: all pages (up to `vl_max_pages`) are sent as a **single request** with all images embedded, which doesn't scale for 40–80+ page papers.
- **Proposal:**
  1. **Short-term (config):** Expose `SCIENCE_GRAPHRAG_VL_MAX_TOKENS` in `Settings` (default `32768` or `65536`); raise `SCIENCE_GRAPHRAG_VL_MAX_PAGES` default to `80` (or `0` = unlimited). Update `VLPDFProcessor` to use the setting.
  2. **Medium-term (batching):** Process pages in batches of N (e.g., 8–12 pages per request), concatenate results. Configurable `vl_batch_size`. Add `vl.pages_total` and `vl.batch_count` to span attributes and `extraction_diagnostics.json`.
  3. **Diagnostics:** Write `pages_total` and `pages_processed` to `extraction_diagnostics.json` so truncation is detectable without re-reading the PDF.
- **Acceptance:** An 80-page PDF ingested with defaults produces markdown covering all pages; `extraction_diagnostics.json` includes `pages_total=81`, `pages_processed=81`; no silent truncation at page 16.
- **Raised:** 2026-04-26

### [OPEN] Ingest dedup — parity with osint-gr (authors/entities + optional gated pipeline)
- **Area:** `science_graphrag/dedup/ingest_conflict_check.py`, `work_dedup_engine.py`, author/entity dedup engines, `science_graphrag/ingestion/_pipeline_impl.py`, ingest job DTO / worker state
- **Issue:** Сейчас при ingest ставится очередь только для **works** (Qdrant summary + при необходимости LLM `_llm_same_work`); в плане фигурировали ещё `AuthorDedupConflict` / `EntityDedupConflict` и более богатый сценарий как в osint (`backend/osint_graphrag/dedup`, KG extract → `ConflictResolver` в `osint-gr/frontend/.../KnowledgeGraphPage`): конфликты на сущностях, сохранение с разрешённым маппингом id, UI **во время** долгой операции, а не только после `completed`.
- **Proposal (фазы):** (1) Расширить `ingest_conflict_check`: те же пороги/пайплайны, что scan-дедуп для авторов/сущностей в scope workspace, писать в соответствующие ORM-таблицы с `origin=ingest`. (2) Опционально: стейт job `awaiting_user_decision` + поле `dedup_decision_required` + `POST .../dedup-decision` для возобновления — только если продуктово нужно блокировать merge до решения (иначе оставить post-hoc карточку). (3) Общие хелперы с osint — только где домен совместим (vector + thresholds), без копипасты бизнес-логики OSINT.
- **Acceptance:** тесты на каждую новую ветку конфликтов; документ в `docs/analysis/` с матрицей «work / author / entity × scan / ingest»; фронт знает, какой тип очереди показывать (или единый агрегированный счётчик с разбивкой).
- **Raised:** 2026-04-26

### [OPEN] Remove unused workspace smart-dedup HTTP routes (after soak)
- **Area:** `science_graphrag/api/workspace_dedup.py` и связанные роутеры
- **Issue:** Фронт больше не дергает scan/merge/candidates из старого graph UI; часть эндпоинтов может быть мёртвой нагрузкой на поддержку и security surface.
- **Proposal:** После наблюдения в проде — удалить неиспользуемые handlers, оставить conflict list + decision для `IngestConflictReviewCard`; миграции не требуются.
- **Acceptance:** тесты API обновлены; нет регрессий для CLI/скриптов, если таковые вызывали удалённые пути.
- **Raised:** 2026-04-26

### [OPEN] BT6 gold realism + optional embedding-soft quote fallback
- **Area:** `eval/claims/`, `tests/fixtures/benchmarks/claims/`, `science_graphrag/ingestion/claims/quote_match.py`
- **Issue:** **P0 quote gate (barrier 1) — [DONE 2026-04-26]** (см. Completed выше + [`_archive/wave5-bt6-quote-tolerance-2026-04-26.md`](../analysis/_archive/wave5-bt6-quote-tolerance-2026-04-26.md)). **Progress (2026-04-27):** per-case `runtime_mode` в `paraphrase_runner` + явный приоритет в `trust_signal` для семейств `claims_paraphrase_*` (см. Completed). Остаётся barrier 2: после P0 PDF-noise barrier снят (`corpus_ssd_v2` + Mistral: 28/28 quotes accepted в одном прогоне), но `claim_recall` на BT6 ограничен **семантикой** gold (`expected_claims[].claim_text_normalized` / `match_mode` vs выход production extractor). Отдельно: часть моделей даёт **truncated** tool JSON до Pydantic (наблюдение: Minimax + distracted body).
- **Proposal:** (1) Reformulate `expected_claims[].claim_text_normalized` toward achievable paraphrases for the production path; add an `aspirational_v2` tier for abstract “principle” gold without CI gating. (2) Optional level-5 in `_quote_accepted`: sentence-window cosine (τ≈0.85) **only** with `claims_quote_embedding_fallback=true`, **replacing** stored `quote` with the nearest real subspan and `evidence.requires_review=true`.
- **Acceptance:** BT6 mini / `corpus_ssd_v2` (or `claims_paraphrase_bt6_mini` tier) reaches **≥ 0.55** `claim_recall` on `mistralai/mistral-small-3.2-24b-instruct` with `--extractor production`; distracted lane completes without LLM JSON truncation under the same provider settings used in CI smoke.
- **Raised:** 2026-04-26 (post P0 quote tolerance).

### [OPEN] Split `scripts/aggregate_benchmark_metrics.py` (BT1 follow-up)
- **Progress (2026-04-26):** вынесены дефолтные пути артефактов в [`scripts/benchmark_aggregator/paths.py`](../../scripts/benchmark_aggregator/paths.py); основной файл импортирует их через `sys.path` к `scripts/`. Далее — `_summarize_*` / `_md_*` / family modules.
- **Area:** `scripts/aggregate_benchmark_metrics.py` (~1100 lines after Wave 3 BT4/BT5 additions).
- **Issue:** Summarizers (`_summarize_*`), markdown render (`_md_*`), CLI `main()`, family logic all live in one file; hard to review and parallel-edit with BT2–BT12 aggregator deltas. File grows with each wave.
- **Proposal:** Extract modules: `scripts/benchmark_aggregator/summarizers.py` (`_summarize_*`), `scripts/benchmark_aggregator/markdown.py` (`_md_*` + `_render_markdown`), `scripts/benchmark_aggregator/family_retrieval.py` (retrieval family assembly), `scripts/benchmark_aggregator/family_claims.py` (claims/refs/concept). Keep thin CLI in `aggregate_benchmark_metrics.py` (≤ 250 LoC). Trust/decision glue stays in `science_graphrag/benchmarks/`.
- **Acceptance:** `aggregate_benchmark_metrics.py` ≤ 250 LoC; `python scripts/aggregate_benchmark_metrics.py` unchanged CLI contract; pytest benchmarks + aggregate smoke pass; no file in `scripts/benchmark_aggregator/` exceeds ~400 LoC.
- **Raised:** 2026-04-26 (post-BT1); updated 2026-04-26 (post-Wave 3, now ~1100 LoC).

### [OPEN] Migrate dual_validate extractors to instructor (Phase 7 task)
- **Progress (2026-04-26):** [`ExtractorBase._safe_parse_json`](../../scripts/dual_validate/extractors/base.py) — единый префикс ошибок; пилот на [`claims_v2.py`](../../scripts/dual_validate/extractors/claims_v2.py). Полная миграция на Instructor — без изменений в этом PR.
- **Area:** `scripts/dual_validate/extractors/*.py` (12 extractor'ов), `scripts/dual_validate/llm_client.py` (станет transport-layer), новый `scripts/dual_validate/instructor_client.py`, новый `science_graphrag/llm/instructor_factory.py` (общий backend с `science_graphrag/ingestion/llm/extractor.py:SyncInstructorExtractor`).
- **Issue:** в Phase 6.E мы потеряли несколько packs из-за malformed JSON от Kimi/Claude/v4-pro (truncated, unescaped quotes). Сейчас каждый из 12 extractor'ов вручную дублирует: (a) JSON-схему в prompt, (b) `parse_json_object_lenient` парсинг, (c) post-hoc валидацию полей через `_VALID_TYPES`/`_VALID_POLARITIES`/etc. **`instructor>=1.7.0` уже в deps** и используется в production ingestion (`SyncInstructorExtractor` с `instructor.Maybe`, mode-selection для OpenRouter Qwen3.5).
- **Proposal:**
  - Каждый extractor получает Pydantic `response_model` (Literal-типы вместо string sets, `Field(min_length=...)` вместо ручных проверок).
  - `instructor.Maybe[Model]` с `max_retries=1` даёт auto-retry с error feedback в prompt при validation failure → восстанавливает потерянные packs Phase 6.E без human review.
  - Наши retry helpers (`_extract_retry_after`, `_compute_backoff`, empty-choices guard) **остаются** на transport-layer (HTTP 429/502/503), Instructor работает на application-layer (Pydantic validation). Они комплементарны.
  - Постепенная миграция: `ExtractorBase.run_for_pack` поддерживает оба режима через атрибут `response_model: type[BaseModel] | None`.
  - Pull common backend в `science_graphrag/llm/instructor_factory.py` (mode-selection + extra_body builder + usage extraction), которым пользуются и ingestion, и dual_validate.
- **Acceptance:**
  - все 12 extractor'ов имеют Pydantic `response_model`;
  - `parse_json_object_lenient` больше не вызывается из `extractors/*` (остаётся как util для legacy raw-логов);
  - failed Phase 6.E packs пере-проганы и либо succeed, либо имеют осмысленный validation-error в logs;
  - tests 57+ → 70+ (новые tests на schemas + Instructor mock);
  - дубль кода между `SyncInstructorExtractor` и dual_validate client устранён.
- **Estimated effort:** 1-2 дня focused work; не блокирует BT2-BT12, кандидат для следующего refactor pass.
- **Reference:** полный анализ — `docs/analysis/instructor-adoption-dual-validate-2026-04-25.md`.
- **Raised:** 2026-04-25.

### [OPEN] Refactor `scripts/dual_validate/extractors/` — extract common base patterns
- **Area:** `scripts/dual_validate/extractors/{base.py, claims_v2.py, concept_topic_v2.py, contradictions_v1.py, idea_assist_live.py}`
- **Issue:** pylint R0801 (`duplicate-code`) флагает 3 повторяющихся блока в 4 extractor'ах: (а) JSON parsing wrapper (теперь решено через `parse_json_object_lenient`, но осталась оболочка `try/except → ValueError("extractor B (...): ...")`), (б) `ExtractorInfo` construction для extractor_b с одинаковыми полями provenance, (в) `summary` dict с `matched_lexical`/`matched_embedding`/`unmatched_*`. Каждый новый extractor добавляет ~30 lines дублирующегося скаффолдинга.
- **Proposal:** добавить в `ExtractorBase`:
  - `_safe_parse(self, raw: str, layer_label: str) -> Any` — обёртка над `parse_json_object_lenient` с layer prefix в ошибке;
  - `_extractor_b_info(self, run, *, role, source) -> ExtractorInfo` — собирает provenance из `run` или возвращает dry-run заглушку;
  - `_summary_skeleton(self, *, a_total, b_total, matched_pairs, unmatched_a, unmatched_b, embedding_used: bool) -> dict` — стандартный summary с opt-in полями (review block, field_agreements);
  - `_safe_relative_paths(self, pack_dir) -> tuple[Path, Path]` — общий resolver pack/gold relative path (сейчас одинаковый try/except в 3 файлах).
- **Acceptance:** pylint без R0801 на всех 4 extractor'ах; каждый extractor ≤180 LoC (сейчас claims_v2 = 280, concept_topic_v2 = 270, contradictions_v1 = 290, idea_assist_live = 320); добавить новый extractor (один из 5 pending) ≤120 LoC скаффолдинга на класс.
- **Raised:** 2026-04-25 (Phase 6.C session)

### [OPEN] Switch Qdrant production embeddings to bge-m3 (ADR-021)
- **Area:** `science_graphrag/ingestion/embeddings/`, `science_graphrag/embeddings/openrouter_provider.py`, `science_graphrag/api/qdrant_client.py`, `.env`, all retrieval benchmarks
- **Issue:** Production Qdrant сейчас использует hash-fallback embeddings (384-dim, deterministic-but-meaningless). Phase 6.D ввела `OpenRouterEmbeddingProvider` с `baai/bge-m3` (1024-dim). Нужна полная миграция: vector_size, recreate collections, reingest corpus, перепрогнать BT1-BT5.
- **Progress (2026-04-27):** в `Settings.merge_runtime_env_overrides` значение вида `org/model` в слоте `embedding_model` (частая ошибка оператора с `SCIENCE_GRAPHRAG_EMBEDDING_MODEL=baai/bge-m3`) **промотируется** в `openrouter_embedding_model`, чтобы `resolve_embedder` выбрал OpenRouter; тест `tests/test_embedding_model_promotion.py`. Это **не** заменяет шаги recreate/reingest ниже.
- **Progress (2026-04-26):** ops runbook [`docs/runbooks/phase0-bge-m3-qdrant-cutover.md`](../runbooks/phase0-bge-m3-qdrant-cutover.md); CLI `science-graphrag qdrant-recreate-embedding-collections --dry-run`; `describe_embedding_collections_cutover` / `qdrant_embedding_collection_names` в `recreate_embedding_collections.py`; **Qdrant recreate выполнен** (1024); **re-ingest завершён** (`ingest-corpus` + `eval/results/ingest-progress-phase0-bge-m3.jsonl`, exit 0, лог `ingest-phase0-bge-m3.log`); `report_qdrant_work_coverage.py`: **32** distinct `work_id` в `chunks`, **1157** points (≥16 — ок). **Исторически в логе:** `Libra R-CNN.pdf` — `PermissionError` в `data/blobs/raw/...` (опциональный догон через [`ingest-corpus.md`](../runbooks/ingest-corpus.md)). **Dedup audit:** 3 duplicate clusters — по необходимости. **Остаётся для закрытия OPEN:** BT2 / BT4 / BT5 + `aggregate_benchmark_metrics.py --write-trust-baseline` + приёмка Proposal.
- **Proposal:** см. `docs/adr/021-openrouter-bge-m3-embeddings.md`. Шаги: (1) добавить `SCIENCE_GRAPHRAG_EMBEDDING_MODEL=baai/bge-m3` в `.env` и `Settings`, (2) plumb provider через `science_graphrag/ingestion/{layer1,layer2,claims}_pipeline.py` (заменить hash-fallback fallback chain), (3) drop+recreate `works`, `claims` Qdrant collections с vector_size=1024, (4) reingest всё корпуса (10-15 мин, $1-2 за embeddings), (5) rerun BT1-BT5 retrieval benchmarks, (6) update `decision_gate` thresholds если потребуется.
- **Acceptance:** все retrieval benchmarks (workspace_scoped_live, hybrid_ablation_v2, multihop_v2, live_corpus_methods_*, judge_pilot) либо стабильны либо улучшились vs baseline; `qdrant info` показывает 1024-dim collections; `Settings.embedding_model == "baai/bge-m3"`; нет hash-fallback кода в production paths.
- **Risks:** hard cutover (не A/B, нельзя rollback без re-ingest); outbound network dependency на OpenRouter в ingestion path (раньше было self-contained); retrieval gates могут сдвинуться.
- **Raised:** 2026-04-25 (out of scope of Phase 6.D — отдельная сессия)

### [PARTIAL] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`
- **Issue:** `node_kind` was equal to Neo4j `type`; edge labels were technical; `LIMIT` was not priority-aware.
- **Proposal:** Add `node_kind` semantics, `EDGE_DISPLAY_TYPE_RAW` mapping, and limit prioritization with `meta.skipped_by_kind`.
- **Acceptance:** priority kinds (`Method`,`Dataset`,`Work`) survive truncation; UI legend can render semantic edge labels.
- **Raised:** 2026-04-25
- **Note (partial 2026-04-25):** backend часть доставлена (`graph_display.py` с `EDGE_DISPLAY_TYPE_RAW`,
  `resolve_node_kind`, `node_kind_priority`, `_enrich_edges_with_display`, `meta.skipped_by_kind` через
  `kind_distribution`). **UI integration не выполнена** — `graphCanvasDraw.js` рисует raw `edge.type`. Закрывается
  Wave GR6 (frontend) — см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md).

### [OPEN] Graph readability — Wave GR8 smarter aggregation defaults (per-kind thresholds, non-Work owners, cap-aware)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_display.py`
- **Issue:** GR3 поставил `AGGREGATOR_THRESHOLD=8` + owner-фильтр `Work`. Типичная статья (4–6 авторов,
  5–10 цитат) **не агрегируется**; cap-truncation (`is_truncated=true`) не отображается визуально.
- **Proposal:** per-kind thresholds (например `AuthorshipReification`/`Author`=4, `Institution`=5, `Work`=8);
  разрешить owner-типы `Author`/`Institution`/`Venue` в дополнение к `Work`; cap-aware агрегатор
  «`+N hidden`» от `meta.skipped_by_kind`/`kind_distribution`; query-параметры
  `aggregator_threshold` (override) и `aggregator_disabled_kinds` (CSV opt-out); расширить
  `_apply_aggregators` на двух-хоп цепочки `Work → Authorship → Author` для `view=raw`.
- **Acceptance:** статья с 5+ авторами свёрнута по умолчанию; `is_truncated=true` показывает
  `+N hidden`-агрегатор; pytest на разных порогах per-kind зелёный.
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.3)

### [OPEN] Graph readability — Wave GR9 reader view with virtual AUTHORED edges (formerly GR4)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_snapshot_diff.py`
- **Issue:** Raw `Authorship` reification полезен для ontology/debug, но избыточен для default reader UX.
  Сейчас параметр `view` влияет только на агрегацию, `:Authorship` всегда возвращается.
- **Proposal:** Добавить настоящий `view=raw|reader`; в reader view не возвращать `:Authorship` узлы
  и `HAS_AUTHORSHIP`/`OF_AUTHOR` рёбра, генерировать виртуальные `Work –[AUTHORED]→ Author` с
  `via: ["HAS_AUTHORSHIP","OF_AUTHOR"]` и `properties: {author_position, is_corresponding, raw_affiliation}`.
  `view=raw` остаётся источником истины для `graph_snapshot_diff` и benchmark `graph_v1`.
- **Acceptance:** reader view не содержит `node_kind: AuthorshipReification`; pytest-симметрия
  множеств `Work`/`Author` между raw и reader; bench `graph_v1` не сломан.
- **Raised:** 2026-04-25 (renamed from GR4 — см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.4)

### [OPEN] Graph readability — Wave GR7 phase B: display_*_key fields in graph payload (i18n-friendly)
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `docs/adr/011-graph-live-ux-and-payload.md`
- **Issue:** `display_type` / `display_label` / `subtitle` / aggregator labels приходят как
  EN-строки, что мешает локализации в UI и не масштабируется для будущих claim-edge типов
  (`SUPPORTS`/`CONTRADICTS`/`MENTIONS`).
- **Proposal:** Добавить аддитивные поля `display_type_key` (например `"authored_by"`),
  `display_label_key` + `display_label_vars` (например `key="aggregator.authors_of_work"`,
  `vars={count: 5}`). Старые `display_type`/`display_label` сохраняются как fallback. Обновить ADR 011.
  Опциональная фаза, активируется по необходимости (см. фаза A — UI-only локализация).
- **Acceptance:** payload содержит `*_key` поля; UI Wave GR7 фаза B читает их через `t(key, vars)`;
  старые клиенты продолжают работать на EN-fallback.
- **Raised:** 2026-04-25 (см. [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md) §2.2.3)

### [OPEN] Graph readability — Wave GR5 denormalized Work counters for weighted layout
- **Area:** `science_graphrag/storage/neo4j_store.py`, ingestion pipelines, graph API payload properties
- **Issue:** Work importance signals (`cites_in/out`, `authors_count`) are recomputed ad hoc and not consistently available for graph styling.
- **Proposal:** Persist denormalized counters on `:Work` and expose them in graph payload properties.
- **Acceptance:** graph payload includes stable counter properties enabling weighted radius/ranking without extra query passes.
- **Raised:** 2026-04-25

### [OPEN] Split idea-assist workflow orchestration (Wave S follow-up)
- **Area:** `science_graphrag/agent/idea_workflow.py`
- **Issue:** `idea_workflow.py` reached ~270 lines and now mixes retrieval orchestration, claim querying, LLM prompting, and output normalization in one module.
- **Proposal:** Extract (1) claim/context collector, (2) LLM schema+prompt builder, and (3) result normalizer into separate modules under `science_graphrag/agent/idea_assist/`.
- **Acceptance:** orchestrator file <= 180 lines, prompt/schema logic isolated, and unit tests target each submodule independently.
- **Raised:** 2026-04-25

### [OPEN] Split benchmark backend hubs: `api/benchmark.py` (1249) + `api/task_store.py` (593)
- **Area:** `science_graphrag/api/benchmark.py`, `science_graphrag/api/task_store.py`, `science_graphrag/api/benchmark_profiles.py`
- **Issue:** `task_store.py` частично разгружен (persistence вынесен в `science_graphrag/storage/benchmark_run_persistence.py`, сериализация — в `science_graphrag/api/task_benchmark_serializers.py`), но `benchmark.py` остаётся главным god-router (fixture catalog + case detail + compare + graph preview + eval integration) и продолжает расти. Глубина seam'ов низкая: добавление нового benchmark family всё ещё требует правок в центральном роутере.
- **Proposal:** зафиксировать новый target split: (1) `api/benchmark.py` → подпакет `api/benchmark/{router,catalog,case_detail,compare,graph_preview}.py`; (2) `task_store.py` добить до orchestration-only слоя с явными adapter seams к persistence/serialization.
- **Acceptance:** `api/benchmark.py` как входной router <= 300 LoC; новые benchmark families добавляются через `catalog` adapter без изменения compare/preview модулей; `task_store.py` не содержит JSON snapshot plumbing и не знает layout on-disk артефактов.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap-2026-04-24.md` — каждое семейство не упирается в god-файл.
- **Raised:** 2026-04-25, updated 2026-05-05

### [PARTIAL] Standardize ingestion LLM seams around structured executor
- **Area:** `science_graphrag/ingestion/llm/`, `science_graphrag/ingestion/claims/extractor.py`, `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/ingestion/_pipeline_impl.py`
- **Issue:** production ingestion использует три разных паттерна LLM-вызова. Metadata/authorships/references/semantic уже идут через `SyncInstructorExtractor` + shared `run_extraction`, но claims по-прежнему вызывает `extract_maybe(...)` напрямую, держит локальные Pydantic-схемы и ad-hoc diagnostics dict; VL PDF path оправданно не использует Instructor, но дублирует transport/timeout/observability policy. В итоге retry/span/error contract и test surface отличаются между стадиями одной ingestion pipeline.
- **Proposal:** (1) перевести claims на тот же structured seam: shared schema modules + `run_extraction(...)`/standardized executor policy + typed diagnostics; (2) ввести extractor factory/presets из `Settings` вместо ручной сборки `SyncInstructorExtractor` в каждом call-site; (3) для VL не тащить Instructor, а вынести общий low-level transport/telemetry seam для non-structured calls; (4) зафиксировать матрицу `stage -> seam` в architecture/docs и tests.
- **Acceptance:** все production stages вида `text/chunks -> typed structured object` используют shared Pydantic schema modules и единый executor contract; claims больше не содержит bespoke direct-call protocol поверх `extract_maybe(...)`; создание extraction clients централизовано; diagnostics vocabulary выровнен между metadata/semantic/claims; VL path использует общий transport helper без дублирования timeout/error handling.
- **Reference:** `docs/analysis/ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`
- **Raised:** 2026-04-27
- **Synergy:** **Wave N/O** (онтология), **Wave Y2** (LangGraph tool-граф) — общий executor можно потом переключить на `langchain_core` LLM-калл без сноса orchestrator.
- **Raised:** 2026-04-25
- **Done in Wave Next (2026-05-05):** claims extraction runtime envelope вынесен в `science_graphrag/ingestion/llm/claims_runtime.py` (preset/budget/deadline), `claims/extractor.py` переключён на shared runtime builder; сохранена backward-совместимость тестовых monkeypatch seam.
- **Remaining:** единый low-level transport helper для non-structured calls (VL) + финальное выравнивание diagnostics keys в ingest report.

### [OPEN] Settings service split (1027)
- **Area:** `science_graphrag/settings/service.py`, `science_graphrag/api/settings.py`
- **Issue:** Модуль смешивает как минимум 4 ответственности: runtime overrides merge, secret-aware LLM config/test, storage/benchmark snapshot assembly, security/diagnostics output. Из-за высокой связности любое расширение settings API повышает риск скрытых регрессий.
- **Proposal:** выделить `settings/runtime_overlay.py` (merge + validation), `settings/snapshots.py` (DTO assembly), `settings/llm_probe.py` (test connection + OpenAI/OpenRouter probes); `SettingsService` оставить как thin orchestration facade.
- **Acceptance:** `settings/service.py` <= 350 LoC; unit-тесты покрывают каждый модуль изоляционно (overlay/snapshots/probes), а API слой проверяет только wiring.
- **Raised:** 2026-04-25, updated 2026-05-05

### [OPEN] Split `cli/main.py` (566) by command groups
- **Area:** `science_graphrag/cli/main.py`
- **Issue:** Typer-приложение фактически — оркестратор offline-операций (`neo4j-wipe`, `ingest`, `merge-work`, `repoint-qdrant-work-ids` и т.п.); по мере Wave Q/T/W будет расти.
- **Proposal:** `cli/{ingest,neo4j,qdrant,dedup,worker}.py`, тонкий `cli/main.py` собирает Typer-app из подкоманд.
- **Acceptance:** ни один файл > ≈200 строк; запуск `science-graphrag --help` идентичен.
- **Synergy:** **Wave W** добавит `cli/worker.py` (запуск Dramatiq) без раздувания main.
- **Raised:** 2026-04-25, updated 2026-05-05

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

### [PARTIAL] Split `api/agent_v2.py` orchestration seams (995)
- **Area:** `science_graphrag/api/agent_v2.py`, `science_graphrag/agent/runtime.py`, `science_graphrag/agent/tool_*`
- **Issue:** `agent_v2.py` аккумулирует transport concerns (SSE/error envelope), orchestration, и mapping request/response payloads. Это снижает locality для регрессионных правок по stream lifecycle и tool-trace/compaction.
- **Proposal:** выделить `api/agent_v2/` подпакет: `router.py` (FastAPI endpoints), `streaming.py` (SSE lifecycle + cancellation), `payloads.py` (DTO mapping), `orchestration.py` (runtime call graph). Текущий файл оставить как compatibility entrypoint.
- **Acceptance:** каждый модуль <= 300 LoC; изменения в SSE протоколе не требуют правок в бизнес-оркестрации tool/runtime; smoke `test_api_agent_v2_smoke.py` и trace-аудит тесты проходят без контрактных изменений.
- **Raised:** 2026-05-05
- **Done in Roadmap pass (2026-05-05):** вынесены новые seams: `api/agent_v2_payloads.py` (payload mapping), `api/agent_v2_errors.py` (error normalization), `api/agent_v2_streaming.py` (graph chunk streaming primitives), `api/agent_v2_runtime_bridge.py` (sync runtime bridge); `agent_v2.py` переведён на эти adapters; smoke/parity тесты зелёные.
- **Done in follow-up packaging slice (2026-05-05):** добавлен подпакет `api/agent_v2_modules/` и основные импорты в `agent_v2.py` переведены на package-path (`...agent_v2_modules.{payloads,errors,streaming,runtime_bridge}`); прежние top-level модули сохранены как compatibility shims.
- **Remaining:** выделить отдельный thin router module и вынести основной `_stream_agent` lifecycle целиком из `agent_v2.py` (финальный шаг к `api/agent_v2/` без импортного конфликта имени).

### [PARTIAL] Split ingest pipeline orchestration seams (`ingestion/_pipeline_impl.py`)
- **Area:** `science_graphrag/ingestion/_pipeline_impl.py`, `science_graphrag/ingestion/stages/*`, `science_graphrag/ingestion/checkpoint.py`
- **Issue:** `_pipeline_impl.py` исторически был god-module; основная оркестрация перенесена в `document_orchestrator.py` + phase modules, но файл всё ещё несёт CLI/corpus entrypoints и artifact writer hooks.
- **Proposal:** поэтапно разнести на deep modules: `ingestion/orchestrator.py` (stage graph + resume contract), `ingestion/progress_store.py` (JSONL progress/checkpoint IO), `ingestion/cache_policy.py` (markdown cache lookup/reuse), `ingestion/document_runtime.py` (per-document execution context).
- **Acceptance:** `_pipeline_impl.py` <= 400 LoC facade; отдельные модули имеют узкие интерфейсы и покрыты unit-тестами на resume/cache/timeout ветки; новые ingest stages подключаются через декларативный stage registry без роста god-file.
- **Raised:** 2026-05-05
- **Done in Roadmap pass (2026-05-05):** добавлены `stage_graph.py`, `claims_phase.py`, `embed_phase.py`, `session_wiring.py`; `ingest_document` переведён на `runtime_state` + вынесенные claims/embed stage runners; `_pipeline_impl.py` сокращён до ~1196 LoC.
- **Done in follow-up seam cleanup (2026-05-05):** `resume_ingest.py` отвязан от `_pipeline_impl.py` и импортирует embed stage напрямую из `ingestion/embed_phase.py` (уменьшен слой неявной связности через god-file).
- **Done in facade cleanup (2026-05-05):** `ingestion/pipeline.py` ужат до публичного facade поверх `_pipeline_impl` + отдельных seam-модулей; private alias surface снят (см. `[DONE] Sunset private exports…` ниже).
- **Done in orchestration extraction slice (2026-05-05):** orchestration skeleton `ingest_document` вынесен в `ingestion/document_orchestrator.py`; `_pipeline_impl.py` оставлен как compatibility entrypoint с делегированием через `DocumentOrchestrationDeps`.
- **Done in stage-path unification slice (2026-05-05):** `ingestion/stages/{claims,embeddings}.py` переведены на canonical phase-modules (`claims_phase`, `embed_phase`) с сохранением legacy ctx-mode для тестов и совместимости.
- **Done in resume/progress hardening slice (2026-05-05):** `resume_ingest.py` передаёт `retry_call`/`logger` в embed phase; `progress_store.append_progress` переведён на append+flush+fsync (убран full-file rewrite на каждый entry).
- **Done in next-wave slice (2026-05-05):** `document_orchestrator.py` отвязан от `_pipeline_impl.py` (helper institutions вынесен в `ingestion/institution_nodes.py`); `stages/{claims,embeddings}` получили явные `*_legacy` + `*_phase` API, internal call-sites переведены на canonical phase-path.
- **Done in Wave Next+1 (2026-05-05):** `_pipeline_impl.py` сжат до compatibility CLI/entrypoint слоя; вынесено `reference_citations.py` + `markdown_extraction.py`.
- **Remaining:** stage registry/декларативный граф (если решим убрать оставшиеся условные ветки в orchestrator) + финальная миграция тестов/скриптов с legacy import paths.

### [DONE] Sunset private exports in `ingestion/pipeline.py`
- **Done:** 2026-05-05 (Wave Next+1) — `ingestion/pipeline.py` экспортирует публичные entrypoints + `persist_reference_citation`/`_persist_reference_citation`; massive private re-exports removed.
- **Area:** `science_graphrag/ingestion/pipeline.py`, callers in tests/eval/scripts.
- **Issue:** Исторический compatibility surface содержит private `_...` symbols и провоцирует coupling внешнего кода к внутренним helper-веткам.
- **Proposal:** оставить только минимально необходимый transition-export (`_persist_reference_citation`), остальные private aliases убрать по этапам; для каждого снятого alias — migration note (куда импортировать теперь).
- **Acceptance:** `pipeline.py` экспортирует только стабильные публичные entrypoints + документированные transition aliases; нет новых импортов private symbols из facade.
- **Raised:** 2026-05-05

### [OPEN] CI gate — `trace_regression_compare` vs committed baseline
- **Area:** `.github/workflows/`, `scripts/live_check/trace_regression_compare.py`, `eval/results/baseline-trace-review.json`
- **Issue:** Wave 1 adds offline regression compare and a committed baseline artifact; PRs that touch agent runtime do not yet fail CI when metrics regress vs baseline.
- **Proposal:** Workflow on pull_request / paths filter for `science_graphrag/agent/**`, `science_graphrag/api/agent_v2.py`, `science_graphrag/agent/tool_*`: run live optional job or candidate-only generation + compare to baseline from `main` / artifact.
- **Acceptance:** CI fails on regression FAIL policies or schema version mismatch (exit 1 / 2); WARN policies documented (`--warn-is-pass` vs strict).
- **Raised:** 2026-05-05 (Wave 1 trace-review toolkit)

### [OPEN] Single canonical tool/run audit trail (roadmap §2.1 / §2.2)
- **Area:** `science_graphrag/agent/graph/state.py`, `science_graphrag/agent/graph/tracing.py`, `science_graphrag/agent/chat_envelope.py`, LangGraph messages vs `tool_trace`
- **Issue:** Duplicate representations of the same turn facts (`messages`, `tool_trace`, typed payloads) risk drift when adding runtimes or changing message shapes.
- **Proposal:** Define one canonical “turn facts” structure consumed by envelope + observability; narrow `chat_envelope` responsibilities per roadmap §2.2.
- **Acceptance:** Documented contract + tests that `tool_trace` and Phoenix spans stay aligned for one reference suite.
- **Raised:** 2026-05-05

### [OPEN] Token budget loop policy (agent runtime P2)
- **Area:** `science_graphrag/api/agent_v2.py`, `science_graphrag/agent/runtime.py`, client SSE contract
- **Issue:** Roadmap §6.4 lists token budget / continue-stop behavior as P2; not implemented as first-class metrics in trace-review.
- **Proposal:** Add cooperative cutoff telemetry + `trace-review-v1` metrics when product adds loop policy; extend regression gate thresholds.
- **Acceptance:** Documented stop reasons + tests; trace-review artifacts include budget signals when enabled.
- **Raised:** 2026-05-05

### [DONE] LX1 integration: translation SSE + ingest/agent threading pools (2026-04-27)
- **Note:** Translation stub SSE gates on cached `get_llm_async_semaphore_map`; ingest/agent/query/dedup/VL use `llm_pool_slot` / `run_extraction(settings=…)` in `science_graphrag/llm/concurrency.py`. Further LX2 real streaming can reuse the same semaphore entry.

<!-- Example:
### [OPEN] Example — tighten retrieval module boundaries
- **Area:** `science_graphrag/api/retrieval.py`, related services
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->
