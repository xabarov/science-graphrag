# Миграция с smolagents на LangChain / LangGraph — анализ и план Wave Y

**Doc status:** `reference`

**Read hint:** deep migration history/plan for Wave Y. For current runtime priorities start with [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md), [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md), and [`ACTIVE.md`](./ACTIVE.md).

**Дата:** 2026-04-25
**Статус:** living working doc; новый трек `Wave Y-LangGraph`, не пересекается с волнами ingest-async (U–W), benchmark-onthology (M–T) и observability (X-Phoenix).
**Цель:** зафиксировать, где сегодня используется `smolagents`, спроектировать целевую архитектуру агентного слоя на `LangChain` + `LangGraph` (multi-agent ready), и оформить пошаговый план перехода с чеклистами, сохраняя совместимость с UI/бенчмарками и Phoenix-разметкой.

**Принятые решения по объёму миграции (см. §5):**
- **Полный выпил `smolagents`**: production-агент (`science_graphrag/agent/`) и research spike (`scripts/experiment_references_smolagents_spike.py`) — оба переезжают, `smolagents` выпиливается из `pyproject.toml` и из `eval/results`/`docs` ссылок.
- **Multi-agent сразу**: целевой runtime — supervisor + specialists (LangGraph `StateGraph`), даже если на старте specialist один (`retrieval_agent`).
- **API v2**: новый `POST /v2/agent/query` со streamingom событий LangGraph; `POST /v1/agent/query` остаётся deprecated с обратной совместимостью на переходный период.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`../adr/016-agent-tool-registry-and-langgraph.md`](../adr/016-agent-tool-registry-and-langgraph.md) | Решение Wave R: tool registry, feature flag, advisory benchmark |
| [`../specs/agent-tools-v1.md`](../specs/agent-tools-v1.md) | Контракт инструментов агента (idea_search, edge_search, …) |
| [`_archive/reference-extraction-llm-agent-tools.md`](_archive/reference-extraction-llm-agent-tools.md) | [HISTORICAL] Описание H2 spike: `ToolCallingAgent` + 6 кастомных tools |
| [`phoenix-tracing-coverage-2026-04-25.md`](phoenix-tracing-coverage-2026-04-25.md) | Wave X-Phoenix: разметка agent-trace (X2.1–X2.8) |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) | §7.7 Wave R + claims/semantic LLM-блоки, к которым придут multi-agent сценарии |
| [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) | **Продуктовый канон research chat:** упрощённый supervisor+nodes граф; `tool_search` и compaction; архив CH-волн: [`_archive/chat-agent-system-roadmap-full-2026-04-26.md`](./_archive/chat-agent-system-roadmap-full-2026-04-26.md) |
| [`../runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) | Сводный список волн (после принятия — добавить Wave Y) |

---

## 1. TL;DR

1. `smolagents` сегодня живёт **только в исследовательском контуре**:
   - `pyproject.toml` `[research]` extra (`smolagents>=1.4.0`).
   - `scripts/experiment_references_smolagents_spike.py` — единственный live consumer (CLI с двумя командами `spike`/`suite`, 6 inline `Tool`-классов, `ToolCallingAgent`).
   - `eval/references_harness/agent_suite_metrics.py` + `tests/test_agent_suite_metrics.py` — пост-хок метрики (импортируют **не** `smolagents`, а локальные `agent_toolkit` + `metrics`).
   - Документация (`docs/analysis/_archive/reference-extraction-llm-agent-tools.md` [HISTORICAL], `docs/analysis/ontology-benchmarks-roadmap-2026-04-24.md`, `eval/results/refs_llm_agent_experiment_*.md`) — описание spike и его метрик.
2. **Production retrieval-агент уже без `smolagents`**, но **ещё без `LangGraph`**:
   - `science_graphrag/agent/runtime.py::RetrievalAgent` — детерминированный, без LLM-планировщика, фиксированный pipeline `idea_search → (опц.) summarize_workspace → final_answer`.
   - 6 tools (`cypher_query`, `entity_search`, `edge_search`, `idea_search`, `summarize_workspace`, `final_answer`) под собственным `BaseAgentTool` + `run_with_trace` (`ToolCallTrace` TypedDict).
   - `cypher_safety.validate_readonly_cypher` — read-only allowlist + max LIMIT.
   - `POST /v1/agent/query` за фичефлагом `SCIENCE_GRAPHRAG_AGENT_ENABLED`.
   - `pyproject.toml` `[agent]` extra **уже содержит** `langgraph>=0.2.50,<0.3`, `langchain-core>=0.3.20`, `langchain-openai>=0.2.10` — фундамент готов, использования нет.
   - В Phoenix агент **не виден** (Wave X2 запланирован, но не сделан).
3. **Целевая архитектура** — LangGraph `StateGraph` с supervisor + specialists, инструменты как `langchain_core.tools.BaseTool` (типизированные через Pydantic), LLM через `ChatOpenAI` с `base_url=settings.extraction_llm_base_url` (OpenRouter-совместимо). Trace берётся из LangGraph state (`messages`, `tool_calls`) и доводится до OpenInference TOOL/LLM/RETRIEVER-спанов.
4. **План — Wave Y-LangGraph** из шести фаз (Y1–Y6), идущих последовательно с возможным распараллеливанием Y2/Y3. Каждая фаза имеет acceptance, не ломает существующие тесты и UI до фазы Y6 (выпил `smolagents`). Полный чеклист — §7.

---

## 2. Текущий снимок: где `smolagents` и собственный agent runtime

### 2.1 `smolagents` — точки использования

| Где | Что |
|---|---|
| [`pyproject.toml`](../../pyproject.toml) | Optional extra `[research] = ["smolagents>=1.4.0"]`; ставится только при `pip install '.[research]'`. |
| [`scripts/experiment_references_smolagents_spike.py`](../../scripts/experiment_references_smolagents_spike.py) | `from smolagents import OpenAIServerModel, Tool, ToolCallingAgent`; 6 inline `Tool`-классов (`HeuristicRefsTool`, `GrepArticleTool`, `GetLinesTool`, `FindBibliographyCandidatesTool`, `CountReferenceMarkersTool`, `SegmentReferenceBlockTool`); CLI `spike` + `suite`; модель — `OpenAIServerModel(model_id=settings.extraction_llm_model, api_key=…, api_base=settings.extraction_llm_base_url)` (OpenRouter); `ToolCallingAgent(tools=…, model=…, max_steps=…, add_base_tools=False, instructions=…)`. |
| [`eval/references_harness/agent_suite_metrics.py`](../../eval/references_harness/agent_suite_metrics.py) | Docstring «Align smolagents router suite rows…», но импортирует локальные модули — самой `smolagents` зависимости нет. |
| [`tests/test_agent_suite_metrics.py`](../../tests/test_agent_suite_metrics.py) | Тесты для метрик; `smolagents` не импортируется. |
| Docs: [`_archive/reference-extraction-llm-agent-tools.md`](_archive/reference-extraction-llm-agent-tools.md) [HISTORICAL], [`ontology-benchmarks-roadmap-2026-04-24.md`](ontology-benchmarks-roadmap-2026-04-24.md) §7.7 (713 строка), [`eval/results/refs_llm_agent_experiment_2026-04-08.md`](../../eval/results/refs_llm_agent_experiment_2026-04-08.md), [`eval/results/refs_llm_agent_experiment_2026-04-09.md`](../../eval/results/refs_llm_agent_experiment_2026-04-09.md) | Описание H2-эксперимента, ссылки на `ToolCallingAgent`. |

**Что делает spike:** `ToolCallingAgent` маршрутизирует «найди библиографию, посчитай записи»: вызывает `find_bibliography_candidates` → опционально `count_reference_markers` → детерминированный `segment_reference_block` → JSON-ответ. Это **не product-runtime**, это «cost/quality-проба» против harness-режимов `scope_llm` и `batched_llm`.

### 2.2 Production agent (без `smolagents`)

```
science_graphrag/agent/
├── __init__.py                # re-export build_agent, RetrievalAgent, AgentRunOutput
├── runtime.py                 # RetrievalAgent (детерминированный pipeline)
├── trace.py                   # ToolCallTrace (TypedDict): step / tool / args_summary / row_count / duration_ms / truncated / error
├── cypher_safety.py           # validate_readonly_cypher: forbidden tokens + label allowlist + max LIMIT
└── tools/
    ├── __init__.py            # re-export 6 tools
    ├── base.py                # BaseAgentTool + ToolResult + run_with_trace (latency + try/except)
    ├── cypher_query.py        # CypherQueryTool (read-only Cypher с safety + max_rows=200)
    ├── edge_search.py         # EdgeSearchTool (Neo4j neighborhood, direction in/out/both)
    ├── entity_search.py       # EntitySearchTool (Neo4j fulltext по Work)
    ├── idea_search.py         # IdeaSearchTool (Qdrant chunks + works, embedding через HashEmbeddingProvider/Sentence-Transformers)
    ├── summarize_workspace.py # SummarizeWorkspaceTool (Neo4j workspace_get → строковая сводка)
    └── final_answer.py        # FinalAnswerTool (упаковка ответа + citations)
```

`RetrievalAgent.run(question, workspace_id, max_tool_calls)` — **детерминированный**: `idea_search` (top_k=5) → если есть `workspace_id` и бюджет позволяет — `summarize_workspace` (top_n_works=8) → склеивает 3 верхних чанка как citations → `final_answer`. **LLM не вызывается**.

### 2.3 API surface

| Endpoint | Где | Что |
|---|---|---|
| `POST /v1/agent/query` | [`science_graphrag/api/agent.py`](../../science_graphrag/api/agent.py) | feature flag `SCIENCE_GRAPHRAG_AGENT_ENABLED` (по умолчанию off → 503); поднимает Neo4j + Qdrant clients per-request; вызывает `build_agent(...).run(...)`; возвращает `AgentQueryResponse{answer, citations, tool_trace, duration_ms, run_metadata{agent_runtime: "langgraph_like_v1", …}}`. |
| `eval/agent_tools/runner.py` | benchmark | дёргает `post_agent_query(...)` напрямую (не через HTTP), пишет `report["tool_trace"]` и считает `score_agent_case` (tool_call_correctness, tool_budget_ok, cypher_safety, answer_grounded, passed). |
| UI AskPanel | [`ui/`](../../ui/) | отображает `tool_trace` (см. Wave R статус-запись в [`roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) §Wave R). |

