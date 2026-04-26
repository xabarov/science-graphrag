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
| 2026-04-26 | **BT6 P0 quote tolerance (barrier 1):** `science_graphrag/ingestion/claims/quote_match.py` (NFKC / dashes / nbsp / `×`→`x` / letter–digit spacing + `find_fuzzy_substring`); 4-level `_quote_accepted` + chunk pre-normalize in `extract_claims_llm`; `eval/claims/article_source.read_claims_article`; tests `tests/ingestion/claims/`. Write-up: [`docs/analysis/wave5-bt6-quote-tolerance-2026-04-26.md`](../analysis/wave5-bt6-quote-tolerance-2026-04-26.md). Barrier 2 (gold semantics, `trust_signal live`) — OPEN item ниже. |
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

## Queue

### [OPEN] BT6 gold realism + optional embedding-soft quote fallback
- **Area:** `eval/claims/`, `tests/fixtures/benchmarks/claims/`, `science_graphrag/ingestion/claims/quote_match.py`
- **Issue:** **P0 quote gate (barrier 1) — [DONE 2026-04-26]** (см. Completed выше + [`wave5-bt6-quote-tolerance-2026-04-26.md`](../analysis/wave5-bt6-quote-tolerance-2026-04-26.md)). Остаётся: после P0 PDF-noise barrier снят (`corpus_ssd_v2` + Mistral: 28/28 quotes accepted в одном прогоне), но `claim_recall` на BT6 ограничен **семантикой** gold (`expected_claims[].claim_text_normalized` / `match_mode` vs выход production extractor — barrier 2). Отдельно: часть моделей даёт **truncated** tool JSON до Pydantic (наблюдение: Minimax + distracted body).
- **Proposal:** (1) Reformulate `expected_claims[].claim_text_normalized` toward achievable paraphrases for the production path; add an `aspirational_v2` tier for abstract “principle” gold without CI gating. (2) Optional level-5 in `_quote_accepted`: sentence-window cosine (τ≈0.85) **only** with `claims_quote_embedding_fallback=true`, **replacing** stored `quote` with the nearest real subspan and `evidence.requires_review=true`.
- **Acceptance:** BT6 mini / `corpus_ssd_v2` (or `claims_paraphrase_bt6_mini` tier) reaches **≥ 0.55** `claim_recall` on `mistralai/mistral-small-3.2-24b-instruct` with `--extractor production`; distracted lane completes without LLM JSON truncation under the same provider settings used in CI smoke.
- **Raised:** 2026-04-26 (post P0 quote tolerance).

### [OPEN] Split `scripts/aggregate_benchmark_metrics.py` (BT1 follow-up)
- **Area:** `scripts/aggregate_benchmark_metrics.py` (~1100 lines after Wave 3 BT4/BT5 additions).
- **Issue:** Summarizers (`_summarize_*`), markdown render (`_md_*`), CLI `main()`, family logic all live in one file; hard to review and parallel-edit with BT2–BT12 aggregator deltas. File grows with each wave.
- **Proposal:** Extract modules: `scripts/benchmark_aggregator/summarizers.py` (`_summarize_*`), `scripts/benchmark_aggregator/markdown.py` (`_md_*` + `_render_markdown`), `scripts/benchmark_aggregator/family_retrieval.py` (retrieval family assembly), `scripts/benchmark_aggregator/family_claims.py` (claims/refs/concept). Keep thin CLI in `aggregate_benchmark_metrics.py` (≤ 250 LoC). Trust/decision glue stays in `science_graphrag/benchmarks/`.
- **Acceptance:** `aggregate_benchmark_metrics.py` ≤ 250 LoC; `python scripts/aggregate_benchmark_metrics.py` unchanged CLI contract; pytest benchmarks + aggregate smoke pass; no file in `scripts/benchmark_aggregator/` exceeds ~400 LoC.
- **Raised:** 2026-04-26 (post-BT1); updated 2026-04-26 (post-Wave 3, now ~1100 LoC).

### [OPEN] Migrate dual_validate extractors to instructor (Phase 7 task)
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
- **Proposal:** см. `docs/adr/021-openrouter-bge-m3-embeddings.md`. Шаги: (1) добавить `SCIENCE_GRAPHRAG_EMBEDDING_MODEL=baai/bge-m3` в `.env` и `Settings`, (2) plumb provider через `science_graphrag/ingestion/{layer1,layer2,claims}_pipeline.py` (заменить hash-fallback fallback chain), (3) drop+recreate `works`, `claims` Qdrant collections с vector_size=1024, (4) reingest всё корпуса (10-15 мин, $1-2 за embeddings), (5) rerun BT1-BT5 retrieval benchmarks, (6) update `decision_gate` thresholds если потребуется.
- **Acceptance:** все retrieval benchmarks (workspace_scoped_live, hybrid_ablation_v2, multihop_v2, live_corpus_methods_*, judge_pilot) либо стабильны либо улучшились vs baseline; `qdrant info` показывает 1024-dim collections; `Settings.embedding_model == "baai/bge-m3"`; нет hash-fallback кода в production paths.
- **Risks:** hard cutover (не A/B, нельзя rollback без re-ingest); outbound network dependency на OpenRouter в ingestion path (раньше было self-contained); retrieval gates могут сдвинуться.
- **Raised:** 2026-04-25 (out of scope of Phase 6.D — отдельная сессия)


### [OPEN] Fix pre-existing isort/black violations in ingest_jobs and idea_workflow
- **Area:** `science_graphrag/api/ingest_jobs.py`, `science_graphrag/agent/idea_workflow.py`
- **Issue:** `isort` and `black --check` fail on these two files (not touched by Round 5; pre-existing).
- **Proposal:** run `isort` and `black` on those paths from repo root (`.venv/bin/isort`, `.venv/bin/black`).
- **Acceptance:** `black --check` and `isort --check-only` over `science_graphrag/` report no issues.
- **Raised:** 2026-04-25 (Round 5 review)

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

### [OPEN] LX1 integration: wire build_llm_semaphore_map into translation SSE handler
- **Area:** [`science_graphrag/utils/llm_semaphore.py`](../../science_graphrag/utils/llm_semaphore.py), translation worker/endpoint (LX2 dependency)
- **Issue:** `build_llm_semaphore_map` создан как фундамент LX1, но ни один production-путь его пока не вызывает. Конкурентность translation/claims/summary LLM-вызовов не ограничена.
- **Proposal:** В translation SSE endpoint/worker (будущий LX2) передавать `semaphore_map["translation"]` как `asyncio.Semaphore`; аналогично для claims и summary в соответствующих точках.
- **Acceptance:** При параллельных translation-запросах система соблюдает `llm_concurrency_translation`; integration-тест или нагрузочный smoke-check.
- **Synergy:** LX2 → LX1 → интеграция.
- **Raised:** 2026-04-26

<!-- Example:
### [OPEN] Example — tighten retrieval module boundaries
- **Area:** `science_graphrag/api/retrieval.py`, related services
- **Issue:** …
- **Proposal:** …
- **Acceptance:** …
- **Raised:** 2026-04-06
-->
