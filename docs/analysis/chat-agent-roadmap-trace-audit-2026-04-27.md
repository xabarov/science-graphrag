# Chat agent roadmap — benchmark workspace + trace audit (2026-04-27)

**Статус:** evidence capture v1 + **live baseline** `eval/results/chat-agent-roadmap-live-2026-04-27` (2026-04-27, baseline cases green). Обновлено после сверки Phoenix: наличие `phoenix_trace_id` уже доказано, но качество agent span tree ещё не является gate.

**Архитектурный baseline:** продукт на **упрощённом** LangGraph (`supervisor` → specialists as nodes, не отдельный swarm из шести subgraphs); системные цели и будущие треки (`tool_search`, compaction) — в slim [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md).

**Companion:** [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md), [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md), [`eval/README.md`](../../eval/README.md).

## 1. Baseline benchmark workspace

| Field | Value |
|-------|--------|
| **workspace_id** | `ws-pilot-od` |
| **Rationale** | Совпадает с retrieval `workspace_scoped` и `agent_tools_v1` (pilot object-detection), лучше дисциплина данных, чем произвольные пользовательские области. |
| **Manifest** | `tests/fixtures/benchmarks/chat_agent_roadmap/baseline_workspace_manifest.json` |

Перед live-прогоном suite обязателен **pre-flight audit** (Neo4j + Qdrant):

- `scripts/chat_agent_workspace_readiness_audit.py`, или
- встроенный шаг в `science-graphrag-chat-agent-roadmap` (по умолчанию **не** `--skip-audit`).

Статусы: `ready` | `degraded` | `blocked`. При `blocked` runner завершается с кодом **3** (не путать с fail метрик кейса = **1**).

Если audit возвращает `workspace_not_found_in_neo4j`, один раз выполните идемпотентный сид из корня репозитория:

```bash
.venv/bin/python scripts/seed_benchmark_workspaces.py
```

(поднимает `ws-pilot-od` и др. из `tests/fixtures/benchmarks/retrieval/workspace_scoped/_workspaces.json`, затем `backfill_workspace_payloads` для Qdrant).

## 2. Harness и артефакты

| Component | Path |
|-----------|------|
| Runner (Typer CLI) | `eval/chat_agent/roadmap_runner.py` → `science-graphrag-chat-agent-roadmap` |
| Scoring / diagnostics | `eval/chat_agent/roadmap_metrics.py` |
| Workspace audit (library) | `eval/chat_agent/workspace_audit.py` |
| Phoenix URL / HTTP snapshot (best-effort) | `eval/chat_agent/phoenix_export.py` |
| Fixtures | `tests/fixtures/benchmarks/chat_agent_roadmap/cases/*.json` |

**Per-case артефакты** (каталог `--out`):

- `cases/<case_id>/case_spec.json` — копия gold.
- `cases/<case_id>/trace_audit.json` — `phoenix_trace_id`, `phoenix_ui_hint`, merged `tool_trace`, `metrics`, `diagnostics`.
- `cases/<case_id>/case_result.json` — полный bundle (`case_spec` + `run` + `trace_audit`).

Важно: текущий `trace_audit.json` подтверждает **корреляцию** API/eval с Phoenix trace id и app-level `tool_trace`, но не доказывает полноту Phoenix span tree. До X2.8/X2.9 это не CI-gate: ручной аудит должен дополнительно смотреть наличие TOOL/RETRIEVER/LLM-спанов в Phoenix.

Suite-level:

- `summary.json` / `summary.md`
- `workspace_audit.json` (если audit не пропущен)

### 2.2 Phoenix scope в live harness

В `.env` часто задают `PHOENIX_TRACE_SCOPE=extraction_llm` (ingest-only спаны). Тогда **все** `chain_span` вне белого списка становятся noop и `phoenix_trace_id` в ответе агента пустой — harness **принудительно** выставляет `PHOENIX_TRACE_SCOPE=full` на время процесса CLI (в `summary.json` → `environment.PHOENIX_TRACE_SCOPE_before_harness`).

### 2.3 Mock sample (CI-friendly)

Детерминированный прогон без LLM и без стора:

```bash
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-mock-2026-04-27 \
  --skip-audit --mock-runtime
```

