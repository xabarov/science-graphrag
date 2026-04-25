# Round 4 — Agent Prompts («Wave Y3 + GR2 + G-RetrievalCore + H-AskV2SSE»)

> Дата: 2026-04-25
> Источник плана: `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §7 «Раунд 4»
> Предусловие: Раунд 3 выполнен (Wave W, Wave Y2+X2, G-Neo4jSplit, H-AskPanelSplit).
> Порядок запуска: **Все 4 агента параллельно** — файловые скоупы не пересекаются (см. примечания по `main.py` ниже).

**Проверка предусловий перед запуском всех агентов:**

```bash
# Раунд 3 complete:
python -c "from science_graphrag.worker.actor import ingest_document_actor; print('worker ok')"
python -c "from science_graphrag.agent.graph.supervisor import build_retrieval_graph; print('langgraph ok')"
python -c "from science_graphrag.storage.neo4j.facade import Neo4jFacade; print('neo4j split ok')"
ls ui/src/components/work/AskAnswerPanel.jsx && echo "ask split ok"
ls ui/src/components/work/useAskSubmit.js && echo "useAskSubmit ok"
```

**Координация `main.py`:**
- Agent 1 добавляет `include_router(agent_v2_router, prefix="/v2")` — новая строка в конец блока роутеров.
- Agent 3 удаляет `sys.modules` shim и чистит `works/__init__.py` — другие строки файла.
- Конфликта нет при независимой правке, но если оба одновременно — применить Agent 3 первым (cleanup), Agent 1 вторым (добавление). Или разрешить мердж руками: файл небольшой.

---

## Agent 1 — Wave Y3: `POST /v2/agent/query` + SSE streaming + spec

**Задача:** создать новый endpoint `/v2/agent/query` с поддержкой SSE-стриминга событий LangGraph
и синхронного JSON-ответа. Написать спецификацию `docs/specs/agent-tools-v2.md`.
`POST /v1/agent/query` остаётся неизменным; добавить заголовок `Deprecation`.

### Контекст

Ты — агент Python/FastAPI. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предыстория:**
- Wave Y2 — ✅ DONE: `science_graphrag/agent/` переведён на LangGraph. `RetrievalAgent` в
  `science_graphrag/agent/runtime.py`. Граф в `agent/graph/supervisor.py`.
- Wave X2 — ✅ DONE (в комбо с Y2): `chain_span("agent.query", ...)` в `runtime.py`, Phoenix
  instrumentation.
- `sse-starlette>=2.1` уже в `pyproject.toml` (доставлено Wave V для ingest SSE).

**Текущее API-состояние:**
- `science_graphrag/api/agent.py` — v1 endpoint `POST /v1/agent/query` (sync JSON). Возвращает
  `AgentQueryResponse` (`answer`, `citations`, `tool_trace`, `duration_ms`, `run_metadata`).
- `science_graphrag/api/main.py` — регистрирует `agent_router` под `/v1`.
- LangGraph граф компилируется через `build_retrieval_graph(stores, settings)`, поддерживает `.stream()`.

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
cat science_graphrag/api/agent.py
cat science_graphrag/agent/runtime.py
cat science_graphrag/agent/graph/supervisor.py
cat science_graphrag/api/main.py | grep -E "include_router|agent|prefix"
# Убедиться, что sse-starlette установлена:
.venv/bin/python -c "import sse_starlette; print('sse ok')"
# Посмотреть, как agent SSE может работать через LangGraph:
.venv/bin/python -c "from langgraph.graph import StateGraph; g = StateGraph.__new__(StateGraph); print(dir(g))" 2>/dev/null | tr ',' '\n' | grep -i stream
```

### Шаг 1 — Спецификация `docs/specs/agent-tools-v2.md`

Создать файл `docs/specs/agent-tools-v2.md`. Содержание:

```markdown
# Agent Tools API v2 — Specification

**Status:** Draft (Wave Y3, 2026-04-25)
**Supersedes:** `docs/specs/agent-tools-v1.md` (v1 deprecated, not yet removed)

## Endpoint

```
POST /v2/agent/query
Content-Type: application/json
Accept: application/json          # → sync JSON response
Accept: text/event-stream         # → SSE stream
```

## Request

| Field          | Type            | Required | Default | Notes                      |
|----------------|-----------------|----------|---------|----------------------------|
| `question`     | string (≥1 ch)  | yes      | —       | Natural-language query      |
| `workspace_id` | string \| null  | no       | null    | Scopes retrieval            |
| `max_tool_calls` | int [1..30]   | no       | settings| Override agent budget       |

## SSE Event Stream (Accept: text/event-stream)

Events are emitted in chronological order. Each `data:` line is a JSON object.

| Event type     | When emitted                     | Key fields                                 |
|----------------|----------------------------------|--------------------------------------------|
| `tool_call`    | Before tool execution            | `step`, `tool`, `args_summary`             |
| `tool_result`  | After tool execution             | `step`, `tool`, `row_count`, `error`       |
| `token`        | Each LLM output token (optional) | `delta` (string fragment)                  |
| `final_answer` | Graph END reached                | `answer`, `citations`, `tool_trace`, `duration_ms`, `phoenix_trace_id`, `run_metadata` |
| `error`        | Unhandled exception              | `detail` (string)                          |

Example stream:

```
data: {"type":"tool_call","step":1,"tool":"entity_search","args_summary":{"query":"BERT"}}

data: {"type":"tool_result","step":1,"tool":"entity_search","row_count":5,"error":null}

data: {"type":"final_answer","answer":"BERT is…","citations":[…],"tool_trace":[…],"duration_ms":1240,"phoenix_trace_id":"abc123","run_metadata":{…}}
```

## Sync JSON Response (Accept: application/json)

Identical to v1 `AgentQueryResponse`, plus `phoenix_trace_id` field:

```json
{
  "answer": "…",
  "citations": […],
  "tool_trace": […],
  "duration_ms": 1240,
  "phoenix_trace_id": "abc123",
  "run_metadata": {
    "agent_runtime": "langgraph_react_v1",
    "agent_enabled": true,
    "agent_max_tool_calls": 8
  }
}
```

## Deprecation of v1

`POST /v1/agent/query` remains available during transition with headers:
```
Deprecation: true
Sunset: 2026-07-01
Link: </v2/agent/query>; rel="successor-version"
```

## Error responses

| Status | Condition                        |
|--------|----------------------------------|
| 503    | `agent_enabled=false` in config  |
| 422    | Validation error in request body |
| 500    | Unhandled exception              |
```

### Шаг 2 — Создать `science_graphrag/api/agent_v2.py`

