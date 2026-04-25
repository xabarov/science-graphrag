# Round 2 — Agent Prompts («StoreFactory + WorkspaceGraph/Works split + GraphPanel split»)

> Дата: 2026-04-25
> Источник плана: `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §7 «Раунд 2»
> Предусловие: Раунд 1 + Раунд 1.5 выполнены ✅ (G-IngestSlim, G-PipelineFacade, G-PhoenixSplit, spans-split, i18n-fixes, Cursor-buttons-in-dedup, Wave Y1)
> Порядок запуска: **Agent 1 → затем Agents 2 + 3 + 4 параллельно** (Agent 1 создаёт `api/deps.py`, на который опираются Agent 2 и 3).

---

## Agent 1 — G-StoreFactory (запустить ПЕРВЫМ, ~1–2 ч)

**Задача:** Ввести централизованный `StoreRegistry` и FastAPI-зависимость `get_stores()` в `science_graphrag/api/deps.py`. Подключить DI во все API-роутеры **кроме** `workspace_graph.py` и `works.py` (их скоуп — Agent 2 и Agent 3).

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Проблема:** `Neo4jGraphStore(settings.neo4j_uri, ...)` поднимается вручную в десятке мест:
`api/retrieval.py`, `api/agent.py`, `api/idea_assist.py`, `api/workspaces.py`,
`api/workspace_dedup.py`, `api/ingest/dispatcher.py`, `ingestion/pipeline.py`, `cli/main.py`.
Аналогично для `QdrantChunkStore` и `BlobStore`. Каждый HTTP-запрос к agent-эндпоинтам
пересоздаёт stores — это зафиксировано как pain в `phoenix-tracing-coverage`.

Дополнительно: `api/workspace_graph.py` использует `GraphDatabase.driver(...)` напрямую,
минуя `Neo4jGraphStore`. Это будет устранено в Agent 2, но здесь нужно создать
инфраструктуру (`StoreRegistry`), которую Agent 2 потом использует.

**Важно:** Agent 2 (WorkspaceGraphSplit) и Agent 3 (WorksSplit) запустятся после тебя и будут
импортировать `get_stores` из созданного тобой `api/deps.py`. Создай этот файл правильно
с первой попытки — он является общей зависимостью двух других агентов.

### Что сделать

1. **Прочитать** актуальное состояние ключевых файлов:
   ```bash
   # Понять паттерны store-init в текущем коде:
   rg "Neo4jGraphStore\|QdrantChunkStore\|BlobStore\|GraphDatabase\.driver" \
       science_graphrag/api/ --include="*.py" -n | head -60
   # Понять текущий lifespan в main.py:
   cat science_graphrag/api/main.py
   # Посмотреть существующую структуру:
   ls science_graphrag/api/
   ls science_graphrag/storage/
   ```

2. **Создать `science_graphrag/api/deps.py`** — централизованный DI-модуль:

   ```python
   """FastAPI dependency-injection layer for shared infrastructure stores.

   All API routes and background workers should obtain stores exclusively
   through get_stores() or the StoreRegistry singleton — never by calling
   Neo4jGraphStore/QdrantChunkStore constructors directly in handler scope.
   """
   from __future__ import annotations

   from dataclasses import dataclass, field
   from typing import Optional

   from fastapi import Request

   from science_graphrag.config import Settings
   # Импорты store-классов: скорректируй пути по актуальной структуре
   from science_graphrag.storage.neo4j_store import Neo4jGraphStore
   from science_graphrag.storage.qdrant_store import QdrantChunkStore  # уточни имя
   from science_graphrag.storage.blob_store import BlobStore            # уточни имя


   @dataclass
   class StoreRegistry:
       """Singleton façade holding all infrastructure store instances.

       Lifetime: created once in FastAPI lifespan, closed on shutdown.
       Tests can substitute with a fixture via app.dependency_overrides.
       """
       neo4j: Neo4jGraphStore
       qdrant_chunks: QdrantChunkStore
       # Добавь остальные Qdrant-коллекции (works, claims) если они есть:
       # qdrant_works: Optional[QdrantWorksStore] = None
       # qdrant_claims: Optional[QdrantClaimsStore] = None
       blobs: Optional[BlobStore] = None

       def close(self) -> None:
           """Release connections. Called from lifespan on shutdown."""
           if hasattr(self.neo4j, "close"):
               self.neo4j.close()
           if hasattr(self.qdrant_chunks, "close"):
               self.qdrant_chunks.close()


   _registry: Optional[StoreRegistry] = None


   def init_store_registry(settings: Settings) -> StoreRegistry:
       """Create and cache the global StoreRegistry. Called from app lifespan."""
       global _registry
       _registry = StoreRegistry(
           neo4j=Neo4jGraphStore(settings.neo4j_uri, settings.neo4j_user, settings.neo4j_password),
           qdrant_chunks=QdrantChunkStore(settings.qdrant_url, settings.qdrant_api_key),
           # blobs=BlobStore(...) — если BlobStore существует
       )
       return _registry


   def close_store_registry() -> None:
       """Close all store connections. Called from app lifespan on shutdown."""
       global _registry
       if _registry is not None:
           _registry.close()
           _registry = None


   def get_stores(request: Request) -> StoreRegistry:
       """FastAPI dependency: returns the application-level StoreRegistry.

       Usage in route:
           @router.get("/...")
           async def my_handler(stores: StoreRegistry = Depends(get_stores)):
               result = await stores.neo4j.get_work(work_id)
       """
       registry = getattr(request.app.state, "stores", None)
       if registry is None:
           raise RuntimeError(
               "StoreRegistry not initialized. "
               "Ensure init_store_registry() is called in FastAPI lifespan."
           )
       return registry
   ```

   **Важные детали реализации:**
   - Уточни реальные имена классов и пути импортов, прочитав файлы `storage/`.
   - Если `BlobStore` или `QdrantWorksStore` не существуют — закомментируй строки с TODO.
   - Конструктор `Neo4jGraphStore` и `QdrantChunkStore` — возьми из существующего кода
     (grep по актуальным вызовам в `api/retrieval.py`, `api/agent.py`).

3. **Обновить `science_graphrag/api/main.py`** — вызов `init_store_registry` в lifespan:

   В существующем lifespan-менеджере (или `startup` event, в зависимости от текущей реализации)
   добавить **в конец `startup`-блока**:
   ```python
   from science_graphrag.api.deps import init_store_registry, close_store_registry

   # В lifespan startup:
   app.state.stores = init_store_registry(settings)

   # В lifespan shutdown:
   close_store_registry()
   ```
   Найди существующий startup/lifespan код и интегрируй в него точечно, не переписывая всё.

4. **Обновить следующие файлы** (заменить per-request store init на `Depends(get_stores)`):

   Список файлов для обновления (НЕ трогай `workspace_graph.py` и `works.py` — это скоупы Agent 2 и Agent 3):

   - **`science_graphrag/api/retrieval.py`** — найди все места `Neo4jGraphStore(...)` и
     `QdrantChunkStore(...)` внутри функций-хендлеров. Замени на:
     ```python
     from fastapi import Depends
     from science_graphrag.api.deps import StoreRegistry, get_stores

     @router.post("/query")
     async def answer_query(
         body: QueryRequest,
         stores: StoreRegistry = Depends(get_stores),
     ):
         result = await do_retrieval(stores.neo4j, stores.qdrant_chunks, body)
         ...
     ```

   - **`science_graphrag/api/agent.py`** — аналогично. Агент-хендлер пересоздаёт stores
     per-request — устранить.

   - **`science_graphrag/api/idea_assist.py`** — аналогично.

   - **`science_graphrag/api/workspaces.py`** — аналогично.

   - **`science_graphrag/api/workspace_dedup.py`** — аналогично (если есть store init).

   Для каждого файла: прочитай его целиком, найди store-инициализации внутри хендлеров,
   замени на `Depends(get_stores)` в сигнатуре и `stores.neo4j` / `stores.qdrant_chunks`
   в теле. Если файл уже использует dependency injection — не переписывай, только убедись
   что паттерн совместим.

5. **Тесты:**

   ```bash
   # Убедиться что app импортируется без ошибок:
   .venv/bin/python -c "from science_graphrag.api.main import app; print('app ok')"
   .venv/bin/python -c "from science_graphrag.api.deps import get_stores, StoreRegistry; print('deps ok')"
   ```

   Создать `tests/api/test_deps.py`:
   - `test_get_stores_raises_without_init` — без `app.state.stores` поднимает `RuntimeError`
   - `test_store_registry_fields` — `StoreRegistry` содержит ожидаемые поля (`neo4j`, `qdrant_chunks`)
   - `test_init_close_cycle` — вызов `init_store_registry` + `close_store_registry` с mock settings
     не бросает исключений

   Запустить smoke тесты:
   ```bash
   .venv/bin/pytest tests/test_api_smoke.py -x -v
   .venv/bin/pytest tests/api/ -x -v
   ```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `science_graphrag/api/deps.py` (создать)
- `science_graphrag/api/main.py` (только lifespan — добавить `init_store_registry`)
- `science_graphrag/api/retrieval.py`
- `science_graphrag/api/agent.py`
- `science_graphrag/api/idea_assist.py`
- `science_graphrag/api/workspaces.py`
- `science_graphrag/api/workspace_dedup.py`
- `tests/api/test_deps.py` (создать)

**НЕ трогать:**
- `science_graphrag/api/workspace_graph.py` — скоуп Agent 2
- `science_graphrag/api/works.py` — скоуп Agent 3
- `science_graphrag/storage/neo4j_store.py` — не рефакторить
- `science_graphrag/ingestion/` — не трогать
- `science_graphrag/cli/` — не трогать (CLI-интеграция позже)
- `ui/` — frontend вне скоупа

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/api/deps.py science_graphrag/api/main.py \
    science_graphrag/api/retrieval.py science_graphrag/api/agent.py \
    science_graphrag/api/idea_assist.py science_graphrag/api/workspaces.py
.venv/bin/black science_graphrag/api/deps.py science_graphrag/api/main.py \
    science_graphrag/api/retrieval.py science_graphrag/api/agent.py \
    science_graphrag/api/idea_assist.py science_graphrag/api/workspaces.py
.venv/bin/pylint science_graphrag/api/deps.py science_graphrag/api/retrieval.py \
    science_graphrag/api/agent.py --fail-under=7.0
.venv/bin/python -c "from science_graphrag.api.main import app; print('app imports ok')"
.venv/bin/python -c "from science_graphrag.api.deps import get_stores, StoreRegistry; print('deps ok')"
.venv/bin/pytest tests/test_api_smoke.py tests/api/ -x -v 2>&1 | tail -30
```