Закоммиченный пример выхода: `eval/results/chat-agent-roadmap-mock-2026-04-27/` (генерируется командой выше).

### 2.4 Live baseline (OpenRouter + локальные сторы)

Команда (после `seed_benchmark_workspaces` при необходимости):

```bash
science-graphrag-chat-agent-roadmap \
  --fixtures tests/fixtures/benchmarks/chat_agent_roadmap \
  --out eval/results/chat-agent-roadmap-live-2026-04-27
```

Артефакты: каталог выше; `summary.json` с `all_passed: true` на прогоне 2026-04-27.

## 3. Suite coverage vs roadmap §2 / §2.3

| case_id | Roadmap | Answer class hint | Primary tool expectations (soft `tools_any_of`) |
|---------|---------|-------------------|--------------------------------------------------|
| `inventory_papers` | §2.1 (1) | inventory | catalog tools |
| `authors_fact_lookup` | §2.1 (4) | fact_lookup | `paper_authors` / metadata |
| `bibliography_gost` | §2.1 (7), export | bibliography_export | `format_bibliography_gost` |
| `quote_detection` | §2.1 (5) | quote_extraction | `paper_quote_search` |
| `relation_cites` | §2.1 (3) | relation_tracing | graph / `cypher_query` / search |
| `ideation_workspace` | §2.1 (6) | ideation | `idea_search` / summarize |
| `multi_turn_clarify` | multi-turn | inventory → follow-up | merged trace across turns |

`answer_classes_allowed` в gold намеренно **широкие** (включают `grounded_explanation`), чтобы не флапать на writer-dominated траекториях; строгий режим — `strict_answer_class: true` (по умолчанию выкл.).

## 4. Phoenix trace audit checklist

Использовать **после** live-прогона, когда в `trace_audit.json` есть `phoenix_trace_id`.

### 4.1 Корреляция

1. **OTel / Phoenix:** trace id в UI совпадает с `phoenix_trace_id` в API-ответе / `case_result.json`.
2. **App-level:** порядок и состав имён инструментов в Phoenix согласованы с `tool_trace`. На текущем этапе допускаются пропуски, но каждый пропуск классифицируется как `traceability gap`, а не как «норма».
3. **Scope:** `summary.json.environment.PHOENIX_TRACE_SCOPE` должен быть `full` для live chat-audit. `extraction_llm` валиден для ingest-cost режима, но не для agent spans.

### 4.2 Span tree (что искать)

- Корневой span вокруг запроса агента: `agent.query` (см. `chain_span("agent.query", …)` в `science_graphrag/agent/runtime.py`), с `session.id = thread_id` для multi-turn и `user.id = workspace_id`.
- Routing/policy CHAIN-спаны: `agent.turn_policy.*`, `agent.supervisor.*`, позже `agent.specialist.<name>`.
- LLM-спаны под policy/supervisor/writer: должны иметь `openinference.span.kind=LLM`, `llm.model_name`, token counts. Если виден только CHAIN вокруг `llm.invoke`, это gap или зависимость от auto-instrumentation, которую надо подтвердить тестом.
- TOOL-спаны: каждый domain tool из `tool_trace` должен иметь `tool.<name>` span с `tool.name`, `tool.parameters`, коротким output и ошибкой при fail.
- RETRIEVER-спаны: semantic/quote search должны показывать Qdrant result set через `openinference.span.kind=RETRIEVER` и `retrieval.documents.*`. Сейчас это ожидаемый gap для X2.3.
- EMBEDDING-спаны: query embedding должен быть отдельным от retrieval (`embedding.agent.*`) и иметь модель/размер/количество input.
- Отсутствие «немых» провалов: нет обрыва цепочки до `final_answer`; budget exhaustion виден и в `tool_trace`, и в span/event metadata.

### 4.3 Классификация находок

| Class | Пример |
|-------|--------|
| **data issue** | audit `blocked` / `no_chunks` / `chunks_missing_workspace_ids_payload` |
| **agent logic issue** | ожидаемый tool из `tools_any_of` не вызывался при `ready` workspace |
| **traceability gap** | пустой `phoenix_trace_id` при `PHOENIX_TRACE_SCOPE=full` и инициализированном tracer |
| **span coverage gap** | `phoenix_trace_id` есть, но tool из `tool_trace` отсутствует как TOOL-спан или Qdrant search не виден как RETRIEVER |
| **llm attribution gap** | routing/writer вызывает модель, но в Phoenix нет LLM-спана с `llm.model_name` и token counts |
| **contract gap** | нет typed-блока (`bibliography`, `inventory`, …) при успешном tool в trace |

