# Backend refactor backlog

Planned structural work for Python packages under this repo (not day-to-day lint fixes).

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- One theme per pass when possible (e.g. only `retrieval` layer, or only CLI layout).

## Completed (archive)

Длинная таблица закрытых волн (2026-04 — 2026-05-13) **убрана**: детали в git, ADR, runbooks и `docs/analysis/`.

**Краткие ориентиры:** transport/SSE — `api/agent_v2_modules/stream_lifecycle.py` + `stream_phase_*`; хвост по рёбрам — см. OPEN «Split oversized agent edges…» / `react_edges.py`. Недавние закрытия по ingest/registry/finalize — в git, здесь не дублируем.

## Queue

Закрытые темы **не** ведутся отдельными карточками `### [DONE]` — только **OPEN** / **PARTIAL** ниже. История закрытых шагов — в git; в backlog остаются **Issue / Proposal / Acceptance / Remaining**.

### Next wave (backend, 2026-05-14+) — SSE/runtime seams after stream-path closure

Sequencing after **SSE stream lifecycle split** (`stream_lifecycle.py` + `stream_phase_*`). Источники: [`agent-engine-next-horizon-2026-05-13.md`](../analysis/agent-engine-next-horizon-2026-05-13.md) (§4.2 R4-next, §6.3 API seams, §R3 измеримость), [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](../analysis/agent-engine-and-benchmarks-next-waves-2026-05-09.md) (E1/E2 operator gate, paired compare).

#### Wave charter (большая взаимосвязанная волна)

- **Name:** `R4/R3 evidence spine: terminals -> live compare -> API seams`
- **Goal:** закрыть один end-to-end контур для безопасного расширения subagent runtime: сначала корректные terminal-инварианты и наблюдаемость long-thread lane, затем парное latency-сравнение, затем структурная стабилизация API seams и unit safety-net.
- **Scope linkage:** W1 + W3 + W2 + W5 + W4 (именно в этом порядке зависимостей); OPEN `Split oversized agent edges...` остаётся companion-track для `react_edges.py` после стабилизации терминалов и coverage.
- **Global acceptance gate:** (1) terminal states согласованы между SSE / `run_metadata` / fork legs, (2) long-thread lane либо проходит, либо fail-fast с machine-readable reason, (3) baseline-vs-candidate compare на одном контуре даёт интерпретируемый latency verdict, (4) refactor API seams не меняет контракт parity/smoke.

| ID | Theme | Acceptance (минимум) |
|----|--------|----------------------|
| **W1** | **R4-next: termination / cancel инварианты spawned-child (fanout≤1)** | При отмене/таймауте дочернего run — терминальный статус (`failed`/`killed`/`timed_out`), нет противоречивого «успешного» merge vs факт; цепочка parent→child→terminal согласована в SSE + `run_metadata`; зелёны `test_api_agent_v2_*` parity; один сценарий зафиксирован в trace-review артефакте. Стыкуется с Queue OPEN «Real subagent runtime v3…» и «Unify subagent lifecycle event contract…» (один адаптер терминалов). |
| **W2** | **Парный live baseline vs candidate + latency compare** | Два артефакта на **одинаковом** suite / `workspace_id` / контуре; в compare явно `latency_p95_ms` (и policy регрессии по horizon ≤25% unless waived); вывод operator: в бюджете / вне бюджета. |
| **W3** | **R3: стабилизация long-thread / compaction live lane** | Закрыть или существенно продвинуть Queue OPEN «Stabilize focused long-thread live probe…»: heartbeat per-turn, fail-fast с `failure_kind` / `failed_turn` без ручного `kill -9`. |
| **W4** | **Дожим split `api/agent_v2.py` после freeze SSE контракта (R2)** | Продолжить Queue **[PARTIAL] Split `api/agent_v2.py`…**: вынести оставшиеся seams (или переименовать пакет в `api/agent_v2/` с shims); каждый новый модуль ≤300 LoC где применимо; `test_api_agent_v2_smoke.py` + ключевые parity без контрактных сдвигов. |
| **W5** | **Unit coverage для `stream_phase_*` entrypoints** | Расширить Queue OPEN «Targeted backend test coverage…» для горячих фаз: минимум по одному контрактному тесту на `stream_phase_tool_events`, `stream_phase_subagent_events`, `stream_phase_routing_leg_abort` (error/edge paths), без дублирования полного `stream_parity` в каждом файле. |