### Backlog

В `docs/backlog/refactor-backend.md` пометить запись `[OPEN] Unified Bolt access factory...` как:
```
### [DONE] Unified Bolt access factory + agent/idea-assist composition root
- **Note (done):** 2026-04-25 — создан api/deps.py: StoreRegistry + get_stores() + init/close;
  lifespan в main.py вызывает init_store_registry; api/{retrieval,agent,idea_assist,workspaces,
  workspace_dedup}.py переключены на Depends(get_stores); api/{workspace_graph,works}.py —
  в скоупе Agent 2/3 (Round 2).
```

---

## Agent 2 — G-WorkspaceGraphSplit (после Agent 1)

**Задача:** Разнести `science_graphrag/api/workspace_graph.py` (≈1214 строк) в пакет
`science_graphrag/api/workspace_graph/` с тремя модулями, убрать прямой `GraphDatabase.driver`.

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предусловие:** Agent 1 (G-StoreFactory) создал `science_graphrag/api/deps.py` с
`StoreRegistry` и `get_stores()`. Убедись что файл существует перед началом:
```bash
ls science_graphrag/api/deps.py && \
    .venv/bin/python -c "from science_graphrag.api.deps import get_stores; print('deps ok')"
```
Если файл отсутствует — не начинай работу, сообщи об ошибке.

**Проблема `workspace_graph.py`:**
1. Файл ≈1214 строк совмещает несколько независимых ответственностей.
2. Прямой вызов `GraphDatabase.driver(neo4j_uri, auth=...)` — дублирует Neo4jGraphStore.
3. Cypher-запросы для neighbor projection/stats смешаны с HTTP-слоем.
4. Логика membership/cites аннотаций смешана с маппингом DTO.
5. Разблокирует **Wave GR2/GR3/GR4**: каждая волна будет точечно менять отдельный модуль.