```python
"""Agent query API v2 — SSE streaming + sync JSON (Wave Y3).

Endpoint: POST /v2/agent/query
Supports:
    Accept: text/event-stream  → SSE event stream
    Accept: application/json   → sync JSON (same as v1 + phoenix_trace_id)
"""

from __future__ import annotations

import json
import logging
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from science_graphrag.agent.runtime import build_agent
from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.observability.spans import chain_span

logger = logging.getLogger(__name__)

router = APIRouter()


class AgentQueryRequestV2(BaseModel):
    question: str = Field(..., min_length=1)
    workspace_id: str | None = None
    max_tool_calls: int | None = Field(default=None, ge=1, le=30)


class AgentQueryResponseV2(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    tool_trace: list[dict[str, Any]]
    duration_ms: int
    phoenix_trace_id: str | None = None
    run_metadata: dict[str, Any]


@router.post("/agent/query")
async def post_agent_query_v2(
    request: Request,
    body: AgentQueryRequestV2,
    accept: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
):
    """POST /v2/agent/query — SSE stream or sync JSON based on Accept header."""
    if not settings.agent_enabled:
        raise HTTPException(status_code=503, detail="agent_disabled")

    wants_sse = "text/event-stream" in (accept or "")
    workspace_id = (body.workspace_id or "").strip() or None
    max_tool_calls = body.max_tool_calls or settings.agent_max_tool_calls

    if wants_sse:
        return EventSourceResponse(
            _stream_agent(
                settings=settings,
                stores=stores,
                question=body.question,
                workspace_id=workspace_id,
                max_tool_calls=max_tool_calls,
            )
        )

    # Sync JSON path — run to completion, return v2 response
    agent = build_agent(settings=settings, stores=stores)
    started = perf_counter()
    out = agent.run(
        question=body.question,
        workspace_id=workspace_id,
        max_tool_calls=max_tool_calls,
    )
    duration_ms = int((perf_counter() - started) * 1000)
    return AgentQueryResponseV2(
        answer=out.answer,
        citations=out.citations,
        tool_trace=[t.__dict__ if hasattr(t, "__dict__") else dict(t) for t in out.tool_trace],
        duration_ms=duration_ms,
        phoenix_trace_id=None,  # TODO: extract from OTel context after X2 trace_id propagation
        run_metadata={
            "agent_runtime": settings.agent_runtime,
            "agent_enabled": settings.agent_enabled,
            "agent_max_tool_calls": max_tool_calls,
            "extraction_llm_model": settings.extraction_llm_model,
        },
    )


async def _stream_agent(
    *,
    settings: Settings,
    stores: StoreRegistry,
    question: str,
    workspace_id: str | None,
    max_tool_calls: int,
) -> AsyncIterator[dict]:
    """Yield SSE events from LangGraph stream."""
    from langchain_core.messages import AIMessage, ToolMessage

    started = perf_counter()
    step = 0
    final_answer = ""
    tool_trace: list[dict[str, Any]] = []
    citations: list[dict[str, Any]] = []

    try:
        from science_graphrag.agent.graph.supervisor import build_retrieval_graph
        from langchain_core.messages import HumanMessage

        graph = build_retrieval_graph(stores, settings)
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "workspace_id": workspace_id,
            "citations": [],
            "tool_trace": [],
            "budget_remaining": max_tool_calls,
            "metadata": {"agent_runtime": settings.agent_runtime},
        }

        # LangGraph .astream() yields partial state dicts per node
        async for chunk in graph.astream(
            initial_state,
            config={"recursion_limit": settings.agent_supervisor_recursion_limit},
        ):
            for node_name, node_state in chunk.items():
                messages = node_state.get("messages") or []
                for msg in messages:
                    if isinstance(msg, AIMessage) and msg.tool_calls:
                        for tc in msg.tool_calls:
                            step += 1
                            args = tc.get("args") or {}
                            event_data = {
                                "type": "tool_call",
                                "step": step,
                                "tool": str(tc.get("name") or ""),
                                "args_summary": {
                                    k: str(v)[:200] for k, v in (args.items() if isinstance(args, dict) else {}.items())
                                },
                            }
                            tool_trace.append(event_data)
                            yield {"data": json.dumps(event_data)}

                    elif isinstance(msg, ToolMessage):
                        # Match result to last tool_call step
                        result_payload: dict[str, Any] = {}
                        error: str | None = None
                        try:
                            parsed = json.loads(str(msg.content or ""))
                            if isinstance(parsed, dict):
                                result_payload = parsed
                        except Exception:  # noqa: BLE001
                            error = str(msg.content or "")[:200]

                        result_event = {
                            "type": "tool_result",
                            "step": step,
                            "tool": "",  # tool name not easily recoverable here
                            "row_count": result_payload.get("row_count"),
                            "error": error,
                        }
                        yield {"data": json.dumps(result_event)}

                    elif isinstance(msg, AIMessage) and not msg.tool_calls:
                        final_answer = str(msg.content or "")

                citations_chunk = node_state.get("citations")
                if citations_chunk:
                    citations = list(citations_chunk)

        duration_ms = int((perf_counter() - started) * 1000)
        final_event = {
            "type": "final_answer",
            "answer": final_answer,
            "citations": citations,
            "tool_trace": tool_trace,
            "duration_ms": duration_ms,
            "phoenix_trace_id": None,
            "run_metadata": {
                "agent_runtime": settings.agent_runtime,
                "agent_max_tool_calls": max_tool_calls,
            },
        }
        yield {"data": json.dumps(final_event)}

    except Exception as exc:  # noqa: BLE001
        logger.exception("agent v2 stream error")
        yield {"data": json.dumps({"type": "error", "detail": str(exc)})}
```

**Важно:**
- `graph.astream()` требует async контекста — endpoint сам `async def`.
- Если `graph.astream()` не поддерживается версией LangGraph — использовать `.stream()` через `asyncio.to_thread()` или синхронную итерацию, завёрнутую в `async def` генератор (fallback).
- Проверить доступность `.astream()`:
  ```bash
  .venv/bin/python -c "from langgraph.graph.state import CompiledGraph; print(hasattr(CompiledGraph, 'astream'))"
  ```
  Если `False` — использовать `asyncio.to_thread(lambda: list(graph.stream(initial_state, config=...)))` и emit события post-factum.

### Шаг 3 — Регистрация в `main.py`

В `science_graphrag/api/main.py` добавить:

```python
from science_graphrag.api.agent_v2 import router as agent_v2_router
# ...в блок include_router (после agent_router строки):
app.include_router(agent_v2_router, prefix="/v2")
```

### Шаг 4 — Deprecation заголовок в v1

В `science_graphrag/api/agent.py` в endpoint `post_agent_query` добавить Response:

```python
from fastapi import Response
# В сигнатуре:
async def post_agent_query(
    body: AgentQueryRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> AgentQueryResponse:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "2026-07-01"
    response.headers["Link"] = '</v2/agent/query>; rel="successor-version"'
    # ... остальное без изменений
```

### Шаг 5 — Тест `tests/test_api_agent_v2_smoke.py`

```python
"""Smoke tests for POST /v2/agent/query (Wave Y3)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from science_graphrag.agent.runtime import AgentRunOutput
from science_graphrag.agent.trace import ToolCallTrace


@pytest.fixture()
def fake_agent_output():
    return AgentRunOutput(
        answer="Test answer",
        citations=[{"work_id": "w1", "title": "Test Work"}],
        tool_trace=[
            ToolCallTrace(
                step=1,
                tool="entity_search",
                args_summary={"query": "test"},
                row_count=3,
                duration_ms=50,
                truncated=False,
                error=None,
            )
        ],
    )


@pytest.fixture()
def client(fake_agent_output):
    from science_graphrag.api.main import app
    from science_graphrag.api.deps import get_stores, StoreRegistry

    fake_stores = MagicMock(spec=StoreRegistry)

    def override_stores():
        return fake_stores

    app.dependency_overrides[get_stores] = override_stores

    with patch("science_graphrag.api.agent_v2.build_agent") as mock_build:
        mock_agent = MagicMock()
        mock_agent.run.return_value = fake_agent_output
        mock_build.return_value = mock_agent
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


def test_v2_sync_json(client):
    """Sync JSON path returns v2 response with phoenix_trace_id field."""
    resp = client.post(
        "/v2/agent/query",
        json={"question": "What is BERT?"},
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "answer" in data
    assert "phoenix_trace_id" in data
    assert "tool_trace" in data
    assert data["answer"] == "Test answer"


def test_v2_sse_stream(client):
    """SSE stream yields tool_call and final_answer events."""
    # For smoke: patch graph.astream with sync iterator
    with patch("science_graphrag.api.agent_v2.build_retrieval_graph") as mock_graph:
        fake_compiled = MagicMock()
        # astream returns empty iterator → final_answer with empty content
        async def fake_astream(state, config=None):
            # Yield nothing — final_answer emitted after loop
            return
            yield  # make it an async generator

        fake_compiled.astream = fake_astream
        mock_graph.return_value = fake_compiled

        with client.stream(
            "POST",
            "/v2/agent/query",
            json={"question": "What is BERT?"},
            headers={"Accept": "text/event-stream"},
        ) as resp:
            assert resp.status_code == 200
            lines = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    lines.append(json.loads(line[5:].strip()))
            types = [e["type"] for e in lines]
            assert "final_answer" in types


def test_v1_has_deprecation_header(client):
    """v1 endpoint returns Deprecation header."""
    resp = client.post("/v1/agent/query", json={"question": "test"})
    assert resp.status_code in (200, 503)  # 503 if agent_enabled=false in test env
    # If 200, check header:
    if resp.status_code == 200:
        assert resp.headers.get("Deprecation") == "true"
```

### Acceptance-критерии Agent 1

- [ ] `GET /v2/agent/query` → 404, `POST /v2/agent/query` с JSON `Accept` → 200 + `phoenix_trace_id` поле.
- [ ] `POST /v2/agent/query` с `Accept: text/event-stream` → `Content-Type: text/event-stream`, события `data:` парсируются как JSON.
- [ ] `POST /v1/agent/query` → header `Deprecation: true` присутствует.
- [ ] `docs/specs/agent-tools-v2.md` создан и описывает request/events/response/deprecation.
- [ ] `pytest tests/test_api_agent_v2_smoke.py` зелёный.
- [ ] `pylint science_graphrag/api/agent_v2.py --fail-under=7.0` зелёный.
- [ ] `isort` + `black` чисты на новых файлах.