**Примечание:** W1–W3 — измеримость и безопасность перед расширением fanout/async; W4–W5 — снижение стоимости следующих правок transport vs runtime.

### Backend structural audit refresh (2026-05-14)

Повторный аудит backend показал две категории долга:

- **Layering:** `StoreRegistry` neutralized under `science_graphrag/stores/registry.py` (API deps remain thin `Depends`); Dramatiq worker + ingest execution import neutral `science_graphrag/ingestion/jobs/*` (`registry`, `single_document_ingest`, `batch_parent_ingest`); `api/ingest/registry.py` remains a compatibility shim for API routers/tests.
- **Size hotspots:** `config.py` (~605 LoC after agent-runtime mixin extract), `science_graphrag/api/benchmark/` package (router split across `routes_catalog.py` / `routes_runs.py` + helpers; thin `task_store.py` facade + `benchmark_task_store_core.py`), `api/works/graph_neighborhood.py` (~184 orchestrator; payload in `graph_neighborhood_payload.py` ~384; aggregation in `graph_neighborhood_aggregation.py` ~328), `settings/service.py` (~398; snapshot assembly in `settings/snapshot_materialize.py`; merge in `service_runtime_merge.py`), `agent/context/thread_insights.py` (~484 after policy + session-control extract), `agent/context/session_backend.py` (~537), `scripts/live_check/trace_review/agent_trace_review_orchestrator.py` (~522; thin `agent_trace_review.py` delegates here), `scripts/live_check/agent_od_workspace_e2e_audit.py` (~360; suites/retry/query/report in `agent_od_audit/`), `scripts/dual_validate/extractors/retrieval_v1.py` (~700 after splits: `retrieval_v1_ranking.py`, `retrieval_v1_schema.py`, `retrieval_v1_inventory.py`, `retrieval_v1_prompts.py`), `storage/qdrant_store/chunk_store.py` (~178 facade; read/write in `chunk_store_read.py` / `chunk_store_write.py`; filters in `chunk_filters.py`), `api/agent_v2_modules/stream_phase_finalize.py` (~279), `ingestion/_pipeline_impl.py` (~310 after CLI/corpus extraction).

Existing `[PARTIAL]` items already cover `api/benchmark.py`, `settings/service.py`, ingest pipeline/resume (`resume_ingest`, `_pipeline_impl` seams), `tool_search.py`, and `api/agent_v2.py` packaging. New items below track gaps not covered by those tickets.

### [PARTIAL] Decompose monolithic `Settings` model by domain
- **Area:** `science_graphrag/config.py`, `science_graphrag/settings/`, `science_graphrag/cli/config_commands.py`
- **Issue:** `config.py` is ~605 LoC (agent-runtime mixin applied) and still mixes storage, ingest, LLM, agent, benchmark, OCR/VL, and runtime rollout fields in one `Settings` model. This creates high conflict churn and makes it hard to audit constants/settings policy by domain.
- **Proposal:** Split field groups into domain modules or mixins (`config_fields/agent.py`, `ingest.py`, `storage.py`, `llm.py`, `benchmarks.py`) with a single assembled `Settings` class and preserved public import path `from science_graphrag.config import Settings`.
- **Acceptance:** No domain config file exceeds ~400 LoC; env names and `Settings` field names remain stable; `science-graphrag config-check` and settings/config tests pass; constants/settings policy remains explicit for operator-facing knobs.
- **Raised:** 2026-05-14