### 4.4 Автоматический HTTP snapshot

Флаг `--fetch-phoenix` вызывает best-effort GET к нескольким путям Phoenix UI/API (`PHOENIX_UI_BASE_URL`, default `http://127.0.0.1:16006`). Результат **не гарантирован** между версиями Phoenix — это дополнительный артефакт, а не gate CI.

## 5. Findings

### 5.1 Mock / CI

На **mock-runtime** LLM-траектории нет; подтверждается wiring runner → метрики → артефакты и pytest `tests/eval/test_chat_agent_roadmap_metrics.py`.

### 5.2 Live baseline (`eval/results/chat-agent-roadmap-live-2026-04-27`)

**Workspace audit:** `ready` — одна работа YOLOv1, 4 автора, 34 исходящих `CITES`, 36 чанков в Qdrant с `workspace_ids`.

**Модель (metadata suite):** `mistralai/mistral-small-3.2-24b-instruct` @ OpenRouter (см. `summary.json` → `benchmark_run_metadata`).

| case_id | Metrics gate | Уникальные tools (кроме служебных маршрутов) | Phoenix id (prefix) | Классификация trace vs intent |
|---------|--------------|-----------------------------------------------|---------------------|--------------------------------|
| `inventory_papers` | PASS | `workspace_list_papers` | `8f33d9aa33b7` | **OK** — inventory + list. |
| `authors_fact_lookup` | PASS | `paper_lookup`, `paper_counts`, `paper_authors` | `8b8593efeb28` | **OK** — fact lookup stack. |
| `bibliography_gost` | PASS | `summarize_workspace`, `format_bibliography_gost` | `fd8c6734480e` | **OK** — GOST formatter вызван. |
| `quote_detection` | PASS | `paper_quote_search` | `6ec40693db9a` | **OK** — quote tool. |
| `relation_cites` | PASS (soft) | `workspace_list_papers` (после серии `route_to_specialist`, в т.ч. попытка `graph_agent`, затем **budget_exhausted** → writer) | `c6ea4c935bb4` | **Agent logic (soft)** — вопрос про граф/cites, финальный `answer_class` = `inventory`, доменных graph tools нет в `tool_trace`; бюджет шагов исчерпан до полезного graph-вызова. Gate зелёный из‑за `strict_answer_class: false`. Для nightly: strict answer class и/или отдельный strict-tier кейс. |
| `ideation_workspace` | PASS | `idea_search`, `paper_lookup`, `paper_quote_search` | `c78e97aeb284` | **OK** — идеи + обзор источников. |
| `multi_turn_clarify` | PASS | `workspace_list_papers`, `paper_authors`, `session_init` | `8dd43d4c6aee` | **OK** — multi-turn + session. |

**Инфраструктура:** на одном из прогонов OpenRouter вернул **502** с телом `BadRequestError` на кейсе `relation_cites`; в harness добавлен **один повтор** при транзиентных кодах (502/503/504/429/timeout). После фикса `PHOENIX_TRACE_SCOPE` полный suite стабильно зелёный.

### 5.3 Phoenix coverage findings

1. **Корреляция работает:** live артефакты содержат `phoenix_trace_id`, а harness защищается от `PHOENIX_TRACE_SCOPE=extraction_llm`, принудительно включая `full`.
2. **`phoenix_trace_id` пока слабее, чем полноценный audit:** baseline PASS означает, что trace создан, но не означает, что все domain tools, retrievers и LLM-вызовы представлены в Phoenix корректными span kinds.
3. **TOOL coverage частичный:** вручную размечены `idea_search` и `paper_quote_search`; остальные tools нужно провести через единый TOOL-wrapper, чтобы `tool_trace` и Phoenix были сопоставимы без ручных оговорок.
4. **RETRIEVER coverage отсутствует для agent Qdrant search:** semantic/quote retrieval виден через TOOL + EMBEDDING, но не как отдельный `openinference.span.kind=RETRIEVER` с `retrieval.documents.*`.
5. **LLM attribution требует проверки:** `agent.turn_policy.llm` и `agent.supervisor.route_llm` сейчас CHAIN-родители вокруг `llm.invoke`; нужно доказать дочерние LLM spans через observability-test или закрепить ручные `llm.agent.*` spans.