### 2.4 Тесты, на которые опирается миграция

| Тест | Что проверяет |
|---|---|
| [`tests/agent/test_runtime.py::test_build_agent_and_run_smoke`](../../tests/agent/test_runtime.py) | smoke: `build_agent(...).run(...)` возвращает `answer`, `citations: list`, `tool_trace ≥ 2` элемента; используются fake Neo4j/Qdrant. |
| [`tests/agent/test_cypher_safety.py`](../../tests/agent/test_cypher_safety.py) | parametric allow/deny для `validate_readonly_cypher` (CREATE/MERGE/DELETE/SET, неизвестный label, LIMIT > 200). |
| [`tests/test_api_agent_smoke.py`](../../tests/test_api_agent_smoke.py) | `POST /v1/agent/query` → 503 при `agent_enabled=False`; 200 + ожидаемый `tool_trace` при включённом флаге (через `monkeypatch build_agent`). |
| [`tests/test_agent_suite_metrics.py`](../../tests/test_agent_suite_metrics.py) | post-hoc метрики над «router» rows; **не зависит** от `smolagents` runtime, только от парсера полей `parsed.start_line/end_line/style_guess`. |

### 2.5 Конфигурация LLM, которую переиспользуем

| Setting | Где | Зачем для агента |
|---|---|---|
| `extraction_llm_api_key` / `extraction_llm_base_url` / `extraction_llm_model` | [`science_graphrag/config.py`](../../science_graphrag/config.py) | OpenRouter-совместимый OpenAI client. Используется в spike. Будет переиспользоваться в `ChatOpenAI(...)` для агентного LLM по умолчанию. |
| `agent_enabled` / `agent_max_tool_calls` | то же | feature flag + budget cap (default 8). Сохраняем семантику. |
| `PHOENIX_TRACE_SCOPE` (`full` / `extraction_llm`) | env | при `extraction_llm` агентные спаны должны быть подавлены (см. §6.3). |

---

## 3. Целевая архитектура — LangGraph multi-agent (single specialist на старте)

### 3.1 Высокоуровневая картинка

```
                ┌──────────────────────────────────────────────────┐
                │   POST /v2/agent/query  (LangGraph runtime)     │
                │   - SSE stream: tool_call / tool_result / token │
                │   - sync fallback: full AgentQueryResponse v2   │
                └──────────────────────────────────────────────────┘
                                    │
                                    ▼
                ┌──────────────────────────────────────────────────┐
                │       Supervisor (LLM-планировщик / router)      │
                │  StateGraph node: decides which specialist       │
                │  handles next step or stops with final_answer    │
                └──────────────────────────────────────────────────┘
                          │             │             │
            ┌─────────────┘             │             └─────────────┐
            ▼                           ▼                           ▼
  ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
  │ retrieval_agent  │        │  graph_agent     │ (Y4+)  │  writer_agent    │ (Y4+)
  │ (idea_search,    │        │  (cypher_query,  │        │  (LLM, цитаты,   │
  │  summarize_ws)   │        │   edge_search,   │        │   final_answer)  │
  │                  │        │   entity_search) │        │                  │
  └──────────────────┘        └──────────────────┘        └──────────────────┘
            │                           │                           │
            └───────────────┬───────────┴────────────┬──────────────┘
                            ▼                        ▼
                   ┌────────────────┐      ┌────────────────────────┐
                   │   ToolNode     │      │  cypher_safety guard   │
                   │  (LangGraph)   │      │  (pre-execution check) │
                   └────────────────┘      └────────────────────────┘
                            │
                            ▼
                ┌──────────────────────────────────────────────────┐
                │  Sources: Neo4j, Qdrant chunks, Qdrant works     │
                │           OpenAlex enrichment, embeddings        │
                └──────────────────────────────────────────────────┘
```

На старте Y2 — **один specialist `retrieval_agent`** + supervisor (формально один node), чтобы не ломать сегодняшний `RetrievalAgent.run` контракт. С Y4 supervisor реально разводит запросы на специалистов.

### 3.2 Целевые компоненты в `science_graphrag/agent/`

```
science_graphrag/agent/
├── __init__.py                # build_agent, RetrievalAgent, AgentRunOutput (legacy proxy)
├── runtime.py                 # legacy proxy → новый LangGraph runtime (фаза Y6: удалить)
├── cypher_safety.py           # без изменений (используется внутри tool wrapper)
├── trace.py                   # ToolCallTrace (legacy adapter target)
├── graph/                     # NEW
│   ├── __init__.py
│   ├── state.py               # AgentState (TypedDict / Pydantic) — messages, tool_results, citations, budget
│   ├── supervisor.py          # build_supervisor_graph(...) — StateGraph + ToolNode + condition_edges
│   ├── nodes/
│   │   ├── retrieval_agent.py # specialist node для idea_search / summarize_workspace
│   │   ├── graph_agent.py     # specialist node для cypher / entity / edge (Y4+)
│   │   └── writer_agent.py    # final answer + citations (Y4+)
│   └── tracing.py             # OpenInference span helpers + LangGraph callbacks → ToolCallTrace adapter
├── llm/
│   ├── __init__.py
│   └── chat.py                # build_chat_model(settings) → ChatOpenAI(model=…, base_url=…, api_key=…)
└── tools/                     # PERESHAGAEM на langchain_core.tools.BaseTool
    ├── __init__.py            # реэкспорт + langchain registry (build_tool_registry())
    ├── base.py                # legacy BaseAgentTool (фаза Y6: удалить); общие helpers
    ├── cypher_query.py        # @tool с Pydantic args + safety pre-check
    ├── edge_search.py
    ├── entity_search.py
    ├── idea_search.py         # внутри использует embedding helper из ingestion (без дублирования)
    ├── summarize_workspace.py
    └── final_answer.py
```