**Прочитай файл целиком** перед началом:
```bash
cat science_graphrag/api/workspace_graph.py | head -100   # imports + init
wc -l science_graphrag/api/workspace_graph.py
rg "GraphDatabase\.driver\|Neo4jGraphStore\|neo4j" \
    science_graphrag/api/workspace_graph.py -n | head -30
rg "def " science_graphrag/api/workspace_graph.py -n   # все функции
```

### Что сделать

1. **Создать пакет `science_graphrag/api/workspace_graph/`** с четырьмя файлами:

   #### `api/workspace_graph/__init__.py`
   Тонкий re-export — только `router` для использования в `main.py`:
   ```python
   from science_graphrag.api.workspace_graph.router import router  # noqa: F401
   ```

   #### `api/workspace_graph/cypher.py`
   Все Cypher-строки и функции, которые строят/исполняют запросы к Neo4j:
   - Константы или функции-шаблоны Cypher (MATCH-запросы, projection queries, neighbor queries)
   - Функция `execute_workspace_projection(driver_or_store, workspace_id, ...)` → raw graph data
   - Функция `execute_workspace_neighbors(driver_or_store, work_id, ...)` → raw neighbors
   - Функция `execute_workspace_stats(driver_or_store, workspace_id)` → stats dict
   - **Убрать прямой `GraphDatabase.driver` отсюда**: вместо этого принимать
     `neo4j_store: Neo4jGraphStore` как аргумент и использовать его сессию/driver.
   - Цель: ≤ 400 строк. Если не умещается — вынеси вспомогательные утилиты в `_cypher_helpers.py`.

   #### `api/workspace_graph/projection.py`
   Логика постобработки и аннотации:
   - Функции `annotate_membership(nodes, workspace_members)` — добавляет `is_member` флаги
   - Функции `annotate_cites(edges, ...)` — аннотирует рёбра цитирования
   - Функция `merge_member_external(member_nodes, external_nodes)` — объединяет узлы
   - `build_graph_payload(raw_nodes, raw_edges, display_helper)` → `GraphPayload` DTO
   - Импортирует из `api/graph_display.py` — **не изменяй `graph_display.py`** (он общий)
   - Цель: ≤ 400 строк.

   #### `api/workspace_graph/router.py`
   Тонкий FastAPI-роутер:
   - `APIRouter` с prefix `/v1/workspaces`
   - Все HTTP-хендлеры: `GET /{id}/graph`, `GET /{id}/graph/neighbors`, `GET /{id}/graph/stats`,
     и любые другие из текущего `workspace_graph.py`
   - Каждый хендлер: получает `stores: StoreRegistry = Depends(get_stores)`, вызывает функции
     из `cypher.py` и `projection.py`, возвращает результат
   - **Никакого Cypher, никакого `GraphDatabase.driver`** в этом файле
   - Цель: ≤ 250 строк.

2. **Убрать прямой `GraphDatabase.driver`:**

   Найди все вхождения в текущем файле:
   ```bash
   rg "GraphDatabase\.driver\|neo4j\.GraphDatabase" science_graphrag/api/workspace_graph.py -n
   ```
   В новом `cypher.py` вместо:
   ```python
   driver = GraphDatabase.driver(settings.neo4j_uri, auth=(user, pwd))
   with driver.session() as session:
       result = session.run(CYPHER, ...)
   ```
   Использовать `neo4j_store: Neo4jGraphStore` (передаётся из `router.py` через stores):
   ```python
   # cypher.py
   def execute_workspace_projection(neo4j_store: Neo4jGraphStore, workspace_id: str, ...):
       with neo4j_store._driver.session() as session:  # используй внутренний driver
           # или neo4j_store предоставляет публичный execute(query, params) — уточни
           result = session.run(CYPHER, workspace_id=workspace_id)
           ...
   ```
   Уточни как `Neo4jGraphStore` предоставляет доступ к драйверу:
   ```bash
   grep -n "def \|driver\|session" science_graphrag/storage/neo4j_store.py | head -30
   ```

3. **Обновить `science_graphrag/api/workspace_graph.py`** — сделать thin re-export shim:
   ```python
   # Backward-compat shim. Logic moved to api/workspace_graph/ package.
   from science_graphrag.api.workspace_graph.router import router  # noqa: F401
   ```

4. **Обновить `science_graphrag/api/main.py`:**
   Если `main.py` делает `from ... import workspace_graph; app.include_router(workspace_graph.router)` —
   убедись что эта строка продолжает работать через shim. Если нужно явно поменять путь импорта:
   ```python
   from science_graphrag.api.workspace_graph import router as workspace_graph_router
   ```
   **Минимальная правка** — не переписывай весь `main.py`.

5. **Убедиться в обратной совместимости HTTP-контрактов:**
   ```bash
   rg "router\.(get\|post\|delete\|put)" science_graphrag/api/workspace_graph/router.py -n
   # Все URL paths должны совпадать с теми, что были в workspace_graph.py
   ```

6. **Тесты:**
   ```bash
   .venv/bin/pytest tests/ -k "workspace_graph" -x -v
   .venv/bin/pytest tests/test_api_smoke.py -x -v
   ```
   Если тесты `tests/test_workspace_graph_*.py` существуют — все должны быть зелёными.
   Если тестов нет — создать `tests/api/workspace_graph/test_workspace_graph_router.py` с:
   - `test_workspace_graph_imports` — импорт `router` из нового пакета не бросает `ImportError`
   - `test_workspace_graph_shim` — импорт из `api/workspace_graph.py` shim тоже работает

### Важные ограничения (файловый скоуп)

**Трогать:**
- `science_graphrag/api/workspace_graph.py` → превратить в shim
- `science_graphrag/api/workspace_graph/` (весь новый пакет)
- `science_graphrag/api/main.py` (только строка include_router — минимально)
- `tests/api/workspace_graph/` (новые тесты)

**НЕ трогать:**
- `science_graphrag/api/graph_display.py` — общий модуль (импортируй, не изменяй)
- `science_graphrag/api/works.py` — скоуп Agent 3
- `science_graphrag/storage/neo4j_store.py` — не изменяй публичный API
- `science_graphrag/api/deps.py` — создан Agent 1, читай но не меняй
- `ui/` — frontend вне скоупа
- Ни один файл в `api/workspace_graph/` **не должен превышать 400 строк**.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/api/workspace_graph/
.venv/bin/black science_graphrag/api/workspace_graph/
.venv/bin/pylint science_graphrag/api/workspace_graph/ --fail-under=7.0

