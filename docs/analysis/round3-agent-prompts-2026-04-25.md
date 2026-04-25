# Round 3 — Agent Prompts («Wave W + Y2/X2 + Neo4jSplit + AskPanelSplit»)

> Дата: 2026-04-25
> Источник плана: `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §7 «Раунд 3»
> Предусловие: Раунд 2 выполнен ✅ (G-StoreFactory, G-WorkspaceGraphSplit, G-WorksSplit, H-GraphWorkspacePanelSplit)
> Порядок запуска: **Все 4 агента параллельно** — файловые скоупы не пересекаются.

**Проверка предусловий перед запуском всех агентов:**
```bash
# Раунд 2 complete:
python -c "from science_graphrag.api.deps import get_stores, StoreRegistry; print('deps ok')"
python -c "from science_graphrag.api.workspace_graph import router; print('wg ok')"
python -c "from science_graphrag.api.works import router; print('works ok')"
ls ui/src/components/graph/hooks/useGraphWorkspaceData.js && echo "frontend split ok"
```

---

## Agent 1 — Wave W backend: Redis + Dramatiq worker

**Задача:** Вынести ingest из threading.Thread внутри API в отдельный процесс Dramatiq-actor на Redis. API только enqueue'ит. `IngestEventBus` переезжает с `asyncio.Queue` на Redis pub/sub. Добавить `redis` и `worker` в `docker-compose.yml`.

### Контекст

Ты — агент Python-инфра рефакторинга. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предыстория треков:**
- Wave U (стадии ingest + OTel spans) — ✅ DONE.
- Wave V (SSE эндпоинт `/v1/ingest/jobs/{id}/events` + `useJobStream` в UI) — ✅ DONE.
- G-IngestSlim (распил `ingest_jobs.py` → `api/ingest/{router,registry,dispatcher,dto,worker}.py`) — ✅ DONE.
- Wave Y1 (LangGraph deps, config, LangChain instrumentation) — ✅ DONE.

**Текущее состояние `api/ingest/`:**
- `dispatcher.py` — содержит `IngestEventBus` (in-process `asyncio.Queue`) и функцию `dispatch_ingest` / `start_ingest_job_async`; это именно то, что меняет Wave W.
- `worker.py` — in-process `threading.Thread`-воркер; его `threading.Thread` должен быть удалён.
- `router.py` — SSE endpoint `/events`, читает из `IngestEventBus`; **не трогай** (контракт не меняется).
- `registry.py` — Postgres-стор jobs/stages; **не трогай**.

**Цель:** после Wave W:
- `api/ingest/worker.py` — больше нет `threading.Thread`; только `enqueue`-вызов к Dramatiq.
- `api/ingest/dispatcher.py` — `IngestEventBus` работает через Redis pub/sub (контракт `.publish(job_id, event)` / `async for event in .subscribe(job_id, last_event_id)` **остаётся**).
- `science_graphrag/worker/` — новый пакет с Dramatiq broker + actor `ingest_document_actor`.
- `docker-compose.yml` + `docker-compose.dev.yml` — добавлены сервисы `redis` и `worker`.
- `docs/adr/` — новый ADR (свободный номер); `docs/specs/ingest-worker-v1.md` — новая спека.

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Понять текущую структуру:
cat science_graphrag/api/ingest/dispatcher.py
cat science_graphrag/api/ingest/worker.py
cat science_graphrag/api/ingest/router.py | head -80

# Понять docker-compose:
cat docker-compose.yml
cat docker-compose.dev.yml 2>/dev/null || echo "no dev compose"

# Найти ADR-нумерацию:
ls docs/adr/ | sort

# Найти все упоминания mark_stale_running_jobs_failed:
rg "mark_stale_running_jobs_failed\|threading\.Thread" science_graphrag/ -n

# Зависимости:
grep -i "dramatiq\|redis" pyproject.toml
```

### Шаг 1 — Добавить зависимости

В `pyproject.toml` в секцию `[project.dependencies]` (или `[project.optional-dependencies]` под ключ `worker`):

```toml
# Добавить в core dependencies или worker extra:
"dramatiq[redis]>=1.17",
"redis>=5.0",
```

Установить:
```bash
.venv/bin/pip install "dramatiq[redis]>=1.17" "redis>=5.0"
```

### Шаг 2 — ADR + спека

1. **Определить свободный номер ADR:** посмотри `ls docs/adr/ | sort`, выбери следующий свободный (вероятно, 018 или 019).

2. **Создать `docs/adr/0{N}-ingest-worker-redis.md`:**

```markdown
# ADR 0{N} — Ingest Worker: Redis + Dramatiq

**Date:** 2026-04-25
**Status:** Accepted
**Supersedes:** None (extends ADR 001-phase1-stack.md)

## Context

Waves U/V delivered stage visibility and SSE progress. The remaining bottleneck is
that `ingest_document` runs in a `threading.Thread` inside the API process.
A restart kills in-flight work. Horizontal scaling is impossible.

Redis was already planned as a multi-purpose component (pub/sub bus for SSE,
future cache, rate-limit). Adding Dramatiq actor on top costs one Redis service.

## Decision

Add `redis:7-alpine` and `worker` (Dramatiq) to `docker-compose.yml`.
`ingest_document_actor` is the sole entry point for long-running ingest.
API only enqueues; `threading.Thread` is removed from `api/ingest/worker.py`.
`IngestEventBus` switches from `asyncio.Queue` to Redis pub/sub.
Job state remains in Postgres (source of truth). Redis is ephemeral transport only.

## Alternatives Considered

- **Postgres SKIP LOCKED (procrastinate):** rejected — no native pub/sub for SSE.
- **Celery:** rejected — excessive ops overhead for our load.
- **Kafka/Temporal:** rejected — overkill for single-consumer single-producer.

## Consequences

- Restart safety: `worker` container retries failed jobs via Dramatiq middleware.
- SSE cross-process: `IngestEventBus` v2 works across multiple API instances.
- New env vars: `SCIENCE_GRAPHRAG_REDIS_URL`.
- ADR 001 extended: Redis becomes core stack component.
```

3. **Создать `docs/specs/ingest-worker-v1.md`** с разделами:
   - Очереди Dramatiq (`queue_name="ingest"`), retry policy (`max_retries=2`, `AgeLimit=3h`, `TimeLimit=1h`).
   - Формат сообщения: `{"job_id": "<uuid>"}` (ничего кроме id).
   - Идемпотентность: повторный запуск `job_id` пропускает уже закрытые стадии.
   - Compensation sweep: `worker` при старте находит `status='queued' AND created_at < now()-60s` и enqueue'ит заново.
   - `IngestEventBus` v2 контракт: pub/sub channel `ingest:events:{job_id}`, TTL 24h.

### Шаг 3 — docker-compose

Добавить в `docker-compose.yml` (и в `docker-compose.dev.yml` если существует) два сервиса:

```yaml
redis:
  image: redis:7-alpine
  command: ["redis-server", "--appendonly", "yes", "--maxmemory", "512mb", "--maxmemory-policy", "allkeys-lru"]
  ports:
    - "16379:6379"
  volumes:
    - redis_data:/data
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 20s
    timeout: 5s
    retries: 5

worker:
  build: { context: ., dockerfile: Dockerfile }
  command: ["python", "-m", "science_graphrag.worker"]
  env_file: [.env]
  environment:
    SCIENCE_GRAPHRAG_REDIS_URL: "redis://redis:6379/0"
  volumes:
    - ./data/blobs:/data/blobs
    - ./data/artifacts:/data/artifacts
  depends_on:
    redis:
      condition: service_healthy
    postgres:
      condition: service_healthy
```

Добавить `SCIENCE_GRAPHRAG_REDIS_URL` к `api` сервису:
```yaml
api:
  environment:
    SCIENCE_GRAPHRAG_REDIS_URL: "redis://redis:6379/0"
```

Добавить `redis_data` в секцию `volumes:` в конце файла.

Добавить `SCIENCE_GRAPHRAG_REDIS_URL` в `.env.example`:
```dotenv
# Wave W — Ingest Worker
SCIENCE_GRAPHRAG_REDIS_URL=redis://localhost:16379/0
```

### Шаг 4 — Config

В `science_graphrag/config.py` добавить поле:
```python
redis_url: str = Field(
    default="redis://localhost:6379/0",
    validation_alias=AliasChoices("SCIENCE_GRAPHRAG_REDIS_URL", "redis_url"),
)
```

### Шаг 5 — `science_graphrag/worker/__init__.py`

Создать новый пакет `science_graphrag/worker/`:

```python
"""Dramatiq worker entry point.

Run with:
    python -m science_graphrag.worker

or via docker-compose worker service.
"""
from __future__ import annotations

import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, Retries, TimeLimit

from science_graphrag.config import get_settings

settings = get_settings()

_broker = RedisBroker(url=settings.redis_url)
_broker.add_middleware(Retries(max_retries=2))
_broker.add_middleware(AgeLimit(max_age=3 * 60 * 60 * 1000))   # 3 hours
_broker.add_middleware(TimeLimit(time_limit=60 * 60 * 1000))   # 1 hour per message
dramatiq.set_broker(_broker)

# Import actor to register it with the broker:
from science_graphrag.worker.actor import ingest_document_actor  # noqa: F401, E402


def run() -> None:
    """Start the Dramatiq worker (called via python -m science_graphrag.worker)."""
    from dramatiq.cli import main  # type: ignore[import-untyped]
    main()


if __name__ == "__main__":
    run()
```