### 3.3 Контракты

#### 3.3.1 LangChain tool

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

class CypherQueryArgs(BaseModel):
    query: str = Field(..., description="Read-only Cypher; no CREATE/MERGE/DELETE/SET/REMOVE/DROP, max LIMIT 200")
    params: dict = Field(default_factory=dict)

@tool("cypher_query", args_schema=CypherQueryArgs, return_direct=False)
def cypher_query_tool(query: str, params: dict | None = None) -> dict:
    """Execute a read-only Cypher query (label allowlist + max LIMIT 200)."""
    validate_readonly_cypher(query, max_limit=200)  # из cypher_safety.py
    ...
    return {"rows": rows, "row_count": len(rows), "truncated_at": ...}
```

`validate_readonly_cypher` — **обязательный pre-check**, остаётся в `cypher_safety.py` без изменений.

#### 3.3.2 LangGraph state

```python
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]            # совместимо с ToolCallTrace для legacy v1 endpoint
    budget_remaining: int             # max_tool_calls − использованные
    metadata: dict                    # extraction_llm_model, agent_runtime_version, …
```

#### 3.3.3 Supervisor

Базовый шаблон — официальный LangGraph supervisor pattern (`StateGraph` с условным переходом по `tool_calls` в последнем `AIMessage` или `final_answer` маркеру). На Y2 supervisor состоит из одного цикла «LLM → ToolNode → LLM → …» (по сути ReAct). На Y4 supervisor разводит вызов в `retrieval_agent` / `graph_agent` / `writer_agent` по эвристике `last_message.additional_kwargs["routing_hint"]` или явному tool-call `route_to(specialist=…)`.

#### 3.3.4 LLM

```python
from langchain_openai import ChatOpenAI
from science_graphrag.config import Settings

def build_chat_model(settings: Settings, *, temperature: float = 0.0, max_tokens: int = 1024) -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.extraction_llm_model,
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,  # OpenRouter совместимо
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=settings.extraction_llm_timeout_seconds,
    )
```

Дополнительные настройки конфига — см. §4.1.

#### 3.3.5 API v1 → v2

**v1 (deprecated, сохраняется до Y6):** контракт без изменений. Внутри — адаптер: после прогона LangGraph собираем `AgentRunOutput` из `state.messages` и `state.tool_trace` в формате текущего `ToolCallTrace`.

**v2:** `POST /v2/agent/query` поддерживает:
- `Accept: text/event-stream` → SSE-стрим: `tool_call`, `tool_result`, `assistant_token` (если включено), `final_answer`, `error`. Удобно для UI.
- `Accept: application/json` → синхронный `AgentQueryResponse` v2 с дополнительными полями: `events: list[AgentEvent]` (timestamp + payload), `phoenix_trace_id`, `agent_runtime: "langgraph_supervisor_v1"`.

Контракт v2 — отдельная спека [`docs/specs/agent-tools-v2.md`](../specs/agent-tools-v2.md) (создаётся в Y3.4).

### 3.4 Что **не меняется**

- `cypher_safety.validate_readonly_cypher` — единственный безопасный путь к Neo4j.
- `agent_max_tool_calls` (default 8) — bounded loop в supervisor → `RecursionError`/`GraphRecursionError` обрабатываем как 422 с `error="budget_exceeded"`.
- Ответный `citations` контракт (`{work_id, snippet}`) — для совместимости с `eval/agent_tools/metrics.py::_tool_sequence_match` и UI.
- Phoenix tracing helpers (`chain_span`, `llm_span`, `traced_tool_span`, `embeddings_span`, `SpanAttributes`) — переиспользуем (см. §3.5).

### 3.5 Phoenix / OpenInference разметка

Используем готовые helpers из [`science_graphrag/observability/phoenix_tracer.py`](../../science_graphrag/observability/phoenix_tracer.py) (см. [_archive/phoenix-tracing-coverage-2026-04-25.md §5.2 Wave X2](_archive/phoenix-tracing-coverage-2026-04-25.md#52-wave-x2--%D1%80%D0%B0%D0%B7%D0%BC%D0%B5%D1%82%D0%B8%D1%82%D1%8C-retrieval-agent-ir)). Дерево спанов целевое:

```
agent.query                                       [CHAIN]   session.id=ask_session_id, user.id=workspace_id
├── agent.supervisor.step_0                       [CHAIN]   step_index=0
│   ├── llm.agent.supervisor                      [LLM]     llm.model_name, tokens, tool_calls.* — auto-instrumentation langchain
│   └── tool.idea_search                          [TOOL]    tool.name, tool.parameters, tool.output
│       ├── embedding.agent.idea_search           [EMBEDDING] embedding.model_name, dim, count
│       └── retrieval.qdrant.chunks               [RETRIEVER] retrieval.documents.{i}.id|score|content
├── agent.supervisor.step_1                       [CHAIN]
│   ├── llm.agent.supervisor                      [LLM]
│   └── tool.summarize_workspace                  [TOOL]
└── agent.supervisor.final                        [CHAIN]
    └── llm.agent.writer (Y4+)                    [LLM]