# Backward compat:
.venv/bin/python -c "from science_graphrag.api.workspace_graph import router; print('router ok')"
.venv/bin/python -c "from science_graphrag.api.workspace_graph.router import router; print('direct ok')"

# Нет прямого GraphDatabase.driver в новом пакете:
rg "GraphDatabase\.driver" science_graphrag/api/workspace_graph/ && echo "FOUND - fix it" || echo "ok"

# Размер файлов:
for f in science_graphrag/api/workspace_graph/*.py; do wc -l "$f"; done

# Тесты:
.venv/bin/pytest tests/ -k "workspace_graph" -v
.venv/bin/pytest tests/test_api_smoke.py -x -v
```

### Backlog

В `docs/backlog/refactor-backend.md` пометить `[OPEN] Split api/workspace_graph.py...` как:
```
### [DONE] Split `api/workspace_graph.py` (1214 lines) — projection vs Cypher vs HTTP
- **Note (done):** 2026-04-25 — разнесено на api/workspace_graph/{cypher.py,projection.py,
  router.py,__init__.py}; GraphDatabase.driver убран; store через get_stores() DI;
  backward-compat shim в workspace_graph.py; Wave GR2/GR3/GR4 правят отдельные модули.
```

---

## Agent 3 — G-WorksSplit (параллельно с Agent 2)

**Задача:** Разнести `science_graphrag/api/works.py` (≈817 строк) в пакет
`science_graphrag/api/works/` с четырьмя модулями.

### Контекст

Ты — агент рефакторинга Python-пакета `science_graphrag`. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Предусловие:** Agent 1 (G-StoreFactory) создал `science_graphrag/api/deps.py`.
Проверь перед началом:
```bash
ls science_graphrag/api/deps.py && \
    .venv/bin/python -c "from science_graphrag.api.deps import get_stores; print('deps ok')"
```
Если файл отсутствует — не начинай, сообщи об ошибке.

**Проблема `works.py`:**
Файл совмещает: (1) список работ, (2) детальный профиль работы, (3) graph neighborhood payload
для страницы Work и /graph, (4) Qdrant-чанки, (5) blob/PDF entrypoint, (6) semantic context.
Параллельно с `workspace_graph.py` участвует в Wave GR1–GR5.

**Прочитай файл:**
```bash
wc -l science_graphrag/api/works.py
rg "def " science_graphrag/api/works.py -n
rg "Neo4jGraphStore\|QdrantChunkStore\|BlobStore" science_graphrag/api/works.py -n
rg "@router\." science_graphrag/api/works.py -n
```

### Что сделать

1. **Создать пакет `science_graphrag/api/works/`** с пятью файлами:

   #### `api/works/__init__.py`
   ```python
   from science_graphrag.api.works.router import router  # noqa: F401
   ```

   #### `api/works/dto.py`
   Pydantic-модели ответов, специфичные для works-эндпоинтов:
   - `WorkDetailResponse`, `WorkListResponse`, `WorkChunksResponse` и т.п.
   - Маппинги ORM/neo4j → DTO (только data-классы, никакого IO)
   - Цель: ≤ 200 строк. Если DTO уже определены в общем месте — реэкспортируй оттуда.

   #### `api/works/detail.py`
   Логика получения детального профиля работы и списка работ:
   - `get_work_detail(work_id, stores)` → `WorkDetailResponse`
   - `list_works(query, filters, stores)` → `WorkListResponse`
   - Работает с `stores.neo4j` (через `Neo4jGraphStore`)
   - Цель: ≤ 300 строк.

   #### `api/works/graph_neighborhood.py`
   Graph neighborhood payload для страниц Work/Graph:
   - `get_work_neighborhood(work_id, depth, stores)` → graph payload dict
   - `get_workspace_work_neighborhood(work_id, workspace_id, stores)` → аналогично
   - Импортирует из `api/graph_display.py` — **не изменяй `graph_display.py`** (он общий).
   - **Wave GR2/GR3/GR4** будут менять только этот файл — делай его читаемым.
   - Цель: ≤ 400 строк.

   #### `api/works/chunks.py`
   Qdrant-чанки и blob/PDF:
   - `get_work_chunks(work_id, stores)` → list of chunks
   - `get_work_blob_url(work_id, stores)` → blob URL или 404
   - `get_work_semantic_context(work_id, stores)` → semantic context payload
   - Работает с `stores.qdrant_chunks` и `stores.blobs`
   - Цель: ≤ 200 строк.

   #### `api/works/router.py`
   Тонкий FastAPI-роутер:
   - `APIRouter` с prefix `/v1/works` (уточни актуальный prefix)
   - Все HTTP-хендлеры из текущего `works.py`:
     `GET /` (list), `GET /{id}`, `GET /{id}/graph`, `GET /{id}/chunks`,
     `GET /{id}/blob`, `GET /{id}/semantic` — и любые другие
   - Каждый хендлер: `stores: StoreRegistry = Depends(get_stores)`, делегирует в `detail.py`,
     `graph_neighborhood.py`, `chunks.py`
   - **Никакой бизнес-логики** в хендлерах — только параметры, Depends, вызов функции, return
   - Цель: ≤ 250 строк.

2. **Сделать `science_graphrag/api/works.py` thin re-export shim:**
   ```python
   # Backward-compat shim. Logic moved to api/works/ package.
   from science_graphrag.api.works.router import router  # noqa: F401
   ```

3. **Обновить `science_graphrag/api/main.py`** (минимально):
   Убедись что `include_router` для works продолжает работать. Если текущий `main.py` делает
   `from science_graphrag.api import works; app.include_router(works.router)` — shim сохраняет
   совместимость. Если нужно явно обновить путь — сделай это.

4. **Проверить совместимость:**
   ```bash
   rg "from.*api.works\|import.*api.works\|api/works" --include="*.py" -l
   # Убедиться что все импорты работают через shim или новый пакет
   ```

5. **Тесты:**
   ```bash
   .venv/bin/pytest tests/ -k "works" -x -v
   .venv/bin/pytest tests/test_api_smoke.py -x -v
   ```
   Если тестов на works нет — создать `tests/api/works/test_works_router.py`:
   - `test_works_router_imports` — `from science_graphrag.api.works import router` не бросает ошибок
   - `test_works_shim_imports` — `from science_graphrag.api.works import router` через shim работает
   - `test_graph_neighborhood_imports` — `from science_graphrag.api.works.graph_neighborhood import ...`

### Важные ограничения (файловый скоуп)

**Трогать:**
- `science_graphrag/api/works.py` → shim
- `science_graphrag/api/works/` (весь новый пакет)
- `science_graphrag/api/main.py` (только строка include_router — минимально)
- `tests/api/works/` (новые тесты)

**НЕ трогать:**
- `science_graphrag/api/graph_display.py` — общий (только импортируй)
- `science_graphrag/api/workspace_graph.py` — скоуп Agent 2
- `science_graphrag/storage/` — не изменяй публичный API
- `science_graphrag/api/deps.py` — создан Agent 1, только читай
- Ни один файл в `api/works/` **не должен превышать 400 строк**.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag
.venv/bin/isort science_graphrag/api/works/
.venv/bin/black science_graphrag/api/works/
.venv/bin/pylint science_graphrag/api/works/ --fail-under=7.0

# Backward compat:
.venv/bin/python -c "from science_graphrag.api.works import router; print('router ok')"
.venv/bin/python -c "from science_graphrag.api.works.graph_neighborhood import get_work_neighborhood; print('neighborhood ok')" \
    || echo "adjust function name to actual"

# Размер файлов:
for f in science_graphrag/api/works/*.py; do wc -l "$f"; done  # каждый ≤ 400

# Тесты:
.venv/bin/pytest tests/ -k "works" -v
.venv/bin/pytest tests/test_api_smoke.py -x -v
```

### Backlog

В `docs/backlog/refactor-backend.md` пометить `[OPEN] Split api/works.py...` как:
```
### [DONE] Split `api/works.py` (817 lines) — graph DTO vs vector vs blob
- **Note (done):** 2026-04-25 — разнесено на api/works/{dto,detail,graph_neighborhood,
  chunks,router}.py; backward-compat shim в works.py; Wave GR2/GR4 правят только
  graph_neighborhood.py.
```

---

## Agent 4 — H-GraphWorkspacePanelSplit (параллельно с Agents 2+3)

**Задача:** Разнести `ui/src/components/graph/GraphWorkspacePanel.jsx` (≈1164 строки) на
хук данных, подкомпоненты и composition-слой.

### Контекст

Ты — агент фронтенд-рефакторинга. Репозиторий:
`/home/roman/pyprojects/ML/Prod/science-graphrag`. UI: `ui/`. После любых правок —
`npm run lint` из `ui/`. Venv backend не нужен.

**Проблема `GraphWorkspacePanel.jsx`:**
Файл ≈1164 строки совмещает:
1. Загрузку данных графа (fetch + merge + retry + кеш neighbors)
2. Переключение Cards/Canvas/Flow (три режима отображения)
3. Боковую колонку деталей (node/edge detail, drag-resize gutter)
4. Debug inspector (raw JSON + диагностика payload)
5. Легенду типов
6. Алерты об ошибках + `formatResearchApiError`
7. URL state management

**Synergy:** Wave GR2/GR3/GR4 добавят UI для `node_kind`, агрегаторов, `view=reader` —
в разнесённом виде сразу видно, в каком компоненте что менять.

**Прочитай файл целиком:**
```bash
wc -l ui/src/components/graph/GraphWorkspacePanel.jsx
head -80 ui/src/components/graph/GraphWorkspacePanel.jsx    # imports, state
grep -n "const use\|function \|export" ui/src/components/graph/GraphWorkspacePanel.jsx | head -40
grep -n "return\|<Cards\|<GraphCanvas\|<GraphFlow\|<GraphSidePanel\|useEffect\|useState" \
    ui/src/components/graph/GraphWorkspacePanel.jsx | head -40
ls ui/src/components/graph/   # посмотри, что уже существует рядом
```

### Что сделать

1. **Создать `ui/src/components/graph/hooks/useGraphWorkspaceData.js`** — хук загрузки и merge:

   Вынести всё, что связано с fetch, polling, merge, retry:
   ```javascript
   /**
    * Fetches, caches and merges graph data for a workspace.
    * @param {string|null} workspaceId
    * @param {string|null} workId - focal work for neighbor fetch
    * @param {object} options - { depth, maxNodes, ... }
    * @returns {{ nodes, edges, loading, error, refetch, fetchNeighbors }}
    */
   export function useGraphWorkspaceData(workspaceId, workId, options = {}) {
     // вся логика useState + useEffect + fetch + merge из GraphWorkspacePanel
     ...
   }
   ```

   Что должно войти:
   - `useEffect` для загрузки workspace graph (основной)
   - `useEffect` для загрузки work neighborhood (если отдельный)
   - `fetchNeighbors(nodeId)` — callback для lazy expand (готовить к GR3)
   - `mergeWorkspaceRawGraph(...)` вызовы — импортируй из существующего
     `mergeWorkspaceRawGraph.js`
   - state: `nodes`, `edges`, `loading`, `error`, `neighborCache`
   - **Не включать** ни одного JSX-элемента

   Цель: ≤ 200 строк.

2. **Создать `ui/src/components/graph/GraphViewModeSwitch.jsx`** — переключатель режимов:

   ```jsx
   /**
    * Cards / Canvas / Flow toggle buttons.
    * @param {{ mode, onChange, compact }} props
    */
   export function GraphViewModeSwitch({ mode, onChange, compact = false }) {
     // Кнопки Cards / Canvas / Flow из существующего GraphWorkspacePanel
     // Использовать CursorButton / CursorSmallButton (дизайн-канон проекта)
     ...
   }
   ```

   Что должно войти:
   - JSX-разметка переключателя режимов (три кнопки или tab-bar)
   - Стили, соответствующие текущему виду
   - **Без данных, без fetch** — только `mode` prop и `onChange` callback

   Цель: ≤ 100 строк.

3. **Создать `ui/src/components/graph/GraphDebugInspector.jsx`** — raw JSON-инспектор:

   ```jsx
   /**
    * Collapsible raw graph payload inspector for debug builds.
    * @param {{ nodes, edges, visible }} props
    */
   export function GraphDebugInspector({ nodes, edges, visible }) {
     if (!visible) return null;
     // raw JSON pre-block + copy button из текущего GraphWorkspacePanel
     ...
   }
   ```

   Что должно войти:
   - Raw JSON display (pre + JSON.stringify)
   - Кнопка "копировать" если есть
   - toggle (show/hide) — props-controlled, не внутренний state
   - Цель: ≤ 100 строк.

4. **Создать `ui/src/components/graph/GraphSidePanel.jsx`** — боковая колонка деталей:

   ```jsx
   /**
    * Detail column for selected node/edge + drag-resize gutter.
    * @param {{ selectedNode, selectedEdge, workId, onClose, width, onWidthChange }} props
    */
   export function GraphSidePanel({
     selectedNode, selectedEdge, workId, onClose, width, onWidthChange
   }) {
     // Боковая колонка из GraphWorkspacePanel:
     // - NodeDetailPanel / EdgeDetailPanel
     // - drag-resize gutter (импортируй из graphDetailColumnWidth.js — он уже существует)
     // - кнопки навигации к Work
     ...
   }
   ```

   Что должно войти:
   - JSX боковой колонки: выбранный узел/ребро, ссылки
   - Gutter resize — используй уже существующий `graphDetailColumnWidth.js`
   - **Без fetch** — только props

   Цель: ≤ 200 строк.

5. **Переписать `GraphWorkspacePanel.jsx`** как тонкий composition-слой:

   После выноса компонентов:
   ```jsx
   export function GraphWorkspacePanel({ workspaceId, workId, ...urlProps }) {
     const { nodes, edges, loading, error, fetchNeighbors } =
       useGraphWorkspaceData(workspaceId, workId, { ... });

     const [mode, setMode] = useGraphViewMode(urlProps);      // URL state
     const [selectedNode, setSelectedNode] = useState(null);
     const [showDebug, setShowDebug] = useState(false);

     return (
       <Box sx={{ ... }}>
         <GraphViewModeSwitch mode={mode} onChange={setMode} />
         <GraphTypeLegend ... />
         {error && <Alert>{formatResearchApiError(error)}</Alert>}

         {mode === 'cards' && <WorkCardList nodes={nodes} />}
         {mode === 'canvas' && (
           <GraphCanvasMvp nodes={nodes} edges={edges}
             onNodeSelect={setSelectedNode}
             onNeighborRequest={fetchNeighbors} />
         )}
         {mode === 'flow' && <GraphFlowView nodes={nodes} edges={edges} />}

         {selectedNode && (
           <GraphSidePanel selectedNode={selectedNode}
             onClose={() => setSelectedNode(null)} ... />
         )}
         <GraphDebugInspector nodes={nodes} edges={edges} visible={showDebug} />
       </Box>
     );
   }
   ```

   Цель: `GraphWorkspacePanel.jsx` ≤ 280 строк.

6. **Проверить все импорты:**
   ```bash
   grep -rn "GraphWorkspacePanel\|useGraphWorkspaceData\|GraphViewModeSwitch\|GraphSidePanel\|GraphDebugInspector" \
       ui/src/ | grep -v "node_modules"
   ```
   Убедиться что `GraphWorkspacePanel` продолжает экспортироваться и все места использования
   (`GraphPage.jsx` и другие) не сломаны.

7. **Запустить lint и тесты:**
   ```bash
   cd ui
   npm run lint
   npm run test -- --passWithNoTests
   ```

### Важные ограничения (файловый скоуп)

**Трогать:**
- `ui/src/components/graph/GraphWorkspacePanel.jsx` (главный файл — переписать как shell)
- `ui/src/components/graph/hooks/useGraphWorkspaceData.js` (создать)
- `ui/src/components/graph/GraphViewModeSwitch.jsx` (создать)
- `ui/src/components/graph/GraphDebugInspector.jsx` (создать)
- `ui/src/components/graph/GraphSidePanel.jsx` (создать или объединить с существующим если есть)

**НЕ трогать:**
- `ui/src/components/graph/GraphCanvasMvp.jsx` — отдельный пункт бэклога (H-GraphCanvasMvpSplit)
- `ui/src/components/graph/GraphFlowView.jsx` — не трогать
- `ui/src/components/graph/graphDetailColumnWidth.js` — используй, не переписывай
- `ui/src/components/graph/mergeWorkspaceRawGraph.js` — используй, не переписывай
- `ui/src/components/graph/GraphTypeLegend.jsx` — если существует, только импортируй
- `ui/src/pages/GraphPage.jsx` — не трогать (пусть импортирует `GraphWorkspacePanel` как раньше)
- `ui/src/services/` — не трогать API-клиент
- Ни один новый файл **не должен превышать 300 строк**.

### Quality gate

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag/ui
npm run lint
npm run test -- --passWithNoTests

# Размер файлов:
wc -l src/components/graph/GraphWorkspacePanel.jsx          # ≤ 280
wc -l src/components/graph/hooks/useGraphWorkspaceData.js   # ≤ 200
wc -l src/components/graph/GraphViewModeSwitch.jsx          # ≤ 100
wc -l src/components/graph/GraphSidePanel.jsx               # ≤ 200
wc -l src/components/graph/GraphDebugInspector.jsx          # ≤ 100

# GraphWorkspacePanel экспортируется из правильного места:
grep -n "export.*GraphWorkspacePanel" src/components/graph/GraphWorkspacePanel.jsx
# Нет import-ошибок в GraphPage:
grep "GraphWorkspacePanel" src/pages/GraphPage.jsx src/pages/GraphPage/*.jsx 2>/dev/null | head -5
```