Создать `science_graphrag/worker/__main__.py`:
```python
from science_graphrag.worker import run

run()
```

### Шаг 6 — `science_graphrag/worker/actor.py`

```python
"""Dramatiq actor for ingest pipeline execution."""
from __future__ import annotations

import logging

import dramatiq

from science_graphrag.config import get_settings

logger = logging.getLogger(__name__)


@dramatiq.actor(queue_name="ingest", max_retries=2)
def ingest_document_actor(job_id: str) -> None:
    """Execute ingest pipeline for a single document.

    Idempotent: stages that are already 'completed' are skipped by the
    stage context manager. Safe to retry on failure.
    """
    settings = get_settings()
    logger.info("Worker: starting ingest for job_id=%s", job_id)

    # Import here to avoid circular imports during broker setup:
    from science_graphrag.api.ingest.registry import IngestJobRegistry
    from science_graphrag.ingestion.pipeline import ingest_document

    registry = IngestJobRegistry()
    registry.bootstrap()  # lazy DB init

    job = registry.get_job(job_id)
    if job is None:
        logger.error("Worker: job_id=%s not found in DB, skipping", job_id)
        return

    if job.status in ("completed", "failed"):
        logger.info("Worker: job_id=%s already terminal (status=%s), skipping", job_id, job.status)
        return

    # Delegate to the existing pipeline (which uses IngestRunContext + stages):
    try:
        ingest_document(
            job_id=job_id,
            workspace_id=job.workspace_id,
            blob_path=job.blob_path,
            settings=settings,
        )
    except Exception:
        logger.exception("Worker: ingest failed for job_id=%s", job_id)
        raise  # Let Dramatiq retry
```

> ⚠️ **Важно:** прочитай `science_graphrag/api/ingest/registry.py` и `science_graphrag/ingestion/pipeline.py` чтобы узнать реальные сигнатуры `get_job` и `ingest_document`. Адаптируй вызовы к реальному API, не гадай.

### Шаг 7 — `IngestEventBus` v2 (Redis pub/sub)

Прочитай текущий `science_graphrag/api/ingest/dispatcher.py` целиком. Найди класс `IngestEventBus`.

Заменить реализацию `IngestEventBus` — **контракт методов `.publish()` и `.subscribe()` должен остаться прежним**, только внутренность меняется с `asyncio.Queue` на Redis pub/sub:

```python
import asyncio
import json
from typing import AsyncIterator

import redis.asyncio as aioredis

from science_graphrag.config import get_settings


class IngestEventBus:
    """Redis pub/sub based event bus for ingest progress events.

    Replaces the in-process asyncio.Queue implementation (Wave V).
    Cross-process: multiple API instances and the worker share the same bus.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        _url = redis_url or get_settings().redis_url
        self._client: aioredis.Redis = aioredis.from_url(_url, decode_responses=True)
        self._channel_prefix = "ingest:events"

    def _channel(self, job_id: str) -> str:
        return f"{self._channel_prefix}:{job_id}"

    async def publish(self, job_id: str, event: dict) -> None:
        """Publish an event dict to the job's Redis channel."""
        await self._client.publish(self._channel(job_id), json.dumps(event))

    async def subscribe(
        self, job_id: str, last_event_id: str | None = None
    ) -> AsyncIterator[dict]:
        """Subscribe to events for job_id. Yields event dicts.

        last_event_id: if provided, attempt to replay missed events from DB
        (replay is handled by the SSE router using DB events; this stream is live-only).
        """
        pubsub = self._client.pubsub()
        await pubsub.subscribe(self._channel(job_id))
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    yield json.loads(data)
                    event = json.loads(data)
                    if event.get("kind") == "terminal":
                        break
        finally:
            await pubsub.unsubscribe(self._channel(job_id))
            await pubsub.aclose()

    async def close(self) -> None:
        await self._client.aclose()
```

Обнови `IngestEventBus` в `dispatcher.py` этой реализацией. Сигнатуру `publish`/`subscribe` сохрани — `router.py` использует её без изменений.

Также обнови функцию `dispatch_ingest` / `start_ingest_job_async` (как она называется в реальном коде) — вместо `threading.Thread` или прямого вызова pipeline:

```python
# В dispatcher.py — функция enqueue'инга:
def enqueue_ingest_job(job_id: str) -> None:
    """Enqueue job to Dramatiq worker."""
    from science_graphrag.worker.actor import ingest_document_actor
    ingest_document_actor.send(job_id)
```

### Шаг 8 — Удалить threading.Thread из `worker.py`

Прочитай `science_graphrag/api/ingest/worker.py`. Найди `threading.Thread`. Удали запуск потока, замени вызов на `enqueue_ingest_job(job_id)` из `dispatcher.py`.

Если `mark_stale_running_jobs_failed` вызывается в `worker.py` или `main.py` — удалить (Wave W делает его ненужным: воркер переживает перезапуск API).

### Шаг 9 — Compensation sweep в worker

В `science_graphrag/worker/__init__.py` или `actor.py` добавить функцию запуска sweep'а:

```python
def run_compensation_sweep() -> None:
    """On worker startup: re-enqueue jobs stuck in 'queued' for > 60s."""
    from datetime import UTC, datetime, timedelta
    from science_graphrag.api.ingest.registry import IngestJobRegistry

    registry = IngestJobRegistry()
    registry.bootstrap()
    cutoff = datetime.now(UTC) - timedelta(seconds=60)
    stale_jobs = registry.list_stale_queued_jobs(before=cutoff)  # реализуй если нет
    for job in stale_jobs:
        logger.info("Compensation sweep: re-enqueuing job_id=%s", job.id)
        ingest_document_actor.send(job.id)
```

Вызвать `run_compensation_sweep()` при старте воркера (в `run()` или через Dramatiq `after_process_boot` middleware).

### Шаг 10 — Тесты

```bash
# Smoke: модули импортируются без ошибок (без реального Redis):
.venv/bin/python -c "
from science_graphrag.worker.actor import ingest_document_actor
print('actor ok:', ingest_document_actor.actor_name)
"

.venv/bin/python -c "
from science_graphrag.api.ingest.dispatcher import IngestEventBus
print('event bus ok')
"

# Запуск существующих тестов:
.venv/bin/pytest tests/test_api_smoke.py tests/test_api_agent_smoke.py -x -v 2>&1 | tail -20

# Тест на enqueue (без реального Redis — mock):
```

Создать `tests/worker/test_actor.py`:
```python
"""Tests for Wave W Dramatiq actor."""
import pytest
from unittest.mock import MagicMock, patch


def test_ingest_document_actor_skips_completed_job():
    """Actor must skip jobs that are already completed."""
    mock_job = MagicMock()
    mock_job.status = "completed"
    mock_job.workspace_id = "ws-1"

    with patch("science_graphrag.worker.actor.get_settings"), \
         patch("science_graphrag.worker.actor.IngestJobRegistry") as mock_reg_cls:
        mock_reg = mock_reg_cls.return_value
        mock_reg.get_job.return_value = mock_job
        with patch("science_graphrag.worker.actor.ingest_document") as mock_pipeline:
            from science_graphrag.worker.actor import ingest_document_actor
            ingest_document_actor("job-123")
            mock_pipeline.assert_not_called()


def test_ingest_document_actor_skips_missing_job():
    """Actor must skip jobs not found in DB (idempotency)."""
    with patch("science_graphrag.worker.actor.get_settings"), \
         patch("science_graphrag.worker.actor.IngestJobRegistry") as mock_reg_cls:
        mock_reg = mock_reg_cls.return_value
        mock_reg.get_job.return_value = None
        with patch("science_graphrag.worker.actor.ingest_document") as mock_pipeline:
            from science_graphrag.worker.actor import ingest_document_actor
            ingest_document_actor("job-missing")
            mock_pipeline.assert_not_called()
```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `docker-compose.yml` + `docker-compose.dev.yml` (добавить redis + worker)
- `pyproject.toml` (добавить dramatiq + redis deps)
- `science_graphrag/config.py` (добавить redis_url)
- `science_graphrag/worker/` (создать пакет целиком)
- `science_graphrag/api/ingest/dispatcher.py` (заменить IngestEventBus на Redis)
- `science_graphrag/api/ingest/worker.py` (убрать threading.Thread)
- `science_graphrag/api/main.py` (убрать mark_stale_running_jobs_failed если там)
- `docs/adr/0{N}-ingest-worker-redis.md` (создать)
- `docs/specs/ingest-worker-v1.md` (создать)
- `.env.example` (добавить REDIS_URL)
- `tests/worker/test_actor.py` (создать)

**НЕ трогать:**
- `science_graphrag/api/ingest/router.py` — SSE endpoint, контракт не меняется
- `science_graphrag/api/ingest/registry.py` — Postgres-стор, не трогать
- `science_graphrag/api/ingest/dto.py` — не трогать
- `science_graphrag/ingestion/pipeline.py` — не трогать логику pipeline
- `science_graphrag/storage/neo4j_store.py` — скоуп Agent 3
- `science_graphrag/agent/` — скоуп Agent 2
- `ui/` — frontend вне скоупа

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Imports ok:
.venv/bin/python -c "from science_graphrag.worker.actor import ingest_document_actor; print('worker ok')"
.venv/bin/python -c "from science_graphrag.api.ingest.dispatcher import IngestEventBus; print('bus ok')"
.venv/bin/python -c "from science_graphrag.api.main import app; print('app ok')"