```

- `openinference-instrumentation-langchain>=0.2` (новая зависимость в `[agent]` extra) даёт авто-LLM-спаны для `ChatOpenAI` + tool-spans для `@tool`. Поверх ставим явные `chain_span("agent.query", …)` и `embeddings_span(...)` — там, где auto-instrumentation не покрывает (custom embedder, кастомные RETRIEVER-спаны).
- `_EXTRACTION_LLM_CHAIN_NAMES` в `phoenix_tracer.py` **не трогаем**: scope `extraction_llm` оставляет только три `llm.*_extraction` спана из ingestion и не пускает агент. Если в будущем понадобится «extraction_llm + agent» — ввести `PHOENIX_TRACE_SCOPE=agent_only`.

---

## 4. Зависимости и конфиг

### 4.1 `pyproject.toml`

**Add (фаза Y1):**

```toml
[project.optional-dependencies]
agent = [
    "langgraph>=0.2.50,<0.3",
    "langchain-core>=0.3.20",
    "langchain-openai>=0.2.10",
    "langgraph-supervisor>=0.0.6",                 # supervisor builder helpers
    "openinference-instrumentation-langchain>=0.2",
]
```

**Remove (фаза Y6):**

```toml
[project.optional-dependencies]
research = [
    # smolagents>=1.4.0  ← удалить
]
```

**Replace в основном `dependencies`:** ничего не добавляется в core — агент остаётся за extra `[agent]`. На старте Y6 в Docker-образе backend extras `[agent]` ставится по умолчанию (см. §4.3).

### 4.2 Settings

В `science_graphrag/config.py` — новые поля (со значениями по умолчанию, обратная совместимость):

| Field | Default | Зачем |
|---|---|---|
| `agent_runtime` | `"langgraph_supervisor_v1"` | переключение между legacy `retrieval_v1` и новым; полезно для A/B и rollback. |
| `agent_supervisor_recursion_limit` | `12` | `StateGraph.compile(...).invoke(..., {"recursion_limit": …})`; коррелирует с `agent_max_tool_calls`. |
| `agent_chat_temperature` | `0.0` | через `build_chat_model`. |
| `agent_chat_max_tokens` | `1024` | то же. |
| `agent_streaming_enabled` | `True` | глобальный switch SSE для v2. |

### 4.3 Docker / CI

- В `Dockerfile` (`backend` target) добавить установку `[agent]` по умолчанию: `pip install -e '.[agent]'`.
- В `docker-compose.dev.yml` / prod compose — без изменений, переменные окружения (`SCIENCE_GRAPHRAG_AGENT_ENABLED`, новые agent_* настройки) подтягиваются из `.env`.
- В CI добавить шаг `pip install -e '.[agent]'` для backend job, чтобы тесты `tests/agent/` и smoke v2 endpoint бежали с реальным LangGraph.

### 4.4 `.env.example`

Добавить блок:

```dotenv
# Agent runtime (Wave Y)
SCIENCE_GRAPHRAG_AGENT_ENABLED=false
SCIENCE_GRAPHRAG_AGENT_RUNTIME=langgraph_supervisor_v1
SCIENCE_GRAPHRAG_AGENT_MAX_TOOL_CALLS=8
SCIENCE_GRAPHRAG_AGENT_SUPERVISOR_RECURSION_LIMIT=12
SCIENCE_GRAPHRAG_AGENT_CHAT_TEMPERATURE=0.0
SCIENCE_GRAPHRAG_AGENT_CHAT_MAX_TOKENS=1024
SCIENCE_GRAPHRAG_AGENT_STREAMING_ENABLED=true
```

---

## 5. Что плохо сейчас и почему мигрируем

### 5.1 Архитектурно

1. **Детерминированный `RetrievalAgent` не масштабируется.** Текущая логика «idea_search → опц. summarize_workspace → final_answer» закрыта от расширения. Любая новая фича (LLM-планировщик, маршрутизация по типу вопроса, цитирование графа, multi-step graph traversal) требует переписать `runtime.py::run`. Это анти-паттерн «agent without agency».
2. **Tool registry не стандартный.** `BaseAgentTool` — собственный мини-фреймворк (с `run_with_trace`), не совместимый с экосистемой LangChain (нет авто-валидации Pydantic args, нет JSON-schema для LLM, нет совместимости с `ChatOpenAI.bind_tools` и `ToolNode`).
3. **`smolagents` живёт параллельной веткой.** Tools spike-а полностью изолированы от production tools, дрейф неизбежен. Любая «полезная» tool из spike (`grep_article`, `get_lines`) не попадает в production реестр без копи-пасты. И наоборот — spike не использует продуктовые `idea_search` / `cypher_query`.
4. **Multi-agent невозможен** в текущей шине. Чтобы добавить второго агента (например, «graph specialist» для сложных Cypher-запросов или «writer» для синтеза ответа), пришлось бы строить отдельный orchestrator руками. LangGraph даёт это «из коробки» через `StateGraph` + `add_conditional_edges`.

### 5.2 Operational

5. **API не виден в Phoenix** (Wave X2 не сделан). Без LangChain auto-instrumentation придётся вручную поднимать TOOL/LLM/RETRIEVER-спаны для каждого custom tool — много дублирующего кода. Переход на `langchain_core` даёт `openinference-instrumentation-langchain` бесплатно.
6. **Per-request init Neo4j/Qdrant.** `api/agent.py::post_agent_query` создаёт `Neo4jGraphStore`/`QdrantChunkStore`/`QdrantWorkEmbeddingStore` каждый запрос, закрывает сессию в `finally`. Для будущего multi-step с долгими сессиями (10+ tool calls) это даст лишний overhead. В Y2 переиспользуем dependency-injected singletons (как в `api/retrieval.py`).
7. **Нет streaming-канала ответа.** UI получает `tool_trace` только в финальном HTTP-ответе. При multi-step sessions UX страдает (`ax 30s — спиннер). LangGraph `StateGraph.astream(...)` решает это нативно.
8. **`ToolCallTrace` теряет полезную информацию.** Хранится только `args_summary` (плоский dict), нет `tool_call_id`, нет `parent_message_id`, нет цепочки «AI → tool → AI». Для дебага и для graph-эвализаторов это болезненно.

### 5.3 Дублирование и долг

9. **6 inline `Tool`-классов в `experiment_references_smolagents_spike.py`** — кандидаты в общий tool registry (`get_lines`, `grep_article`, `count_reference_markers`, `find_bibliography_candidates`, `segment_reference_block`, `heuristic_references`). Часть из них (`heuristic_references`) — обёртка над production `ingestion.stages.references.extract_references`. После миграции эти tools регистрируются как «research tools» в `science_graphrag/agent/tools/research/` и могут переиспользоваться будущим reference-агентом продакшна.
10. **Документация про `smolagents`** будет вводить в заблуждение после удаления библиотеки. Все ссылки в `docs/analysis/` и `eval/results/` нужно обновить (ссылка на новый spec/анализ + пометка «archived experiment»).

---

## 6. План работ — Wave Y-LangGraph

Шесть фаз: Y1 — фундамент (без изменения runtime), Y2 — single-agent ReAct на LangGraph (legacy v1 endpoint неизменно работает через адаптер), Y3 — v2 endpoint + streaming, Y4 — multi-agent (supervisor + 2-3 specialists), Y5 — миграция research spike, Y6 — выпил `smolagents` и legacy `BaseAgentTool`.

Y2/Y3 и Y4/Y5 могут идти параллельно, если хватает рук. Минимальный последовательный путь: Y1 → Y2 → Y6.

### 6.1 Wave Y1 — фундамент (зависимости, config, observability hooks)

**Цель:** установить LangChain/LangGraph, проверить, что `ChatOpenAI` работает с OpenRouter через текущие `extraction_llm_*` настройки, подключить OpenInference-инструментацию. Никаких изменений в `RetrievalAgent`.

#### Чеклист Y1

- [ ] **Y1.1 Зависимости.**
  - В `[project.optional-dependencies]` `agent` добавить `langgraph-supervisor>=0.0.6` и `openinference-instrumentation-langchain>=0.2`.
  - `pip install -e '.[agent]'` в venv; зафиксировать lock (если используется constraints).
  - Acceptance: `python -c "import langgraph, langchain_core, langchain_openai, langgraph_supervisor; from openinference.instrumentation.langchain import LangChainInstrumentor"` — без ошибок.

- [ ] **Y1.2 Smoke `ChatOpenAI` → OpenRouter.**
  - Скрипт `scripts/smoke_langchain_openrouter.py` (сделать одноразовым; не оставлять в репо или положить в `scripts/_dev/`).
  - Запросить `extraction_llm_model` с одним сообщением «ping»; получить `AIMessage`.
  - Acceptance: ответ есть, `usage_metadata` (или `response_metadata.token_usage`) содержит токены.

- [ ] **Y1.3 LangChain instrumentation в Phoenix.**
  - В `science_graphrag/observability/phoenix_tracer.py` рядом с `_register_optional_openai_instrumentation` добавить `_register_optional_langchain_instrumentation` (тот же шаблон через `importlib`, переменная окружения `PHOENIX_LANGCHAIN_AUTO_INSTRUMENTATION` по умолчанию `1`).
  - Включается из `init_tracer_provider()`.
  - Acceptance: smoke-вызов из Y1.2 виден в Phoenix как LLM-спан с `llm.model_name`, `llm.token_count.*`, `llm.provider="openrouter"`.

