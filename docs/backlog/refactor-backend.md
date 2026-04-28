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

### [OPEN] Graph work vs workspace — single reader projection seam + parity (DRY)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`, `science_graphrag/api/graph_display.py`, `science_graphrag/api/workspace_graph/`, new package `science_graphrag/api/graph_reader_projection/` (TBD), `ui/src/components/graph/authorSemanticProjection.js`
- **Issue:** Two graph surfaces duplicate reader semantics (collapse, enrich, display); work graph lacks workspace `membership` context unless URL forces full workspace union; 2-hop reader entities (e.g. institution) are policy-opaque. Violates DRY and confuses product expectations.
- **Proposal:** Execute phased plan in [`docs/analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](../analysis/graph-work-vs-workspace-unification-dry-plan-2026-04-28.md): Phase 0 `meta` contract, Phase 1 extract shared projection package, Phase 2 optional `workspace_id` on work graph for membership annotation, Phase 3 explicit institution hop flag, Phase 4 slim UI projection, Phase 5 i18n/mode labels.
- **Acceptance:** Single Python definition site for reader authorship collapse + shared enrich import path; documented when `workspace_membership` appears; integration + parity tests for membership and optional institution flag; UI projection reduced or documented as presentation-only.
- **Raised:** 2026-04-28 (graph architecture closure)

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

### [OPEN] Ingest resume — claims + Neo4j selective rebuild
- **Area:** `science_graphrag/ingestion/resume_ingest.py`, `science_graphrag/ingestion/_pipeline_impl.py`
- **Issue:** `ingest-resume-embed` only repopulates chunk + work-summary vectors in Qdrant; it does not re-extract claims or refresh `CITES` titles when those stages were skipped or half-written.
- **Proposal:** Add optional `--stages claims,references` (or separate CLI) that reuses `normalized.md` + Neo4j `work_id`, re-runs LLM stages with idempotent upserts, and aligns checkpoint keys. **Interim operator path:** `scripts/backfill_workspace_claims.py` (chunks in Qdrant → LLM claims → Neo4j + Qdrant claims collection; JSONL progress).
- **Acceptance:** Integration test on a fixture document that forces embed failure then resumes claims+embed without duplicating layer1 Work nodes.
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

### [OPEN] VL JSON parse error for DN-DETR.pdf (reproducible)
- **Area:** `science_graphrag/ingestion/vl_pdf.py`, `_call_vl_api`
- **Issue:** `DN-DETR.pdf` (13 pages, `doc_id=dff05d47`) fails VL 3/3 times with `Expecting value: line 585 column 1 (char 3212)` — `response.json()` raises, meaning OpenRouter returns a non-JSON HTTP body despite status 200. Likely: the PDF contains content (mathematical notation / special layout) causing the model to output something that breaks the chat completions JSON wrapper. Currently falls back to pypdf (61 KB article, acceptable quality for 13-page paper).
- **Proposal:** (1) In `_call_vl_api`, catch `json.JSONDecodeError`, log `response.text[:500]` at WARNING, and raise `VLAPIError` for cleaner fallback. (2) Try smaller `vl_batch_size=4` for this PDF (may avoid the problematic page). (3) If model returns markdown-wrapped JSON (` ```json ... ``` `), strip the fences before parsing.
- **Acceptance:** DN-DETR ingested via VL with `vl_pages_total=13`; `extraction_diagnostics.json` shows `markdown_source=vl`.
- **Raised:** 2026-04-26

### [OPEN] reuse_cached_markdown cache-collision: too many fallback paths
- **Area:** `science_graphrag/ingestion/_pipeline_impl.py` (`_read_cached_markdown`)
- **Issue:** Cache lookup checks 4 paths in priority order: `ingestion/{doc_id}/article.md` → `ingestion/{doc_id}/normalized.md` → `articles/{slug}/article.md` → `ingestion/*/{slug}/article.md` (glob). When re-ingesting after VL failure, deleting only the first two paths causes the pipeline to silently pick up the third (canonical slug copy) or fourth (legacy slug copy), reporting `cached-normalized` and skipping VL entirely. Discovered during bulk re-index 2026-04-26: 4 papers (DN-DETR, Mask R-CNN, R-CNN, SPPNet) required 3 manual retry iterations due to this.
- **Proposal:** (1) For force-re-ingest scenarios, add `--no-cache` / `force_reextract` flag that bypasses `_read_cached_markdown` entirely. (2) Long-term: consolidate to a single canonical path keyed by `document_id` only (drop slug-based paths as primary cache); legacy slug lookup only for migration. (3) Log at WARN (not INFO) when reusing cache, including which path was used, so silent cache hits are visible.
- **Acceptance:** Re-ingest of any document with `--no-cache` always runs VL/pypdf regardless of what's on disk; no `cached-normalized` in diagnostics after explicit force-re-ingest.
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

### [OPEN] Standardize ingestion LLM seams around structured executor
- **Area:** `science_graphrag/ingestion/llm/`, `science_graphrag/ingestion/claims/extractor.py`, `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/ingestion/_pipeline_impl.py`
- **Issue:** production ingestion использует три разных паттерна LLM-вызова. Metadata/authorships/references/semantic уже идут через `SyncInstructorExtractor` + shared `run_extraction`, но claims по-прежнему вызывает `extract_maybe(...)` напрямую, держит локальные Pydantic-схемы и ad-hoc diagnostics dict; VL PDF path оправданно не использует Instructor, но дублирует transport/timeout/observability policy. В итоге retry/span/error contract и test surface отличаются между стадиями одной ingestion pipeline.
- **Proposal:** (1) перевести claims на тот же structured seam: shared schema modules + `run_extraction(...)`/standardized executor policy + typed diagnostics; (2) ввести extractor factory/presets из `Settings` вместо ручной сборки `SyncInstructorExtractor` в каждом call-site; (3) для VL не тащить Instructor, а вынести общий low-level transport/telemetry seam для non-structured calls; (4) зафиксировать матрицу `stage -> seam` в architecture/docs и tests.
- **Acceptance:** все production stages вида `text/chunks -> typed structured object` используют shared Pydantic schema modules и единый executor contract; claims больше не содержит bespoke direct-call protocol поверх `extract_maybe(...)`; создание extraction clients централизовано; diagnostics vocabulary выровнен между metadata/semantic/claims; VL path использует общий transport helper без дублирования timeout/error handling.
- **Reference:** `docs/analysis/ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`
- **Raised:** 2026-04-27
- **Synergy:** **Wave N/O** (онтология), **Wave Y2** (LangGraph tool-граф) — общий executor можно потом переключить на `langchain_core` LLM-калл без сноса orchestrator.
- **Raised:** 2026-04-25

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

### [OPEN] CLI config-check command (`science-graphrag config-check`)
- **Area:** `science_graphrag/cli/main.py` (или новый `science_graphrag/cli/config_check.py`)
- **Issue:** Нет встроенного способа быстро проверить, что Settings видит правильные значения (API-ключи, URL-сервисов, feature flags) — агент и оператор вынуждены писать throwaway-питон, а smoke-check в правиле ломается при рефакторинге полей. Это повторяющийся источник зависших инgestов и потерянного времени (постмортем Wave 4, 2026-04-26).
- **Proposal:**
  - Добавить `science-graphrag config-check` (или подкоманду `config check`) который выводит:
    ```
    [config-check] extraction_llm_api_key : SET
    [config-check] vl_api_key             : SET
    [config-check] embeddings channel     : openrouter (model=baai/bge-m3)
    [config-check] database_url           : postgresql+psycopg://science:***@localhost:15432/...
    [config-check] neo4j_uri              : bolt://localhost:17687
    [config-check] qdrant_url             : http://localhost:16333
    [config-check] SKIP_HOST_DOTENV       : False
    [config-check] extraction_llm_enabled : True
    [config-check] blob_root              : ./data/blobs (exists=True)
    ```
  - API-ключи выводятся только как `SET` / `UNSET` (никогда не в открытую).
  - Exit code 1 если хотя бы один обязательный ключ `UNSET` (чтобы можно было использовать как gate в CI/скриптах).
  - Обновить smoke-check в `long-running-ops.mdc` на вызов этой команды.
- **Acceptance:** `science-graphrag config-check` выводит полную диагностику; exit code 1 при пустом extraction_llm_api_key; правило обновлено на эту команду вместо throwaway-питона.
- **Raised:** 2026-04-26 (постмортем Wave 4 env-var footgun).

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