# No threading.Thread in ingest worker:
rg "threading\.Thread" science_graphrag/api/ingest/ && echo "FOUND — fix it" || echo "ok: no Thread"

# Formatting:
.venv/bin/isort science_graphrag/worker/ science_graphrag/api/ingest/dispatcher.py
.venv/bin/black science_graphrag/worker/ science_graphrag/api/ingest/dispatcher.py
.venv/bin/pylint science_graphrag/worker/ --fail-under=7.0

# Tests:
.venv/bin/pytest tests/test_api_smoke.py tests/worker/ -x -v 2>&1 | tail -30
```

### Backlog

В `docs/backlog/refactor-backend.md` обновить `[PARTIAL] Ingest pipeline async-redesign (Wave U–W)`:
```
### [DONE] Ingest pipeline async-redesign (Wave U–W)
- **Note (done Wave W):** 2026-04-25 — добавлены redis + worker в compose; создан science_graphrag/worker/
  с dramatiq actor ingest_document_actor; IngestEventBus v2 на Redis pub/sub в dispatcher.py;
  threading.Thread удалён из api/ingest/worker.py; ADR 0{N}-ingest-worker-redis.md принят;
  specs/ingest-worker-v1.md создана; compensation sweep при старте воркера.
```

---

## Agent 2 — Wave Y2 + Wave X2 (один PR в `agent/`)

**Задача:** Перевести production-агент на LangGraph (`StateGraph` ReAct loop, 6 tools на `langchain_core`), сохранив контракт v1 endpoint. Параллельно — добавить Phoenix observability (Wave X2): `chain_span("agent.query")`, `traced_tool_span` вокруг tools, RETRIEVER-спан для Qdrant в `idea_search`.

### Контекст

Ты — агент Python-рефакторинга. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предусловие — проверь перед началом:**
```bash
# Wave Y1 (foundation) выполнена:
.venv/bin/python -c "
import langgraph, langchain_core, langchain_openai
from openinference.instrumentation.langchain import LangChainInstrumentor
print('Y1 deps ok')
"
# G-StoreFactory выполнена:
.venv/bin/python -c "from science_graphrag.api.deps import get_stores, StoreRegistry; print('deps ok')"
```

**Текущее состояние `science_graphrag/agent/`:**
```
agent/
├── __init__.py        # build_agent, RetrievalAgent, AgentRunOutput
├── runtime.py         # RetrievalAgent — детерминированный pipeline, БЕЗ LLM
├── cypher_safety.py   # validate_readonly_cypher — не трогать
├── trace.py           # ToolCallTrace TypedDict — сохранить совместимость
├── idea_workflow.py   # idea_assist (не агент) — не трогать
└── tools/
    ├── __init__.py    # re-export 6 tools
    ├── base.py        # BaseAgentTool, ToolResult, run_with_trace
    ├── cypher_query.py
    ├── edge_search.py
    ├── entity_search.py
    ├── idea_search.py
    ├── summarize_workspace.py
    └── final_answer.py
```

**Прочитай все файлы перед началом:**
```bash
cat science_graphrag/agent/runtime.py
cat science_graphrag/agent/tools/base.py
cat science_graphrag/agent/tools/idea_search.py
cat science_graphrag/agent/tools/cypher_query.py
cat science_graphrag/agent/trace.py
cat science_graphrag/api/agent.py
cat science_graphrag/config.py | grep -A5 "agent"
cat science_graphrag/observability/phoenix_tracer.py | head -60
cat science_graphrag/observability/spans/decorators.py
```

### Y2.1 — `agent/llm/` модуль

Создать `science_graphrag/agent/llm/__init__.py` и `science_graphrag/agent/llm/chat.py`:

```python
# agent/llm/chat.py
"""LLM factory for agent runtime."""
from __future__ import annotations

from langchain_openai import ChatOpenAI
from science_graphrag.config import Settings


def build_chat_model(settings: Settings, *, temperature: float | None = None, max_tokens: int | None = None) -> ChatOpenAI:
    """Build ChatOpenAI client pointing to OpenRouter-compatible endpoint."""
    return ChatOpenAI(
        model=settings.extraction_llm_model,
        api_key=settings.extraction_llm_api_key,
        base_url=settings.extraction_llm_base_url,
        temperature=temperature if temperature is not None else settings.agent_chat_temperature,
        max_tokens=max_tokens if max_tokens is not None else settings.agent_chat_max_tokens,
        timeout=settings.extraction_llm_timeout_seconds,
    )
```

### Y2.2 — `agent/graph/state.py`

```python
# agent/graph/state.py
"""LangGraph AgentState definition."""
from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]          # совместимо с ToolCallTrace для v1 endpoint
    budget_remaining: int           # max_tool_calls − использованные
    metadata: dict                  # agent_runtime_version, model, etc.