### Backlog

В `docs/backlog/refactor-frontend.md` пометить `[OPEN] Split GraphWorkspacePanel.jsx...` как:
```
### [DONE] Split `GraphWorkspacePanel.jsx` (1164) — data hook vs view modes vs debug
- **Note (done):** 2026-04-25 — разнесено на hooks/useGraphWorkspaceData.js,
  GraphViewModeSwitch.jsx, GraphSidePanel.jsx, GraphDebugInspector.jsx;
  GraphWorkspacePanel.jsx = shell ≤280 строк; Wave GR2/GR3/GR4 правят точечно.
```

---

## Review Agent — Финальная проверка Round 2

**Задача:** Проверить, что все 4 задачи Round 2 выполнены корректно, backward-compat не сломан
и Round 3 (Wave W + Y2 + X2 + Neo4jSplit) можно запускать без блокировок.

### Контекст

Ты — агент code review. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`.
Venv: `.venv/`. UI: `ui/`.

Round 2 выполнил следующее (должно быть проверено):
- **Agent 1 G-StoreFactory:** `api/deps.py` с `StoreRegistry` + `get_stores()`; lifespan в `main.py` вызывает `init_store_registry`; роутеры `api/{retrieval,agent,idea_assist,workspaces,workspace_dedup}.py` используют `Depends(get_stores)`
- **Agent 2 G-WorkspaceGraphSplit:** `api/workspace_graph.py` → пакет `api/workspace_graph/{cypher,projection,router,__init__}.py`; `GraphDatabase.driver` убран
- **Agent 3 G-WorksSplit:** `api/works.py` → пакет `api/works/{dto,detail,graph_neighborhood,chunks,router,__init__}.py`
- **Agent 4 H-GraphWorkspacePanelSplit:** `GraphWorkspacePanel.jsx` → shell + `useGraphWorkspaceData`, `GraphViewModeSwitch`, `GraphSidePanel`, `GraphDebugInspector`

### Чеклист проверки

Пройди **все** пункты последовательно. По каждому выведи: ✅ OK, ⚠️ Частично, ❌ Провалено.

#### 1. Структура: файлы созданы

```bash
# Agent 1 — deps.py:
ls science_graphrag/api/deps.py