### Качественные ворота

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/pytest tests/test_api_agent_v2_smoke.py tests/agent/ -q
.venv/bin/pylint science_graphrag/api/agent_v2.py science_graphrag/api/agent.py --fail-under=7.0
.venv/bin/isort --check science_graphrag/api/agent_v2.py science_graphrag/api/agent.py
.venv/bin/black --check science_graphrag/api/agent_v2.py science_graphrag/api/agent.py
```

---

## Agent 2 — Wave GR2: `node_kind` + semantic `display_type` + prioritized LIMIT

**Задача:** улучшить читаемость графа на уровне API-проекции:
1. Ввести `node_kind` как семантический подкласс (отличный от `type`).
2. Заменить технические имена рёбер (`HAS_AUTHORSHIP`, `OF_AUTHOR`) на читабельные `display_type`.
3. Добавить приоритетную обрезку соседей: `Method`/`Dataset`/`Work` выживают при LIMIT, `Institution`/`Venue`/`Authorship` идут последними.
4. Обновить `GraphTypeLegend.jsx` для отображения новых групп.
5. Обновить ADR 011 аддендумом.

### Контекст

Ты — агент Python/FastAPI + React. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предыстория:**
- G-WorkspaceGraphSplit ✅ DONE: `api/workspace_graph/` пакет (`cypher.py`, `projection.py`, `router.py`).
- G-WorksSplit ✅ DONE: `api/works/` пакет (`graph_neighborhood.py`, `detail.py`, `chunks.py`, `router.py`).
- `api/graph_display.py` — `compute_node_display()`, `edge_display_type()`, `resolve_node_kind()` — общие хелперы.
- `graphCanvasStyle.js` — уже знает `workspace_membership: internal/external`.

**Файлы, которые трогает этот агент:**
- `science_graphrag/api/works/graph_neighborhood.py` — `_append_neighbor_edge()`, приоритетный LIMIT.
- `science_graphrag/api/workspace_graph/projection.py` — workspace-граф проекция, `node_kind`.
- `science_graphrag/api/graph_display.py` — `edge_display_type()` таблица, `resolve_node_kind()`.
- `ui/src/components/graph/GraphTypeLegend.jsx` — обновить группировку на `node_kind`.
- `docs/adr/011-graph-live-ux-and-payload.md` — аддендум GR2.

**Не трогай:**
- `api/works/router.py`, `api/works/detail.py`, `api/works/chunks.py` — вне скоупа.
- `api/workspace_graph/router.py`, `api/workspace_graph/cypher.py` — вне скоупа.
- Схему Neo4j, `storage/neo4j/` — только API-проекция.

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
cat science_graphrag/api/graph_display.py
cat science_graphrag/api/works/graph_neighborhood.py
cat science_graphrag/api/workspace_graph/projection.py
# Проверить текущие display_type и node_kind:
grep -n "display_type\|node_kind\|edge_display_type\|resolve_node_kind" \
  science_graphrag/api/graph_display.py science_graphrag/api/works/graph_neighborhood.py | head -40
# Frontend:
cat ui/src/components/graph/GraphTypeLegend.jsx 2>/dev/null | head -60
```

### Шаг 1 — Расширить `api/graph_display.py`

**1a. Обновить `edge_display_type()` — добавить семантические метки:**

Текущий словарь (snake → space) недостаточен для UX. Новая таблица:

```python
_EDGE_DISPLAY_TYPE: dict[str, str] = {
    # Authorship cluster
    "HAS_AUTHORSHIP": "authored by",
    "OF_AUTHOR": "is author of",
    "AFFILIATED_WITH": "affiliated with",
    # Content relationships
    "CITES": "cites",
    "PUBLISHED_IN": "published in",
    # Semantic relationships
    "USES_METHOD": "uses method",
    "EVALUATED_ON": "evaluated on",
    "TRAINED_OR_TESTED_ON": "trained/tested on",
    # Claims
    "SUPPORTS": "supports",
    "CONTRADICTS": "contradicts",
    "MENTIONS": "mentions",
}

def edge_display_type(rel_type: str) -> str:
    """Return human-readable edge label for UI."""
    return _EDGE_DISPLAY_TYPE.get(rel_type, rel_type.replace("_", " ").lower())
```

**1b. Обновить `resolve_node_kind()` — ввести семантические подклассы:**

```python
def resolve_node_kind(
    ntype: str,
    *,
    workspace_membership: str | None = None,
) -> str:
    """
    Return UI-level node_kind (may differ from Neo4j label).

    node_kind values:
      Work, WorkInternal, WorkExternal  — зависит от workspace_membership
      AuthorshipReification             — `:Authorship` reified node (collapse hint)
      Author, Method, Dataset, Venue, Institution
      Aggregator                        — будущий Wave GR3
    """
    if ntype == "Authorship":
        return "AuthorshipReification"
    if ntype == "Work":
        if workspace_membership == "internal":
            return "WorkInternal"
        if workspace_membership == "external":
            return "WorkExternal"
        return "Work"
    # Остальные типы — 1:1 с Neo4j label
    return ntype
```

**1c. Приоритетный порядок для LIMIT-обрезки:**

```python
# Порядок: меньший индекс = выше приоритет (выживает при LIMIT)
_NODE_KIND_PRIORITY: dict[str, int] = {
    "Work": 0,
    "WorkInternal": 0,
    "WorkExternal": 0,
    "Method": 1,
    "Dataset": 2,
    "Author": 3,
    "AuthorshipReification": 4,
    "Venue": 5,
    "Institution": 5,
    "Aggregator": 6,
}

def node_kind_priority(node_kind: str) -> int:
    """Lower = higher priority when truncating neighbors."""
    return _NODE_KIND_PRIORITY.get(node_kind, 99)
```

### Шаг 2 — Обновить `api/works/graph_neighborhood.py`

**2a. В `_append_neighbor_edge()` — добавить `node_kind` к каждому узлу:**

После вызова `compute_node_display(...)` и получения `rendered` — добавить:

```python
workspace_membership = props.get("workspace_membership") or rec.get("n_workspace_membership")
node_kind = resolve_node_kind(ntype, workspace_membership=workspace_membership)

node_entry = {
    "id": nid,
    "type": ntype,
    "node_kind": node_kind,          # НОВОЕ
    "display_label": rendered.display_label,
    "subtitle": rendered.subtitle,
    # ... остальные поля
}
nodes.append(node_entry)
```

Для рёбер — заменить вызов `edge_display_type(rel_type)` — он уже должен быть, убедись что использует новую таблицу.

**2b. Приоритетная обрезка — добавить в функцию, которая строит список соседей:**

Найди место где `LIMIT` применяется или где список nodes/edges формируется. Добавить сортировку перед возвратом:

```python
# После построения всего списка nodes:
from science_graphrag.api.graph_display import node_kind_priority

center_id = str(work_id)
neighbor_nodes = [n for n in nodes if n["id"] != center_id]
neighbor_nodes.sort(key=lambda n: node_kind_priority(n.get("node_kind", "")))

# Применить LIMIT только к соседям, центральный узел — всегда
if len(neighbor_nodes) > MAX_WORK_GRAPH_NEIGHBORS:
    skipped = neighbor_nodes[MAX_WORK_GRAPH_NEIGHBORS:]
    neighbor_nodes = neighbor_nodes[:MAX_WORK_GRAPH_NEIGHBORS]
    # Собрать статистику skipped по типам:
    skipped_by_kind: dict[str, int] = {}
    for n in skipped:
        k = n.get("node_kind", "Unknown")
        skipped_by_kind[k] = skipped_by_kind.get(k, 0) + 1
else:
    skipped_by_kind = {}

nodes = [center_node] + neighbor_nodes  # где center_node — центральный узел

# В meta:
meta["skipped_by_kind"] = skipped_by_kind
meta["is_truncated"] = bool(skipped_by_kind)
```

### Шаг 3 — Обновить `api/workspace_graph/projection.py`

В функциях построения workspace-графа — для каждого узла добавить `node_kind`:

```python
node_kind = resolve_node_kind(
    ntype,
    workspace_membership=node.get("workspace_membership"),
)
node_payload["node_kind"] = node_kind
```

Если `edge_display_type()` ещё не применяется в projection — добавить для ребра:

```python
edge_payload["display_type"] = edge_display_type(rel_type)
```

### Шаг 4 — Обновить `GraphTypeLegend.jsx`

Найти файл: `ui/src/components/graph/GraphTypeLegend.jsx`.

Обновить группировку легенды для отображения групп `node_kind`:

```jsx
const NODE_KIND_GROUPS = [
  {
    group: "Works",
    kinds: ["Work", "WorkInternal", "WorkExternal"],
    description: "Research papers",
  },
  {
    group: "Semantic",
    kinds: ["Method", "Dataset"],
    description: "Methods & Datasets",
  },
  {
    group: "People",
    kinds: ["Author", "AuthorshipReification"],
    description: "Authors & Authorship",
  },
  {
    group: "Context",
    kinds: ["Venue", "Institution"],
    description: "Venues & Institutions",
  },
];
```

Если файл не существует или имеет другую структуру — адаптировать по смыслу. Не ломать существующие стили.

### Шаг 5 — Аддендум ADR 011

В конец `docs/adr/011-graph-live-ux-and-payload.md` добавить:

```markdown
## Addendum: Wave GR2 (2026-04-25)

- Added `node_kind` field to all nodes in graph payload. `node_kind` is the
  UI-level semantic subtype and may differ from `type` (Neo4j label).
  Values: `Work | WorkInternal | WorkExternal | AuthorshipReification |
  Author | Method | Dataset | Venue | Institution | Aggregator`.
- Expanded `display_type` for edges: now uses human-readable labels
  (`"cites"`, `"authored by"`, `"affiliated with"`, etc.) instead of
  `_`-separated Neo4j relation names.
- Added prioritized LIMIT: neighbors sorted by `node_kind_priority` before
  truncation. `meta.skipped_by_kind` reports dropped counts per kind.
```

### Шаг 6 — Тест `tests/storage/test_graph_display.py` (новый или расширение)

```python
"""Unit tests for graph_display projections (Wave GR2)."""

from science_graphrag.api.graph_display import (
    edge_display_type,
    node_kind_priority,
    resolve_node_kind,
)


def test_edge_display_type_semantic():
    assert edge_display_type("HAS_AUTHORSHIP") == "authored by"
    assert edge_display_type("OF_AUTHOR") == "is author of"
    assert edge_display_type("CITES") == "cites"
    assert edge_display_type("USES_METHOD") == "uses method"


def test_edge_display_type_unknown_fallback():
    assert edge_display_type("SOME_RELATION") == "some relation"


def test_resolve_node_kind_authorship():
    assert resolve_node_kind("Authorship") == "AuthorshipReification"


def test_resolve_node_kind_work_internal():
    assert resolve_node_kind("Work", workspace_membership="internal") == "WorkInternal"


def test_resolve_node_kind_work_external():
    assert resolve_node_kind("Work", workspace_membership="external") == "WorkExternal"


def test_resolve_node_kind_work_unknown():
    assert resolve_node_kind("Work") == "Work"


def test_node_kind_priority_order():
    """Method and Dataset survive truncation before Venue/Institution."""
    assert node_kind_priority("Method") < node_kind_priority("Institution")
    assert node_kind_priority("Dataset") < node_kind_priority("AuthorshipReification")
    assert node_kind_priority("Work") < node_kind_priority("Author")
```

### Acceptance-критерии Agent 2

- [ ] `GET /v1/works/{id}/graph-neighborhood` → ответ содержит `node_kind` для каждого узла.
- [ ] `node_kind` для `:Authorship` узлов = `"AuthorshipReification"`.
- [ ] Рёбро `HAS_AUTHORSHIP` → `display_type = "authored by"` в payload.
- [ ] `meta.skipped_by_kind` присутствует в ответе (пустой объект если нет обрезки).
- [ ] Workspace-граф (`/v1/workspaces/{id}/graph`) — узлы тоже имеют `node_kind`.
- [ ] `pytest tests/storage/test_graph_display.py -q` зелёный.
- [ ] `npm run lint` в `ui/` зелёный (ESLint).
- [ ] `pylint science_graphrag/api/graph_display.py science_graphrag/api/works/graph_neighborhood.py --fail-under=7.0`.

### Качественные ворота

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/pytest tests/storage/test_graph_display.py tests/test_api_smoke.py -q
.venv/bin/pylint science_graphrag/api/graph_display.py science_graphrag/api/works/graph_neighborhood.py science_graphrag/api/workspace_graph/projection.py --fail-under=7.0
.venv/bin/isort --check science_graphrag/api/graph_display.py
.venv/bin/black --check science_graphrag/api/graph_display.py
cd ui && npm run lint -- --max-warnings=0
```

---

## Agent 3 — G-RetrievalCore: split `api/retrieval.py` + cleanup `main.py` shim

**Задача:** выделить `science_graphrag/retrieval/` пакет из `api/retrieval.py` (714 строк).
Параллельно закрыть долг из бэклога: убрать `sys.modules` shim в `main.py` и исправить naming
conflict в `api/works/__init__.py`.

### Контекст

Ты — агент Python-рефакторинга. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предыстория:**
- G-WorksSplit ✅ DONE: `api/works/` создан. При split появился shim `works_api = sys.modules["science_graphrag.api.works.router"]` в `main.py` из-за naming conflict между `__init__.py` re-export и подмодулем.
- `api/retrieval.py` — 714 строк: query embedding, Qdrant search, Neo4j контекст, hybrid RRF, second-stage LLM answer. Тестировать в изоляции невозможно.

**Цели:**

1. **G-RetrievalCore:** `api/retrieval.py` → `science_graphrag/retrieval/` пакет; `api/retrieval.py` остаётся как тонкий router.
2. **Cleanup shim:** удалить `sys.modules` hack из `main.py`, исправить `works/__init__.py`.

**Файлы, которые трогает этот агент:**
- `science_graphrag/api/retrieval.py` → переписывается в тонкий router.
- `science_graphrag/retrieval/` — создать новый пакет.
- `science_graphrag/api/main.py` — удалить shim (≤3 строки).
- `science_graphrag/api/works/__init__.py` — исправить naming conflict.
- `tests/` — unit-тесты для retrieval core.

**Не трогай:**
- `api/works/router.py` — только `__init__.py`.
- `api/agent.py`, `api/agent_v2.py` — вне скоупа.
- `api/workspace_graph/` — вне скоупа.

### Шаг 0 — Прочитать текущий код полностью

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
cat science_graphrag/api/retrieval.py
cat science_graphrag/api/main.py
cat science_graphrag/api/works/__init__.py
# Найти все импорты из api/retrieval.py:
rg "from science_graphrag.api.retrieval import\|from science_graphrag.api import retrieval\|api\.retrieval\." science_graphrag/ tests/ --include="*.py" -n
# Найти shim:
grep -n "sys.modules\|works_api" science_graphrag/api/main.py
```

### Шаг 1 — Исправить `works/__init__.py` naming conflict

**Проблема:** `api/works/__init__.py` re-экспортирует `router` (APIRouter instance) под именем `router`,
что затеняет submodule `works/router.py`. В `main.py` добавлен костыльный `sys.modules` shim.

**Решение:**

В `science_graphrag/api/works/__init__.py` найти строку вида:
```python
from science_graphrag.api.works.router import router
```
или `router = ...` — и переименовать re-export:

```python
# Вместо: from .router import router
from .router import router as works_router  # используется в main.py напрямую

__all__ = ["works_router"]
```

В `science_graphrag/api/main.py`:
1. Найти shim: `works_api = sys.modules["science_graphrag.api.works.router"]`.
2. Заменить на прямой импорт:
   ```python
   from science_graphrag.api.works import router as works_router
   # или:
   import science_graphrag.api.works.router as works_api_module
   ```
3. Везде, где используется `works_api.list_works` или аналог — заменить на прямое имя модуля.
4. `include_router` для works — убедиться, что роутер передаётся корректно.

После правки:
```bash
.venv/bin/python -c "import science_graphrag.api.works.router as m; print(type(m))"
# должно вернуть <class 'module'>
```

### Шаг 2 — Создать `science_graphrag/retrieval/` пакет

Структура нового пакета:

```
science_graphrag/retrieval/
    __init__.py          # re-export публичного API: answer_query, GroundedAnswer
    query_embedder.py    # _embed_query → embed_query()
    qdrant_search.py     # _qdrant_hits_for_answer, _hybrid_hits_for_answer, _workspace_scope_work_ids
    neo4j_context.py     # _neo4j_graph_context_for_work, _graph_context_for_hits
    ranking.py           # _rank_hits_for_answer, _citations_and_snippets_from_hits,
                         # _reciprocal_rank_fusion, _hit_fingerprint_key,
                         # _is_likely_back_matter_section, _body_section_bonus,
                         # _effective_work_id
    answer.py            # _try_query_answer_llm, GroundedAnswer, answer_query (оркестратор)
```

**Правило разнесения:**

- Из `retrieval.py` извлечь все функции по категориям выше.
- Подмодули импортируют друг друга явно (нет циклов):
  - `answer.py` импортирует из `query_embedder`, `qdrant_search`, `neo4j_context`, `ranking`.
  - `qdrant_search.py` — только `QdrantChunkStore`, `Settings`, `StoreRegistry`.
  - `neo4j_context.py` — только `Neo4jGraphStore`.
  - `ranking.py` — pure Python (нет store-зависимостей).

**`__init__.py`:**
```python
"""Retrieval core — public API."""

from .answer import GroundedAnswer, answer_query

__all__ = ["GroundedAnswer", "answer_query"]
```

**Каждый файл не должен превышать ~300 строк.**

### Шаг 3 — Сделать тонкий `api/retrieval.py` router

После переноса логики `api/retrieval.py` оставить только FastAPI endpoint:

```python
"""Thin retrieval router — delegates to science_graphrag/retrieval/."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from science_graphrag.api.deps import StoreRegistry, get_stores
from science_graphrag.config import Settings, get_settings
from science_graphrag.retrieval import GroundedAnswer, answer_query

router = APIRouter()


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)
    work_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=50)
    workspace_id: str | None = None
    retrieval_mode: str = Field(default="vector")


class QueryResponse(BaseModel):
    answer: str
    citations: list[dict[str, Any]]
    graph_context: dict[str, Any]
    retrieval_trace: dict[str, Any]


@router.post("/query", response_model=QueryResponse)
def post_query(
    body: QueryRequest,
    settings: Settings = Depends(get_settings),
    stores: StoreRegistry = Depends(get_stores),
) -> QueryResponse:
    result: GroundedAnswer = answer_query(
        query=body.query,
        work_id=body.work_id,
        top_k=body.top_k,
        workspace_id=body.workspace_id,
        retrieval_mode=body.retrieval_mode,
        settings=settings,
        stores=stores,
    )
    return QueryResponse(
        answer=result.answer,
        citations=result.citations,
        graph_context=result.graph_context,
        retrieval_trace=result.retrieval_trace,
    )
```

Если в `main.py` есть `@app.post("/v1/query", ...)` дублирующий endpoint — перенести его сюда или удалить дубль. Проверить:
```bash
grep -n "v1/query\|answer_query" science_graphrag/api/main.py
```

### Шаг 4 — Юнит-тесты `tests/retrieval/`

Создать `tests/retrieval/__init__.py` (пустой) и:

**`tests/retrieval/test_ranking.py`:**
```python
"""Unit tests for retrieval/ranking.py — pure Python, no stores needed."""

from science_graphrag.retrieval.ranking import (
    _body_section_bonus,
    _hit_fingerprint_key,
    _is_likely_back_matter_section,
    _rank_hits_for_answer,
    _reciprocal_rank_fusion,
)


def _make_hit(score: float, work_id: str = "w1", chunk_id: str = "c1",
              section: str | None = None) -> dict:
    return {
        "score": score,
        "work_id": work_id,
        "chunk_id": chunk_id,
        "section_path": section,
        "text": "test chunk",
        "title": "Test Work",
    }


def test_back_matter_section():
    assert _is_likely_back_matter_section("references") is True
    assert _is_likely_back_matter_section("introduction") is False
    assert _is_likely_back_matter_section(None) is False


def test_body_section_bonus():
    assert _body_section_bonus("abstract") > 0
    assert _body_section_bonus("references") <= 0


def test_rank_hits_returns_top_k():
    hits = [_make_hit(0.9 - i * 0.1, chunk_id=f"c{i}") for i in range(10)]
    ranked = _rank_hits_for_answer(hits, top_k=3)
    assert len(ranked) == 3


def test_reciprocal_rank_fusion_deduplicates():
    hits_a = [_make_hit(0.9, work_id="w1", chunk_id="c1")]
    hits_b = [_make_hit(0.8, work_id="w1", chunk_id="c1")]
    merged = _reciprocal_rank_fusion([hits_a, hits_b])
    keys = [_hit_fingerprint_key(h) for h in merged]
    assert len(keys) == len(set(keys)), "duplicates present after RRF"
```

**`tests/retrieval/test_query_embedder.py`:**
```python
"""Unit tests for retrieval/query_embedder.py."""

from unittest.mock import MagicMock, patch

from science_graphrag.retrieval.query_embedder import embed_query


def test_embed_query_hash_fallback():
    """Without embedding model — uses hash embedder."""
    settings = MagicMock()
    settings.embedding_model = None
    vec, trace = embed_query("test query", settings)
    assert isinstance(vec, list)
    assert len(vec) > 0
    assert trace["embedding_model"] == "hash-deterministic"


def test_embed_query_returns_float_list():
    settings = MagicMock()
    settings.embedding_model = ""
    vec, trace = embed_query("hello world", settings)
    assert all(isinstance(v, float) for v in vec)
```

### Шаг 5 — Обновить бэклог

В `docs/backlog/refactor-backend.md` найти:

```
### [OPEN] Core/router split for `api/retrieval.py` (682)
```

Заменить `[OPEN]` на `[DONE]` и добавить note:

```markdown
- **Note (done):** 2026-04-25 (Round 4) — выделен пакет `science_graphrag/retrieval/`
  с модулями `query_embedder.py`, `qdrant_search.py`, `neo4j_context.py`,
  `ranking.py`, `answer.py`; `api/retrieval.py` — тонкий router ≤80 строк;
  unit-тесты в `tests/retrieval/`; ни один файл не превышает 300 строк.
```

В `docs/backlog/refactor-backend.md` найти:

```
### [OPEN] Cleanup `api/main.py` works_api shim + works package __init__ naming conflict
```

Заменить `[OPEN]` на `[DONE]` и добавить note:

```markdown
- **Note (done):** 2026-04-25 (Round 4) — shim удалён из `main.py`;
  `works/__init__.py` переименовал re-export; patching в тестах через прямой импорт модуля.
```

### Acceptance-критерии Agent 3

- [ ] `science_graphrag/retrieval/` пакет создан, ни один файл не превышает 300 строк.
- [ ] `api/retrieval.py` (router) ≤ 80 строк.
- [ ] `main.py` не содержит `sys.modules` hack.
- [ ] `python -c "import science_graphrag.api.works.router as m; print(type(m))"` → `<class 'module'>`.
- [ ] `pytest tests/retrieval/ -q` зелёный (новые unit-тесты без store).
- [ ] `pytest tests/test_api_smoke.py -q` зелёный (регрессия не сломана).
- [ ] `pylint science_graphrag/retrieval/ --fail-under=7.0`.
- [ ] `isort` + `black` чисты.
- [ ] Бэклог обновлён (`[DONE]`).

### Качественные ворота

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/python -c "from science_graphrag.retrieval import answer_query, GroundedAnswer; print('import ok')"
.venv/bin/python -c "import science_graphrag.api.works.router as m; assert hasattr(m, '__file__'); print('works module ok')"
.venv/bin/pytest tests/retrieval/ tests/test_api_smoke.py -q
.venv/bin/pylint science_graphrag/retrieval/ science_graphrag/api/retrieval.py --fail-under=7.0
.venv/bin/isort --check science_graphrag/retrieval/ science_graphrag/api/retrieval.py
.venv/bin/black --check science_graphrag/retrieval/ science_graphrag/api/retrieval.py
```

---

## Agent 4 — H-AskV2SSE: frontend wiring для `/v2/agent/query` SSE

**Задача:** добавить поддержку SSE-стриминга ответов агента в UI. При `retrievalMode === "agent"` в
лаб-режиме — переключить на `/v2/agent/query` c `Accept: text/event-stream`. Показывать tool-события
в реальном времени. Ответ на backend Agent 1 (Wave Y3) — разрабатывать параллельно с мокированием.

### Контекст

Ты — агент React/JavaScript. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/` (для Python), Node: `ui/` директория.

**Предыстория:**
- H-AskPanelSplit ✅ DONE: `AskPanel.jsx` (215 строк), `AskAnswerPanel.jsx` (75 строк),
  `AskSessionControls.jsx` (109 строк), `useAskSubmit.js` (88 строк).
- `useAskSubmit.js` — orchestrates submit: при `retrievalMode === "agent"` вызывает `postAgentQuery()`,
  который делает `POST /v1/agent/query` (sync JSON).
- `researchApi.js` — `postAgentQuery(body, config)` на `/v1/agent/query`.
- Backend Agent 1 (Wave Y3) создаст `POST /v2/agent/query` с SSE. До его завершения — работай с мок-сервером.

**Файлы, которые трогает этот агент:**
- `ui/src/hooks/useAgentStream.js` — новый SSE hook (создать).
- `ui/src/services/researchApi.js` — добавить `streamAgentQuery()`.
- `ui/src/components/work/useAskSubmit.js` — переключить agent path на SSE.
- `ui/src/components/work/AskAnswerPanel.jsx` — добавить стриминговый индикатор tool событий.

**Не трогай:**
- `AskPanel.jsx` — вне скоупа (логика submit уже в `useAskSubmit`).
- `AskSessionControls.jsx` — вне скоупа.
- Backend файлы — вне скоупа.

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
cat ui/src/components/work/useAskSubmit.js
cat ui/src/components/work/AskAnswerPanel.jsx
cat ui/src/services/researchApi.js | grep -A 10 "postAgentQuery"
ls ui/src/hooks/
```

### Шаг 1 — Создать `ui/src/hooks/useAgentStream.js`

```javascript
/**
 * useAgentStream — SSE hook for /v2/agent/query streaming.
 *
 * Emits events: tool_call, tool_result, final_answer, error.
 * Falls back to sync JSON if SSE is unavailable or rejected by server.
 *
 * @param {object} params
 * @param {string|null} params.workspaceId
 * @param {(event: AgentStreamEvent) => void} params.onEvent
 * @param {(answer: object) => void} params.onFinalAnswer
 * @param {(error: string) => void} params.onError
 * @param {() => void} params.onStart
 * @param {() => void} params.onFinish
 */