```

### Y2.3 — Tools на `langchain_core.tools`

Для каждого из 6 tools создать обёртку через `@tool`. Внутри — переиспользовать текущую логику из `tools/*.py`.

Прочитай каждый файл `agent/tools/*.py` и адаптируй под `langchain_core.tools.tool` + Pydantic args_schema.

**Шаблон для `cypher_query.py`:**
```python
# agent/tools/cypher_query.py
from __future__ import annotations

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from science_graphrag.agent.cypher_safety import validate_readonly_cypher


class CypherQueryArgs(BaseModel):
    query: str = Field(..., description="Read-only Cypher. No CREATE/MERGE/DELETE/SET/REMOVE/DROP. max LIMIT 200.")
    params: dict = Field(default_factory=dict, description="Optional Cypher parameters.")


@tool("cypher_query", args_schema=CypherQueryArgs, return_direct=False)
def cypher_query_tool(query: str, params: dict | None = None) -> dict:
    """Execute a read-only Cypher query against the knowledge graph (label allowlist + LIMIT 200)."""
    validate_readonly_cypher(query, max_limit=200)
    # Используй _store для Neo4j — store инжектируется через closure, см. build_tool_registry
    ...
```

**Ключевое:** tools требуют доступа к stores (Neo4j, Qdrant). Для этого используй `build_tool_registry(stores: StoreRegistry) -> list[BaseTool]` — функцию, которая создаёт tools с захваченным `stores` через closure или partial:

```python
# agent/tools/__init__.py
from __future__ import annotations

from science_graphrag.api.deps import StoreRegistry


def build_tool_registry(stores: StoreRegistry) -> list:
    """Build list of LangChain tools with injected stores."""
    from langchain_core.tools import BaseTool
    # Создать closure-обёртки для каждого tool с stores:
    tools = [
        _make_cypher_query_tool(stores.neo4j),
        _make_entity_search_tool(stores.neo4j),
        _make_edge_search_tool(stores.neo4j),
        _make_idea_search_tool(stores.qdrant_chunks),
        _make_summarize_workspace_tool(stores.neo4j),
        _make_final_answer_tool(),
    ]
    return tools
```

**Возвращаемый формат** каждого tool должен быть совместим с текущим `ToolResult.payload` (dict с ключами, которые UI и `eval/agent_tools/metrics.py` ожидают).

После реализации всех tools — убедиться что `cypher_safety.validate_readonly_cypher` вызывается внутри `cypher_query_tool`.

### Y2.4 — `agent/graph/supervisor.py`

```python
# agent/graph/supervisor.py
"""LangGraph ReAct supervisor graph (single-specialist, Wave Y2)."""
from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.agent.tools import build_tool_registry
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings


def build_retrieval_graph(stores: StoreRegistry, settings: Settings):
    """Build and compile the single-agent ReAct StateGraph."""
    tool_registry = build_tool_registry(stores)
    llm = build_chat_model(settings).bind_tools(tool_registry)

    def chat_node(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        # Декрементировать budget:
        budget = state.get("budget_remaining", settings.agent_max_tool_calls)
        return {"messages": [response], "budget_remaining": budget - 1}

    def should_continue(state: AgentState) -> str:
        last = state["messages"][-1]
        budget = state.get("budget_remaining", 0)
        if budget <= 0:
            return END
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    tools_node = ToolNode(tool_registry)

    graph = StateGraph(AgentState)
    graph.add_node("chat", chat_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("chat")
    graph.add_conditional_edges("chat", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "chat")

    return graph.compile()
```

### Y2.5 — `agent/graph/tracing.py`

```python
# agent/graph/tracing.py
"""Adapter: LangGraph state → legacy ToolCallTrace list (for v1 API contract)."""
from __future__ import annotations

from langchain_core.messages import AIMessage, ToolMessage

from science_graphrag.agent.trace import ToolCallTrace


def collect_tool_trace(messages: list) -> list[ToolCallTrace]:
    """Extract ToolCallTrace entries from LangGraph message sequence."""
    traces = []
    step = 0
    for i, msg in enumerate(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                # Find corresponding ToolMessage:
                result_msg = next(
                    (m for m in messages[i+1:] if isinstance(m, ToolMessage) and m.tool_call_id == tc["id"]),
                    None,
                )
                result_payload = {}
                error = None
                row_count = None
                if result_msg:
                    import json
                    try:
                        result_payload = json.loads(result_msg.content) if isinstance(result_msg.content, str) else {}
                    except Exception:
                        error = str(result_msg.content)[:200]
                    row_count = result_payload.get("row_count")

                traces.append(ToolCallTrace(
                    step=step,
                    tool=tc["name"],
                    args_summary={k: str(v)[:200] for k, v in tc.get("args", {}).items()},
                    row_count=row_count,
                    duration_ms=None,  # LangChain callbacks can fill this
                    truncated=result_payload.get("truncated", False),
                    error=error,
                ))
                step += 1
    return traces
```

### Y2.6 — Обновить `agent/runtime.py`

`RetrievalAgent.run(...)` теперь — тонкая обёртка вокруг LangGraph + `collect_tool_trace`.

**Обязательно:** сохранить backward-compat — если `settings.agent_runtime == "retrieval_v1"` → использовать старую детерминированную логику из `runtime_legacy.py` (перенеси туда без изменений).

```python
# agent/runtime.py
"""Production retrieval agent runtime (Wave Y2: LangGraph ReAct)."""
from __future__ import annotations

from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.trace import AgentRunOutput
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings


class RetrievalAgent:
    def __init__(self, stores: StoreRegistry, settings: Settings) -> None:
        self._stores = stores
        self._settings = settings
        if settings.agent_runtime == "retrieval_v1":
            # Legacy deterministic mode — import from runtime_legacy.py
            from science_graphrag.agent.runtime_legacy import LegacyRetrievalAgent
            self._legacy = LegacyRetrievalAgent(stores, settings)
        else:
            self._graph = build_retrieval_graph(stores, settings)
            self._legacy = None

    def run(self, question: str, workspace_id: str | None = None, max_tool_calls: int | None = None) -> AgentRunOutput:
        if self._legacy is not None:
            return self._legacy.run(question, workspace_id, max_tool_calls)
        return self._run_langgraph(question, workspace_id, max_tool_calls)

    def _run_langgraph(self, question: str, workspace_id: str | None, max_tool_calls: int | None) -> AgentRunOutput:
        from langchain_core.messages import HumanMessage

        budget = max_tool_calls or self._settings.agent_max_tool_calls
        initial_state = {
            "messages": [HumanMessage(content=question)],
            "workspace_id": workspace_id,
            "citations": [],
            "tool_trace": [],
            "budget_remaining": budget,
            "metadata": {"agent_runtime": self._settings.agent_runtime},
        }
        final_state = self._graph.invoke(
            initial_state,
            config={"recursion_limit": self._settings.agent_supervisor_recursion_limit},
        )
        tool_trace = collect_tool_trace(final_state["messages"])
        # Extract final answer from last AIMessage without tool_calls:
        answer = ""
        for msg in reversed(final_state["messages"]):
            if hasattr(msg, "content") and msg.content and not getattr(msg, "tool_calls", None):
                answer = msg.content
                break
        citations = final_state.get("citations", [])
        return AgentRunOutput(answer=answer, citations=citations, tool_trace=tool_trace)
```

Создать `science_graphrag/agent/runtime_legacy.py` — скопируй текущую детерминированную логику `RetrievalAgent.run` (без изменений) и назови класс `LegacyRetrievalAgent`.

### X2 — Phoenix observability для агента

После реализации Y2 добавить трассировку. Используй helpers из `science_graphrag/observability/spans/decorators.py`.

**В `agent/runtime.py::_run_langgraph`** обернуть в `chain_span`:
```python
from science_graphrag.observability.spans import chain_span

def _run_langgraph(self, question, workspace_id, max_tool_calls):
    attrs = {
        "agent.runtime": self._settings.agent_runtime,
        "agent.max_tool_calls": max_tool_calls or self._settings.agent_max_tool_calls,
        "user.id": workspace_id or "",
        "input.value": question[:500],
    }
    with chain_span("agent.query", attrs):
        # ... весь код graph.invoke выше ...
```

**В `tools/idea_search.py`** добавить RETRIEVER-спан и EMBEDDING-спан:
```python
from science_graphrag.observability.spans import traced_tool_span

# Внутри idea_search_tool function:
with traced_tool_span("tool.idea_search", tool_name="idea_search", tool_parameters={"query": query[:200]}):
    # ... существующий код поиска ...
```

Если есть embedding-вызов внутри `idea_search` — обернуть в `embeddings_span`:
```python
from science_graphrag.observability.spans.decorators import embeddings_span
with embeddings_span("embedding.agent.idea_search", attrs={"embedding.model_name": "...", ...}):
    embedding = get_query_embedding(query)
```

LangChain auto-instrumentation (установленная в Y1) покрывает LLM-спаны автоматически. Нет нужды добавлять `llm_span` вручную.

### Тесты

**Сохранить green без правок:**
- `tests/agent/test_runtime.py::test_build_agent_and_run_smoke`
- `tests/test_api_agent_smoke.py`

Создать новые тесты `tests/agent/`:

**`tests/agent/test_tools_registry.py`:**
```python
from unittest.mock import MagicMock

def test_build_tool_registry_returns_six_tools():
    from science_graphrag.agent.tools import build_tool_registry
    stores = MagicMock()
    tools = build_tool_registry(stores)
    assert len(tools) == 6
    tool_names = {t.name for t in tools}
    assert "cypher_query" in tool_names
    assert "idea_search" in tool_names


def test_cypher_query_tool_rejects_write():
    from science_graphrag.agent.cypher_safety import CypherNotAllowedError
    from unittest.mock import MagicMock
    from science_graphrag.agent.tools import build_tool_registry
    stores = MagicMock()
    tools = build_tool_registry(stores)
    cypher_tool = next(t for t in tools if t.name == "cypher_query")
    with pytest.raises((CypherNotAllowedError, Exception)):
        cypher_tool.invoke({"query": "MATCH (n) DELETE n"})
```

**`tests/agent/test_graph_smoke.py`:**
```python
from unittest.mock import MagicMock, patch

def test_langgraph_compile_smoke():
    from science_graphrag.agent.graph.supervisor import build_retrieval_graph
    stores = MagicMock()
    settings = MagicMock()
    settings.agent_max_tool_calls = 4
    settings.agent_supervisor_recursion_limit = 10
    settings.extraction_llm_model = "test-model"
    settings.extraction_llm_api_key = "test-key"
    settings.extraction_llm_base_url = "http://localhost"
    settings.extraction_llm_timeout_seconds = 30
    settings.agent_chat_temperature = 0.0
    settings.agent_chat_max_tokens = 512

    with patch("science_graphrag.agent.graph.supervisor.build_chat_model") as mock_llm:
        mock_llm.return_value.bind_tools.return_value.invoke.return_value = MagicMock(
            tool_calls=[], content="test answer"
        )
        graph = build_retrieval_graph(stores, settings)
        assert graph is not None  # compiled without error
```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `science_graphrag/agent/` (весь пакет — runtime, tools, + новые подпакеты graph/, llm/)
- `science_graphrag/api/agent.py` (минимально — обновить `build_agent` вызов если сигнатура изменилась)
- `tests/agent/` (новые тесты + обновление существующих при необходимости)

**НЕ трогать:**
- `science_graphrag/api/agent_v2.py` — это задача Раунда 4 (Wave Y3)
- `science_graphrag/api/deps.py` — не менять (только использовать `StoreRegistry`)
- `science_graphrag/storage/` — не трогать store-реализации
- `science_graphrag/api/workspace_graph/` и `api/works/` — не трогать
- `ui/` — frontend вне скоупа
- `science_graphrag/agent/cypher_safety.py` — не трогать (только импортировать)
- `science_graphrag/agent/idea_workflow.py` — не трогать (idea-assist, не retrieval-агент)

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# LangGraph работает:
.venv/bin/python -c "
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.tracing import collect_tool_trace
print('graph modules ok')
"

# Backward compat — v1 endpoint:
.venv/bin/python -c "from science_graphrag.api.agent import router; print('agent router ok')"

# Cypher safety сохранена:
.venv/bin/python -c "
from science_graphrag.agent.cypher_safety import validate_readonly_cypher
print('cypher safety ok')
"

# Форматирование:
.venv/bin/isort science_graphrag/agent/
.venv/bin/black science_graphrag/agent/
.venv/bin/pylint science_graphrag/agent/ --fail-under=7.0

# Тесты:
.venv/bin/pytest tests/agent/ tests/test_api_agent_smoke.py -x -v 2>&1 | tail -30

# Нет прямого BaseAgentTool использования в runtime.py (перенесено в legacy):
rg "BaseAgentTool" science_graphrag/agent/runtime.py && echo "FOUND in runtime — move to legacy" || echo "ok"
```

### Backlog

В `docs/backlog/refactor-backend.md` добавить новую запись:
```
### [DONE] Wave Y2: LangGraph single-agent ReAct behind v1 endpoint + X2 Phoenix
- **Note (done):** 2026-04-25 — создан agent/graph/{state,supervisor,tracing}.py;
  agent/llm/chat.py; 6 tools переведены на langchain_core.tools + build_tool_registry;
  runtime.py обёртка вокруг LangGraph graph.invoke; legacy fallback в runtime_legacy.py;
  chain_span("agent.query") + traced_tool_span на idea_search + embeddings_span;
  tests/agent/{test_tools_registry,test_graph_smoke}.py; v1 endpoint без изменений контракта.
```

---

## Agent 3 — G-Neo4jSplit (большой: `storage/neo4j_store.py` → `storage/neo4j/`)

**Задача:** Разнести `science_graphrag/storage/neo4j_store.py` (1022 строки) в пакет `science_graphrag/storage/neo4j/` по доменам. Публичный класс `Neo4jGraphStore` сохраняет прежний API как фасад.

### Контекст

Ты — агент Python-рефакторинга. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Зачем:** `Neo4jGraphStore` (1022 строки) совмещает schema/init, write-операции по 5 доменам, reads, merge и wipe. **Wave T** (entity dedup) добавит writes/{authors,institutions,...} — без split это растянет god-файл ещё на 400+ строк.

**Прочитай файл целиком перед началом:**
```bash
wc -l science_graphrag/storage/neo4j_store.py
# Все методы:
rg "def " science_graphrag/storage/neo4j_store.py -n
# Все классы:
rg "class " science_graphrag/storage/neo4j_store.py -n
# Импортеры:
rg "from.*neo4j_store\|import.*neo4j_store" science_graphrag/ --include="*.py" -l
rg "from.*neo4j_store\|import.*neo4j_store" tests/ --include="*.py" -l
```

### Целевая структура `storage/neo4j/`

```
science_graphrag/storage/neo4j/
├── __init__.py          # re-export Neo4jGraphStore + store public API
├── client.py            # _Neo4jClient: driver init, session(), close(), wipe_all()
├── schema.py            # ensure_schema() — constraints + indexes
├── reads.py             # read-only queries: find_work_id_by_*, work_exists,
│                        # fulltext_search_work_ids, cites_neighbor_work_ids,
│                        # fetch_work_bibliography_card, workspace_*, list_workspace_authors,
│                        # fetch_author_affiliation_hint, find_work_dedup_violations
├── writes/
│   ├── __init__.py
│   ├── works.py         # upsert_work_layer1, _write_work_tx, upsert_minimal_work,
│   │                    # merge_cites, merge_related_version, work_has_incoming_cites,
│   │                    # detach_delete_work_if_no_incoming_cites, get_work_external_keys
│   ├── semantic.py      # sync_work_semantic_layer, _sync_semantic_tx,
│   │                    # _semantic_method_id, _semantic_dataset_id, _semantic_provenance_json
│   ├── claims.py        # detach_delete_claims_for_work, upsert_claims_with_evidence
│   ├── dedup.py         # merge_work_into_canonical, _merge_work_tx,
│   │                    # merge_author_into_canonical, _merge_author_tx
│   └── workspace.py     # workspace_create, workspace_list, workspace_get,
│                        # workspace_rename, workspace_delete
└── facade.py            # Neo4jGraphStore — публичный фасад, делегирует в подмодули
```

### Шаг 1 — Анализ и группировка

Прочитай `neo4j_store.py` полностью. Сгруппируй методы по модулям согласно структуре выше. Составь мысленную карту: какие private-методы относятся к какому домену.

Ключевые паттерны:
- `session()` и `_driver` — в `client.py`
- `ensure_schema()` (строки ~48–137) — в `schema.py`
- Методы `find_*`, `list_*`, `fetch_*`, `fulltext_search_*`, `cites_neighbor_*`, `workspace_get`, `workspace_list`, `work_exists`, `work_has_incoming_cites`, `find_work_dedup_violations` — в `reads.py`
- `upsert_work_layer1`, `_write_work_tx`, `merge_cites`, `merge_related_version`, `upsert_minimal_work` — в `writes/works.py`
- `sync_work_semantic_layer`, `_sync_semantic_tx` — в `writes/semantic.py`
- `upsert_claims_with_evidence`, `detach_delete_claims_for_work` — в `writes/claims.py`
- `merge_work_into_canonical`, `merge_author_into_canonical`, `_merge_*_tx` — в `writes/dedup.py`
- `workspace_create`, `workspace_rename`, `workspace_delete` — в `writes/workspace.py`

### Шаг 2 — Создать `storage/neo4j/client.py`

```python
# storage/neo4j/client.py
"""Neo4j driver management (connection pooling, session factory)."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from neo4j import GraphDatabase


class _Neo4jClient:
    """Low-level driver wrapper. Shared by all domain write/read modules."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        self._driver.close()

    @contextmanager
    def session(self) -> Iterator:
        with self._driver.session() as s:
            yield s

    def wipe_all(self) -> None:
        with self.session() as s:
            s.run("MATCH (n) DETACH DELETE n")
```

### Шаг 3 — Создать `storage/neo4j/schema.py`

Перенести `ensure_schema()` (строки ~48–137 в оригинале) — все `CREATE CONSTRAINT` / `CREATE INDEX` запросы.

```python
# storage/neo4j/schema.py
"""Neo4j schema setup: constraints and indexes."""
from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def ensure_schema(client: _Neo4jClient) -> None:
    """Apply all constraints and indexes. Idempotent."""
    with client.session() as session:
        # Перенеси все CREATE CONSTRAINT и CREATE INDEX запросы из оригинала:
        ...
```

### Шаг 4 — Создать `storage/neo4j/reads.py`

Перенести все read-only методы. Каждый принимает `client: _Neo4jClient` как первый аргумент.

```python
# storage/neo4j/reads.py
"""Read-only Neo4j queries (no writes)."""
from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient


def find_work_id_by_doi(client: _Neo4jClient, doi: str) -> str | None:
    with client.session() as session:
        # Перенести логику из оригинального Neo4jGraphStore.find_work_id_by_doi:
        ...

# ... все остальные read-методы аналогично ...
```

### Шаг 5 — Создать `storage/neo4j/writes/*.py`

По одному файлу на домен. Каждая функция принимает `client: _Neo4jClient`.

```python
# storage/neo4j/writes/works.py
"""Write operations for :Work nodes (upsert, merge, delete)."""
from __future__ import annotations
from typing import Any
from science_graphrag.storage.neo4j.client import _Neo4jClient


def upsert_work_layer1(client: _Neo4jClient, work_data: dict, ...) -> str:
    """Upsert a work node with all layer-1 properties."""
    # Перенести из оригинала с адаптацией client.session() вместо self.session()
    ...
```

### Шаг 6 — Создать `storage/neo4j/facade.py`

**Публичный класс `Neo4jGraphStore`** — тонкий фасад, делегирующий в подмодули:

```python
# storage/neo4j/facade.py
"""Neo4jGraphStore — backward-compatible public facade."""
from __future__ import annotations

from science_graphrag.storage.neo4j.client import _Neo4jClient
from science_graphrag.storage.neo4j import schema as _schema
from science_graphrag.storage.neo4j import reads as _reads
from science_graphrag.storage.neo4j.writes import works as _works
from science_graphrag.storage.neo4j.writes import semantic as _semantic
from science_graphrag.storage.neo4j.writes import claims as _claims
from science_graphrag.storage.neo4j.writes import dedup as _dedup
from science_graphrag.storage.neo4j.writes import workspace as _workspace


class Neo4jGraphStore:
    """Facade over neo4j/ subpackage. Public API unchanged from v1."""

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._client = _Neo4jClient(uri, user, password)

    def close(self) -> None:
        self._client.close()

    def session(self):
        return self._client.session()

    def wipe_all(self) -> None:
        self._client.wipe_all()

    def ensure_schema(self) -> None:
        _schema.ensure_schema(self._client)

    # --- Reads ---
    def find_work_id_by_doi(self, doi: str):
        return _reads.find_work_id_by_doi(self._client, doi)

    def work_exists(self, work_id: str) -> bool:
        return _reads.work_exists(self._client, work_id)

    # ... все остальные методы аналогично делегируют ...

    # --- Writes: works ---
    def upsert_work_layer1(self, work_data, ...):
        return _works.upsert_work_layer1(self._client, work_data, ...)

    # ... и т.д. для каждого метода ...
```

**Ключевое правило:** каждый публичный метод `Neo4jGraphStore` **делегирует** — не содержит логики.

### Шаг 7 — `storage/neo4j/__init__.py`

```python
# storage/neo4j/__init__.py
"""Neo4j storage package. Public surface: Neo4jGraphStore."""
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore  # noqa: F401

__all__ = ["Neo4jGraphStore"]
```

### Шаг 8 — Обновить `storage/neo4j_store.py`

Сделать backward-compat shim:
```python
# storage/neo4j_store.py
# Backward-compat shim. Implementation moved to storage/neo4j/ package.
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore  # noqa: F401
```

### Шаг 9 — Обновить импорты (если нужно)

Проверь все файлы, которые импортируют из `neo4j_store`:
```bash
rg "from science_graphrag.storage.neo4j_store\|from science_graphrag.storage import neo4j_store" \
    science_graphrag/ tests/ --include="*.py" -l
```

Через shim в `neo4j_store.py` большинство импортов продолжат работать без изменений. Если где-то есть `from science_graphrag.storage.neo4j_store import Neo4jGraphStore` — через shim это работает. Проверь что нет прямых импортов private-методов.

### Шаг 10 — Тесты

```bash
# Backward compat:
.venv/bin/python -c "
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore as Facade
from science_graphrag.storage.neo4j import Neo4jGraphStore as Pkg
print('all Neo4jGraphStore paths ok')
"

# Smoke — app imports:
.venv/bin/python -c "from science_graphrag.api.main import app; print('app ok')"

# Запустить все тесты:
.venv/bin/pytest tests/ -x -q 2>&1 | tail -30
```

Создать `tests/storage/test_neo4j_facade.py`:
```python
"""Smoke tests for Neo4j storage facade after split."""

def test_neo4j_graph_store_import_paths():
    """All import paths must work after the split."""
    from science_graphrag.storage.neo4j_store import Neo4jGraphStore as A
    from science_graphrag.storage.neo4j.facade import Neo4jGraphStore as B
    from science_graphrag.storage.neo4j import Neo4jGraphStore as C
    assert A is B
    assert A is C


def test_neo4j_graph_store_has_all_public_methods():
    """Facade must expose the same public API as the original."""
    expected_methods = [
        "find_work_id_by_doi", "find_work_id_by_fingerprint", "find_work_id_by_arxiv",
        "work_exists", "work_has_incoming_cites", "upsert_work_layer1",
        "merge_cites", "merge_related_version", "upsert_minimal_work",
        "sync_work_semantic_layer", "merge_work_into_canonical",
        "merge_author_into_canonical", "upsert_claims_with_evidence",
        "workspace_create", "workspace_list", "workspace_get",
        "workspace_rename", "workspace_delete", "ensure_schema", "close",
        "fulltext_search_work_ids", "find_work_dedup_violations",
    ]
    from science_graphrag.storage.neo4j.facade import Neo4jGraphStore
    for method in expected_methods:
        assert hasattr(Neo4jGraphStore, method), f"Missing method: {method}"
```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `science_graphrag/storage/neo4j_store.py` → thin shim
- `science_graphrag/storage/neo4j/` (весь новый пакет)
- `tests/storage/test_neo4j_facade.py` (создать)

**НЕ трогать:**
- `science_graphrag/storage/qdrant_store.py` — не трогать
- `science_graphrag/storage/blobs.py` — не трогать
- `science_graphrag/api/` — не трогать (shim сохраняет compat)
- `science_graphrag/ingestion/` — не трогать (shim сохраняет compat)
- `science_graphrag/agent/` — скоуп Agent 2
- `ui/` — frontend вне скоупа
- Ни один файл в `storage/neo4j/` **не должен превышать 400 строк**

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Backward compat:
.venv/bin/python -c "
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.neo4j import Neo4jGraphStore as Pkg
assert Neo4jGraphStore is Pkg
print('backward compat ok')
"

.venv/bin/python -c "from science_graphrag.api.main import app; print('app ok')"

# Размер файлов:
echo "=== neo4j shim ==="
wc -l science_graphrag/storage/neo4j_store.py   # должен быть ≤ 5
echo "=== neo4j package ==="
for f in science_graphrag/storage/neo4j/*.py science_graphrag/storage/neo4j/writes/*.py; do
    wc -l "$f"
done
# каждый ≤ 400

# Форматирование:
.venv/bin/isort science_graphrag/storage/neo4j/
.venv/bin/black science_graphrag/storage/neo4j/
.venv/bin/pylint science_graphrag/storage/neo4j/ --fail-under=7.0

# Все тесты:
.venv/bin/pytest tests/ -x -q 2>&1 | tail -30
```

### Backlog

В `docs/backlog/refactor-backend.md` пометить `[OPEN] Split storage/neo4j_store.py...` как:
```
### [DONE] Split `storage/neo4j_store.py` (1022 lines) by domain or layer
- **Note (done):** 2026-04-25 — разнесено на storage/neo4j/{client,schema,reads,facade}.py +
  storage/neo4j/writes/{works,semantic,claims,dedup,workspace}.py; публичный Neo4jGraphStore
  остаётся фасадом; backward-compat shim в storage/neo4j_store.py;
  Wave T (entity dedup) добавит storage/neo4j/writes/{authors,institutions,...}.py без god-файла.
```

---

## Agent 4 — H-AskPanelSplit (frontend)

**Задача:** Разнести `ui/src/components/work/AskPanel.jsx` (841 строка) на `useAskSubmit`, `AskSessionControls`, `AskAnswerPanel` + тонкий composition-shell.

### Контекст

Ты — агент фронтенд-рефакторинга. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. UI: `ui/`. После любых правок — `npm run lint` из `ui/`. Venv backend не нужен.

**Прочитай файлы перед началом:**
```bash
wc -l ui/src/components/work/AskPanel.jsx
# Все функции/хуки:
grep -n "const use\|function \|export\|useState\|useEffect\|useCallback" \
    ui/src/components/work/AskPanel.jsx | head -50
# Структура рендера:
grep -n "return\|<AgentToolTrace\|<Box\|<Button\|<TextField\|<Alert\|session" \
    ui/src/components/work/AskPanel.jsx | head -40
# Что уже существует рядом:
ls ui/src/components/work/
ls ui/src/hooks/
# Сервисы агента:
ls ui/src/services/
grep -rn "agent\|agentQuery\|useAgent" ui/src/services/ | head -20
```

**Синергия:** Wave Y3 добавит `/v2/agent/query` SSE. После split — `useAskSubmit` будет **единственной** точкой переключения REST→SSE. AskPanel не нужно будет трогать вообще.

### Что сделать

**1. Создать `ui/src/components/work/useAskSubmit.js`** — submit-оркестрация:

```javascript
/**
 * Orchestrates Ask submit flow: builds request, calls API, updates session state.
 * 
 * @param {object} params
 * @param {string} params.workId
 * @param {string|null} params.workspaceId
 * @param {string} params.agentRuntime - 'retrieval_v1' | 'langgraph_supervisor_v1'
 * @param {function} params.onResult - callback(agentResult)
 * @param {function} params.onError - callback(errorMessage)
 * @returns {{ submit, isLoading, abortRef }}
 */