# Agent 2 — workspace_graph package:
ls science_graphrag/api/workspace_graph/__init__.py
ls science_graphrag/api/workspace_graph/cypher.py
ls science_graphrag/api/workspace_graph/projection.py
ls science_graphrag/api/workspace_graph/router.py

# Agent 3 — works package:
ls science_graphrag/api/works/__init__.py
ls science_graphrag/api/works/dto.py
ls science_graphrag/api/works/detail.py
ls science_graphrag/api/works/graph_neighborhood.py
ls science_graphrag/api/works/chunks.py
ls science_graphrag/api/works/router.py

# Agent 4 — frontend:
ls ui/src/components/graph/hooks/useGraphWorkspaceData.js
ls ui/src/components/graph/GraphViewModeSwitch.jsx
ls ui/src/components/graph/GraphSidePanel.jsx
ls ui/src/components/graph/GraphDebugInspector.jsx
```

#### 2. Backward-compat: импорты через shim не сломаны

```bash
.venv/bin/python -c "
from science_graphrag.api.deps import get_stores, StoreRegistry, init_store_registry
print('deps ok')
"

.venv/bin/python -c "
from science_graphrag.api.workspace_graph import router as wg_router
print('workspace_graph shim ok')
"

.venv/bin/python -c "
from science_graphrag.api.works import router as works_router
print('works shim ok')
"