- [ ] **Y1.4 Settings.**
  - Добавить поля из §4.2 в `science_graphrag/config.py` с валидацией (`agent_supervisor_recursion_limit ≥ agent_max_tool_calls + 4`).
  - Дополнить `.env.example` блоком из §4.4.
  - Acceptance: `pytest tests/test_config.py` (если есть) или новый smoke; `Settings()` валидируется без env-ключей.

- [ ] **Y1.5 Docker / CI.**
  - В backend `Dockerfile` поменять `pip install -e '.'` → `pip install -e '.[agent]'`.
  - В CI workflow (`.github/workflows/*.yml`) добавить тот же extras для backend job.
  - Acceptance: контейнер собирается; `docker compose run --rm api python -c "import langgraph"` — OK.

- [ ] **Y1.6 Doc анонс.**
  - Дополнить [`runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) разделом `Wave Y` (ссылка на этот документ + статус: **Y1 в работе**).

### 6.2 Wave Y2 — single-agent LangGraph за тем же v1 endpoint

**Цель:** заменить тело `RetrievalAgent.run` на LangGraph `StateGraph` с одним specialist'ом (по сути ReAct loop), сохранив контракт `AgentRunOutput`/`AgentQueryResponse` и `ToolCallTrace`. Детерминированный режим оставить через флаг `agent_runtime="retrieval_v1"` (rollback).

#### Чеклист Y2

- [ ] **Y2.1 Tool registry на `langchain_core.tools`.**
  - Для каждого из 6 tools (`cypher_query`, `entity_search`, `edge_search`, `idea_search`, `summarize_workspace`, `final_answer`) сделать обёртку через `@tool(args_schema=…)` с Pydantic args. Внутри — реюз текущей реализации (`Neo4jGraphStore.session()`, `QdrantChunkStore.search_similar`, `validate_readonly_cypher`, …).
  - Возвращаемый JSON-формат идентичен текущему `ToolResult.payload` (важно для UI и evaluator'а).
  - В `science_graphrag/agent/tools/__init__.py::build_tool_registry(stores)` — функция, которая возвращает `list[BaseTool]` для подачи в `ChatOpenAI.bind_tools(...)`.
  - Acceptance: `tests/agent/test_tools_registry.py` — конструируется список из 6 tools, у каждого `args_schema` и `description`; вызов `cypher_query(query="MATCH ... DELETE")` бросает `CypherNotAllowedError`.

- [ ] **Y2.2 LangGraph `StateGraph`.**
  - В `science_graphrag/agent/graph/state.py` определить `AgentState` (см. §3.3.2).
  - В `science_graphrag/agent/graph/supervisor.py::build_retrieval_graph(stores, settings)` — один цикл `chat_node → tools_node` с `add_conditional_edges` по наличию `tool_calls` в последнем `AIMessage`. `chat_node` — `ChatOpenAI(...).bind_tools(...).invoke(state.messages)`. `tools_node` — стандартный `ToolNode(tool_registry)`. Условие выхода — `final_answer` tool либо отсутствие новых tool calls.
  - Recursion limit = `agent_supervisor_recursion_limit`.
  - Acceptance: `tests/agent/test_graph_smoke.py` — конструируется compiled graph, `graph.invoke({"messages": [HumanMessage("hello")], …})` отрабатывает на fake LLM (`langchain_core.language_models.fake.FakeListChatModel`).

- [ ] **Y2.3 Адаптер LangGraph state → `ToolCallTrace`.**
  - В `science_graphrag/agent/graph/tracing.py::collect_tool_trace(state) -> list[ToolCallTrace]` — обходим `state.messages`, превращаем `ToolMessage` + предшествующий `AIMessage.tool_calls[i]` в `ToolCallTrace{step, tool, args_summary, row_count, duration_ms, truncated, error}`.
  - `args_summary` — заполняется по контракту, который сейчас использует `BaseAgentTool.run_with_trace.args_summary` (короткие текстовые срезы запроса, top_k, workspace_id, и т. п.) — при необходимости передавать через `state.metadata.tool_args_summary[tool_call_id]`.
  - `duration_ms` — измеряется callbacks LangChain (`BaseCallbackHandler.on_tool_start/on_tool_end`).
  - Acceptance: `tests/agent/test_tool_trace_adapter.py` — на собранном fake state получаем тот же набор полей, что и текущий `BaseAgentTool.run_with_trace`.

- [ ] **Y2.4 Новый `runtime.py::RetrievalAgent`.**
  - `RetrievalAgent` теперь — тонкая обёртка вокруг `build_retrieval_graph(...).compile(...)` + `collect_tool_trace`.
  - Сигнатура `.run(question, workspace_id, max_tool_calls)` сохраняется → `AgentRunOutput{answer, citations, tool_trace}` сохраняется.
  - Если `settings.agent_runtime == "retrieval_v1"` — fallback на старую детерминированную реализацию (живёт в `runtime_legacy.py`, переезд кода без правок).
  - Acceptance:
    - `tests/agent/test_runtime.py::test_build_agent_and_run_smoke` — зелёный без правок (с fake LLM через `monkeypatch`).
    - `tests/test_api_agent_smoke.py` — зелёный без правок.
    - `eval-stand: pip install -e '.[agent]' && pytest tests/agent` — зелёный.

- [ ] **Y2.5 Phoenix разметка (минимум, ручная).**
  - В `RetrievalAgent.run` обернуть тело в `chain_span("agent.query", {"agent.runtime": settings.agent_runtime, "agent.max_tool_calls": …, "session.id": ask_session_id, "user.id": workspace_id, "agent.question": question})`.
  - В адаптере `collect_tool_trace` дополнительно пройтись `traced_tool_span("tool.{name}", tool_name=…, tool_parameters=args_summary)` если LangChain auto-instrumentation отключена (на случай ENV-конфигурации). Нормальный путь — auto-instrumentation покрывает всё.
  - Acceptance: один `POST /v1/agent/query` → один trace в Phoenix с CHAIN-кореннем `agent.query` и tool-spans.

- [ ] **Y2.6 Smoke + benchmark `agent_tools_v1`.**
  - Запустить `science-graphrag-agent-benchmark tests/fixtures/benchmarks/agent_tools --suite --tier agent_tools_mini` с реальным LLM (если ключ есть) и с `--mock-runtime`.
  - Проверить `score_agent_case`: tool_call_correctness, budget, cypher_safety, answer_grounded.
  - Acceptance: `passed=True` минимум на mini-tier; `eval/results/agent-tools-langgraph-y2.json` сохранён.

- [ ] **Y2.7 Doc.**
  - В [`docs/specs/agent-tools-v1.md`](../specs/agent-tools-v1.md) добавить секцию «Implementation: LangGraph (Wave Y2)» с указанием на `agent/graph/`.
  - Обновить ADR 016: status → Accepted, добавить раздел «Implementation history» с пометкой Y2.

### 6.3 Wave Y3 — `/v2/agent/query` + streaming + Phoenix корреляция

**Цель:** UI получает события агента в реальном времени; ответ имеет `phoenix_trace_id` и `events`-историю; v1 остаётся как deprecated alias.

#### Чеклист Y3

- [ ] **Y3.1 SSE endpoint.**
  - `POST /v2/agent/query` (новый файл `science_graphrag/api/agent_v2.py`); поддержка `Accept: text/event-stream` через `sse-starlette`.
  - События: `event: tool_call` (`tool_call_id`, `tool_name`, `args_summary`), `event: tool_result` (`tool_call_id`, `row_count`, `truncated`, `preview`), `event: token` (если включено), `event: final_answer` (`answer`, `citations`), `event: error`.
  - Под капотом — `graph.astream({"messages": [...], …}, …, stream_mode="updates")`.
  - Acceptance: `tests/test_api_agent_v2_smoke.py` — через `httpx.AsyncClient` стримим события, проверяем порядок `tool_call → tool_result → final_answer` на fake LLM.

- [ ] **Y3.2 Sync ответ v2.**
  - При `Accept: application/json` — собираем все события в один `AgentQueryResponseV2{answer, citations, tool_trace, events, duration_ms, phoenix_trace_id, run_metadata}`.
  - `phoenix_trace_id` берётся `format(trace_api.get_current_span().get_span_context().trace_id, "032x")` из root-спана `agent.query`.
  - Acceptance: smoke-тест возвращает `phoenix_trace_id` (32 hex) и непустой `events`.

- [ ] **Y3.3 Корреляция с ask-session.**
  - Принимать `session_id` (UUID `ask_sessions.id`) в request; пробрасывать в `chain_span("agent.query", {"session.id": session_id, …})`.
  - Если `session_id` не передан — генерировать `uuid4()` per request (как в Wave X2.6).
  - Acceptance: в Phoenix → Sessions UI один `ask_session_id` группирует серию trace'ов.

- [ ] **Y3.4 Spec.**
  - Создать [`docs/specs/agent-tools-v2.md`](../specs/agent-tools-v2.md) с полным контрактом v2: request, события SSE, sync response, ошибки, `phoenix_trace_id`.
  - В [`runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) Wave R обновить ссылку с v1 → v2.

