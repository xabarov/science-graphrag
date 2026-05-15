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

**Progress (implementation through 2026-05-15):** W1 — `terminal_truth` + runtime merge/patch invariants; contract tests in `tests/agent/test_subagent_terminal_truth.py`. W2 — runbook [`docs/runbooks/trace-review-w2-paired-latency-compare.md`](../runbooks/trace-review-w2-paired-latency-compare.md) + [`paired_trace_review_w2.py`](../../scripts/live_check/paired_trace_review_w2.py) (default +25% `latency_p95_ms` cap → `operator_latency_verdict`, verdict values `in_budget` / `warn_band` / `out_of_budget`). W3 — compaction JSON `heartbeat_contract`, stderr `compaction_turn_wait_heartbeat`, plus `stop_reason` / `fail_fast`; helper `_log_turn_fail_stderr`. W4 — [`stream_lifecycle_graph_abort_specs.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_abort_specs.py) + `stream_lifecycle_graph_stream.py` (~363 LoC; optional further chunk-loop split if growth resumes). W5 — dedicated contract modules: `tests/test_api_agent_v2_modules_stream_phase_{tool_events,subagent_events,routing_leg_abort}_contract.py` + existing `stream_phases_contracts.py`. Trace-review split: thin [`agent_trace_review_orchestrator.py`](../../scripts/live_check/trace_review/agent_trace_review_orchestrator.py) + [`orchestrator_argparse.py`](../../scripts/live_check/trace_review/orchestrator_argparse.py) / [`orchestrator_main_runner.py`](../../scripts/live_check/trace_review/orchestrator_main_runner.py). **Operator/live-check depth (2026-05-14):** [`orchestrator_run_artifacts.py`](../../scripts/live_check/trace_review/orchestrator_run_artifacts.py) facade + [`artifact_pipeline.py`](../../scripts/live_check/trace_review/artifact_pipeline.py) / [`artifact_writers.py`](../../scripts/live_check/trace_review/artifact_writers.py); compaction package split `turn_executor` / `heartbeat_monitor` / `result_aggregator` / `report_schema` / `parsed_args`; tests [`test_trace_review_artifact_modules.py`](../../tests/scripts/live_check/test_trace_review_artifact_modules.py). Evidence skeleton unchanged. **Remaining wave work:** live operator fill for 50-turn `agent_note` numbers; optional `stream_lifecycle_graph_stream` chunk-phase extract if file crosses ~400 LoC again; next operator pass — shrink [`artifact_pipeline.py`](../../scripts/live_check/trace_review/artifact_pipeline.py) complexity; OD E2E audit split; [`http_suite.py`](../../scripts/live_check/http_suite.py) size.

**Wave status (2026-05-15):** W1–W5 **baseline deliverables are in tree**; global acceptance gate (4 bullets in charter) is **partially met** — live contour evidence and long regression compare remain operator-owned before calling the wave “closed”.

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

**Примечание:** W1–W3 — измеримость и безопасность перед расширением fanout/async; W4–W5 — снижение стоимости следующих правок transport vs runtime. **W2 (контракт):** в `trace_regression_compare` / `paired_trace_review_w2` поле `operator_latency_verdict.verdict` — `in_budget` / `warn_band` / `out_of_budget` / `unknown` (реализация: `scripts/live_check/trace_compare/policies.py`).

### Backend structural audit refresh (2026-05-15)

Глубокий пересмотр дерева `science_graphrag/` + `scripts/` (wc по `.py`, верхние хвосты). Цель — обновить **приоритеты** и не вести устаревшие цифры в карточках.

#### Size / churn heatmap (top-of-mind)

| Bucket | Representative paths (LoC, rounded) | Risk |
|--------|--------------------------------------|------|
| **Settings / config** | [`config_mixins/agent_runtime_fields.py`](../../science_graphrag/config_mixins/agent_runtime_fields.py) **~971**; [`config.py`](../../science_graphrag/config.py) **~546** | Любой флаг agent-runtime трогает огромный mixin; конфликты PR и сложность аудита констант. |
| **Offline / eval scripts** | `scripts/dual_validate/extractors/retrieval_v1.py` **~663**; `dedup_v1.py` **~513**; `triple_vote_consensus.py` **~473** | Долг уже заведён OPEN для `retrieval_v1`; соседние экстракторы масштабируются тем же паттерном. |
| **Live-check / operator** | [`compaction_turn_review.py`](../../scripts/live_check/compaction_turn_review.py) **~106** (entry) + [`compaction_review/`](../../scripts/live_check/compaction_review/) (`run` ~93 LoC, `turn_executor`, `report_schema`, …); [`trace_review/artifact_pipeline.py`](../../scripts/live_check/trace_review/artifact_pipeline.py) **~266**; [`http_suite.py`](../../scripts/live_check/http_suite.py) **~459** | R3/R4 evidence: compaction/trace artifact orchestration вынесены в подмодули; дальше — сжать `artifact_pipeline` / `http_suite`; OD E2E audit. |
| **Agent runtime** | [`agent/subagents/runtime.py`](../../science_graphrag/agent/subagents/runtime.py) **~540**; [`agent/tool_search.py`](../../science_graphrag/agent/tool_search.py) **~547**; [`agent/runtime.py`](../../science_graphrag/agent/runtime.py) **~462** | Транспорт графа vs tool orchestration; PARTIAL по `tool_search` остаётся актуальным. |
| **Ingest** | [`ingestion/resume_ingest.py`](../../science_graphrag/ingestion/resume_ingest.py) **~579**; [`document_orchestrator.py`](../../science_graphrag/ingestion/document_orchestrator.py) **~573**; [`ingestion/claims/extractor.py`](../../science_graphrag/ingestion/claims/extractor.py) **~454** | Resume + stage graph — отдельная волна от agent/SSE. |
| **API / benchmark** | Пакет [`api/benchmark/`](../../science_graphrag/api/benchmark/) **~1258** суммарно; hotspot [`inspector.py`](../../science_graphrag/api/benchmark/inspector.py) **~322**; [`benchmark_task_store_core.py`](../../science_graphrag/api/benchmark_task_store_core.py) **~572** | God-router `api/benchmark.py` **снят** в пользу подпакета; остаётся выравнивание «catalog vs inspector vs serializers». |
| **Agent v2 SSE** | [`stream_lifecycle_graph_stream.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_stream.py) **~363**; [`stream_phase_finalize_run_metadata.py`](../../science_graphrag/api/agent_v2_modules/stream_phase_finalize_run_metadata.py) **~234** | Ниже порога «400 LoC panic»; дальнейший split — по росту или по фазам chunk vs finalize glue. |
| **Graph API** | [`graph_neighborhood_payload.py`](../../science_graphrag/api/works/graph_neighborhood_payload.py) **~384**; [`workspace_graph/projection.py`](../../science_graphrag/api/workspace_graph/projection.py) **~453** | Совпадает с PARTIAL по graph neighborhood / reader-raw split. |
| **Agent context** | [`thread_insights.py`](../../science_graphrag/agent/context/thread_insights.py) **~477**; [`session_backend.py`](../../science_graphrag/agent/context/session_backend.py) **~137** | `session_backend` уже сжат; основной долг — `thread_insights` + политики памяти. |