import { useCallback, useRef, useState } from "react";
import { buildApiUrl } from "../services/researchApi.js";

/**
 * @typedef {Object} AgentStreamEvent
 * @property {'tool_call'|'tool_result'|'final_answer'|'error'} type
 * @property {number} [step]
 * @property {string} [tool]
 * @property {object} [args_summary]
 * @property {number|null} [row_count]
 * @property {string|null} [error]
 * @property {string} [answer]
 * @property {Array} [citations]
 * @property {Array} [tool_trace]
 * @property {number} [duration_ms]
 * @property {string|null} [phoenix_trace_id]
 */

export function useAgentStream({ workspaceId = "", onEvent, onFinalAnswer, onError, onStart, onFinish }) {
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(null);

  const stream = useCallback(
    async ({ question, maxToolCalls = 8 }) => {
      if (!String(question || "").trim()) return;

      abortRef.current?.abort?.();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsStreaming(true);
      onStart?.();

      try {
        const url = buildApiUrl("/v2/agent/query");
        const response = await fetch(url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            question,
            workspace_id: workspaceId || null,
            max_tool_calls: maxToolCalls,
          }),
          signal: controller.signal,
        });

        if (!response.ok) {
          const errText = await response.text().catch(() => "Unknown error");
          onError?.(`Agent error ${response.status}: ${errText}`);
          return;
        }

        const contentType = response.headers.get("content-type") || "";
        if (!contentType.includes("text/event-stream")) {
          // Fallback: sync JSON response from /v2/agent/query
          const data = await response.json();
          onFinalAnswer?.(data);
          return;
        }

        // SSE parsing
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data:")) continue;
            const raw = line.slice(5).trim();
            if (!raw) continue;
            try {
              const event = JSON.parse(raw);
              onEvent?.(event);
              if (event.type === "final_answer") {
                onFinalAnswer?.(event);
              } else if (event.type === "error") {
                onError?.(event.detail || "Stream error");
              }
            } catch {
              // Ignore malformed SSE lines
            }
          }
        }
      } catch (err) {
        if (err?.name === "AbortError") return;
        onError?.(String(err?.message || err));
      } finally {
        if (abortRef.current === controller) {
          abortRef.current = null;
        }
        setIsStreaming(false);
        onFinish?.();
      }
    },
    [workspaceId, onEvent, onFinalAnswer, onError, onStart, onFinish],
  );

  const abort = useCallback(() => {
    abortRef.current?.abort?.();
  }, []);

  return { stream, isStreaming, abort };
}
```

### Шаг 2 — Добавить `buildApiUrl` экспорт (если нет) и `streamAgentQuery` в `researchApi.js`

Проверить: `buildApiUrl` уже экспортируется из `researchApi.js`? Если нет — добавить:

```javascript
// В researchApi.js — добавить (если нет):
export function buildApiUrl(path) {
  const base = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");
  return `${base}${path}`;
}
```

Также добавить **sync fallback** для тестов (без SSE):

```javascript
/**
 * Post to /v2/agent/query and get sync JSON response.
 * Used as fallback when SSE is unavailable.
 */
export async function postAgentQueryV2(body, config) {
  return apiClient.post(buildApiUrl("/v2/agent/query"), body, {
    ...config,
    headers: {
      ...config?.headers,
      Accept: "application/json",
    },
  });
}
```

### Шаг 3 — Обновить `useAskSubmit.js`

Добавить SSE path через `useAgentStream`. Сохранить совместимость с legacy `postAgentQuery`:

```javascript
import { useCallback, useRef, useState } from "react";
import {
  formatResearchApiError,
  normalizeQueryResponse,
  postAgentQuery,
  postQuery,
} from "../../services/researchApi.js";
import { useAgentStream } from "../../hooks/useAgentStream.js";

export function useAskSubmit({
  workspaceId = "",
  onResult,
  onError,
  onToolTrace,
  onStart,
  onFinish,
  onStreamEvent,       // НОВОЕ: callback для промежуточных SSE событий
  useStreamingAgent = true,  // НОВОЕ: переключатель SSE vs legacy sync
}) {
  const [isLoading, setIsLoading] = useState(false);
  const abortRef = useRef(null);

  const { stream: streamAgent, isStreaming, abort: abortStream } = useAgentStream({
    workspaceId,
    onEvent: (event) => {
      onStreamEvent?.(event);
      // Накапливать tool_trace из stream:
      if (event.type === "tool_call" || event.type === "tool_result") {
        // будет собрано в final_answer
      }
    },
    onFinalAnswer: (event) => {
      const trace = Array.isArray(event.tool_trace) ? event.tool_trace : [];
      onToolTrace?.(trace);
      const normalized = normalizeQueryResponse({
        answer: String(event.answer || ""),
        citations: Array.isArray(event.citations) ? event.citations : [],
        graph_context: {},
        retrieval_trace: {
          retrieval_mode: "agent_v2_stream",
          hit_count: Array.isArray(event.citations) ? event.citations.length : 0,
          citations_returned: Array.isArray(event.citations) ? event.citations.length : 0,
          retrieval_policy: "agent_tools_v2",
        },
      });
      onResult?.(normalized);
    },
    onError: (msg) => onError?.(msg),
    onStart: () => {
      setIsLoading(true);
      onStart?.();
    },
    onFinish: () => {
      setIsLoading(false);
      onFinish?.();
    },
  });

  const submit = useCallback(
    async ({ query, topK, retrievalMode, retrievalLabVisible, bodyPreview }) => {
      if (!String(query || "").trim()) return null;

      const isAgentMode = retrievalLabVisible && retrievalMode === "agent";

      if (isAgentMode && useStreamingAgent) {
        // SSE path через /v2/agent/query
        await streamAgent({ question: query, maxToolCalls: 8 });
        return null; // результат приходит через onResult callback
      }

      // Legacy path (vector retrieval или агент без SSE)
      abortRef.current?.abort?.();
      const controller = new AbortController();
      abortRef.current = controller;

      setIsLoading(true);
      onStart?.();
      try {
        let normalized;
        let trace = [];

        if (isAgentMode) {
          // Legacy sync JSON path через /v1/agent/query
          const res = await postAgentQuery(
            {
              question: query,
              workspace_id: workspaceId || null,
              max_tool_calls: 8,
            },
            { signal: controller.signal },
          );
          const raw = res.data || {};
          trace = Array.isArray(raw.tool_trace) ? raw.tool_trace : [];
          normalized = normalizeQueryResponse({
            answer: String(raw.answer || ""),
            citations: Array.isArray(raw.citations) ? raw.citations : [],
            graph_context: {},
            retrieval_trace: {
              retrieval_mode: "agent",
              hit_count: Array.isArray(raw.citations) ? raw.citations.length : 0,
              top_k_requested: topK,
              citations_returned: Array.isArray(raw.citations) ? raw.citations.length : 0,
              retrieval_policy: "agent_tools_v1",
            },
          });
        } else {
          const res = await postQuery(bodyPreview, { signal: controller.signal });
          normalized = normalizeQueryResponse(res.data);
        }

        onToolTrace?.(trace);
        onResult?.(normalized);
        return normalized;
      } catch (err) {
        if (err?.name === "CanceledError" || err?.name === "AbortError") return null;
        onError?.(formatResearchApiError(err));
        return null;
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setIsLoading(false);
        onFinish?.();
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [onError, onFinish, onResult, onStart, onToolTrace, workspaceId, useStreamingAgent, streamAgent],
  );

  const isActive = isLoading || isStreaming;

  return { submit, isLoading: isActive, abortRef };
}
```

### Шаг 4 — Обновить `AskAnswerPanel.jsx` — добавить streaming indicator

В `AskAnswerPanel.jsx` добавить отображение промежуточных tool-событий при стриминге:

**Новые пропсы для `AskAnswerPanel`:**
- `streamEvents?: AgentStreamEvent[]` — массив накопленных промежуточных событий.
- `isStreaming?: boolean` — показывает индикатор в реальном времени.

**В компоненте добавить блок (после/до ответа):**

```jsx
{isStreaming && (
  <Box sx={{ mb: 1 }}>
    <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.4)", fontSize: "0.7rem" }}>
      Agent thinking…
    </Typography>
    {(streamEvents || [])
      .filter((e) => e.type === "tool_call")
      .map((e, i) => (
        <Box
          key={i}
          sx={{
            display: "flex",
            alignItems: "center",
            gap: 0.5,
            py: 0.25,
            opacity: 0.7,
          }}
        >
          <Typography
            component="span"
            sx={{
              fontSize: "0.7rem",
              fontFamily: "monospace",
              color: "rgba(129,140,248,0.9)",
            }}
          >
            {e.tool}
          </Typography>
          {e.args_summary?.query && (
            <Typography
              component="span"
              sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)" }}
            >
              "{String(e.args_summary.query).slice(0, 40)}"
            </Typography>
          )}
        </Box>
      ))}
  </Box>
)}
```

**Важно:** соблюдать color palette из `.cursorrules` (цвета через rgba, без ярких акцентов кроме indigo `rgba(129,140,248,...)` для tool name).

### Шаг 5 — Прокинуть streamEvents в `AskPanel.jsx`

В `AskPanel.jsx` добавить state для `streamEvents` и передавать в `useAskSubmit` + `AskAnswerPanel`:

```jsx
const [streamEvents, setStreamEvents] = useState([]);