- [ ] **Y3.5 UI: подключить v2 (опционально, если ресурс есть).**
  - В backlog frontend ([`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md)) добавить запись «AskPanel: переключить на `/v2/agent/query` SSE» (отдельный PR, чтобы не ломать Wave Y backend-PR).

- [ ] **Y3.6 Deprecation warning v1.**
  - В response `POST /v1/agent/query` — header `Deprecation: true` + `Sunset: <date>`. В run_metadata — `deprecated: true, replacement: "/v2/agent/query"`.
  - Внутренне — переадресация на тот же LangGraph runtime (без дублирования кода).

### 6.4 Wave Y4 — multi-agent (supervisor + specialists)

**Цель:** активизировать supervisor pattern, развести нагрузку на специалистов. На этой фазе закрепляются roles и появляется `writer_agent` (LLM-синтезатор финального ответа).

#### Чеклист Y4

- [ ] **Y4.1 Specialists.**
  - `science_graphrag/agent/graph/nodes/retrieval_agent.py` — фокус на `idea_search`, `summarize_workspace` (Qdrant + Workspace Neo4j).
  - `science_graphrag/agent/graph/nodes/graph_agent.py` — `cypher_query`, `entity_search`, `edge_search` (Neo4j-навигация). На вход — workspace context, на выход — структурированные узлы/рёбра + потенциальные кандидаты work_id.
  - `science_graphrag/agent/graph/nodes/writer_agent.py` — финальный LLM-синтез ответа с citations. Вход — все накопленные `tool_results` + question, выход — `AIMessage` с `final_answer` tool call.
  - Каждый specialist — отдельный LangGraph subgraph (compile отдельно), supervisor вызывает их через `Send(...)` или прямой `node()`.

- [ ] **Y4.2 Supervisor.**
  - `science_graphrag/agent/graph/supervisor.py::build_supervisor_graph(stores, settings)` — `langgraph_supervisor.create_supervisor` или ручной `StateGraph`.
  - Routing prompt: `"You are a supervisor for scholarly research agents. Available specialists: retrieval_agent (semantic + workspace search), graph_agent (Neo4j cypher + neighbors), writer_agent (final answer). Decide which to call next given the question and accumulated tool results. Stop when you have enough evidence."`.
  - Acceptance: `tests/agent/test_supervisor_routing.py` — на синтетических вопросах supervisor делает разумный выбор (ассерты на последовательность вызовов через fake LLM с предзаданными ответами).

- [ ] **Y4.3 State расширение.**
  - В `AgentState` добавить `specialist_results: dict[str, list[dict]]` для аккумуляции результатов специалистов; `current_specialist: str | None`; `routing_log: list[dict]`.
  - Адаптер `collect_tool_trace` дополнительно собирает `routing_log` для legacy `tool_trace` (как «pseudo-tool steps» с `tool="route_to_specialist"`).

- [ ] **Y4.4 Acceptance benchmark.**
  - В `tests/fixtures/benchmarks/agent_tools/case_tiers.json` добавить tier `agent_tools_multiagent` с кейсами, где ожидается работа `graph_agent` (Cypher на конкретные DOI/work_id) и `writer_agent` (нетривиальный синтез).
  - В `eval/agent_tools/metrics.py` расширить `score_agent_case` опциональным `expected_specialist_sequence` (рядом с `expected_tool_sequence`).
  - Acceptance: новый tier зелёный с реальным LLM; mini-tier по-прежнему зелёный.

- [ ] **Y4.5 Doc + ADR.**
  - Новый ADR `017-langgraph-supervisor-multiagent.md` (статус Accepted) — фиксирует supervisor pattern, role boundaries, расширяемость.
  - Обновить [`agent-tools-v2.md`](../specs/agent-tools-v2.md): секция `events.specialist_routing`.

### 6.5 Wave Y5 — миграция research spike (`scripts/experiment_references_smolagents_spike.py`)

**Цель:** переписать spike на LangGraph, заменив `ToolCallingAgent` + 6 inline tools. Сохранить CLI-интерфейс (`spike` / `suite`) и контракт выходного JSON (`refs_agent_suite_v2`), чтобы не ломать `eval/references_harness/agent_suite_metrics.py` и `tests/test_agent_suite_metrics.py`.

#### Чеклист Y5

- [ ] **Y5.1 Перенести 6 tools в `science_graphrag/agent/tools/research/`.**
  - `heuristic_references` (обёртка `extract_references`), `grep_article`, `get_lines`, `find_bibliography_candidates`, `count_reference_markers`, `segment_reference_block`.
  - Каждый — `@tool(args_schema=…)`. На вход — текст статьи (или путь / список строк) через closure / DI.
  - Acceptance: `tests/agent/test_research_tools.py` — каждый tool отрабатывает на фикстуре `tests/fixtures/benchmarks/layer1/yolov1/article.md` так же, как сегодняшние `Tool.forward(...)`.

- [ ] **Y5.2 LangGraph `references_router` graph.**
  - `science_graphrag/agent/graph/research/references_router.py::build_references_router(text)` — single-specialist ReAct loop.
  - Системный prompt — как сейчас в spike (instructions для router с ожиданием JSON `{start_line, end_line, entry_count, style_guess, confidence, reasoning_summary}`).
  - Парсер финального JSON — переиспользует `_parse_structured_guess` из spike (вынести в `science_graphrag/agent/graph/research/parsers.py`).

- [ ] **Y5.3 Новый CLI `scripts/experiment_references_langgraph_spike.py`.**
  - Тот же интерфейс `spike` / `suite` (опции `--case-id`, `--tier`, `--max-steps`, `--output-path`).
  - Внутри — `build_references_router(text).compile().invoke(...)` + сбор той же row-shape, что и сегодня (`status`, `case_id`, `task_mode`, `max_steps`, `final_answer`, `wall_seconds`, `heuristic_baseline_count`, `parsed`, `parsed_entry_count`, метрики через `harness_metrics_for_parsed_span`).
  - Старый `experiment_references_smolagents_spike.py` пометить **deprecated** (выводит warning, импортирует новый при наличии extras `[agent]`); удалить в Y6.
  - Acceptance: `python scripts/experiment_references_langgraph_spike.py suite --tier references_benchmark_v1 --case yolov1` → JSON c теми же ключами; `tests/test_agent_suite_metrics.py` зелёный (не зависит от runtime).

- [ ] **Y5.4 Документация.**
  - Обновить [`_archive/reference-extraction-llm-agent-tools.md`](_archive/reference-extraction-llm-agent-tools.md) (или вернуть из `_archive/` если станет вновь активным): секция «Migration to LangGraph (Wave Y5)» — что переехало, ссылки на новые файлы.
  - В `eval/results/refs_llm_agent_experiment_*.md` добавить запись о Y5: «новые прогоны через LangGraph; legacy smolagents результаты сохранены для исторической репродукции».

### 6.6 Wave Y6 — выпил `smolagents` и legacy `BaseAgentTool`

**Цель:** окончательно убрать `smolagents` из дерева и из зависимостей, удалить `runtime_legacy.py` (детерминированный режим), почистить упоминания в документации.

#### Чеклист Y6

- [ ] **Y6.1 Удалить `smolagents` из `pyproject.toml`.**
  - `[project.optional-dependencies] research = []` → удалить ключ полностью или оставить пустым с комментарием.
  - `pip install -e '.[agent]'` без претензий на `[research]`.
  - Acceptance: `rg -n smolagents` по репо возвращает только архивные `eval/results/refs_llm_agent_experiment_*.md` и (опционально) `docs/analysis/_archive/reference-extraction-llm-agent-tools.md` [HISTORICAL] в исторической секции.

- [ ] **Y6.2 Удалить `scripts/experiment_references_smolagents_spike.py`.**
  - Перенести историческую копию (если нужна для воспроизводимости) в `scripts/_archive/`. Обычно достаточно git history.
  - Удалить ссылки на скрипт из README, runbooks.

- [ ] **Y6.3 Удалить `science_graphrag/agent/runtime_legacy.py`.**
  - Сценарий `agent_runtime="retrieval_v1"` больше не поддерживается; в `Settings` валидация `agent_runtime ∈ {"langgraph_supervisor_v1"}`.

- [ ] **Y6.4 Удалить `BaseAgentTool` (старая база).**
  - `science_graphrag/agent/tools/base.py` — удалить класс `BaseAgentTool` + `ToolResult` (если не используются нигде, кроме legacy adapter).
  - Acceptance: `rg -n BaseAgentTool` по репо — пусто.

- [ ] **Y6.5 Удалить `POST /v1/agent/query`.**
  - Endpoint удаляется; в `science_graphrag/api/main.py` оставить redirect (308) на `/v2/agent/query` либо просто 410 Gone.
  - UI к этому моменту мигрирован на v2 (см. Y3.5 follow-up).

- [ ] **Y6.6 Документация — финальный sweep.**
  - В [`docs/adr/016-agent-tool-registry-and-langgraph.md`](../adr/016-agent-tool-registry-and-langgraph.md) — раздел «Implementation completed (Wave Y)».
  - В [`runbooks/roadmap-next-waves.md`](../runbooks/roadmap-next-waves.md) Wave R — «Status: Wave Y migration completed YYYY-MM-DD».
  - В этом документе — `**Статус:** completed YYYY-MM-DD`, переместить в `docs/analysis/_archive/` (если такая папка появится; иначе оставить в `docs/analysis/` как исторический).

- [ ] **Y6.7 Финальный quality gate.**
  - `pytest tests/agent tests/test_api_agent_smoke.py tests/test_api_agent_v2_smoke.py tests/test_agent_suite_metrics.py` — зелёный.
  - `science-graphrag-agent-benchmark` mini + multiagent tier — зелёный.
  - `pylint science_graphrag/agent tests/agent` — без новых критических warnings.
  - `black science_graphrag tests` + `isort science_graphrag tests` — без diff.

---

## 7. Сводный чеклист по Wave Y-LangGraph

### Y1 — фундамент

- [ ] Y1.1 Зависимости `[agent]` (+supervisor +instrumentation-langchain).
- [ ] Y1.2 Smoke `ChatOpenAI` ↔ OpenRouter.
- [ ] Y1.3 LangChain Phoenix instrumentation в `phoenix_tracer.py`.
- [ ] Y1.4 Settings (`agent_runtime`, `agent_supervisor_recursion_limit`, `agent_chat_*`, `agent_streaming_enabled`) + `.env.example`.
- [ ] Y1.5 Docker / CI: backend image и job ставят `[agent]`.
- [ ] Y1.6 Doc: `runbooks/roadmap-next-waves.md` — Wave Y stub.

### Y2 — single-agent LangGraph за v1 endpoint

- [ ] Y2.1 6 tools на `langchain_core.tools.@tool` + `build_tool_registry`.
- [ ] Y2.2 `StateGraph` ReAct loop; recursion limit; fake-LLM smoke.
- [ ] Y2.3 Адаптер `collect_tool_trace` (LangGraph state → legacy `ToolCallTrace`).
- [ ] Y2.4 `RetrievalAgent` обёртка; `agent_runtime` switch; `tests/agent/`+`tests/test_api_agent_smoke.py` зелёные без правок.
- [ ] Y2.5 Phoenix root-span `agent.query` + auto LLM/TOOL spans.
- [ ] Y2.6 `agent_tools_v1` mini benchmark — pass.
- [ ] Y2.7 Doc: `agent-tools-v1.md` implementation note + ADR 016 history.

### Y3 — `/v2/agent/query` + streaming

- [ ] Y3.1 SSE endpoint: `tool_call` / `tool_result` / `token` / `final_answer` / `error`.
- [ ] Y3.2 Sync v2 response с `events`, `phoenix_trace_id`.
- [ ] Y3.3 `session_id` корреляция → Phoenix Sessions.
- [ ] Y3.4 Spec [`agent-tools-v2.md`](../specs/agent-tools-v2.md).
- [ ] Y3.5 UI follow-up: AskPanel → SSE (отдельный PR, через `refactor-frontend.md`).
- [ ] Y3.6 v1 deprecation header + run_metadata.

### Y4 — multi-agent supervisor

- [ ] Y4.1 Specialists (`retrieval_agent`, `graph_agent`, `writer_agent`).
- [ ] Y4.2 Supervisor (`langgraph_supervisor.create_supervisor` или ручной).
- [ ] Y4.3 `AgentState.specialist_results` + `routing_log`; адаптер `tool_trace`.
- [ ] Y4.4 Benchmark tier `agent_tools_multiagent` + `expected_specialist_sequence`.
- [ ] Y4.5 ADR 017 + spec update.

### Y5 — research spike → LangGraph

- [ ] Y5.1 6 research tools в `agent/tools/research/`.
- [ ] Y5.2 `references_router` LangGraph subgraph.
- [ ] Y5.3 `scripts/experiment_references_langgraph_spike.py` (тот же CLI/JSON-shape).
- [ ] Y5.4 Doc update в `_archive/reference-extraction-llm-agent-tools.md` [HISTORICAL] + `eval/results/refs_llm_agent_experiment_*.md`.

### Y6 — выпил smolagents и legacy

- [ ] Y6.1 Удалить `smolagents` из `pyproject.toml` (`[research]` пустой/убран).
- [ ] Y6.2 Удалить старый `experiment_references_smolagents_spike.py`.
- [ ] Y6.3 Удалить `runtime_legacy.py` + `agent_runtime="retrieval_v1"`.
- [ ] Y6.4 Удалить `BaseAgentTool` / `ToolResult`.
- [ ] Y6.5 Удалить `POST /v1/agent/query` (308 → v2 или 410 Gone).
- [ ] Y6.6 Doc sweep: ADR 016 «completed», runbook Wave R, этот документ → `**Статус:** completed`.
- [ ] Y6.7 Quality gate (pytest + benchmarks + pylint + black/isort).

### Acceptance уровня волны

- [ ] `rg -n "smolagents" -g '!eval/results/*' -g '!docs/analysis/_archive/*'` — пусто.
- [ ] `rg -n "BaseAgentTool" -g '!docs/**'` — пусто.
- [ ] `science-graphrag-agent-benchmark tests/fixtures/benchmarks/agent_tools --suite --tier agent_tools_mini` — `passed=True` для всех кейсов.
- [ ] `science-graphrag-agent-benchmark tests/fixtures/benchmarks/agent_tools --suite --tier agent_tools_multiagent` — `passed=True` для всех кейсов (после Y4).
- [ ] В Phoenix → Traces для одного `POST /v2/agent/query` есть один trace `agent.query` с TOOL/LLM/RETRIEVER-spans и `phoenix_trace_id` равный возвращённому в response.
- [ ] В Phoenix → Sessions один `ask_session_id` группирует все вопросы из одного диалога.
- [ ] CI: backend job включает `pip install -e '.[agent]'` и `pytest tests/agent`; стат-чек `pylint --fail-under=7.0` зелёный.

---

## 8. Связь с другими волнами и рисками

### 8.1 Интерфейсы с волнами

- **Wave X-Phoenix (`_archive/phoenix-tracing-coverage-2026-04-25.md`)**: Y2.5 + Y3.2 закрывают пункты X2.1, X2.2, X2.7 «по факту» через auto-instrumentation; X2.3 (RETRIEVER в `idea_search`) и X2.4 (EMBEDDING) лучше делать **внутри Y2.1** при переписывании tool — чтобы не возвращаться. Wave X1 (fix ingest-tracing) и Wave Y независимы.
- **Wave R (Agent retrieval + tool-use benchmarks)**: Wave Y — это **техническая реализация** ADR 016, которое было принято в Wave R. После Y4 advisory benchmark `agent_tools_v1` → `agent_tools_v2` (через promotion review, см. [`benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md)).
- **Wave V (SSE для ingest)**: тот же `sse-starlette` + nginx-конфиг (`proxy_buffering off`, `proxy_read_timeout 1h`) переиспользуется для `/v2/agent/query` SSE. Если Wave V уже в проде — Y3.1 ставится «бесплатно» с уже отлаженным каналом.
- **Wave U/V (Redis/Dramatiq для ingest)**: агент не использует фоновую обработку (всё synchronous per-request), но если позже понадобится «long-running agent jobs» (research mode с десятками шагов и LLM-рассуждениями) — переиспользуем pattern Dramatiq + Redis. **Рисков пересечения нет.**
- **ADR 017 (новый, в Y4)**: фиксирует supervisor pattern и role boundaries; ссылается на этот документ как источник плана.