#### Layering (кратко, без регресса)

- **Stores / ingest jobs:** по-прежнему нейтральный `stores/registry.py`, ingest jobs под `ingestion/jobs/*`, API shim `api/ingest/registry.py` — ок.
- **Agent v2:** пакет `api/agent_v2/` + `agent_v2_modules/stream_*`; lazy `build_retrieval_graph` через `stream_lifecycle` сохраняет monkeypatch surface для тестов — менять только осознанно.

#### Приоритизированные проходы рефакторинга (план на ближайшие волны)

Один проход = одна тема (см. `.cursor/rules/refactor-rhythm-and-backlog.mdc`).

1. **Operator / live-check depth** — продолжить OPEN «Reduce live-check…»: снизить сложность [`artifact_pipeline.py`](../../scripts/live_check/trace_review/artifact_pipeline.py) (ветвления / локальные переменные); при росте — ещё один слой для OD E2E [`agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py); [`http_suite.py`](../../scripts/live_check/http_suite.py). *Зависимости:* зелёные `tests/scripts/live_check/*`, без смены CLI контракта.
2. **dual_validate retrieval** — закрыть OPEN `retrieval_v1.py` ≤350 LoC (сейчас ~663); держать в одной волне только экстракторы, не смешивать с prod API.
3. **Settings domain split** — расширить PARTIAL по `Settings`: первый удар по [`config_mixins/agent_runtime_fields.py`](../../science_graphrag/config_mixins/agent_runtime_fields.py) (~971 LoC): нарезать по подсистемам (timeouts, subagent flags, side-LLM, compaction, …) с сохранением env имён; затем облегчить [`config.py`](../../science_graphrag/config.py).
4. **Agent context / memory** — PARTIAL «Deepen agent context»: фокус на [`thread_insights.py`](../../science_graphrag/agent/context/thread_insights.py) (~477 LoC); `session_backend` пересмотреть только если снова растёт.
5. **Benchmark package** — PARTIAL split benchmark: снизить [`inspector.py`](../../science_graphrag/api/benchmark/inspector.py) / укрепить границы catalog vs runs vs serializers; `task_store` довести до orchestration-only (см. карточку).
6. **Agent v2 optional** — если `stream_lifecycle_graph_stream` >~400 LoC или появляется вторая «фаза» в том же файле: вынести chunk-timeout/heartbeat loop в модуль рядом с `stream_lifecycle_graph_abort_specs.py`; не трогать SSE JSON контракт без parity-тестов.

*Параллельно вне этих волн:* ingest resume/VL/cache (существующие PARTIAL), Qdrant chunk split, error_class coverage — по операторскому давлению, не блокируя agent wave.

### [PARTIAL] Decompose monolithic `Settings` model by domain
- **Area:** `science_graphrag/config.py`, `science_graphrag/config_mixins/agent_runtime_fields.py`, `science_graphrag/settings/`, `science_graphrag/cli/config_commands.py`
- **Issue:** Корневой [`config.py`](../../science_graphrag/config.py) (~546 LoC) уже собран из mixins, но доминирующий объём сосредоточен в [`config_mixins/agent_runtime_fields.py`](../../science_graphrag/config_mixins/agent_runtime_fields.py) (**~971 LoC**): agent-runtime rollout, таймауты, subagent/tool flags, side-LLM, compaction и др. в одном файле — высокий churn и риск нарушить constants/settings policy при точечных PR.
- **Proposal:** (1) Распилить `agent_runtime_fields` на несколько mixins по подсистемам (`agent_runtime_subagent.py`, `agent_runtime_tools.py`, `agent_runtime_side_llm.py`, …) с **стабильными** именами полей и env. (2) Затем довести `config.py` до тонкой сборки + при необходимости вынести `CoreStorageFields` соседние куски. (3) Сохранить единый импорт `from science_graphrag.config import Settings`.
- **Acceptance:** ни один mixin-файл > ~400 LoC; `science-graphrag config-check` и тесты settings/config зелёные; operator knobs остаются в `Field(description=...)` где политика требует.
- **Raised:** 2026-05-14, **updated:** 2026-05-15

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
- **Issue:** [`thread_insights.py`](../../science_graphrag/agent/context/thread_insights.py) (~**477** LoC) всё ещё смешивает chunking, synthesis, persistence audit и политики влияния на промпт. [`session_backend.py`](../../science_graphrag/agent/context/session_backend.py) (~**137** LoC) после выносов уже не является главным hotspot — приоритет низкий, пока файл не растёт снова.
- **Proposal:** Split `thread_insights` into a package (`chunking.py`, `synthesis.py`, `persistence.py`, `audit.py`) and separate session storage adapter concerns from policy/serialization in `session_backend` **только если** снова появится рост или новая фича трогает оба слоя.
- **Acceptance:** `thread_insights.py` becomes a thin facade or is replaced by a package with no file > ~400 LoC; `tests/test_thread_insights.py`, `tests/test_prompt_memory_policy.py`, and long-thread eval tests pass; memory influence audit remains stable.
- **Raised:** 2026-05-14, **updated:** 2026-05-15

### [OPEN] Reduce live-check entrypoint size after trace-review split
- **Area:** `scripts/live_check/trace_review/orchestrator_main_runner.py`, `scripts/live_check/trace_review/orchestrator_argparse.py`, `scripts/live_check/trace_review/agent_trace_review_orchestrator.py`, `scripts/live_check/trace_review/artifact_pipeline.py`, `scripts/live_check/trace_review/artifact_writers.py`, `scripts/live_check/compaction_turn_review.py`, `scripts/live_check/compaction_review/*`, `scripts/live_check/agent_od_workspace_e2e_audit.py`, `scripts/live_check/agent_trace_review.py`
- **Issue:** Исторически оркестрация и compaction review были сосредоточены в крупных entry-модулях; это повышало стоимость правок R3/R4 evidence и heartbeat-политик.
- **Proposal:** (1) Нарезать `orchestrator_main_runner` по вертикали стадий (например `orchestrator_run_http_and_e2e.py`, `orchestrator_run_artifacts.py`, общий `orchestrator_run_context.py` для `run_context` / feature_flags). (2) Вынести из `compaction_turn_review` слой `httpx` + retry + сбор отчёта в подмодули `scripts/live_check/compaction_review/`. (3) Продолжить дробление OD audit в `agent_od_audit/` по мере роста.
- **Acceptance:** ни один модуль оркестрации не >~300 LoC где практично; CLI флаги и schema trace-review-v1 без регрессий; `tests/scripts/live_check/*` зелёные; heartbeat/timeout диагностика остаётся видимой в stderr и в JSON.
- **Remaining (2026-05-14 follow-up):** `orchestrator_main_runner` ~66 LoC; [`orchestrator_run_artifacts.py`](../../scripts/live_check/trace_review/orchestrator_run_artifacts.py) — **тонкий фасад** (~7 LoC); стадии merge/verdict/write/compaction в [`artifact_pipeline.py`](../../scripts/live_check/trace_review/artifact_pipeline.py) (~266 LoC — **следующий кандидат** на декомпозицию по под-стадиям или вынесение phoenix/long-thread вспомогательных модулей); запись/merge артефактов в [`artifact_writers.py`](../../scripts/live_check/trace_review/artifact_writers.py) (~118 LoC). `compaction_turn_review.py` — entry ~106 LoC; пакет [`compaction_review/`](../../scripts/live_check/compaction_review/): [`run.py`](../../scripts/live_check/compaction_review/run.py) ~93 LoC, [`turn_executor.py`](../../scripts/live_check/compaction_review/turn_executor.py), [`heartbeat_monitor.py`](../../scripts/live_check/compaction_review/heartbeat_monitor.py), [`result_aggregator.py`](../../scripts/live_check/compaction_review/result_aggregator.py), [`report_schema.py`](../../scripts/live_check/compaction_review/report_schema.py), [`parsed_args.py`](../../scripts/live_check/compaction_review/parsed_args.py), [`report_builder.py`](../../scripts/live_check/compaction_review/report_builder.py) (MD-only). Юнит-хелперы: [`tests/scripts/live_check/test_trace_review_artifact_modules.py`](../../tests/scripts/live_check/test_trace_review_artifact_modules.py). **Дальше:** снизить complexity `artifact_pipeline.py` (ветки/локали); OD E2E audit; `http_suite.py`.
- **Raised:** 2026-05-14, **updated:** 2026-05-14 (operator/live-check depth slice)

### [OPEN] Split dual-validate retrieval extractor
- **Area:** `scripts/dual_validate/extractors/retrieval_v1.py`, `scripts/dual_validate/extractors/base.py`
- **Issue:** [`retrieval_v1.py`](../../scripts/dual_validate/extractors/retrieval_v1.py) остаётся **~663** LoC после выноса prompts/schemas/inventory/ranking; цель ≤350 LoC не достигнута.
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

### [PARTIAL] Split benchmark backend hubs: historical `api/benchmark.py` → package + task store
- **Area:** `science_graphrag/api/benchmark/` (в т.ч. [`routes_catalog.py`](../../science_graphrag/api/benchmark/routes_catalog.py), [`routes_runs.py`](../../science_graphrag/api/benchmark/routes_runs.py), [`inspector.py`](../../science_graphrag/api/benchmark/inspector.py) ~322 LoC), `science_graphrag/api/task_store.py`, `science_graphrag/api/benchmark_task_store_core.py`, `science_graphrag/api/benchmark_profiles.py`
- **Issue:** Монолитный `api/benchmark.py` снят в пользу подпакета (**~1258** LoC суммарно), но **inspector** и **task_store** слой всё ещё концентрируют сложность; добавление benchmark family тянет за собой несколько файлов без жёсткого adapter boundary.
- **Proposal:** (1) Разгрузить [`inspector.py`](../../science_graphrag/api/benchmark/inspector.py) (preview/compare/diagnostics shards). (2) `task_store.py` довести до orchestration-only с явными seams к [`benchmark_task_store_core.py`](../../science_graphrag/api/benchmark_task_store_core.py) + serializers. (3) Catalog/runs оставить тонкими HTTP слоями над use-cases.
- **Acceptance:** входной router-пакет без «god-файла» > ~350 LoC; новые семейства benchmark подключаются через catalog adapter без правок inspector/compare; `task_store` не содержит JSON snapshot plumbing.
- **Synergy:** **Wave M/P/Q/R/S** в `ontology-benchmarks-roadmap-2026-04-24.md` — каждое семейство не упирается в один файл.
- **Remaining:** сплит inspector + финальный orchestration-only `task_store.py`.
- **Raised:** 2026-04-25, **updated:** 2026-05-15 (актуальные пути и LoC)

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
- **Area:** `science_graphrag/api/agent_v2/`, `science_graphrag/api/agent_v2_modules/stream_lifecycle.py`, `science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_stream.py`, `science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_abort_specs.py`
- **Issue:** Router/digest facade lives in package `api/agent_v2/`; основной SSE chunk loop в [`stream_lifecycle_graph_stream.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_stream.py) (**~363** LoC) + вынесенные abort builders в [`stream_lifecycle_graph_abort_specs.py`](../../science_graphrag/api/agent_v2_modules/stream_lifecycle_graph_abort_specs.py). Lazy `build_retrieval_graph` через `stream_lifecycle` сохраняет monkeypatch surface для тестов.
- **Proposal:** дальнейший split только при росте файла или появлении второй крупной фазы в том же модуле (chunk-timeout loop vs finalize bridge); companion — OPEN «Split oversized agent edges…» / `react_edges.py` transport glue.
- **Acceptance:** each hot module ≤400 LoC where practical (мягкий порог до следующего крупного фича); SSE protocol edits do not require editing business orchestration; `test_api_agent_v2_smoke.py` and trace-audit tests pass without contract drift.
- **Remaining:** optional chunk-loop extract; companion `react_edges.py` transport glue.
- **Raised:** 2026-05-05, **updated:** 2026-05-15

### [PARTIAL] Split ingest pipeline orchestration seams (`ingestion/_pipeline_impl.py`)
- **Area:** `science_graphrag/ingestion/_pipeline_impl.py`, `science_graphrag/ingestion/stages/*`, `science_graphrag/ingestion/checkpoint.py`
- **Issue:** `_pipeline_impl.py` shrank substantially (~310 LoC after moving batch/single-file CLI entrypoints to `pipeline_cli_entrypoints.py` and corpus discovery to `corpus_discovery.py`), but further stage-registry work remains.
- **Proposal:** continue toward deep modules: `ingestion/orchestrator.py` (stage graph + resume contract), `ingestion/progress_store.py` (JSONL progress/checkpoint IO), `ingestion/cache_policy.py` (markdown cache lookup/reuse), `ingestion/document_runtime.py` (per-document execution context).
- **Acceptance:** `_pipeline_impl.py` <= 400 LoC facade; modules expose narrow interfaces with unit tests for resume/cache/timeout branches; new ingest stages plug into a declarative stage registry without growing a god-file.
- **Remaining:** stage registry / declarative graph (if we remove remaining conditional branches in orchestrator) + final migration of tests/scripts off legacy import paths. `ingestion/pipeline.py` is the public facade; private export surface from `_pipeline_impl` should stay minimal.
- **Raised:** 2026-05-05

### [OPEN] External research: OpenAlex search + Semantic Scholar tools
- **Area:** `science_graphrag/agent/tools/external/`, `science_graphrag/agent/tool_manifest.py`, `science_graphrag/agent/request_turn_policy.py`
- **Issue:** ADR 030 + `unpaywall_lookup` cover assembly and OA-by-DOI; `doi_resolver` already hits OpenAlex by DOI. Product gap vs `docs/analysis/sci-tools.md`: **search** across works (OpenAlex), citations/graph (Semantic Scholar), without duplicating DOI resolution paths.
- **Proposal:** add bounded `openalex_works_search` / `semantic_scholar_*` modules under `external/`, reuse `http_transport`, operator flags in `Settings`, extend `EXTERNAL_RESEARCH_TOOL_NAMES` when user web-toggle applies.
- **Acceptance:** httpx-mocked unit tests, manifest/registry sync tests, product_step mapping, shortlist rules documented for each new name.
- **Raised:** 2026-05-15