export function useAskSubmit({ workId, workspaceId, agentRuntime, onResult, onError }) {
  // Вынести из AskPanel:
  // - логику вызова API (postAgentQuery / ask-endpoint)
  // - useState loading
  // - useCallback submit
  // - обработку ошибок через formatResearchApiError
  // - abortController ref если есть
  ...
}
```

Что должно войти:
- `useState` для `isLoading`
- `useCallback` для `submit(question, sessionId)`
- Вызов API функции (из `services/researchApi.js` или отдельного сервис-модуля)
- Обработка ошибок → `onError`
- Передача результата → `onResult`
- **Без JSX** — только логика

Цель: ≤ 150 строк.

**2. Создать `ui/src/components/work/AskSessionControls.jsx`** — поле ввода + кнопки сессии:

```jsx
/**
 * Input field, submit button, new-session button.
 * Controlled component: question text is managed by parent (AskPanel).
 * 
 * @param {{ question, onQuestionChange, onSubmit, onNewSession, isLoading, disabled }} props
 */
export function AskSessionControls({ question, onQuestionChange, onSubmit, onNewSession, isLoading, disabled }) {
  // Перенести из AskPanel:
  // - <TextField> для вопроса
  // - кнопку Submit / отправки
  // - кнопку "Новая сессия" (New Session) если есть
  // - onKeyDown (Enter → submit)
  // Использовать CursorButton / CursorPrimaryButton согласно дизайн-канону проекта
}
```

Цель: ≤ 150 строк.

**3. Создать `ui/src/components/work/AskAnswerPanel.jsx`** — отображение результата:

```jsx
/**
 * Renders the agent answer, citations, and tool trace.
 * Stateless: all data via props.
 * 
 * @param {{ answer, citations, toolTrace, agentRuntime, isLoading }} props
 */