### 8.2 Риски и митигации

| Риск | Описание | Митигация |
|---|---|---|
| **OpenRouter compatibility** | `ChatOpenAI` с произвольным `base_url` иногда некорректно парсит `tool_calls` для не-OpenAI моделей (mistral, claude-haiku) — особенно при структурированных JSON-ответах. | Y1.2 + Y2.6 проверяют это эмпирически на `mistralai/mistral-small-3.2-24b-instruct`. Если падает — fallback на `instructor`-style structured output, либо смена tool-format на `<function>...</function>` через специальный prompt template. |
| **`smolagents` API drift в research workflows** | Команда могла привыкнуть к CLI `experiment_references_smolagents_spike.py` для дебага/прогонов. | Y5.3 сохраняет CLI-сигнатуру; в Y5.4 — короткий runbook. |
| **`ToolCallTrace` breaking change** | `args_summary` сейчас собирается tools руками; LangChain даёт сырой `tool.invoke({"query": …})`. | Адаптер Y2.3 имеет фиксированный mapper `tool_call.args → args_summary` с теми же полями (выборка по схеме `args_schema`). На неизвестные поля — `*: <truncated>`. |
| **Phoenix double-instrumentation** | Если включить и `openinference-instrumentation-openai`, и `openinference-instrumentation-langchain`, внутри `ChatOpenAI` будут **два** LLM-спана на один вызов. | В `_register_optional_openai_instrumentation` добавить условие: «если LangChain instrumentation активна — выключаем openai auto». ENV-переключатель `PHOENIX_OPENAI_AUTO_INSTRUMENTATION=0`. |
| **`recursion_limit` vs `max_tool_calls`** | LangGraph `recursion_limit` считает все node-переходы, включая supervisor-итерации, а не только tool calls. Можно упасть в `GraphRecursionError` раньше, чем израсходовать `max_tool_calls`. | `agent_supervisor_recursion_limit ≥ agent_max_tool_calls + 4` (validated в Settings). При исчерпании supervisor отдаёт partial answer с `error="budget_exceeded"`, не 500. |
| **Async vs sync API** | LangGraph `astream` async; FastAPI endpoint sync (`def post_agent_query(...)`). | v2 endpoint объявить `async def`; для v1 (после Y2) — синхронный wrapper через `asyncio.run(graph.ainvoke(...))` либо `graph.invoke(...)` (LangGraph поддерживает оба). |
| **Tests, опирающиеся на детерминированный output** | `tests/agent/test_runtime.py` ассертит «`tool_trace ≥ 2`» — это пройдёт, но `eval/agent_tools` cases с `expected_tool_sequence` могут стать flaky из-за LLM-вариативности. | До Y4 supervisor вызывает только `retrieval_agent`, и temperature=0 + структурированный prompt дают воспроизводимый порядок. На случай LLM-вариативности — `min_tool_call_correctness` уже есть в gold (default 0.7). |
| **`PHOENIX_TRACE_SCOPE=extraction_llm` и agent в одном процессе** | Сегодня scope скрывает всё кроме ingest-LLM. После Y2 в том же процессе будет `POST /v1/agent/query` — его трейсы тоже скроются. | Документировать: `extraction_llm` режим — для batch-ingest CI, не для production API. Для production оставлять `full`. Опционально ввести `agent_only` режим (parameter X-X). |