// В useAskSubmit:
const { submit, isLoading } = useAskSubmit({
  workspaceId,
  onStart: () => {
    setStreamEvents([]);  // сбросить предыдущие события
    // ... остальное
  },
  onStreamEvent: (event) => {
    if (event.type === "tool_call" || event.type === "tool_result") {
      setStreamEvents((prev) => [...prev, event]);
    }
  },
  // ... остальные callbacks
});

// В JSX:
<AskAnswerPanel
  // ... существующие пропсы
  streamEvents={streamEvents}
  isStreaming={isLoading && streamEvents.length > 0}
/>
```

### Шаг 6 — Тест `ui/src/hooks/useAgentStream.test.js`

```javascript
/**
 * @jest-environment jsdom
 */
import { renderHook, act } from "@testing-library/react";
import { useAgentStream } from "./useAgentStream.js";

// Mock fetch
global.fetch = jest.fn();

describe("useAgentStream", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("calls onError if fetch fails", async () => {
    global.fetch.mockRejectedValueOnce(new Error("Network error"));
    const onError = jest.fn();
    const { result } = renderHook(() =>
      useAgentStream({ onError, onFinalAnswer: jest.fn(), onEvent: jest.fn() })
    );
    await act(async () => {
      await result.current.stream({ question: "test" });
    });
    expect(onError).toHaveBeenCalledWith(expect.stringContaining("Network error"));
  });

  it("calls onError on non-ok response", async () => {
    global.fetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      text: async () => "agent_disabled",
      headers: { get: () => "application/json" },
    });
    const onError = jest.fn();
    const { result } = renderHook(() =>
      useAgentStream({ onError, onFinalAnswer: jest.fn(), onEvent: jest.fn() })
    );
    await act(async () => {
      await result.current.stream({ question: "test" });
    });
    expect(onError).toHaveBeenCalled();
  });
});
```

### Acceptance-критерии Agent 4

- [ ] `ui/src/hooks/useAgentStream.js` создан.
- [ ] При `retrievalMode === "agent"` в лаб-режиме `useAskSubmit` вызывает SSE-поток.
- [ ] `AskAnswerPanel` показывает `tool_call` события во время стриминга.
- [ ] Fallback: если `/v2/agent/query` недоступен (500/404) — graceful `onError`.
- [ ] `useAskSubmit` остаётся обратно совместимым: вектор-режим работает без изменений.
- [ ] `npm run lint` в `ui/` зелёный.
- [ ] `npm test` (если настроен) — тесты `useAgentStream.test.js` зелёные.
- [ ] `AskPanel.jsx` ≤ 230 строк (не раздулся от новых пропсов).

### Качественные ворота

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui
npm run lint -- --max-warnings=0
# Если jest настроен:
npx jest src/hooks/useAgentStream.test.js --passWithNoTests
# Размер файлов:
wc -l src/components/work/AskPanel.jsx src/components/work/AskAnswerPanel.jsx \
   src/components/work/useAskSubmit.js src/hooks/useAgentStream.js
```

---

## Review Agent — финальная проверка Раунда 4

**Задача:** Проверить, что все 4 агента выполнили свои задачи корректно, без регрессий и
структурного долга. Запустить все тестовые ворота. Зафиксировать результат в мастер-плане.

### Контекст

Ты — агент code review и quality assurance. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

Раунд 4 включает:
- **Agent 1 (Y3):** `api/agent_v2.py` + `docs/specs/agent-tools-v2.md` + deprecation header v1.
- **Agent 2 (GR2):** `api/graph_display.py` + `api/works/graph_neighborhood.py` + `api/workspace_graph/projection.py` — `node_kind`, semantic `display_type`, prioritized LIMIT.
- **Agent 3 (RetrievalCore):** `science_graphrag/retrieval/` пакет + тонкий `api/retrieval.py` + cleanup `main.py` shim + `works/__init__` fix.
- **Agent 4 (AskV2SSE):** `ui/src/hooks/useAgentStream.js` + обновлённый `useAskSubmit.js` + `AskAnswerPanel.jsx` + `researchApi.js`.

### Шаг 1 — Проверка структуры файлов

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Agent 1: Wave Y3
echo "=== Agent 1 checks ==="
test -f science_graphrag/api/agent_v2.py && echo "✓ agent_v2.py exists" || echo "✗ MISSING agent_v2.py"
test -f docs/specs/agent-tools-v2.md && echo "✓ agent-tools-v2.md exists" || echo "✗ MISSING spec"
grep -q "agent_v2_router\|agent_v2" science_graphrag/api/main.py && echo "✓ v2 router registered" || echo "✗ v2 router NOT in main.py"
grep -q "Deprecation" science_graphrag/api/agent.py && echo "✓ v1 has Deprecation header" || echo "✗ NO Deprecation in v1"
grep -q "/v2" docs/specs/agent-tools-v2.md && echo "✓ spec mentions /v2 endpoint" || echo "✗ spec incomplete"

# Agent 2: Wave GR2
echo "=== Agent 2 checks ==="
grep -q "node_kind" science_graphrag/api/graph_display.py && echo "✓ node_kind in graph_display.py" || echo "✗ node_kind missing"
grep -q "AuthorshipReification" science_graphrag/api/graph_display.py && echo "✓ AuthorshipReification in graph_display" || echo "✗ MISSING"
grep -q "authored by\|is author of" science_graphrag/api/graph_display.py && echo "✓ semantic display_type present" || echo "✗ MISSING semantic display_type"
grep -q "node_kind_priority\|skipped_by_kind" science_graphrag/api/works/graph_neighborhood.py && echo "✓ prioritized LIMIT in graph_neighborhood" || echo "✗ MISSING priority"
grep -q "node_kind" science_graphrag/api/workspace_graph/projection.py && echo "✓ node_kind in workspace projection" || echo "✗ MISSING"
grep -q "GR2\|Wave GR2" docs/adr/011-graph-live-ux-and-payload.md && echo "✓ ADR 011 updated" || echo "✗ ADR 011 NOT updated"

# Agent 3: G-RetrievalCore
echo "=== Agent 3 checks ==="
test -d science_graphrag/retrieval/ && echo "✓ retrieval/ package exists" || echo "✗ MISSING retrieval/ package"
for f in query_embedder qdrant_search neo4j_context ranking answer; do
  test -f "science_graphrag/retrieval/${f}.py" && echo "✓ ${f}.py" || echo "✗ MISSING ${f}.py"
done
wc -l science_graphrag/api/retrieval.py | awk '{if ($1 <= 100) print "✓ api/retrieval.py slim ("$1" lines)"; else print "✗ api/retrieval.py TOO FAT ("$1" lines, should be ≤100)"}'
grep -q "sys.modules" science_graphrag/api/main.py && echo "✗ sys.modules shim STILL present in main.py" || echo "✓ shim removed from main.py"
.venv/bin/python -c "import science_graphrag.api.works.router as m; assert hasattr(m, '__file__'); print('✓ works.router is module, not APIRouter')" 2>/dev/null || echo "✗ works.router naming conflict still present"
grep -q "\[DONE\].*RetrievalCore\|DONE.*Core/router" docs/backlog/refactor-backend.md && echo "✓ RetrievalCore marked DONE in backlog" || echo "✗ backlog NOT updated"

# Agent 4: H-AskV2SSE
echo "=== Agent 4 checks ==="
test -f ui/src/hooks/useAgentStream.js && echo "✓ useAgentStream.js exists" || echo "✗ MISSING useAgentStream.js"
grep -q "useAgentStream\|streamAgent" ui/src/components/work/useAskSubmit.js && echo "✓ useAskSubmit uses streaming" || echo "✗ streaming NOT integrated"
grep -q "streamEvents\|isStreaming\|tool_call" ui/src/components/work/AskAnswerPanel.jsx && echo "✓ AskAnswerPanel shows stream events" || echo "✗ NO stream display in AskAnswerPanel"
grep -q "v2/agent/query\|/v2/agent" ui/src/hooks/useAgentStream.js && echo "✓ hook calls /v2 endpoint" || echo "✗ hook doesn't call /v2"
grep -q "buildApiUrl\|streamAgentQuery\|postAgentQueryV2" ui/src/services/researchApi.js && echo "✓ researchApi has v2 or SSE helper" || echo "✗ researchApi not updated"
```

### Шаг 2 — Тесты Python

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

echo "=== Python tests ==="
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -20

# Целевые наборы:
.venv/bin/pytest tests/test_api_agent_v2_smoke.py -v 2>&1 | tail -20
.venv/bin/pytest tests/retrieval/ -v 2>&1 | tail -20
.venv/bin/pytest tests/storage/test_graph_display.py -v 2>&1 | tail -20
.venv/bin/pytest tests/test_api_smoke.py -v 2>&1 | tail -20
.venv/bin/pytest tests/agent/ -v 2>&1 | tail -20
```