export function AskAnswerPanel({ answer, citations, toolTrace, agentRuntime, isLoading }) {
  // Перенести из AskPanel:
  // - отображение answer (текст ответа)
  // - список citations
  // - <AgentToolTrace toolTrace={...} /> — уже существующий компонент, только импортируй
  // - skeleton / loading state
  // - Alert для ошибок answer (если есть)
}
```

Что должно войти:
- Рендер ответа агента
- Рендер цитат (список)
- `<AgentToolTrace>` — только импортируй, не переписывай
- Скелетон при loading
- **Без submit-логики и без state управления сессией**

Цель: ≤ 200 строк.

**4. Переписать `AskPanel.jsx` как тонкий composition-shell:**

```jsx
/**
 * Ask panel: composition shell for agent Q&A.
 * Manages session state, delegates rendering to sub-components.
 */
export function AskPanel({ workId, workspaceId }) {
  // Session state (из askSessionState.js — уже существует):
  const { sessions, activeSession, createSession, clearSession } = useAskSessionState(workId);

  // Submit orchestration:
  const [answer, setAnswer] = useState(null);
  const [error, setError] = useState(null);
  const [question, setQuestion] = useState("");

  const { submit, isLoading } = useAskSubmit({
    workId,
    workspaceId,
    agentRuntime: activeSession?.agentRuntime,
    onResult: setAnswer,
    onError: setError,
  });

  return (
    <Box>
      {error && <Alert severity="error">{formatResearchApiError(error)}</Alert>}
      <AskSessionControls
        question={question}
        onQuestionChange={setQuestion}
        onSubmit={() => submit(question, activeSession?.id)}
        onNewSession={() => { createSession(); setAnswer(null); setError(null); }}
        isLoading={isLoading}
      />
      {answer && (
        <AskAnswerPanel
          answer={answer.answer}
          citations={answer.citations}
          toolTrace={answer.tool_trace}
          agentRuntime={activeSession?.agentRuntime}
          isLoading={isLoading}
        />
      )}
    </Box>
  );
}
```

**Важно:** сохрани все существующие props/callbacks `AskPanel` — он используется в `WorkerWorkBody.jsx` или другом родительском компоненте. Прочитай где именно `AskPanel` используется:
```bash
rg "AskPanel\|AskPanel" ui/src/ --include="*.jsx" --include="*.js" -l
```

Адаптируй composition-shell под реальный существующий state (не переопределяй session-логику, которая уже в `askSessionState.js`).

Цель: `AskPanel.jsx` ≤ 280 строк.

**5. Проверить импорты:**
```bash
# AgentToolTrace.jsx — не трогать (только импортировать в AskAnswerPanel):
grep -n "export" ui/src/components/work/AgentToolTrace.jsx | head -5
# askSessionState.js — не трогать (только использовать):
grep -n "export" ui/src/components/work/askSessionState.js | head -10
# Сервисы:
grep -rn "postAgentQuery\|askAgent\|agent" ui/src/services/ | head -10
```

**6. ESLint + тесты:**
```bash
cd ui
npm run lint
npm run test -- --passWithNoTests
```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `ui/src/components/work/AskPanel.jsx` (переписать как shell)
- `ui/src/components/work/useAskSubmit.js` (создать)
- `ui/src/components/work/AskSessionControls.jsx` (создать)
- `ui/src/components/work/AskAnswerPanel.jsx` (создать)

**НЕ трогать:**
- `ui/src/components/work/AgentToolTrace.jsx` — только импортировать
- `ui/src/components/work/askSessionState.js` — только использовать
- `ui/src/components/work/askHistoryState.js` — не трогать
- `ui/src/components/work/HypothesisPanel.jsx` — не трогать
- `ui/src/hooks/` — не создавать новые хуки там (хук submit в `components/work/`)
- `ui/src/services/` — не трогать API-клиент
- `ui/src/components/graph/` — не трогать (скоуп Раунда 2, done)
- Backend — вне скоупа
- Ни один новый файл **не должен превышать 300 строк**

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui

npm run lint
npm run test -- --passWithNoTests

# Размер файлов:
wc -l src/components/work/AskPanel.jsx           # ≤ 280
wc -l src/components/work/useAskSubmit.js        # ≤ 150
wc -l src/components/work/AskSessionControls.jsx # ≤ 150
wc -l src/components/work/AskAnswerPanel.jsx     # ≤ 200

# AskPanel экспортируется и импортируется корректно:
grep -n "export.*AskPanel" src/components/work/AskPanel.jsx
# Нет JSX в useAskSubmit:
grep -n "return (<\|<Box\|<div\|<Stack" src/components/work/useAskSubmit.js && \
    echo "WARNING: JSX in hook" || echo "ok: no JSX"
# AgentToolTrace используется в AskAnswerPanel:
grep -n "AgentToolTrace" src/components/work/AskAnswerPanel.jsx
```