---

## 9. Что **не входит** в Wave Y

- Замена существующих ingestion LLM-вызовов (`extractor.SyncInstructorExtractor.extract_maybe`, claims/semantic) на LangChain. Они используют `instructor` + structured output — это отдельный технологический выбор, и LangChain здесь не даёт явного выигрыша. Ingestion LLM-стэк трогаем только в рамках Wave X1 (Phoenix-разметка), не миграции.
- Замена эмбеддингов (`HashEmbeddingProvider` / `try_sentence_transformer`) на `langchain_community.embeddings`. Сегодня — local sentence-transformers, прямые вызовы; LangChain-обёртка излишняя.
- LangChain memory / vector stores. Qdrant — наш source of truth, обёртка `QdrantVectorStore` из `langchain_qdrant` сегодня не нужна; tools идут напрямую через `QdrantChunkStore`.
- LangSmith. Phoenix покрывает observability; LangSmith — вторая платформа без явного выигрыша.

Если впоследствии понадобится LangChain memory или LangChain vectorstore — это будет отдельный микро-ADR, не Wave Y.

---

## 10. Глоссарий

- **Specialist** — отдельный LangGraph node, отвечающий за узкую группу tools (retrieval / graph / writer). На старте Y2 один specialist; с Y4 — три и больше.
- **Supervisor** — LangGraph node-роутер, который по состоянию диалога выбирает следующего specialist'а или принимает решение «достаточно, формировать final_answer».
- **AgentState** — TypedDict с типизированным `messages`, `workspace_id`, `tool_trace`, `citations`, `budget_remaining`, `metadata`. Передаётся между всеми nodes.
- **ToolNode** — стандартный LangGraph node, выполняющий все `tool_calls` из последнего `AIMessage` параллельно.
- **`agent_runtime`** — feature flag в `Settings`: `langgraph_supervisor_v1` (default после Y2) или `retrieval_v1` (legacy, удалён в Y6).
- **`recursion_limit`** — параметр `StateGraph.invoke`, ограничивающий число node-переходов; защита от бесконечного цикла supervisor↔specialist.