.venv/bin/python -c "
from science_graphrag.api.main import app
print('main app imports ok')
"
```

#### 3. StoreRegistry: корректная реализация

```bash
# get_stores — FastAPI-зависимость (не обычная функция):
.venv/bin/python -c "
from science_graphrag.api.deps import get_stores, StoreRegistry
import inspect
sig = inspect.signature(get_stores)
print('get_stores params:', list(sig.parameters.keys()))
# Должен содержать 'request' (FastAPI Request)
"

# StoreRegistry содержит ожидаемые поля:
.venv/bin/python -c "
from science_graphrag.api.deps import StoreRegistry
import dataclasses
fields = [f.name for f in dataclasses.fields(StoreRegistry)]
print('StoreRegistry fields:', fields)
assert 'neo4j' in fields, 'neo4j field missing'
assert 'qdrant_chunks' in fields, 'qdrant_chunks field missing'
print('fields ok')
"

# main.py вызывает init_store_registry в lifespan:
grep -n "init_store_registry\|store_registry\|app\.state\.stores" \
    science_graphrag/api/main.py && echo "lifespan wiring found" || echo "MISSING lifespan wiring"
```

#### 4. G-StoreFactory: роутеры используют get_stores

```bash
# Не должно быть прямой инициализации Neo4jGraphStore в хендлерах:
for f in science_graphrag/api/retrieval.py science_graphrag/api/agent.py \
         science_graphrag/api/idea_assist.py science_graphrag/api/workspaces.py; do
  echo "=== $f ==="
  grep -n "Neo4jGraphStore(\|QdrantChunkStore(" "$f" | grep -v "import\|#" \
    && echo "FOUND per-request init — check" || echo "ok"
done

# get_stores должен использоваться в обновлённых файлах:
grep -l "get_stores\|Depends(get_stores)" \
    science_graphrag/api/retrieval.py \
    science_graphrag/api/agent.py \
    science_graphrag/api/idea_assist.py \
    2>/dev/null | wc -l
echo "files using get_stores (expect ≥ 2)"
```

#### 5. G-WorkspaceGraphSplit: нет GraphDatabase.driver

```bash
rg "GraphDatabase\.driver\|neo4j\.GraphDatabase" \
    science_graphrag/api/workspace_graph/ && \
    echo "FOUND direct driver — must fix" || echo "ok: no direct driver"

# Все URL paths из нового router совпадают с оригиналом:
grep -n "@router\.\|prefix" science_graphrag/api/workspace_graph/router.py
# Сравни с:
grep -n "@router\.\|prefix" science_graphrag/api/workspace_graph.py 2>/dev/null || \
    echo "(workspace_graph.py is now a shim — compare with git diff)"
```

#### 6. Размер файлов: god-файлы распилены

```bash
echo "=== Backend shims (должны быть ≤15 строк) ==="
wc -l science_graphrag/api/workspace_graph.py
wc -l science_graphrag/api/works.py