### Backlog

В `docs/backlog/refactor-frontend.md` пометить `[OPEN] AskPanel decomposition after Wave R agent mode` как:
```
### [DONE] AskPanel decomposition after Wave R agent mode
- **Note (done):** 2026-04-25 — разнесено на useAskSubmit.js (submit orchestration),
  AskSessionControls.jsx (input + buttons), AskAnswerPanel.jsx (answer + citations + trace);
  AskPanel.jsx = composition shell ≤280 строк; Wave Y3 SSE переключается только в useAskSubmit.
```

---

## Review Agent — Финальная проверка Round 3

**Задача:** Проверить, что все 4 задачи Round 3 выполнены корректно, backward-compat не сломан, и Round 4 (Wave Y3 + GR2 backend + G-RetrievalCore + H-AskV2SSE) можно запускать без блокировок.

### Контекст

Ты — агент code review. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`.
Venv: `.venv/`. UI: `ui/`.

**Round 3 выполнил следующее (должно быть проверено):**
- **Agent 1 Wave W:** `science_graphrag/worker/` пакет с `ingest_document_actor`; `IngestEventBus` на Redis pub/sub в `api/ingest/dispatcher.py`; `threading.Thread` удалён; `docker-compose.yml` содержит `redis` + `worker`; ADR + spec созданы.
- **Agent 2 Wave Y2 + X2:** `agent/graph/{state,supervisor,tracing}.py` + `agent/llm/chat.py`; 6 tools на `langchain_core.tools`; `runtime_legacy.py` с детерминированным fallback; `chain_span("agent.query")` + `traced_tool_span` в `idea_search`; v1 endpoint без изменений.
- **Agent 3 G-Neo4jSplit:** `storage/neo4j_store.py` → пакет `storage/neo4j/{client,schema,reads,facade}.py` + `storage/neo4j/writes/{works,semantic,claims,dedup,workspace}.py`; shim в `neo4j_store.py`.
- **Agent 4 H-AskPanelSplit:** `AskPanel.jsx` → shell + `useAskSubmit.js`, `AskSessionControls.jsx`, `AskAnswerPanel.jsx`.

### Чеклист проверки

Пройди **все** пункты последовательно. По каждому выведи: ✅ OK, ⚠️ Частично, ❌ Провалено.

#### 1. Структура: файлы созданы

```bash
# Agent 1 — Worker:
ls science_graphrag/worker/__init__.py
ls science_graphrag/worker/actor.py
ls docs/specs/ingest-worker-v1.md
ls docs/adr/ | grep "ingest-worker-redis"

# Agent 2 — LangGraph:
ls science_graphrag/agent/graph/__init__.py
ls science_graphrag/agent/graph/state.py
ls science_graphrag/agent/graph/supervisor.py
ls science_graphrag/agent/graph/tracing.py
ls science_graphrag/agent/llm/__init__.py
ls science_graphrag/agent/llm/chat.py
ls science_graphrag/agent/runtime_legacy.py

# Agent 3 — Neo4jSplit:
ls science_graphrag/storage/neo4j/__init__.py
ls science_graphrag/storage/neo4j/client.py
ls science_graphrag/storage/neo4j/schema.py
ls science_graphrag/storage/neo4j/reads.py
ls science_graphrag/storage/neo4j/facade.py
ls science_graphrag/storage/neo4j/writes/__init__.py
ls science_graphrag/storage/neo4j/writes/works.py
ls science_graphrag/storage/neo4j/writes/semantic.py
ls science_graphrag/storage/neo4j/writes/claims.py
ls science_graphrag/storage/neo4j/writes/dedup.py
ls science_graphrag/storage/neo4j/writes/workspace.py

# Agent 4 — AskPanelSplit:
ls ui/src/components/work/useAskSubmit.js
ls ui/src/components/work/AskSessionControls.jsx
ls ui/src/components/work/AskAnswerPanel.jsx
```

#### 2. Backward-compat импорты

```bash
.venv/bin/python -c "
from science_graphrag.storage.neo4j_store import Neo4jGraphStore
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore as Facade
from science_graphrag.storage.neo4j import Neo4jGraphStore as Pkg
assert Neo4jGraphStore is Facade
assert Neo4jGraphStore is Pkg
print('Neo4jGraphStore paths ok')
"

.venv/bin/python -c "
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.agent.tools import build_tool_registry
print('agent graph modules ok')
"

.venv/bin/python -c "
from science_graphrag.worker.actor import ingest_document_actor
print('dramatiq actor ok:', ingest_document_actor.actor_name)
"

.venv/bin/python -c "
from science_graphrag.api.ingest.dispatcher import IngestEventBus
print('IngestEventBus ok')
"

.venv/bin/python -c "
from science_graphrag.api.main import app
print('main app ok')
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f'Total routes: {len(routes)}')
"
```

#### 3. Wave W: нет threading.Thread в ingest

```bash
# threading.Thread должен быть удалён из api/ingest/:
rg "threading\.Thread" science_graphrag/api/ingest/ && \
    echo "FOUND Thread — check" || echo "ok: no Thread in api/ingest/"

# IngestEventBus должен использовать redis:
grep -n "redis\|aioredis\|from_url" science_graphrag/api/ingest/dispatcher.py | head -5 && \
    echo "ok: Redis-based bus" || echo "WARNING: might still be asyncio.Queue"

# docker-compose имеет redis и worker:
grep -c "redis:\|worker:" docker-compose.yml && echo "services found" || echo "MISSING"

# Actor зарегистрирован как dramatiq actor:
.venv/bin/python -c "
import dramatiq
from science_graphrag.worker.actor import ingest_document_actor
assert hasattr(ingest_document_actor, 'actor_name'), 'not a dramatiq actor'
print('dramatiq actor name:', ingest_document_actor.actor_name)
"
```

#### 4. Wave Y2: LangGraph реализован, v1 контракт сохранён

```bash
# LangGraph StateGraph компилируется:
.venv/bin/python -c "
from unittest.mock import MagicMock
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
print('build_retrieval_graph importable')
"

# runtime.py — тонкая обёртка, не god-файл:
wc -l science_graphrag/agent/runtime.py
# Должен быть ≤ 150 строк (facade)