### [PARTIAL] Split graph neighborhood response assembly
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`, `science_graphrag/api/works/graph_neighborhood_payload.py`, `science_graphrag/api/works/graph_neighborhood_institutions.py`, `science_graphrag/api/graph_reader_projection/`, `science_graphrag/api/workspace_graph/`
- **Issue:** Reader vs raw assembly, counters, truncation metadata, and legacy aggregation knobs are split across modules, but **view-specific** builders (`reader_payload` / `raw_payload`) and shared truncation/display helpers are still not isolated — the next graph UX change can still touch multiple files.
- **Proposal:** Extract view-specific payload builders (`reader_payload.py`, `raw_payload.py`), center-node/counter mapping, and truncation/display metadata helpers on top of the existing `graph_reader_projection` package. Keep the router-facing module as orchestration and compatibility glue.
- **Acceptance:** `graph_neighborhood.py` <= ~350 LoC; reader/raw JSON contract unchanged; graph tests (`tests/test_works_graph_*`, `tests/test_workspace_graph_api.py`) pass; adding a graph display field does not require editing raw and reader paths in one god-module.
- **Raised:** 2026-05-14

### [PARTIAL] Split Qdrant chunk store query/write/schema responsibilities
- **Area:** `science_graphrag/storage/qdrant_store/chunk_store.py`
- **Issue:** Facade + `chunk_store_read` / `chunk_store_write` / `chunk_search` exist, but filter construction, payload mapping, and schema/migration assumptions can still churn together when retrieval/Qdrant contracts evolve.
- **Proposal:** Split into focused modules such as `chunk_filters.py`, `chunk_queries.py`, `chunk_writes.py`, and `chunk_payloads.py`, with `chunk_store.py` retaining the public adapter/facade.
- **Acceptance:** Each module has a narrow public surface; Qdrant integration tests and any retrieval tests using chunk search pass; payload schema changes are localized to mapping/schema helpers.
- **Raised:** 2026-05-14

### [PARTIAL] Deepen agent context modules after long-thread delivery
- **Area:** `science_graphrag/agent/context/thread_insights.py`, `science_graphrag/agent/context/session_backend.py`, prompt/memory policy tests
- **Issue:** Long-thread acceptance is functionally closed, but `thread_insights.py` (~612 LoC) and `session_backend.py` (~537 LoC) remain large modules mixing chunking/synthesis/persistence audit and session storage/policy concerns. Future memory changes will be expensive to review.
- **Proposal:** Split `thread_insights` into a package (`chunking.py`, `synthesis.py`, `persistence.py`, `audit.py`) and separate session storage adapter concerns from policy/serialization in `session_backend`.
- **Acceptance:** `thread_insights.py` becomes a thin facade or is replaced by a package with no file > ~400 LoC; `tests/test_thread_insights.py`, `tests/test_prompt_memory_policy.py`, and long-thread eval tests pass; memory influence audit remains stable.
- **Raised:** 2026-05-14

### [OPEN] Reduce live-check entrypoint size after trace-review split
- **Area:** `scripts/live_check/trace_review/agent_trace_review_orchestrator.py`, `scripts/live_check/agent_od_workspace_e2e_audit.py`, `scripts/live_check/agent_trace_review.py`
- **Issue:** `agent_trace_review.py` is now a thin wrapper, but the heavy orchestration still sits in `trace_review/agent_trace_review_orchestrator.py` (~522 LoC after submodule split); OD E2E entrypoint remains large (~839 LoC). Together they still mix CLI/suite registry, subprocess orchestration, heartbeat policy, artifact writing, and rendering.
- **Proposal:** Move suite registry, stage execution, artifact writer, and OD E2E audit assembly into dedicated modules under `scripts/live_check/trace_review/` or adjacent packages; leave entrypoints as thin CLI orchestration.
- **Acceptance:** CLI entrypoints stay thin (`agent_trace_review.py` facade) and orchestrators are split to <= ~250–300 LoC modules where practical; existing CLI flags and artifact schema stay compatible; `tests/scripts/live_check/*` pass; long-running heartbeat/timeout diagnostics remain visible.
- **Raised:** 2026-05-14

### [OPEN] Split dual-validate retrieval extractor
- **Area:** `scripts/dual_validate/extractors/retrieval_v1.py`, `scripts/dual_validate/extractors/base.py`
- **Issue:** `retrieval_v1.py` is still ~700 LoC (extractor classes + report assembly) after moving prompts/schemas/inventory/ranking helpers out; further splits are needed to reach the acceptance target.
- **Proposal:** Extract retrieval-specific matching/scoring and summary rendering into helper modules, keeping the extractor class focused on loading inputs, calling the LLM client, and composing the result.
- **Acceptance:** `retrieval_v1.py` <= ~350 LoC; shared extractor tests and retrieval dual-validate fixtures pass; adding a retrieval metric does not require editing prompt/client orchestration.
- **Raised:** 2026-05-14

### [PARTIAL] Split oversized `tool_search.py` after hybrid / web selector growth
- **Area:** `science_graphrag/agent/tool_search.py`, `tool_selector_hybrid.py`, optional `agent/tools/web_research_tools.py` call-sites
- **Issue:** `tool_search.py` still mixes rules scoring, discovery merge, strict-deferred telemetry, and hybrid rerank orchestration; further growth will reintroduce a god-module.
- **Proposal:** If growth exceeds ~700 LoC again, extract a subpackage or move hybrid glue behind a narrow interface; keep scoring/discovery helpers as separate modules (already split partially).
- **Acceptance:** No regression in tool selection tests; orchestration program stays unblocked.
- **Remaining:** further subpackage or hybrid glue extraction if file size/regression pressure returns.
- **Raised:** 2026-05-06 (hybrid selector + external research slice)

### [PARTIAL] Stable error_class enum on `error` SSE — extend coverage
- **Area:** `science_graphrag/api/agent_v2_modules/errors.py` (`classify_agent_stream_error`), `docs/specs/agent-chat-v1.md`
- **Issue:** Classifier covers common paths, but real-world failures (LangChain validation, langgraph deadline before tool call, instructor parse failures) can still collapse to `internal_error`.
- **Proposal:** Walk recent traces (`eval/results/trace-review-*.json`) and add discriminator branches for the most common opaque error kinds; keep the small enum (`provider_*`, `internal_error`) and document each new code in `chat-errors.md` / spec.
- **Acceptance:** ≥80% of `error` events from a recent live run land on a non-`internal_error` class; UI ships a localized message for each new class via `chat.errors.<error_class>`.
- **Remaining:** measure non-`internal_error` share on a fixed live/trace set (acceptance ≥80%); add `chat-errors.md` if the spec grows.
- **Raised:** 2026-05-05 (readable-stream-events plan)

### [PARTIAL] Evaluate `agent_note` token cost on 50 typical turns
- **Area:** `science_graphrag/agent/notes.py`, `science_graphrag/api/agent_v2_modules/stream_lifecycle.py` (`emit_agent_note`), `docs/specs/agent-chat-v1.md`, eval harness
- **Issue:** `agent_note_enabled=False` by default (off-by-default LLM extra). Before flipping default for a pilot we need cost evidence: tokens per turn, latency added (with `agent_note_max_per_turn=2`), and any visible-quality gain over plain `product_step` headlines.
- **Proposal:** Run a small benchmark batch (50 turns across `inventory` / `grounded_explanation` / `relation_tracing`) with `agent_note_enabled=True` and a stubbed-cheap model; compare turn-level `usage.total_tokens` and end-to-end p50 / p95 latency vs. baseline; record the result in `docs/analysis/`.
- **Acceptance:** ADR-light note in `docs/analysis/` with «pilot / postpone / drop» recommendation and concrete numbers; UI changelog flag updated.
- **Decision (R2 / 2026-05-13):** **postpone** default-on pilot — `agent_note` stays **optional** and outside the canonical minimal chat contract until product requests live numbers; see [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) §**R2 product contract** and [`docs/analysis/r2-chat-contract-closeout-2026-05-13.md`](../analysis/r2-chat-contract-closeout-2026-05-13.md).
- **Remaining:** operator-owned **live** 50-turn run with token/latency table filled in.
- **Raised:** 2026-05-05 (Cursor-like agent progress plan)

### [PARTIAL] Ingest resume — claims + Neo4j selective rebuild
- **Area:** `science_graphrag/ingestion/resume_ingest.py`, `science_graphrag/storage/neo4j/writes/works.py`
- **Issue:** `ingest-resume-embed` only repopulates chunk + work-summary vectors in Qdrant; it does not re-extract claims or refresh `CITES` titles when those stages were skipped or half-written.
- **Proposal:** Add optional `--stages claims,references` (or separate CLI) that reuses `normalized.md` + Neo4j `work_id`, re-runs LLM stages with idempotent upserts, and aligns checkpoint keys. **Interim operator path:** `scripts/backfill_workspace_claims.py` (chunks in Qdrant → LLM claims → Neo4j + Qdrant claims collection; JSONL progress).
- **Acceptance:** Integration test on a fixture document that forces embed failure then resumes claims+embed without duplicating layer1 Work nodes.
- **Remaining:** broaden resume scenarios / edge cases if they show up in ops; keep PARTIAL because scope spans CLI + Neo4j + checkpoint.
- **Raised:** 2026-04-27 (stage-safe ingest follow-up)

### [PARTIAL] VL JSON parse error for DN-DETR.pdf (reproducible)
- **Area:** `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/ingestion/llm/raw_openai_transport.py`
- **Issue:** `DN-DETR.pdf` (13 pages, `doc_id=dff05d47`) fails VL 3/3 times with `Expecting value: line 585 column 1 (char 3212)` — OpenRouter/chat-completions wrappers occasionally return **non-JSON bodies** despite HTTP 200, which breaks `response.json()` parsing.
- **Proposal:** (1) Normalize transport errors + raise a typed error for non-JSON bodies. (2) Harden VL response parsing (`message.content` variants, markdown fences). (3) Provide clean fallback + structured diagnostics.
- **Acceptance:** Stable operator behavior: non-JSON VL responses do not explode with opaque tracebacks; fallback path emits structured ingest diagnostics suitable for auditing.
- **Remaining:** DN-DETR acceptance (“VL processes all pages, `markdown_source=vl`”) is still provider/model dependent — track separately if 100% VL markdown is required for this PDF family.
- **Raised:** 2026-04-26

### [PARTIAL] reuse_cached_markdown cache-collision: too many fallback paths
- **Area:** `science_graphrag/ingestion/cache_policy.py`, `science_graphrag/ingestion/orchestrator.py`, `science_graphrag/cli/main.py`
- **Issue:** legacy markdown cache lookups can silently reuse unexpected on-disk artifacts (slug-based copies / multiple roots), causing `cached-normalized` skips when operators expect a forced re-extract.
- **Proposal:** (1) explicit operator bypass for cache reuse; (2) louder logging for cache hits; (3) long-term: single canonical cache keying by `document_id` only.
- **Acceptance:** Re-ingest of any document with `--no-cache` always runs VL/pypdf regardless of what's on disk; no `cached-normalized` in diagnostics after explicit force-re-ingest.
- **Remaining:** one-shot migration of old artifacts to document-scoped keys; collapse remaining ambiguous roots; new writes use canonical `document_id` only.
- **Raised:** 2026-04-26

### [PARTIAL] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Area:** `science_graphrag/api/graph_display.py`, `science_graphrag/api/works/graph_neighborhood.py`, `science_graphrag/api/workspace_graph/projection.py`
- **Issue:** Backend exposes semantic `node_kind`, edge display mapping, and priority-aware `LIMIT` metadata (`meta.skipped_by_kind`), but the graph canvas still renders raw Neo4j edge types — users do not get the intended legend/semantics until frontend catches up.
- **Proposal:** Wire UI to `EDGE_DISPLAY_TYPE` / semantic labels and skipped-kind metadata (frontend wave GR6).
- **Acceptance:** priority kinds (`Method`,`Dataset`,`Work`) survive truncation in API responses; UI legend renders semantic edge labels (tracked primarily in frontend backlog/analysis).
- **Remaining:** frontend integration — see [`docs/analysis/graph-readability-followup-2026-04-25.md`](../analysis/graph-readability-followup-2026-04-25.md).
- **Raised:** 2026-04-25

### [PARTIAL] Split benchmark backend hubs: `api/benchmark.py` (1249) + `api/task_store.py` (593)
- **Area:** `science_graphrag/api/benchmark.py`, `science_graphrag/api/task_store.py`, `science_graphrag/api/benchmark_profiles.py`
- **Issue:** `task_store.py` частично разгружен (persistence вынесен в `science_graphrag/storage/benchmark_run_persistence.py`, сериализация — в `science_graphrag/api/task_benchmark_serializers.py`), но `benchmark.py` остаётся главным god-router (fixture catalog + case detail + compare + graph preview + eval integration) и продолжает расти. Глубина seam'ов низкая: добавление нового benchmark family всё ещё требует правок в центральном роутере.
- **Proposal:** зафиксировать новый target split: (1) `api/benchmark.py` → подпакет `api/benchmark/{router,catalog,case_detail,compare,graph_preview}.py`; (2) `task_store.py` добить до orchestration-only слоя с явными adapter seams к persistence/serialization.
- **Acceptance:** `api/benchmark.py` как входной router <= 300 LoC; новые benchmark families добавляются через `catalog` adapter без изменения compare/preview модулей; `task_store.py` не содержит JSON snapshot plumbing и не знает layout on-disk артефактов.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap-2026-04-24.md` — каждое семейство не упирается в god-файл.
- **Remaining:** основной сплит на `api/benchmark/{router,catalog,case_detail,compare,graph_preview}.py` и финальный orchestration-only `task_store.py`.
- **Raised:** 2026-04-25, updated 2026-05-05

### [PARTIAL] Standardize ingestion LLM seams around structured executor
- **Area:** `science_graphrag/ingestion/llm/`, `science_graphrag/ingestion/claims/extractor.py`, `science_graphrag/ingestion/vl_pdf.py`, `science_graphrag/ingestion/_pipeline_impl.py`
- **Issue:** production ingestion still mixes patterns: metadata/authorships/references/semantic go through `SyncInstructorExtractor` + shared `run_extraction`, but claims and VL paths diverge in diagnostics/retry/test surface.
- **Proposal:** (1) move claims onto the same structured seam: shared schema modules + `run_extraction(...)` + typed diagnostics; (2) extractor factory/presets from `Settings` instead of manual `SyncInstructorExtractor` wiring per call-site; (3) VL stays non-Instructor but shares low-level transport/telemetry; (4) document `stage -> seam` matrix in architecture/docs + tests.
- **Acceptance:** all production `text/chunks -> typed structured object` stages share schema modules and one executor contract; claims drops bespoke `extract_maybe(...)` protocol; client construction centralized; diagnostics vocabulary aligned; VL uses shared transport helper for timeout/error handling.
- **Reference:** `docs/analysis/ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`
- **Synergy:** **Wave N/O** (ontology), **Wave Y2** (LangGraph tool graph) — shared executor can later swap to `langchain_core` without rewriting orchestrators.
- **Remaining:** finish factory/executor rollout across stages; align diagnostics keys across ingest report consumers.
- **Raised:** 2026-04-27 (structured executor standardization; see also historical context 2026-04-25 in the analysis doc).

### [PARTIAL] Settings service split (historically ~1k LoC; now ~432 in `service.py`)
- **Area:** `science_graphrag/settings/service.py`, `science_graphrag/api/settings.py`, `science_graphrag/settings/snapshot_*.py`, `science_graphrag/settings/snapshot_materialize.py`
- **Issue:** `SettingsService` still orchestrates runtime overrides merge, secret-aware LLM config/test, multi-section snapshot assembly, and security/diagnostics output in one module — further API growth risks hidden regressions.
- **Proposal:** extract `settings/runtime_overlay.py` (merge + validation), keep snapshot DTO assembly in focused `snapshot_*` modules, add `settings/llm_probe.py` (test connection + OpenAI/OpenRouter probes); leave `SettingsService` as a thin facade.
- **Acceptance:** `settings/service.py` <= 350 LoC; unit tests cover overlay/snapshots/probes in isolation; API layer tests wiring only.
- **Remaining:** extract `llm_probe` + schema/update groups; keep file size under the acceptance threshold.
- **Raised:** 2026-04-25, updated 2026-05-05

### [PARTIAL] Split `cli/main.py` (566) by command groups
- **Area:** `science_graphrag/cli/main.py`
- **Issue:** Основная разборка по command groups уже сделана, `cli/main.py` now ~47 LoC. Remaining debt is incomplete grouping (`neo4j`, future `worker`) and keeping `main.py` as registry-only as new commands land.
- **Proposal:** `cli/{ingest,neo4j,qdrant,dedup,worker}.py`, тонкий `cli/main.py` собирает Typer-app из подкоманд.
- **Acceptance:** ни один файл > ≈200 строк; запуск `science-graphrag --help` идентичен.
- **Synergy:** **Wave W** добавит `cli/worker.py` (запуск Dramatiq) без раздувания main.
- **Remaining:** extract `cli/neo4j_commands.py` and `cli/worker.py` when worker-runner scope lands, to match the full command-group split from Proposal.
- **Raised:** 2026-04-25, updated 2026-05-05

### [PARTIAL] Split `api/agent_v2.py` orchestration seams (historically 995; now thin facade)
- **Area:** `science_graphrag/api/agent_v2/`, `science_graphrag/api/agent_v2_modules/stream_lifecycle.py`, `science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_stream.py`
- **Issue:** Router/digest facade now lives in package `api/agent_v2/`; main SSE loop moved to `stream_lifecycle_graph_stream.py` (~310 LoC) with `stream_lifecycle.py` as re-exports + shortcut path. Lazy `build_retrieval_graph` indirection via `stream_lifecycle` preserves test monkeypatch surface.
- **Proposal:** further shrink `stream_lifecycle_graph_stream.py` if it grows; optional companion split for `react_edges.py` transport glue.
- **Acceptance:** each module ≤300 LoC where practical; SSE protocol edits do not require editing business orchestration; `test_api_agent_v2_smoke.py` and trace-audit tests pass without contract drift.
- **Remaining:** optional further SSE splits; companion OPEN «Split oversized agent edges…» for `react_edges.py` transport glue.
- **Raised:** 2026-05-05, updated 2026-05-14

### [PARTIAL] Split ingest pipeline orchestration seams (`ingestion/_pipeline_impl.py`)
- **Area:** `science_graphrag/ingestion/_pipeline_impl.py`, `science_graphrag/ingestion/stages/*`, `science_graphrag/ingestion/checkpoint.py`
- **Issue:** `_pipeline_impl.py` shrank substantially (~310 LoC after moving batch/single-file CLI entrypoints to `pipeline_cli_entrypoints.py` and corpus discovery to `corpus_discovery.py`), but further stage-registry work remains.
- **Proposal:** continue toward deep modules: `ingestion/orchestrator.py` (stage graph + resume contract), `ingestion/progress_store.py` (JSONL progress/checkpoint IO), `ingestion/cache_policy.py` (markdown cache lookup/reuse), `ingestion/document_runtime.py` (per-document execution context).
- **Acceptance:** `_pipeline_impl.py` <= 400 LoC facade; modules expose narrow interfaces with unit tests for resume/cache/timeout branches; new ingest stages plug into a declarative stage registry without growing a god-file.
- **Remaining:** stage registry / declarative graph (if we remove remaining conditional branches in orchestrator) + final migration of tests/scripts off legacy import paths. `ingestion/pipeline.py` is the public facade; private export surface from `_pipeline_impl` should stay minimal.
- **Raised:** 2026-05-05