### 5.4 Рекомендованный remediation backlog

1. **Relation tracing:** усилить маршрутизацию/промпт или gold (`strict_answer_class`, обязательный `cypher_query`/`edge_search`) для вопросов про citations/graph — см. строку `relation_cites` выше.
2. Сузить `tools_any_of` там, где траектория уже стабильна (inventory, bibliography).
3. Optional **strict** tier JSON для nightly поверх текущих «мягких» кейсов.
4. Расширить `trace_audit` project-specific URL в Phoenix при нестандартном deployment.
5. **Agent TOOL span coverage:** закрыть X2.2 из [`phoenix-tracing-coverage-2026-04-25.md`](./phoenix-tracing-coverage-2026-04-25.md) — все tools из `tool_trace` должны иметь TOOL spans.
6. **Retriever spans:** закрыть X2.3 — `idea_search` / `paper_quote_search` должны показывать Qdrant documents в Phoenix.
7. **LLM span contract:** закрыть X2.5 — тестом подтвердить `llm.model_name` / token counts для supervisor/classifier/writer.
8. **Trace-audit gate:** закрыть X2.8/X2.9 — deterministic InMemorySpanExporter test + best-effort Phoenix fetch, чтобы отличать answer-quality PASS от observability PASS.

### 5.5 Обновление после закрытия X2 (2026-04-27)

Реализованы X2.2–X2.9: единый `run_tool_result_with_span`, RETRIEVER для `idea_search` / `paper_quote_search`, явные `llm_span` для policy/supervisor/specialists, root output summary на `agent.query`, блок `observability` в `trace_audit.json` (сверка с Phoenix при `--fetch-phoenix`), опция `expect.require_observability_match`, UI deep link при `VITE_PHOENIX_UI_BASE_URL`. Детерминированный CI gate: `tests/observability/test_agent_span_tree.py`, `tests/eval/test_observability_audit.py`. Пункты §5.3 п.3–5 и backlog §5.4 п.5–8 считаются закрытыми на уровне кода; live-валидация span tree по-прежнему best-effort через Phoenix UI.

### 5.6 Качество aftercare (live review, 2026-04-27)

Дополнительная live-проверка после внедрения X2 показала два разных слоя проблем:

1. **Настоящий tracing bug был в runtime:** `agent.query` открывался в основном потоке, а `graph.invoke(...)` уходил в `ThreadPoolExecutor` (`agent/graph/invoke_timeout.py`) без переноса OTel context. Из-за этого Phoenix показывал один общий trace рядом с отдельно “выпавшими” root traces (`LangGraph`, `tool.*`, `llm.agent.*`). Исправление: явный `opentelemetry.context.attach/detach` вокруг worker-thread invoke + regression test `tests/observability/test_worker_trace_propagation.py`.
2. **Live Phoenix fetch (2026-04-27 closeout):** `eval/chat_agent/phoenix_export.py` переведён на Phoenix **13.x** project-aware REST (`/v1/projects/.../spans|traces`), deep links — `/projects/{project}/traces/{traceId}`; `observability_audit` различает валидный JSON и HTML shell (`phoenix_payload_valid`, `observability_match_reliable`). Старые ложные FAIL из-за SPA shell **сняты**.

Следствие: deterministic CI gate по span-tree остаётся валидным и зелёным; live `--fetch-phoenix` снова может использоваться как **дополнительный** сигнал при `observability_match_reliable=true`. См. также [`phoenix-closeout-evidence-2026-04-27.md`](./phoenix-closeout-evidence-2026-04-27.md).

## 6. Reproducibility

- `summary.json` включает `benchmark_run_metadata` (модель / fingerprint из `eval.bench_common`).
- Каждый кейс хранит полный `tool_trace` и финальный envelope-подмножество в `case_result.json`.
- До внедрения X2.9 ручной reviewer должен открывать `phoenix_ui_hint` и проверять span tree по чеклисту §4.2, а не ограничиваться наличием trace id.