# Legacy fallback существует:
.venv/bin/python -c "
from science_graphrag.agent.runtime_legacy import LegacyRetrievalAgent
print('legacy agent ok')
"

# build_tool_registry возвращает list:
.venv/bin/python -c "
from unittest.mock import MagicMock
from science_graphrag.agent.tools import build_tool_registry
tools = build_tool_registry(MagicMock())
print(f'tool registry: {len(tools)} tools')
names = [t.name for t in tools]
print('tools:', names)
assert 'cypher_query' in names
assert 'idea_search' in names
print('ok')
"

# v1 endpoint работает:
.venv/bin/python -c "from science_graphrag.api.agent import router; print('agent router ok')"
```

#### 5. Wave X2: Phoenix observability в agent

```bash
# chain_span("agent.query") используется в runtime.py:
grep -n "chain_span.*agent.query\|agent\.query" science_graphrag/agent/runtime.py | head -5

# traced_tool_span в idea_search:
grep -n "traced_tool_span\|traced_tool" science_graphrag/agent/tools/idea_search.py | head -5

# cypher_safety.py не изменялся:
git diff science_graphrag/agent/cypher_safety.py 2>/dev/null | head -10 || \
    echo "git diff not available — check manually"
```

#### 6. G-Neo4jSplit: разнесено корректно

```bash
# Shim — ≤ 5 строк:
wc -l science_graphrag/storage/neo4j_store.py

# Facade делегирует (нет бизнес-логики в методах):
grep -n "def \|return \|with client" science_graphrag/storage/neo4j/facade.py | head -30

# Размер файлов (каждый ≤ 400):
echo "=== neo4j package ===" && \
for f in science_graphrag/storage/neo4j/*.py science_graphrag/storage/neo4j/writes/*.py; do
    wc -l "$f"
done

# Neo4jGraphStore имеет все публичные методы:
.venv/bin/python -c "
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore
methods = [m for m in dir(Neo4jGraphStore) if not m.startswith('_')]
print('public methods:', methods)
required = ['find_work_id_by_doi', 'upsert_work_layer1', 'workspace_create', 'ensure_schema']
for m in required:
    assert m in methods, f'Missing: {m}'
print('all required methods present ok')
"
```

#### 7. H-AskPanelSplit: корректная декомпозиция

```bash
# Размер файлов:
wc -l ui/src/components/work/AskPanel.jsx           # ≤ 280
wc -l ui/src/components/work/useAskSubmit.js        # ≤ 150
wc -l ui/src/components/work/AskSessionControls.jsx # ≤ 150
wc -l ui/src/components/work/AskAnswerPanel.jsx     # ≤ 200

# AskPanel содержит новые компоненты:
grep "useAskSubmit\|AskSessionControls\|AskAnswerPanel" ui/src/components/work/AskPanel.jsx | head -5

# Нет JSX в хуке:
grep -n "<[A-Z]\|return (<\|<div\|<Box" ui/src/components/work/useAskSubmit.js | head -3 && \
    echo "WARNING: JSX in hook" || echo "ok: no JSX in useAskSubmit"

# AgentToolTrace используется в AskAnswerPanel:
grep "AgentToolTrace" ui/src/components/work/AskAnswerPanel.jsx | head -3
```

#### 8. Quality gates: Python

```bash
# isort + black:
.venv/bin/isort --check \
    science_graphrag/worker/ \
    science_graphrag/agent/graph/ \
    science_graphrag/agent/llm/ \
    science_graphrag/agent/tools/ \
    science_graphrag/storage/neo4j/ \
    science_graphrag/api/ingest/dispatcher.py

.venv/bin/black --check \
    science_graphrag/worker/ \
    science_graphrag/agent/graph/ \
    science_graphrag/agent/llm/ \
    science_graphrag/storage/neo4j/ \
    science_graphrag/api/ingest/dispatcher.py

# pylint:
.venv/bin/pylint \
    science_graphrag/worker/ \
    science_graphrag/agent/graph/ \
    science_graphrag/agent/llm/ \
    science_graphrag/storage/neo4j/ \
    --fail-under=7.0

# Все тесты:
.venv/bin/pytest tests/ -x -q 2>&1 | tail -30
```

#### 9. Quality gates: Frontend

```bash
cd ui && npm run lint 2>&1 | tail -20
npm run test -- --passWithNoTests 2>&1 | tail -10
```

#### 10. Backlog hygiene

```bash
# Wave W:
grep "\[DONE\].*Wave W\|ingest-worker-redis\|Dramatiq" \
    docs/backlog/refactor-backend.md | head -3

# Wave Y2:
grep "\[DONE\].*Y2\|LangGraph.*single\|build_tool_registry" \
    docs/backlog/refactor-backend.md | head -3

# G-Neo4jSplit:
grep "\[DONE\].*neo4j_store\|Neo4jSplit" \
    docs/backlog/refactor-backend.md | head -3

# H-AskPanelSplit:
grep "\[DONE\].*AskPanel\|useAskSubmit" \
    docs/backlog/refactor-frontend.md | head -3
```

#### 11. Конфликты в `api/main.py` и `api/agent.py`

```bash
# api/main.py — nет дублей include_router:
grep "include_router\|ingest\|workspace_graph\|works" science_graphrag/api/main.py | head -20

# api/agent.py — нет per-request store init:
grep -n "Neo4jGraphStore(\|QdrantChunkStore(" science_graphrag/api/agent.py | grep -v "import\|#" && \
    echo "FOUND per-request store init — should use get_stores" || echo "ok"
```

#### 12. Готовность к Round 4

```bash
# Round 4 требует:
# 1. agent/graph/ готов (для Wave Y3):
.venv/bin/python -c "from science_graphrag.agent.graph.supervisor import build_retrieval_graph; print('Y3 ready')"

# 2. api/works/graph_neighborhood.py готов (для Wave GR2):
.venv/bin/python -c "from science_graphrag.api.works.graph_neighborhood import *; print('GR2 ready')" 2>&1

# 3. api/workspace_graph/projection.py готов (для Wave GR2):
.venv/bin/python -c "from science_graphrag.api.workspace_graph.projection import *; print('GR2 proj ready')" 2>&1

# 4. useAskSubmit.js готов (для H-AskV2SSE):
ls ui/src/components/work/useAskSubmit.js && echo "AskV2SSE ready"
```

#### 13. Smoke: полная загрузка приложения

```bash
.venv/bin/python -c "
from science_graphrag.api.main import app
from science_graphrag.api.deps import get_stores, StoreRegistry
from science_graphrag.storage.neo4j.facade import Neo4jGraphStore
from science_graphrag.agent.graph.supervisor import build_retrieval_graph
from science_graphrag.worker.actor import ingest_document_actor
print('All Round 3 imports ok')
routes = [r.path for r in app.routes if hasattr(r, 'path')]
print(f'Routes: {len(routes)}')
"
```

### Что делать с найденными проблемами

После прогона всех проверок:

1. **Если все ✅** — написать:
   «Round 3 complete. Ready for Round 4 (Wave Y3 `/v2/agent/query` SSE + Wave GR2 display_type/node_kind + G-RetrievalCore + H-AskV2SSE).»
   Указать метрику: сколько строк распилено суммарно, количество новых модулей, тесты зелёные.

2. **Если есть ⚠️** — описать конкретно что частично выполнено, какие шаги остались.
   Приоритет: проблемы в `neo4j_store.py` (импортируется всем стеком) и в `agent/runtime.py` (должен остаться backward-compat) — критичные; проблемы в `worker/` — менее критичны для других агентов.

3. **Если есть ❌** — описать пункт провала, вывод команды, возможную причину.
   Не пытаться починить самостоятельно — только репортировать.

### Не входит в scope Review Agent

- Не вносить изменения в код — только читать и запускать команды.
- Не запускать интеграционные тесты с реальными БД (Neo4j, Qdrant, Postgres, Redis).
- Не проверять визуальный рендеринг frontend — только lint/test/import.
- Не оценивать качество кода субъективно — только факты из checklist.

---

## Примечания по конфликтам в Round 3

### Файлы, которые несколько агентов могут читать, но не трогать одновременно

- `science_graphrag/api/main.py` — Agent 1 может добавить `redis_url` в config (не в main.py); Agent 2 не трогает main.py. Риска нет.
- `science_graphrag/api/agent.py` — Agent 2 минимально обновляет вызов `build_agent`. Agent 1 не трогает. Риска нет.
- `science_graphrag/config.py` — Agent 1 добавляет `redis_url`. Agent 2 читает существующие поля. Риска нет.
- `tests/test_api_smoke.py` — никто не должен модифицировать (только запускать).

### Порядок при следующем раунде (Round 4)

Round 4 требует:
- **Agent 1 (Wave W)** ✅ — `api/ingest/dispatcher.py` готов к использованию Redis bus.
- **Agent 2 (Wave Y2 + X2)** ✅ — `agent/graph/supervisor.py` готов; Wave Y3 добавит `/v2/agent/query` endpoint.
- **Agent 3 (G-Neo4jSplit)** ✅ — `storage/neo4j/` готов; Wave T (entity dedup) добавит `writes/{authors,institutions,...}`.
- **Agent 4 (H-AskPanelSplit)** ✅ — `useAskSubmit.js` готов; H-AskV2SSE подключит SSE именно там.