echo "=== workspace_graph package (каждый ≤400) ==="
for f in science_graphrag/api/workspace_graph/*.py; do wc -l "$f"; done

echo "=== works package (каждый ≤400) ==="
for f in science_graphrag/api/works/*.py; do wc -l "$f"; done

echo "=== Frontend (лимиты) ==="
wc -l ui/src/components/graph/GraphWorkspacePanel.jsx          # ≤ 280
wc -l ui/src/components/graph/hooks/useGraphWorkspaceData.js   # ≤ 200
wc -l ui/src/components/graph/GraphViewModeSwitch.jsx          # ≤ 100
wc -l ui/src/components/graph/GraphSidePanel.jsx               # ≤ 200
wc -l ui/src/components/graph/GraphDebugInspector.jsx          # ≤ 100
```

#### 7. Quality gates: Python

```bash
.venv/bin/isort --check \
    science_graphrag/api/deps.py \
    science_graphrag/api/workspace_graph/ \
    science_graphrag/api/works/
.venv/bin/black --check \
    science_graphrag/api/deps.py \
    science_graphrag/api/workspace_graph/ \
    science_graphrag/api/works/
.venv/bin/pylint \
    science_graphrag/api/deps.py \
    science_graphrag/api/workspace_graph/ \
    science_graphrag/api/works/ \
    --fail-under=7.0
.venv/bin/pytest tests/ -x -q 2>&1 | tail -20
```

#### 8. Quality gates: Frontend

```bash
cd ui && npm run lint 2>&1 | tail -20
npm run test -- --passWithNoTests 2>&1 | tail -10
```

#### 9. GraphWorkspacePanel: правильная декомпозиция

```bash
# GraphWorkspacePanel — shell (не god-file):
wc -l ui/src/components/graph/GraphWorkspacePanel.jsx
# Должен содержать импорты новых компонентов:
grep "useGraphWorkspaceData\|GraphViewModeSwitch\|GraphSidePanel\|GraphDebugInspector" \
    ui/src/components/graph/GraphWorkspacePanel.jsx | head -10

# useGraphWorkspaceData — не содержит JSX:
grep -n "return (<\|JSX\|<div\|<Box\|<Stack" \
    ui/src/components/graph/hooks/useGraphWorkspaceData.js | head -5 && \
    echo "WARNING: JSX in hook — should not be there" || echo "ok: no JSX in hook"
```

#### 10. Wave GR2 — готовность к следующему раунду

```bash
# graph_neighborhood.py существует и импортирует graph_display:
grep -n "graph_display\|display_label\|node_kind" \
    science_graphrag/api/works/graph_neighborhood.py | head -5 || \
    echo "NOTE: graph_display not yet referenced in graph_neighborhood.py"

# workspace_graph/projection.py импортирует graph_display:
grep -n "graph_display" science_graphrag/api/workspace_graph/projection.py | head -5 || \
    echo "NOTE: graph_display not yet referenced in projection.py"

# Эндпоинты graph существуют:
grep -n "def.*graph\|/graph" science_graphrag/api/workspace_graph/router.py | head -10
grep -n "def.*graph\|/graph" science_graphrag/api/works/router.py | head -10
```

#### 11. Backlog hygiene

```bash
grep "\[DONE\].*StoreFactory\|Unified Bolt\|get_stores" \
    docs/backlog/refactor-backend.md | head -3
grep "\[DONE\].*workspace_graph\|WorkspaceGraphSplit" \
    docs/backlog/refactor-backend.md | head -3
grep "\[DONE\].*works\.py\|WorksSplit" \
    docs/backlog/refactor-backend.md | head -3
grep "\[DONE\].*GraphWorkspacePanel\|GraphPanel" \
    docs/backlog/refactor-frontend.md | head -3
```

#### 12. Нет конфликтов в api/main.py

```bash
# main.py должен содержать include_router для обоих:
grep "workspace_graph\|works" science_graphrag/api/main.py | grep -i "router\|include"
# Не должно быть дублей:
grep -c "include_router.*workspace_graph\|include_router.*works" science_graphrag/api/main.py
```

#### 13. Smoke: app полностью загружается

```bash
.venv/bin/python -c "
from science_graphrag.api.main import app
from science_graphrag.api.deps import get_stores, StoreRegistry
from science_graphrag.api.workspace_graph import router as wg_r
from science_graphrag.api.works import router as works_r
print('All Round 2 imports ok')
routes = [r.path for r in app.routes]
# Проверь что workspace_graph и works маршруты зарегистрированы:
wg_routes = [r for r in routes if 'workspace' in r.lower() or 'graph' in r.lower()]
works_routes = [r for r in routes if '/works' in r.lower()]
print(f'Workspace/graph routes: {len(wg_routes)}, Works routes: {len(works_routes)}')
"
```

### Что делать с найденными проблемами

После прогона всех проверок:

1. **Если все ✅** — написать:
   «Round 2 complete. Ready for Round 3 (Wave W Dramatiq + Wave Y2 LangGraph + Wave X2 Phoenix + G-Neo4jSplit + H-AskPanelSplit).»
   Указать метрику: сколько строк распилено суммарно, какие тесты зелёные.

2. **Если есть ⚠️** — описать конкретно что частично выполнено, какие шаги остались.
   Особое внимание: конфликты в `api/main.py` (несколько агентов могли менять один файл).

3. **Если есть ❌** — описать пункт провала, вывод команды, возможную причину.
   Не пытаться починить самостоятельно — только репортировать.

### Не входит в scope Review Agent

- Не вносить изменения в код — только читать и запускать команды.
- Не запускать интеграционные тесты с реальными БД (Neo4j, Qdrant, Postgres).
- Не проверять визуальный рендеринг frontend — только lint/test/import.
- Не оценивать качество кода субъективно — только факты из checklist.

---

## Примечания по конфликтам в Round 2

### api/main.py

Все три бэкенд-агента (1, 2, 3) могут минимально трогать `api/main.py`:
- Agent 1: добавляет `init_store_registry` в lifespan
- Agent 2: может обновить путь `include_router` для workspace_graph
- Agent 3: может обновить путь `include_router` для works

Если агенты запускались истинно параллельно — возможен merge-конфликт в `main.py`.
После завершения всех агентов: проверить `api/main.py` вручную, убедиться что:
- lifespan содержит `init_store_registry` (от Agent 1)
- `include_router` для workspace_graph работает через shim или новый пакет (Agent 2)
- `include_router` для works работает через shim или новый пакет (Agent 3)
- Нет дублированных `include_router` вызовов

### graph_display.py

Оба Agent 2 и Agent 3 импортируют `api/graph_display.py` но не должны его изменять.
Проверь что `graph_display.py` не был случайно модифицирован:
```bash
git diff science_graphrag/api/graph_display.py
```

### Порядок при следующем раунде (Round 3)

Следующий Раунд 3 требует:
- Agent 1 (G-StoreFactory) ✅ завершён — `api/deps.py` готов
- Agent 2 (G-WorkspaceGraphSplit) ✅ завершён — Wave GR2 может стартовать
- Agent 3 (G-WorksSplit) ✅ завершён — Wave GR2 backend в `works/graph_neighborhood.py`
- G-Neo4jSplit (Раунд 3) — может идти параллельно с Wave Y2
- H-AskPanelSplit (Раунд 3) — frontend, независим
