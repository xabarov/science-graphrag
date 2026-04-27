# Chat agent roadmap — benchmark workspace + trace audit (2026-04-27)

**Статус:** evidence capture v1 + **live baseline** `eval/results/chat-agent-roadmap-live-2026-04-27` (2026-04-27, all cases green).  
**Companion:** [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md), [`eval/README.md`](../../eval/README.md).

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
2. **App-level:** порядок и состав имён инструментов в Phoenix (если видны) согласованы с `tool_trace` (допускаются пропуски, если инструмент не инструментирован в LangChain layer).

### 4.2 Span tree (что искать)

- Корневой span вокруг запроса агента (см. `chain_span("agent.query", …)` в `science_graphrag/agent/runtime.py`).
- Дочерние LLM / tool spans от LangGraph/OpenInference (зависит от `PHOENIX_TRACE_SCOPE` — в режиме `extraction_llm` агентные спаны подавлены; для chat-audit нужен **`full`**).
- Отсутствие «немых» провалов: нет ли обрыва цепочки до `final_answer`.

### 4.3 Классификация находок

| Class | Пример |
|-------|--------|
| **data issue** | audit `blocked` / `no_chunks` / `chunks_missing_workspace_ids_payload` |
| **agent logic issue** | ожидаемый tool из `tools_any_of` не вызывался при `ready` workspace |
| **traceability gap** | пустой `phoenix_trace_id` при `PHOENIX_TRACE_SCOPE=full` и инициализированном tracer |
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

### 5.3 Рекомендованный remediation backlog

1. **Relation tracing:** усилить маршрутизацию/промпт или gold (`strict_answer_class`, обязательный `cypher_query`/`edge_search`) для вопросов про citations/graph — см. строку `relation_cites` выше.
2. Сузить `tools_any_of` там, где траектория уже стабильна (inventory, bibliography).
3. Optional **strict** tier JSON для nightly поверх текущих «мягких» кейсов.
4. Расширить `trace_audit` project-specific URL в Phoenix при нестандартном deployment.

## 6. Reproducibility

- `summary.json` включает `benchmark_run_metadata` (модель / fingerprint из `eval.bench_common`).
- Каждый кейс хранит полный `tool_trace` и финальный envelope-подмножество в `case_result.json`.