Ожидаемый результат: **все тесты зелёные, 0 errors**. Допустимо: skipped тесты, помеченные `pytest.mark.skip` с явным reason.

### Шаг 3 — Линтеры Python

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

echo "=== pylint ==="
.venv/bin/pylint \
  science_graphrag/api/agent_v2.py \
  science_graphrag/api/agent.py \
  science_graphrag/api/graph_display.py \
  science_graphrag/api/works/graph_neighborhood.py \
  science_graphrag/api/workspace_graph/projection.py \
  science_graphrag/retrieval/ \
  science_graphrag/api/retrieval.py \
  --fail-under=7.0 2>&1 | tail -10

echo "=== isort ==="
.venv/bin/isort --check \
  science_graphrag/api/agent_v2.py \
  science_graphrag/api/graph_display.py \
  science_graphrag/retrieval/ \
  science_graphrag/api/retrieval.py

echo "=== black ==="
.venv/bin/black --check \
  science_graphrag/api/agent_v2.py \
  science_graphrag/api/graph_display.py \
  science_graphrag/retrieval/ \
  science_graphrag/api/retrieval.py
```

### Шаг 4 — Frontend lint

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui
npm run lint -- --max-warnings=0 2>&1 | tail -20
```

### Шаг 5 — Размерный аудит (file size check)

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

echo "=== File size audit ==="
# Python — лимит 300 строк на файл в пакете
for f in science_graphrag/retrieval/*.py science_graphrag/api/agent_v2.py \
          science_graphrag/api/graph_display.py science_graphrag/api/retrieval.py \
          science_graphrag/api/works/graph_neighborhood.py \
          science_graphrag/api/workspace_graph/projection.py; do
  lines=$(wc -l < "$f" 2>/dev/null || echo 0)
  if [ "$lines" -gt 300 ]; then
    echo "✗ TOO LONG: $f ($lines lines, limit 300)"
  else
    echo "✓ $f ($lines lines)"
  fi
done

# Frontend — лимит ~250 строк для хуков, ~400 для компонентов
for f in ui/src/hooks/useAgentStream.js \
          ui/src/components/work/useAskSubmit.js \
          ui/src/components/work/AskAnswerPanel.jsx \
          ui/src/components/work/AskPanel.jsx; do
  lines=$(wc -l < "$f" 2>/dev/null || echo 0)
  echo "  $f: $lines lines"
done
```

### Шаг 6 — Контрактные smoke-проверки API

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Проверить что v2 endpoint зарегистрирован в app
.venv/bin/python -c "
from science_graphrag.api.main import app
routes = [r.path for r in app.routes]
assert any('/v2/agent/query' in r for r in routes), f'v2 route missing! routes={routes}'
assert any('/v1/agent/query' in r for r in routes), 'v1 route missing!'
print('✓ both v1 and v2 routes registered')
print('Routes:', [r for r in routes if 'agent' in r])
"

# Проверить импорты retrieval package
.venv/bin/python -c "
from science_graphrag.retrieval import answer_query, GroundedAnswer
print('✓ retrieval package imports ok')
from science_graphrag.retrieval.ranking import _rank_hits_for_answer
print('✓ retrieval.ranking imports ok')
from science_graphrag.retrieval.query_embedder import embed_query
print('✓ retrieval.query_embedder imports ok')
"

# Проверить graph_display новые функции
.venv/bin/python -c "
from science_graphrag.api.graph_display import (
    edge_display_type, resolve_node_kind, node_kind_priority
)
assert edge_display_type('HAS_AUTHORSHIP') != 'HAS_AUTHORSHIP', 'semantic display_type not working'
assert resolve_node_kind('Authorship') == 'AuthorshipReification', 'node_kind projection broken'
assert node_kind_priority('Method') < node_kind_priority('Institution'), 'priority order broken'
print('✓ graph_display GR2 functions ok')
"
```

### Шаг 7 — Проверка целостности спецификаций и документации

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

echo "=== Docs checks ==="
# agent-tools-v2.md — основные секции
for section in "Endpoint" "Request" "SSE Event" "Sync JSON" "Deprecation" "Error"; do
  grep -q "$section" docs/specs/agent-tools-v2.md && echo "✓ spec has $section section" || echo "✗ MISSING $section in spec"
done

# ADR 011 — аддендум GR2
grep -q "Wave GR2\|node_kind\|display_type" docs/adr/011-graph-live-ux-and-payload.md && \
  echo "✓ ADR 011 has GR2 addendum" || echo "✗ ADR 011 not updated"

# Backlog hygiene
grep -c "\[DONE\]" docs/backlog/refactor-backend.md | xargs -I{} echo "Backend backlog DONE items: {}"
grep -c "\[OPEN\]" docs/backlog/refactor-backend.md | xargs -I{} echo "Backend backlog OPEN items: {}"
```

### Шаг 8 — Обновить мастер-план

В `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` найти блок:

```
- **Раунд 4 (Wave Y3 + GR2 + benchmark UI):**
  - Agent 1: Wave Y3 backend (`api/agent_v2.py` + spec).
  - Agent 2: Wave GR2 backend (после WorkspaceGraphSplit и WorksSplit).
  - Agent 3: G-RetrievalCore.
  - Agent 4: H-AskV2SSE (после backend Y3 готов в превью).
```

Заменить на:

```
- **Раунд 4 (Wave Y3 + GR2 + G-RetrievalCore + H-AskV2SSE) ✅ DONE 2026-04-25:**
  - Agent 1: Wave Y3 backend — `api/agent_v2.py`, `/v2/agent/query` (SSE+sync), `docs/specs/agent-tools-v2.md`, deprecation header v1. ✅
  - Agent 2: Wave GR2 backend — `node_kind`, semantic `display_type`, prioritized LIMIT + `meta.skipped_by_kind`; ADR 011 updated. ✅
  - Agent 3: G-RetrievalCore — `science_graphrag/retrieval/` пакет; `api/retrieval.py` тонкий router; `main.py` shim удалён; `works/__init__` naming fixed. ✅
  - Agent 4: H-AskV2SSE — `useAgentStream.js`; `useAskSubmit.js` SSE path; `AskAnswerPanel` stream events. ✅

  > **Review 2026-04-25:** [заполнить по итогам — дефекты, фиксы, финальный счёт тестов]
```

Также обновить строку трека B в таблице §2:

```
| **B** | LangGraph migration | [...] | Wave Y3 done | **Wave Y4** (multi-agent supervisor) |
```

И трека E:

```
| **E** | Graph UX aggregation | [...] | GR1 done, GR2 done, GR3..GR5 open | **Wave GR3** (aggregator + lazy expand) |
```

### Шаг 9 — Итоговый вывод Review агента

После всех проверок вывести итог в виде:

```
=== Round 4 Review Summary ===

Agent 1 (Wave Y3):    [ PASS / FAIL / PARTIAL ]
Agent 2 (Wave GR2):   [ PASS / FAIL / PARTIAL ]
Agent 3 (RetrievalCore): [ PASS / FAIL / PARTIAL ]
Agent 4 (AskV2SSE):   [ PASS / FAIL / PARTIAL ]

Tests: N passed, M failed, K skipped
Pylint: X.XX/10
ESLint: clean / N warnings / N errors

Known issues (list any ✗ from above + brief description):
- ...

Recommended actions before Round 5:
- ...
```

**Условия PASS:**
- Все структурные проверки (✓) без критических ✗.
- `pytest tests/ -q` — 0 errors (failures допустимы только если помечены известным `xfail`).
- `pylint` ≥ 7.0/10 на всех новых файлах.
- `npm run lint` — 0 errors.
- Мастер-план обновлён.

**Условия PARTIAL (агент завершился, но есть долги):**
- Тесты написаны, но ≤2 теста падают по нефункциональным причинам (env/mock).
- Pylint 6.5–7.0 (снижение не критично, добавить в backlog).
- Размер файла превысил лимит на 10–20% (добавить в backlog, не блокировать).

**Условия FAIL (блокирует Round 5):**
- Импорт нового пакета ломается (`ImportError`).
- `POST /v2/agent/query` не зарегистрирован или возвращает 404.
- `works.router` всё ещё является APIRouter-инстансом вместо модуля.
- `npm run lint` — ошибки в изменённых файлах.
