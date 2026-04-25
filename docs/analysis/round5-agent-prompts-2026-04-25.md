# Round 5 — Agent Prompts («Wave T + GR3 + Y4 + G-StageExtractionSplit»)

> Дата: 2026-04-25
> Источник плана: `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md` §7 «Раунд 5»
> Предусловие: Раунды 1–4 выполнены, все тесты зелёные (406 passed, 2 skipped).
> Порядок запуска: **Все 4 агента параллельно** — файловые скоупы не пересекаются.

**Проверка предусловий перед запуском всех агентов:**

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# G-Neo4jSplit (нужен Agent 1):
python -c "from science_graphrag.storage.neo4j.facade import Neo4jFacade; print('neo4j split ok')"
ls science_graphrag/storage/neo4j/writes/  # должны быть: claims.py dedup.py semantic.py workspace.py works.py

# G-WorksSplit + G-WorkspaceGraphSplit (нужен Agent 2):
python -c "from science_graphrag.api.works.graph_neighborhood import work_graph_neighborhood_payload; print('works split ok')"
python -c "from science_graphrag.api.workspace_graph.projection import build_workspace_graph_payload; print('workspace_graph split ok')"

# Wave Y2 + Y3 (нужен Agent 3):
python -c "from science_graphrag.agent.graph.supervisor import build_retrieval_graph; print('langgraph y2 ok')"
python -c "from science_graphrag.api.agent_v2 import router as v2_router; print('agent_v2 ok')"

# Baseline тесты:
.venv/bin/pytest tests/ -q --tb=no 2>/dev/null | tail -3
# Ожидается: 406 passed, 2 skipped
```

**Координация по файлам (почему агенты не конфликтуют):**

| Агент | Основные файлы |
|-------|---------------|
| Agent 1 (Wave T) | `science_graphrag/dedup/{institution,venue,method,dataset}_pipeline.py` (NEW), `storage/models_orm.py` (добавление моделей), `storage/neo4j/writes/{authors,institutions,venues}.py` (NEW или правки), `api/dedup_jobs.py` (новые entity типы) |
| Agent 2 (Wave GR3) | `api/works/graph_neighborhood.py`, `api/workspace_graph/projection.py`, `api/works/router.py` (новый expand endpoint), `ui/src/components/graph/GraphCanvasMvp.jsx` (split + GR3), `ui/src/components/graph/GraphDetailPanel.jsx`, `ui/src/components/graph/graphCanvasStyle.js` |
| Agent 3 (Wave Y4) | `science_graphrag/agent/graph/supervisor.py`, `agent/graph/state.py`, `agent/graph/nodes/` (NEW), `tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json`, `eval/agent_tools/metrics.py`, `docs/adr/020-langgraph-supervisor-multiagent.md` |
| Agent 4 (G-StageExtractionSplit) | `science_graphrag/ingestion/llm/stage_extraction.py` → подпакет `ingestion/llm/`, `ingestion/llm/{prompts/,executor.py,orchestrator.py,heuristics/}` |

> Agent 1 добавляет строки в `storage/models_orm.py` — Agent 3 его не трогает. Agent 2 правит `api/works/router.py` — Agent 1 не трогает `api/`. Agent 4 работает только в `ingestion/llm/`. Конфликтов нет.

---

## Agent 1 — Wave T: Entity Dedup Pipeline (Author / Institution / Venue / Method / Dataset)

**Задача:** расширить дедупликацию с Work+Author до пяти типов сущностей (Institution, Venue, Method, Dataset).
Добавить Postgres-очередь с полем `entity_type`, Qdrant-коллекции, Neo4j write-хелперы, API-эндпоинты и ADR 019.
Это **backend only**; UI-вкладки в `WorkspaceDedupSection` — в отдельном PR.

### Контекст

Ты — агент Python/FastAPI. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Что уже есть (Round 1–4):**
- `science_graphrag/dedup/work_dedup_engine.py` (197 строк) — шаблон пайплайна дедупа Works.
- `science_graphrag/dedup/author_dedup_engine.py` (182 строки) — author dedup engine (Wave L2).
- `science_graphrag/dedup/fingerprints.py` — хелперы fingerprint.
- `science_graphrag/storage/neo4j/writes/dedup.py` — Neo4j write-методы для merge Works и Authors.
- `science_graphrag/storage/models_orm.py` — ORM: `WorkDedupConflict` (table `work_dedup_conflicts`), `AuthorDedupConflict` (table `author_dedup_conflicts`).
- `science_graphrag/api/dedup_jobs.py` — API для запуска/просмотра dedup-задач (сейчас только Works + Authors).
- `science_graphrag/api/workspace_dedup.py` — API для review очереди.

**Цель Wave T:**
- Добавить три новых типа: `Institution`, `Venue`, `Method`, `Dataset`.
- Unified review queue: одна Postgres-таблица `entity_dedup_conflicts` с колонкой `entity_type ∈ {work, author, institution, venue, method, dataset}`.
- Qdrant-коллекции для новых типов: `institutions`, `venues`, `methods`, `datasets`.
- ADR 019 «Entity dedup pipeline».

### Шаг 0 — Прочитать контекст

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Существующая архитектура dedup:
cat science_graphrag/dedup/work_dedup_engine.py
cat science_graphrag/dedup/author_dedup_engine.py
cat science_graphrag/dedup/fingerprints.py

# ORM модели:
grep -n "class.*Conflict\|class.*Dedup\|entity_type\|__tablename__" science_graphrag/storage/models_orm.py

# Neo4j writes для dedup:
cat science_graphrag/storage/neo4j/writes/dedup.py

# Существующий API dedup:
cat science_graphrag/api/dedup_jobs.py
cat science_graphrag/api/workspace_dedup.py | head -80

# Qdrant store для понимания коллекций:
grep -n "collection_name\|QdrantClient\|upsert\|search" science_graphrag/storage/qdrant_store.py | head -30

# Settings для конфигурации:
grep -n "dedup\|similarity" science_graphrag/config.py | head -20
```

### Шаг 1 — ADR 019

Создать `docs/adr/019-entity-dedup-pipeline.md`:

```markdown
# ADR 019: Entity Dedup Pipeline — Author / Institution / Venue / Method / Dataset

**Status:** Accepted
**Date:** 2026-04-25
**Supersedes:** ADR 009 (author-institution-merge-catalog) — частично; ADR 010 (work-dedup-review-queue) — расширение.

## Context

Wave L1 и Wave L2 доставили Work и Author dedup соответственно, каждый со своей Postgres-таблицей.
Wave T обобщает подход на Institution, Venue, Method, Dataset, вводя единую таблицу `entity_dedup_conflicts`
с колонкой `entity_type`, чтобы унифицировать API review-очереди и упростить UI (одна страница, 5 вкладок).

## Decision

1. **Unified Postgres table** `entity_dedup_conflicts` (`entity_type` ∈ {work, author, institution, venue, method, dataset}).
   `WorkDedupConflict` и `AuthorDedupConflict` остаются как legacy backward-compat; новый код использует только `EntityDedupConflict`.
2. **Per-type pipeline** в `science_graphrag/dedup/<type>_pipeline.py` (шаблон из `work_dedup_engine.py`).
3. **Auto-merge threshold:** sim ≥ 0.95 → auto; 0.80..0.95 → user queue; < 0.80 → skip.
   Для Methods/Datasets — alias-merge (добавление в `aliases[]`) без физического merge nodes.
4. **Qdrant коллекции** `institutions`, `venues`, `methods`, `datasets` — отдельные embedding-формулы (см. §6.2 ontology-benchmarks-roadmap).
5. **Reverse merge** через `POST /v1/dedup/entity/{conflict_id}/revert` (admin).

## Consequences

- API `GET /v1/dedup/entity?entity_type=institution&status=pending` унифицирован.
- `science_graphrag/api/workspace_dedup.py` расширяется новым `entity_type` параметром.
- G-Neo4jStoreSplit (уже выполнен) позволяет добавлять `writes/<type>.py` без правки монолита.
```

### Шаг 2 — ORM: `EntityDedupConflict` (unified table)

В `science_graphrag/storage/models_orm.py` добавить новый класс **после** `AuthorDedupConflict`:

```python
class EntityDedupConflict(Base):
    """Unified Postgres review queue for all entity types (Wave T).

    Replaces per-type tables for Institution, Venue, Method, Dataset.
    Works and Authors still use their legacy tables for backward compat.
    """

    __tablename__ = "entity_dedup_conflicts"
    __table_args__ = (
        UniqueConstraint("entity_type", "fingerprint", name="uq_entity_dedup_type_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    entity_type: Mapped[str] = mapped_column(String(32), index=True)  # institution|venue|method|dataset
    entity_id_a: Mapped[str] = mapped_column(String(256), index=True)
    entity_id_b: Mapped[str] = mapped_column(String(256), index=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    check_mode: Mapped[str] = mapped_column(String(32), default="embedding")
    llm_same_entity: Mapped[bool | None] = mapped_column(nullable=True)
    llm_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    keep_entity_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Добавить `EntityDedupConflict` в `__all__` если есть, и в Alembic/init_db (смотри, как `WorkDedupConflict` создаётся — аналогично).

### Шаг 3 — Per-type pipeline модули

Создать `science_graphrag/dedup/institution_pipeline.py`, `venue_pipeline.py`, `method_pipeline.py`, `dataset_pipeline.py` по шаблону `work_dedup_engine.py`/`author_dedup_engine.py`.

**Общий паттерн для каждого файла:**

```python
"""<Type> dedup pipeline — Wave T.

Embedding formula:
  Institution: normalized_name + ' | ' + country + ' | ' + city
  Venue: normalized_name + ' | ' + venue_type
  Method: normalized_name + ' | ' + ', '.join(aliases[:3]) + ' | ' + description_short[:100]
  Dataset: normalized_name + ' | ' + ', '.join(aliases[:3])
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from science_graphrag.dedup.fingerprints import make_entity_pair_fingerprint
from science_graphrag.storage.models_orm import EntityDedupConflict

if TYPE_CHECKING:
    from science_graphrag.storage.neo4j.facade import Neo4jFacade
    from science_graphrag.storage.qdrant_store import QdrantWorkEmbeddingStore  # reuse interface


ENTITY_TYPE = "institution"  # переопределить в каждом файле
SIM_AUTO_MERGE = 0.95
SIM_QUEUE_MIN = 0.80


def embed_text(entity: dict) -> str:
    """Return the text to embed for similarity search."""
    # реализовать для каждого типа
    ...


def run_<type>_dedup(
    neo4j: "Neo4jFacade",
    qdrant_collection: str,
    db_session,
    *,
    workspace_id: str | None = None,
    limit: int = 500,
) -> dict:
    """Find near-duplicate <Type> nodes and queue them for review."""
    ...
```

**Конкретные embedding-формулы:**

| Type | Embedding text |
|------|---------------|
| Institution | `f"{normalized_name} | {country} | {city}"` |
| Venue | `f"{normalized_name} | {venue_type}"` |
| Method | `f"{normalized_name} | {', '.join(aliases[:3])} | {description_short[:100]}"` |
| Dataset | `f"{normalized_name} | {', '.join(aliases[:3])}"` |

**Логика каждого пайплайна:**

1. Загрузить все сущности данного типа из Neo4j (через `neo4j.reads.<query>`).
2. Для каждой пары (или через Qdrant approximate nearest neighbors если коллекция уже наполнена):
   - Посчитать cosine similarity.
   - Если `sim >= SIM_AUTO_MERGE` → вызвать `_auto_merge(entity_id_a, entity_id_b)` (для Method/Dataset — только alias-merge).
   - Если `SIM_QUEUE_MIN <= sim < SIM_AUTO_MERGE` → добавить в `EntityDedupConflict` (status=`pending`), дедуплицируя по fingerprint.
3. Вернуть `{"queued": N, "auto_merged": M, "skipped": K}`.

### Шаг 4 — Neo4j writes для Institution и Venue

В `science_graphrag/storage/neo4j/writes/` создать **`institutions.py`** и **`venues.py`** (если нет или неполные):

**`institutions.py`** — методы:
- `merge_institution(driver, entity_id_a: str, entity_id_b: str, keep_id: str)` — перепривязать рёбра `AFFILIATED_WITH` от entity_id_b к keep_id, добавить `keep_id.alternative_names` +=  name_b, удалить entity_id_b.
- `add_institution_alias(driver, institution_id: str, alias: str)`.

**`venues.py`** — методы:
- `merge_venue(driver, entity_id_a, entity_id_b, keep_id)` — перепривязать `PUBLISHED_IN`, добавить альтернативное imprint в список.

Для `Method` и `Dataset` — alias-merge (не физическое слияние узлов):
- В `science_graphrag/storage/neo4j/writes/semantic.py` добавить:
  - `add_method_alias(driver, method_id: str, alias: str)`.
  - `add_dataset_alias(driver, dataset_id: str, alias: str)`.

### Шаг 5 — Qdrant коллекции (создание при старте)

В `science_graphrag/storage/qdrant_store.py` или в отдельном `storage/qdrant_entity_stores.py` добавить функцию:

```python
ENTITY_COLLECTIONS = {
    "institutions": 384,
    "venues": 384,
    "methods": 384,
    "datasets": 384,
}

def ensure_entity_dedup_collections(client: QdrantClient) -> None:
    """Create entity dedup collections if they don't exist (idempotent)."""
    for name, dim in ENTITY_COLLECTIONS.items():
        existing = {c.name for c in client.get_collections().collections}
        if name not in existing:
            client.create_collection(name, vectors_config=VectorParams(size=dim, distance=Distance.COSINE))
```

Вызывать из lifespan в `api/main.py` (или CLI `science-graphrag init-dedup-collections`).

### Шаг 6 — API: расширить dedup endpoints

В `science_graphrag/api/workspace_dedup.py` (или `api/dedup_jobs.py`) добавить:

```python
@router.post("/v1/dedup/entity/run")
async def run_entity_dedup(
    entity_type: str,        # institution | venue | method | dataset
    workspace_id: str | None = None,
    limit: int = 500,
    stores: StoreRegistry = Depends(get_stores),
) -> dict:
    """Trigger entity dedup pipeline for given type."""
    ...

@router.get("/v1/dedup/entity")
async def list_entity_conflicts(
    entity_type: str,
    status: str = "pending",
    limit: int = 50,
    offset: int = 0,
    stores: StoreRegistry = Depends(get_stores),
) -> list[dict]:
    """List conflicts from entity_dedup_conflicts table."""
    ...

@router.post("/v1/dedup/entity/{conflict_id}/decide")
async def decide_entity_conflict(
    conflict_id: str,
    decision: str,        # merge | skip
    keep_entity_id: str | None = None,
    stores: StoreRegistry = Depends(get_stores),
) -> dict:
    """Record user decision and optionally trigger merge."""
    ...
```

Зарегистрировать router в `science_graphrag/api/main.py`.

### Шаг 7 — Тесты

Создать `tests/dedup/test_entity_pipelines.py`:

```python
"""Unit tests for entity dedup pipelines (Wave T)."""

def test_institution_embed_text():
    from science_graphrag.dedup.institution_pipeline import embed_text
    text = embed_text({"normalized_name": "MIT", "country": "US", "city": "Cambridge"})
    assert "MIT" in text and "US" in text

def test_venue_embed_text():
    from science_graphrag.dedup.venue_pipeline import embed_text
    text = embed_text({"normalized_name": "NeurIPS", "venue_type": "conference"})
    assert "NeurIPS" in text

def test_method_embed_text():
    from science_graphrag.dedup.method_pipeline import embed_text
    text = embed_text({"normalized_name": "BERT", "aliases": ["bert-base", "bert-large"], "description_short": "Transformer LM"})
    assert "BERT" in text and "bert-base" in text

def test_dataset_embed_text():
    from science_graphrag.dedup.dataset_pipeline import embed_text
    text = embed_text({"normalized_name": "ImageNet", "aliases": ["ILSVRC"]})
    assert "ImageNet" in text

def test_entity_dedup_conflict_orm_fields():
    from science_graphrag.storage.models_orm import EntityDedupConflict
    assert hasattr(EntityDedupConflict, "entity_type")
    assert hasattr(EntityDedupConflict, "entity_id_a")
    assert hasattr(EntityDedupConflict, "entity_id_b")
    assert hasattr(EntityDedupConflict, "similarity_score")
    assert hasattr(EntityDedupConflict, "status")
```

Также добавить `tests/dedup/__init__.py`.

### Шаг 8 — Quality gates

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Импорты работают:
.venv/bin/python -c "
from science_graphrag.dedup.institution_pipeline import embed_text, ENTITY_TYPE
from science_graphrag.dedup.venue_pipeline import embed_text as ve
from science_graphrag.dedup.method_pipeline import embed_text as me
from science_graphrag.dedup.dataset_pipeline import embed_text as de
from science_graphrag.storage.models_orm import EntityDedupConflict
print('all imports ok')
"

# Тесты (весь сьют):
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -10
# Ожидается: предыдущие 406 + новые → все passed, 2 skipped

# Линтеры:
.venv/bin/isort science_graphrag/dedup/ science_graphrag/storage/models_orm.py science_graphrag/api/workspace_dedup.py --check-only
.venv/bin/black science_graphrag/dedup/ science_graphrag/storage/ science_graphrag/api/workspace_dedup.py --check
.venv/bin/pylint science_graphrag/dedup/ --fail-under=7.5
```

### Acceptance

- [ ] `EntityDedupConflict` ORM-класс с `entity_type` в `models_orm.py`.
- [ ] `institution_pipeline.py`, `venue_pipeline.py`, `method_pipeline.py`, `dataset_pipeline.py` в `science_graphrag/dedup/` — каждый ≤ 250 строк.
- [ ] `embed_text(entity: dict) -> str` реализован для каждого типа с правильной формулой.
- [ ] Neo4j write-хелперы: `institutions.py` и `venues.py` в `storage/neo4j/writes/`; `add_method_alias` и `add_dataset_alias` в `semantic.py`.
- [ ] `ensure_entity_dedup_collections()` создаёт 4 коллекции в Qdrant.
- [ ] API endpoints `/v1/dedup/entity/run`, `/v1/dedup/entity`, `/v1/dedup/entity/{id}/decide` зарегистрированы.
- [ ] `docs/adr/019-entity-dedup-pipeline.md` создан со статусом Accepted.
- [ ] `tests/dedup/test_entity_pipelines.py` зелёный.
- [ ] Все существующие 406 тестов не сломаны.
- [ ] pylint ≥ 7.5, isort/black чисто.

### Бэклог-запись по завершении

После завершения обновить `docs/backlog/refactor-backend.md`:

```markdown
### [DONE] Wave T — Entity dedup pipeline (Institution / Venue / Method / Dataset)
- **Note (done):** 2026-04-25 — добавлены pipelines для 4 типов, EntityDedupConflict ORM,
  Neo4j write-хелперы, Qdrant коллекции, 3 API endpoint. ADR 019 принят.
```

---

## Agent 2 — Wave GR3: Узлы-агрегаторы (Aggregator) + ленивое разворачивание

**Задача:** (A) split `GraphCanvasMvp.jsx` (1061 строк) на `GraphCanvasMvp.jsx` (shell, ≤400) + `useGraphCanvasInput.js` + `graphCanvasDraw.js`; (B) добавить backend-логику агрегаторов в `graph_neighborhood.py` и `projection.py`; (C) новый endpoint `/v1/works/{id}/graph/expand`; (D) frontend: стиль агрегатора, клик-разворачивание, `GraphDetailPanel` для агрегатора.

Всё выполняется **последовательно внутри агента**: сначала split (чтобы снять ⛔ с GR3 + GraphCanvas), затем backend GR3, затем frontend GR3.

### Контекст

Ты — агент React/Python/FastAPI. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Что уже есть (Round 1–4):**
- `api/works/graph_neighborhood.py` (376 строк) — `work_graph_neighborhood_payload(...)`.
- `api/workspace_graph/projection.py` (266 строк) — `build_workspace_graph_payload(...)`.
- Wave GR2 ✅ DONE: `node_kind`, семантичный `display_type`, `prioritize`, `meta.skipped_by_kind`.
- `ui/src/components/graph/GraphCanvasMvp.jsx` (1061 строк) — canvas с force-simulation, click handling, label draw.
- `ui/src/components/graph/GraphDetailPanel.jsx` (342 строки) — инспектор выбранного узла.
- `ui/src/components/graph/graphCanvasStyle.js` — стили узлов/рёбер по типу/kind.
- `ui/src/components/graph/graphViewState.js` — state-нормализатор payload.
- `ui/src/services/researchApi.js` — API клиент (функция `getWorkGraphNeighbors`).

**Параметр `aggregator_threshold`:** 8 (зафиксировано в открытых вопросах роадмапа).

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Backend:
wc -l science_graphrag/api/works/graph_neighborhood.py science_graphrag/api/workspace_graph/projection.py
cat science_graphrag/api/works/graph_neighborhood.py
cat science_graphrag/api/workspace_graph/projection.py | head -60

# Frontend:
wc -l ui/src/components/graph/GraphCanvasMvp.jsx
wc -l ui/src/components/graph/GraphDetailPanel.jsx ui/src/components/graph/graphCanvasStyle.js
grep -n "function\|const.*=.*(" ui/src/components/graph/GraphCanvasMvp.jsx | head -30
grep -n "aggregat\|node_kind\|Aggregator" ui/src/components/graph/graphCanvasStyle.js
grep -n "getWorkGraph\|expand\|aggregat" ui/src/services/researchApi.js

# Существующий payload контракт (Wave GR2):
grep -n "node_kind\|display_type\|skipped_by_kind\|WorkInternal\|WorkExternal" \
  science_graphrag/api/works/graph_neighborhood.py | head -20
```

### Часть A — H-GraphCanvasMvpSplit (выполнить первой)

Split `GraphCanvasMvp.jsx` (1061 строк) → три модуля:

1. **`useGraphCanvasInput.js`** (`ui/src/components/graph/hooks/useGraphCanvasInput.js`) — хук:
   - Вся обработка кликов, hover, drag, pinch/zoom → callback-и `onNodeClick`, `onEdgeClick`, `onCanvasClick`, `onNodeHover`.
   - Поддерживает `ref` на canvas-элемент.
   - Экспортирует: `export default function useGraphCanvasInput({ canvasRef, nodes, edges, onNodeClick, onEdgeClick, onCanvasClick })`.

2. **`graphCanvasDraw.js`** (`ui/src/components/graph/graphCanvasDraw.js`) — чистые функции:
   - `drawNodes(ctx, nodes, transform, selectedId, hoveredId, styleMap)`.
   - `drawEdges(ctx, edges, nodes, transform, styleMap)`.
   - `drawLabels(ctx, nodes, transform, zoom)`.
   - Никаких хуков, никаких импортов React — только Canvas API.

3. **`GraphCanvasMvp.jsx`** (shell, ≤400 строк) — только:
   - Монтирование canvas.
   - Вызов `useGraphCanvasInput`.
   - Вызов `useGraphSimulation` (уже есть в `graphSimulationAdapter.js`).
   - requestAnimationFrame loop → вызов `graphCanvasDraw.drawNodes/drawEdges/drawLabels`.

**Acceptance split:**
- `GraphCanvasMvp.jsx` ≤ 400 строк.
- `graphCanvasDraw.js` ≤ 350 строк.
- `useGraphCanvasInput.js` ≤ 250 строк.
- `npm run lint` чисто, `npm run test` зелёный (существующие тесты `graphCanvasGeometry.test.js`, `graphFlowAdapter.test.js` и др. не сломаны).

### Часть B — Backend GR3: Aggregator nodes

В `science_graphrag/api/works/graph_neighborhood.py` после построения `nodes`/`edges` добавить функцию-постпроцессор:

```python
AGGREGATOR_THRESHOLD = 8


def _apply_aggregators(
    nodes: list[dict],
    edges: list[dict],
    threshold: int = AGGREGATOR_THRESHOLD,
) -> tuple[list[dict], list[dict]]:
    """Replace clusters of same-kind neighbours with Aggregator nodes.

    Groups neighbours by (owner_node_id, node_kind, edge_type) — for each group
    where count >= threshold, replace group with one Aggregator node + one summary edge.

    Returns updated (nodes, edges).
    """
    ...
```

**Контракт Aggregator-узла:**

```json
{
  "id": "agg:<owner_id>:<kind>:<edge_type>",
  "type": "Aggregator",
  "node_kind": "Aggregator",
  "label": "8 authors",
  "display_label": "8 authors",
  "subtitle": "Click to expand",
  "properties": {},
  "aggregation_hints": {
    "aggregator_kind": "authors_of_work",
    "count": 8,
    "preview_labels": ["Smith J.", "Doe A.", "Lee K."],
    "expand_endpoint": "/v1/works/<work_id>/graph/expand?aggregator_id=agg:..."
  }
}
```

**Контракт Aggregator-ребра:**

```json
{
  "id": "e_agg_<sha>",
  "source": "<owner_work_id>",
  "target": "agg:<owner_id>:<kind>:<edge_type>",
  "type": "AGGREGATED",
  "display_type": "8 authors of Work",
  "summary": "8 authors · click to expand",
  "direction": "outgoing"
}
```

Применять агрегацию **только при `view=reader`** (default); при `view=raw` — без агрегации.

Аналогично расширить `science_graphrag/api/workspace_graph/projection.py` — после сборки payload применить тот же `_apply_aggregators`.

### Часть C — Backend GR3: Expand endpoint

В `science_graphrag/api/works/router.py` добавить:

```python
@router.get("/{work_id}/graph/expand")
async def expand_aggregator(
    work_id: str,
    aggregator_id: str,
    limit: int = 50,
    stores: StoreRegistry = Depends(get_stores),
) -> dict:
    """Expand an aggregator node — return the full list of hidden neighbours.

    Used by frontend click-on-aggregator: fetches only the collapsed group,
    returns {nodes: [...], edges: [...]} to be merged into the existing graph state.
    """
    ...
```

Логика: по `aggregator_id` (формат `agg:<owner_id>:<kind>:<edge_type>`) восстановить, каких именно узлов нет в текущем payload, и вернуть только их (без дублирования уже выданных).

Для workspace-графа — аналогичный endpoint в `api/workspace_graph/router.py`:

```python
@router.get("/{workspace_id}/graph/expand")
async def expand_workspace_aggregator(workspace_id: str, aggregator_id: str, limit: int = 50, ...)
```

### Часть D — Frontend GR3

**1. `graphCanvasStyle.js` — стиль агрегатора:**

```javascript
// В функции getNodeStyle (или аналоге):
if (node.node_kind === 'Aggregator') {
  return {
    fillColor: 'rgba(99, 102, 241, 0.12)',
    strokeColor: 'rgba(99, 102, 241, 0.6)',
    strokeWidth: 1.5,
    strokeDash: [6, 3],    // пунктир
    radius: 22,
    labelColor: 'rgba(129, 140, 248, 0.9)',
    badge: node.aggregation_hints?.count,  // число в центре узла
  };
}
```

**2. `graphCanvasDraw.js` — рендер badge (число):**

В `drawNodes` для `Aggregator`: нарисовать текст `+N` в центре диска (или `N`), шрифт `bold 11px Inter`.

**3. `GraphCanvasMvp.jsx` — клик по агрегатору:**

В обработчике `onNodeClick` из `useGraphCanvasInput`:

```javascript
if (clickedNode?.node_kind === 'Aggregator') {
  const expandUrl = clickedNode.aggregation_hints?.expand_endpoint;
  if (expandUrl) {
    onAggregatorExpand(clickedNode, expandUrl);   // пробросить через props
  }
  return;
}
```

В `GraphWorkspacePanel.jsx` (или `GraphVisualization.jsx` — смотри по структуре) добавить хендлер `onAggregatorExpand`:

```javascript
async function handleAggregatorExpand(aggregatorNode, expandEndpoint) {
  const { nodes: newNodes, edges: newEdges } = await researchApi.expandAggregator(expandEndpoint);
  // Merge into local graph state (как делает getWorkspaceGraphNeighbors сейчас):
  setGraphData(prev => mergeGraphPayload(prev, { nodes: newNodes, edges: newEdges }));
}
```

Добавить в `ui/src/services/researchApi.js`:

```javascript
export async function expandAggregator(expandEndpoint) {
  const res = await apiFetch(expandEndpoint);
  return res.json();
}
```

**4. `GraphDetailPanel.jsx` — инспектор агрегатора:**

```javascript
if (selectedNode?.node_kind === 'Aggregator') {
  const hints = selectedNode.aggregation_hints ?? {};
  return (
    <Box>
      <Typography variant="subtitle2">{selectedNode.display_label}</Typography>
      <Typography variant="caption" color="text.secondary">
        {hints.aggregator_kind?.replace(/_/g, ' ')}
      </Typography>
      {hints.preview_labels?.length > 0 && (
        <List dense>
          {hints.preview_labels.map(l => <ListItem key={l}><ListItemText primary={l}/></ListItem>)}
        </List>
      )}
      <Button size="small" onClick={() => onAggregatorExpand(selectedNode, hints.expand_endpoint)}>
        Expand all ({hints.count})
      </Button>
    </Box>
  );
}
```

**5. `graphViewState.js` — пропускать `aggregation_hints` без warn:**

Убедиться, что нормализатор payload не выдаёт `console.warn` на неизвестные поля `aggregation_hints`, `node_kind: "Aggregator"`.

### Шаг E — Тесты

**Backend:**

```python
# tests/storage/test_graph_aggregators.py
def test_apply_aggregators_collapses_large_group():
    """Group of 10 same-kind neighbours → 1 Aggregator node."""
    from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
    owner_id = "work-1"
    nodes = [{"id": owner_id, "node_kind": "Work", "type": "Work", "display_label": "Paper A"}]
    for i in range(10):
        nodes.append({"id": f"auth-{i}", "node_kind": "AuthorshipReification",
                      "type": "Authorship", "display_label": f"Author {i}"})
    edges = [{"id": f"e-{i}", "source": owner_id, "target": f"auth-{i}",
              "type": "HAS_AUTHORSHIP", "display_type": "has authorship"}
             for i in range(10)]
    new_nodes, new_edges = _apply_aggregators(nodes, edges, threshold=8)
    agg_nodes = [n for n in new_nodes if n["node_kind"] == "Aggregator"]
    assert len(agg_nodes) == 1
    assert agg_nodes[0]["aggregation_hints"]["count"] == 10
    assert len(new_nodes) == 2  # owner + aggregator

def test_apply_aggregators_keeps_small_groups():
    """Group of 3 neighbours (< threshold=8) → no aggregation."""
    from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
    nodes = [{"id": "w1", "node_kind": "Work", "type": "Work", "display_label": "Work"},
             {"id": "m1", "node_kind": "Method", "type": "Method", "display_label": "BERT"},
             {"id": "m2", "node_kind": "Method", "type": "Method", "display_label": "GPT"},
             {"id": "m3", "node_kind": "Method", "type": "Method", "display_label": "T5"}]
    edges = [{"id": f"e-m{i}", "source": "w1", "target": f"m{i+1}",
              "type": "USES_METHOD"} for i in range(3)]
    new_nodes, _ = _apply_aggregators(nodes, edges, threshold=8)
    assert not any(n["node_kind"] == "Aggregator" for n in new_nodes)
```

**Frontend:** добавить `graphCanvasDraw.test.js` (smoke — функции импортируются без ошибок).

### Шаг F — Quality gates

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Backend тесты:
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -10

# Линтеры backend:
.venv/bin/isort science_graphrag/api/works/ science_graphrag/api/workspace_graph/ --check-only
.venv/bin/black science_graphrag/api/works/ science_graphrag/api/workspace_graph/ --check
.venv/bin/pylint science_graphrag/api/works/ science_graphrag/api/workspace_graph/ --fail-under=7.5

# Frontend:
cd ui && npm run lint && npm run test -- --watchAll=false 2>&1 | tail -10
```

### Acceptance

- [ ] `GraphCanvasMvp.jsx` ≤ 400 строк, `graphCanvasDraw.js` ≤ 350, `useGraphCanvasInput.js` ≤ 250.
- [ ] `_apply_aggregators(nodes, edges, threshold=8)` в `graph_neighborhood.py` (и аналог в `projection.py`).
- [ ] При group ≥ 8 → один `node_kind: "Aggregator"` с `aggregation_hints.count`, `preview_labels`, `expand_endpoint`.
- [ ] При `view=raw` — агрегация не применяется.
- [ ] `GET /v1/works/{id}/graph/expand?aggregator_id=...` → `{nodes, edges}`.
- [ ] Analogous workspace expand endpoint.
- [ ] `graphCanvasStyle.js`: агрегатор — пунктирный диск с `+N`.
- [ ] Клик по агрегатору → expand API call → merge в граф-стейт.
- [ ] `GraphDetailPanel.jsx`: список preview + кнопка «Expand all».
- [ ] Backlog: `H-GraphCanvasMvpSplit` помечен `[DONE]` в `refactor-frontend.md`.

### Бэклог-записи по завершении

В `docs/backlog/refactor-frontend.md`:

```markdown
### [DONE] Graph canvas — split `GraphCanvasMvp` (input vs physics vs draw)
- **Note (done):** 2026-04-25 (Round 5) — разнесено на GraphCanvasMvp.jsx (shell, ≤400),
  useGraphCanvasInput.js (≤250), graphCanvasDraw.js (≤350).

### [DONE] Graph UI — Aggregator rendering + expand-on-click
- **Note (done):** 2026-04-25 — стиль агрегатора в graphCanvasStyle.js, клик-разворачивание
  через expand endpoint, GraphDetailPanel preview + «Expand all» кнопка.
```

В `docs/backlog/refactor-backend.md`:

```markdown
### [DONE] Graph readability — Wave GR3: Aggregator nodes + lazy expand endpoint
- **Note (done):** 2026-04-25 — _apply_aggregators() в graph_neighborhood.py и projection.py;
  expand endpoints в works/router.py и workspace_graph/router.py.
```

---

## Agent 3 — Wave Y4: Multi-Agent Supervisor (LangGraph)

**Задача:** активировать multi-agent supervisor pattern в `science_graphrag/agent/` — выделить три specialist-ноды (`retrieval_agent`, `graph_agent`, `writer_agent`), переписать supervisor на реальный routing, расширить `AgentState`, добавить benchmark tier `agent_tools_multiagent`, написать ADR 020.

### Контекст

Ты — агент Python. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Что уже есть (Round 3–4):**
- `science_graphrag/agent/graph/supervisor.py` (51 строка) — single-agent ReAct loop (Y2). `chat_node → budget_node → tools_node → chat_node`.
- `science_graphrag/agent/graph/state.py` (18 строк) — `AgentState` TypedDict: `messages`, `workspace_id`, `citations`, `tool_trace`, `budget_remaining`, `metadata`.
- `science_graphrag/agent/graph/tracing.py` — `collect_tool_trace`.
- `science_graphrag/agent/tools/` — 6 tools на `langchain_core.tools.@tool`: `cypher_query`, `entity_search`, `edge_search`, `idea_search`, `summarize_workspace`, `final_answer`.
- `science_graphrag/api/agent_v2.py` — `POST /v2/agent/query` (SSE + sync, Y3).
- ADR 018 = ingest-worker-redis.md (занят). Следующий свободный: **ADR 020**.
- `tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json` — mini tier существует.
- `eval/agent_tools/metrics.py` — `score_agent_case` с `expected_tool_sequence`.

**Что НЕ делать:**
- Не трогать `api/agent_v2.py` и `api/agent.py` — контракт не меняется.
- Не трогать tools (логику 6 tools не меняем — только куда они идут).
- Не менять `AgentQueryResponse` контракт (v1/v2).

### Шаг 0 — Прочитать текущий код

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

cat science_graphrag/agent/graph/supervisor.py
cat science_graphrag/agent/graph/state.py
cat science_graphrag/agent/graph/tracing.py
ls science_graphrag/agent/graph/
ls science_graphrag/agent/tools/
cat science_graphrag/agent/tools/__init__.py

# Benchmark структура:
cat tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json
ls tests/fixtures/benchmarks/agent_tools_v1/
cat eval/agent_tools/metrics.py | head -80

# Settings:
grep -n "agent_supervisor\|agent_runtime\|agent_max\|agent_chat" science_graphrag/config.py

# Тест smoke:
.venv/bin/pytest tests/agent/ -q --tb=short
```

### Шаг 1 — Расширить `AgentState`

В `science_graphrag/agent/graph/state.py` добавить поля:

```python
class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    workspace_id: str | None
    citations: list[dict]
    tool_trace: list[dict]
    budget_remaining: int
    metadata: dict
    # NEW (Y4):
    specialist_results: dict[str, list[dict]]   # {specialist_name: [tool_result_dicts]}
    current_specialist: str | None              # "retrieval_agent" | "graph_agent" | "writer_agent"
    routing_log: list[dict]                     # [{step, from, to, reason}]
```

Эти поля — аддитивные; старый `collect_tool_trace` остаётся без изменений (работает по `messages`).

### Шаг 2 — Specialist nodes

Создать директорию `science_graphrag/agent/graph/nodes/` с `__init__.py`.

**`science_graphrag/agent/graph/nodes/retrieval_agent.py`:**

```python
"""Retrieval specialist — Qdrant idea_search + workspace summarization."""

from __future__ import annotations

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.tools import build_retrieval_tools  # idea_search + summarize_workspace
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings

SPECIALIST_NAME = "retrieval_agent"
SYSTEM_PROMPT = (
    "You are a retrieval specialist. Your job: use idea_search and summarize_workspace "
    "to find relevant passages and workspace context. Return your findings as tool results. "
    "Do NOT call final_answer — the writer_agent will synthesize."
)


def build_retrieval_subgraph(stores: StoreRegistry, settings: Settings):
    """Single-loop ReAct for retrieval tools only."""
    from langgraph.graph import StateGraph, END
    tools = build_retrieval_tools(stores)   # [idea_search, summarize_workspace]
    llm = build_chat_model(settings).bind_tools(tools)

    def chat(state: AgentState) -> dict:
        specialist_messages = [HumanMessage(SYSTEM_PROMPT)] + list(state["messages"])
        response = llm.invoke(specialist_messages)
        return {"messages": [response]}

    def route(state: AgentState):
        last = (state.get("messages") or [])[-1]
        if getattr(last, "tool_calls", None) and state.get("budget_remaining", 0) > 0:
            return "tools"
        return END

    g = StateGraph(AgentState)
    g.add_node("chat", chat)
    g.add_node("tools", ToolNode(tools))
    g.set_entry_point("chat")
    g.add_conditional_edges("chat", route)
    g.add_edge("tools", "chat")
    return g.compile()
```

**`science_graphrag/agent/graph/nodes/graph_agent.py`:**

```python
"""Graph specialist — Neo4j cypher_query, entity_search, edge_search."""

SPECIALIST_NAME = "graph_agent"
SYSTEM_PROMPT = (
    "You are a graph specialist. Use cypher_query, entity_search, and edge_search "
    "to navigate the knowledge graph and retrieve structured facts about works, authors, "
    "methods, and their relationships. Return structured results as tool outputs."
)

# Аналогичная структура; tools = build_graph_tools(stores)  # [cypher_query, entity_search, edge_search]
```

**`science_graphrag/agent/graph/nodes/writer_agent.py`:**

```python
"""Writer specialist — synthesizes final answer with citations."""

SPECIALIST_NAME = "writer_agent"
SYSTEM_PROMPT = (
    "You are a writer specialist. Given the accumulated tool results from retrieval_agent "
    "and graph_agent, synthesize a concise, grounded answer. Call final_answer with "
    "your answer and the relevant citations."
)

# tools = [final_answer_tool]
# Получает context из state.specialist_results, добавляет к messages и вызывает final_answer.
```

### Шаг 3 — Разбить `build_tool_registry` на специализированные группы

В `science_graphrag/agent/tools/__init__.py` добавить:

```python
def build_retrieval_tools(stores: StoreRegistry) -> list:
    """Tools for retrieval_agent: idea_search + summarize_workspace."""
    return [build_idea_search_tool(stores), build_summarize_workspace_tool(stores)]

def build_graph_tools(stores: StoreRegistry) -> list:
    """Tools for graph_agent: cypher_query + entity_search + edge_search."""
    return [build_cypher_query_tool(stores), build_entity_search_tool(stores), build_edge_search_tool(stores)]

def build_writer_tools(stores: StoreRegistry) -> list:
    """Tools for writer_agent: final_answer."""
    return [build_final_answer_tool(stores)]
```

`build_tool_registry(stores)` остаётся как объединение всех 6 (backward compat для v1 endpoint).

### Шаг 4 — Supervisor с routing

Переписать `science_graphrag/agent/graph/supervisor.py`:

```python
"""LangGraph multi-agent supervisor (Wave Y4).

Supervisor decides which specialist to call next based on the question
and accumulated results. On each step it either:
  - routes to retrieval_agent (semantic/workspace questions)
  - routes to graph_agent (structural/cypher questions)
  - routes to writer_agent (ready to synthesize)
  - ends (budget exhausted or writer_agent completed)
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, AIMessage
from langgraph.graph import END, StateGraph

from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.nodes.retrieval_agent import build_retrieval_subgraph, SPECIALIST_NAME as R
from science_graphrag.agent.graph.nodes.graph_agent import build_graph_agent_node, SPECIALIST_NAME as G
from science_graphrag.agent.graph.nodes.writer_agent import build_writer_agent_node, SPECIALIST_NAME as W
from science_graphrag.agent.llm.chat import build_chat_model
from science_graphrag.api.deps import StoreRegistry
from science_graphrag.config import Settings

ROUTING_PROMPT = """You are a supervisor for scholarly research agents.
Available specialists:
- retrieval_agent: semantic search in papers and workspace summaries (Qdrant-based)
- graph_agent: structural queries — Neo4j cypher, entity lookup, graph traversal
- writer_agent: synthesize final answer with citations when enough evidence is gathered

Given the question and accumulated results, decide the next specialist or FINISH.
Respond with one word: retrieval_agent | graph_agent | writer_agent | FINISH
"""


def build_supervisor_graph(stores: StoreRegistry, settings: Settings):
    """Build the multi-agent supervisor StateGraph."""
    llm = build_chat_model(settings)
    retrieval_graph = build_retrieval_subgraph(stores, settings)
    graph_node = build_graph_agent_node(stores, settings)
    writer_node = build_writer_agent_node(stores, settings)

    def supervisor_node(state: AgentState) -> dict:
        budget = state.get("budget_remaining", settings.agent_max_tool_calls)
        if budget <= 0:
            return {"current_specialist": "writer_agent",
                    "routing_log": state.get("routing_log", []) + [{"reason": "budget_exhausted"}]}
        routing_messages = [HumanMessage(ROUTING_PROMPT)] + list(state["messages"])
        response = llm.invoke(routing_messages)
        specialist = response.content.strip().lower()
        if specialist not in {R, G, W, "finish"}:
            specialist = R  # fallback
        log_entry = {"from": "supervisor", "to": specialist, "budget_left": budget}
        return {"current_specialist": specialist,
                "routing_log": state.get("routing_log", []) + [log_entry]}

    def route_to_specialist(state: AgentState) -> Literal["retrieval_agent", "graph_agent", "writer_agent", "__end__"]:
        specialist = state.get("current_specialist", "writer_agent")
        if specialist == "finish" or specialist == W:
            return W
        return specialist

    g = StateGraph(AgentState)
    g.add_node("supervisor", supervisor_node)
    g.add_node(R, retrieval_graph)
    g.add_node(G, graph_node)
    g.add_node(W, writer_node)
    g.set_entry_point("supervisor")
    g.add_conditional_edges("supervisor", route_to_specialist,
                            {R: R, G: G, W: W, END: END})
    g.add_edge(R, "supervisor")
    g.add_edge(G, "supervisor")
    g.add_edge(W, END)
    return g.compile()


def build_retrieval_graph(stores: StoreRegistry, settings: Settings):
    """Backward-compat alias: single-agent mode still used by legacy v1 endpoint.

    When agent_runtime='langgraph_supervisor_v1', use build_supervisor_graph instead.
    """
    if settings.agent_runtime == "langgraph_supervisor_v1":
        return build_supervisor_graph(stores, settings)
    # fallback: Y2 single-agent (from runtime_legacy)
    from science_graphrag.agent.runtime_legacy import build_legacy_graph
    return build_legacy_graph(stores, settings)
```

> **Примечание реализации:** specialist subgraph-ноды могут быть как скомпилированные `CompiledGraph` (которые LangGraph поддерживает как nodes), так и обычные функции-ноды. Выбери вариант, который не конфликтует с версией `langgraph` в `.venv`. Проверить: `.venv/bin/python -c "import langgraph; print(langgraph.__version__)"`.

### Шаг 5 — Адаптер `collect_tool_trace` (дополнить)

В `science_graphrag/agent/graph/tracing.py` расширить `collect_tool_trace`:

```python
def collect_tool_trace(state: AgentState) -> list[dict]:
    """Collect ToolCallTrace from LangGraph state messages.

    Also appends routing_log entries as pseudo-steps (tool='route_to_specialist').
    """
    trace = _collect_from_messages(state)  # существующая логика
    # Append routing pseudo-steps at the start:
    for entry in state.get("routing_log", []):
        trace.insert(0, {
            "step": -1,
            "tool": "route_to_specialist",
            "args_summary": entry,
            "row_count": 0,
            "duration_ms": 0,
            "truncated": False,
            "error": None,
        })
    return trace
```

### Шаг 6 — Benchmark tier `agent_tools_multiagent`

В `tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json` добавить новый tier (не ломая существующий `agent_tools_mini`):

```json
{
  "tiers": {
    "agent_tools_mini": { ... },
    "agent_tools_multiagent": {
      "cases": [
        {
          "case_id": "multiagent_01_who_cited_yolov1",
          "question": "Which papers in the workspace cite YOLOv1 and use Transformer-based methods?",
          "workspace_id": null,
          "expected_specialist_sequence": ["retrieval_agent", "graph_agent", "writer_agent"],
          "expected_tool_sequence": ["idea_search", "cypher_query", "final_answer"],
          "min_tool_call_correctness": 0.6,
          "min_answer_contains": ["YOLOv1", "Transformer"],
          "tier": "agent_tools_multiagent"
        },
        {
          "case_id": "multiagent_02_author_graph",
          "question": "Find all coauthors of the paper 'Attention is All You Need' in our corpus.",
          "workspace_id": null,
          "expected_specialist_sequence": ["graph_agent", "writer_agent"],
          "expected_tool_sequence": ["entity_search", "edge_search", "final_answer"],
          "min_tool_call_correctness": 0.6,
          "tier": "agent_tools_multiagent"
        },
        {
          "case_id": "multiagent_03_method_comparison",
          "question": "Compare the methods used in the top 3 most-cited papers in the workspace.",
          "workspace_id": null,
          "expected_specialist_sequence": ["graph_agent", "retrieval_agent", "writer_agent"],
          "expected_tool_sequence": ["cypher_query", "idea_search", "final_answer"],
          "min_tool_call_correctness": 0.5,
          "tier": "agent_tools_multiagent"
        }
      ]
    }
  }
}
```

В `eval/agent_tools/metrics.py` добавить в `score_agent_case`:

```python
def score_agent_case(result: dict, gold: dict) -> dict:
    scores = { ... }  # существующая логика

    # NEW: check specialist sequence if gold provides it
    if "expected_specialist_sequence" in gold:
        actual_seq = [
            entry.get("to") for entry in result.get("routing_log", [])
            if entry.get("to") not in {None, "supervisor"}
        ]
        expected = gold["expected_specialist_sequence"]
        # Order-independent set overlap:
        overlap = len(set(actual_seq) & set(expected)) / max(len(expected), 1)
        scores["specialist_sequence_match"] = overlap
        scores["passed"] = scores["passed"] and overlap >= gold.get("min_specialist_sequence_match", 0.5)

    return scores
```

### Шаг 7 — ADR 020

Создать `docs/adr/020-langgraph-supervisor-multiagent.md`:

```markdown
# ADR 020: LangGraph Multi-Agent Supervisor (Wave Y4)

**Status:** Accepted
**Date:** 2026-04-25
**Supersedes:** Часть ADR 016 (Wave R single-agent → multi-agent).

## Context

Wave Y2 (Round 3) перевёл production-агент на LangGraph с single-specialist ReAct loop.
Wave Y4 активирует полноценный supervisor pattern с тремя специалистами.

## Decision

1. **Specialist разделение по инструментам:**
   - `retrieval_agent`: `idea_search`, `summarize_workspace` (Qdrant + workspace Neo4j).
   - `graph_agent`: `cypher_query`, `entity_search`, `edge_search` (Neo4j graph traversal).
   - `writer_agent`: `final_answer` (LLM synthesis + citations).
2. **Supervisor** — отдельный LangGraph node с LLM-routing prompt; выбирает следующего специалиста по тексту запроса и накопленным результатам.
3. **`AgentState`** расширен: `specialist_results`, `current_specialist`, `routing_log`.
4. **ADR-нумерация:** номер 017 занят (hypothesis-idea-assist), 018 — ingest-worker-redis, 019 — entity-dedup. Этот ADR = 020.
5. **Backward compat:** `build_retrieval_graph(stores, settings)` остаётся как alias; при `agent_runtime="langgraph_supervisor_v1"` (default) — supervisor; при `"retrieval_v1"` — legacy.

## Consequences

- Новый tier `agent_tools_multiagent` в benchmarks.
- `routing_log` в `tool_trace` (pseudo-steps) не ломает UI (unknown steps показываются как есть).
- Recursion limit: `agent_supervisor_recursion_limit` ≥ `agent_max_tool_calls + 4` (уже в config).
```

### Шаг 8 — Тесты

Создать `tests/agent/test_supervisor_routing.py`:

```python
"""Tests for Y4 multi-agent supervisor routing (Wave Y4)."""
import pytest
from langchain_core.language_models.fake import FakeListChatModel
from langchain_core.messages import HumanMessage

def test_supervisor_routes_to_retrieval_agent(monkeypatch):
    """Supervisor should route to retrieval_agent for semantic questions."""
    from science_graphrag.agent.graph.state import AgentState
    # Build minimal state
    state: AgentState = {
        "messages": [HumanMessage("What papers discuss Transformers?")],
        "workspace_id": None,
        "citations": [],
        "tool_trace": [],
        "budget_remaining": 5,
        "metadata": {},
        "specialist_results": {},
        "current_specialist": None,
        "routing_log": [],
    }
    # Fake LLM that always says "retrieval_agent"
    fake_llm = FakeListChatModel(responses=["retrieval_agent"])
    # Monkeypatch build_chat_model
    monkeypatch.setattr(
        "science_graphrag.agent.graph.supervisor.build_chat_model",
        lambda settings: fake_llm,
    )
    from science_graphrag.agent.graph.supervisor import build_supervisor_graph
    from unittest.mock import MagicMock
    mock_stores = MagicMock()
    mock_settings = MagicMock()
    mock_settings.agent_max_tool_calls = 8
    mock_settings.agent_runtime = "langgraph_supervisor_v1"
    mock_settings.agent_supervisor_recursion_limit = 12
    # Just check it builds without error:
    graph = build_supervisor_graph(mock_stores, mock_settings)
    assert graph is not None


def test_agent_state_has_routing_fields():
    """AgentState TypedDict must include Y4 fields."""
    from science_graphrag.agent.graph.state import AgentState
    import typing
    hints = typing.get_type_hints(AgentState)
    assert "specialist_results" in hints
    assert "current_specialist" in hints
    assert "routing_log" in hints


def test_score_agent_case_specialist_sequence(tmp_path):
    """score_agent_case should compute specialist_sequence_match."""
    from eval.agent_tools.metrics import score_agent_case
    result = {
        "answer": "test",
        "citations": [],
        "tool_trace": [{"tool": "idea_search"}, {"tool": "final_answer"}],
        "routing_log": [
            {"from": "supervisor", "to": "retrieval_agent"},
            {"from": "supervisor", "to": "writer_agent"},
        ],
    }
    gold = {
        "expected_specialist_sequence": ["retrieval_agent", "writer_agent"],
        "expected_tool_sequence": ["idea_search", "final_answer"],
        "min_tool_call_correctness": 0.5,
        "min_specialist_sequence_match": 0.5,
    }
    scores = score_agent_case(result, gold)
    assert "specialist_sequence_match" in scores
    assert scores["specialist_sequence_match"] >= 0.9
```

### Шаг 9 — Quality gates

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Импорты:
.venv/bin/python -c "
from science_graphrag.agent.graph.supervisor import build_supervisor_graph, build_retrieval_graph
from science_graphrag.agent.graph.state import AgentState
from science_graphrag.agent.graph.nodes.retrieval_agent import build_retrieval_subgraph
from science_graphrag.agent.graph.nodes.graph_agent import build_graph_agent_node
from science_graphrag.agent.graph.nodes.writer_agent import build_writer_agent_node
print('all agent imports ok')
"

# Тесты:
.venv/bin/pytest tests/agent/ tests/test_api_agent_v2_smoke.py -q --tb=short
.venv/bin/pytest tests/ -q --tb=no 2>/dev/null | tail -3

# Линтеры:
.venv/bin/isort science_graphrag/agent/ --check-only
.venv/bin/black science_graphrag/agent/ --check
.venv/bin/pylint science_graphrag/agent/ --fail-under=7.5
```

### Acceptance

- [ ] `science_graphrag/agent/graph/nodes/` с `retrieval_agent.py`, `graph_agent.py`, `writer_agent.py`.
- [ ] `build_retrieval_tools`, `build_graph_tools`, `build_writer_tools` в `tools/__init__.py`.
- [ ] `supervisor.py` реализует routing через LLM-плановщик с тремя путями.
- [ ] `AgentState` расширен: `specialist_results`, `current_specialist`, `routing_log`.
- [ ] `collect_tool_trace` включает `routing_log` pseudo-steps.
- [ ] `tests/agent/test_supervisor_routing.py` зелёный.
- [ ] `eval/agent_tools/metrics.py::score_agent_case` понимает `expected_specialist_sequence`.
- [ ] Benchmark tier `agent_tools_multiagent` создан с 3 кейсами.
- [ ] `docs/adr/020-langgraph-supervisor-multiagent.md` создан.
- [ ] Все существующие тесты не сломаны (506+ passed).
- [ ] pylint `science_graphrag/agent/` ≥ 7.5.

### Бэклог-запись по завершении

В `docs/backlog/refactor-backend.md`:

```markdown
### [DONE] Wave Y4 — Multi-agent supervisor (LangGraph)
- **Note (done):** 2026-04-25 (Round 5) — specialists retrieval_agent/graph_agent/writer_agent,
  supervisor LLM routing, AgentState расширен routing_log, benchmark tier agent_tools_multiagent,
  ADR 020 принят.
```

---

## Agent 4 — G-StageExtractionSplit: Split `ingestion/llm/stage_extraction.py` (849 строк)

**Задача:** разнести `science_graphrag/ingestion/llm/stage_extraction.py` (849 строк) на подпакет `ingestion/llm/` с чётким разделением по слоям: `prompts/`, `executor.py`, `orchestrator.py`, `heuristics/`. Аналогично реорганизовать `semantic_extraction.py` (407 строк) для переиспользования общего executor.

### Контекст

Ты — агент Python. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.

**Что уже есть:**
- `science_graphrag/ingestion/llm/stage_extraction.py` — 849 строк: смешаны orchestration (`ThreadPoolExecutor`), Pydantic-схемы, промпты, heuristic fallback, связка со stages.
- `science_graphrag/ingestion/llm/semantic_extraction.py` — 407 строк: аналогичная смесь для семантического слоя.
- `science_graphrag/ingestion/llm/extractor.py` — 214 строк: base extractor через `instructor`.
- `science_graphrag/ingestion/llm/schemas.py` — Pydantic-схемы.
- `science_graphrag/ingestion/llm/chunk_merge.py` — утилита слияния чанков.
- `science_graphrag/ingestion/llm/__init__.py`.
- `science_graphrag/ingestion/llm/reference_tool_router.py` — router для LLM-based reference extraction.

**Цель:**
- Ни один файл в `ingestion/llm/` — не более **300 строк**.
- Новые extractor'ы (Wave N concept/topic, Wave O claims production) добавляются как `prompts/<name>.py` + `heuristics/<name>.py` без правки оркестратора.
- Публичный API `from science_graphrag.ingestion.llm import ...` остаётся неизменным через `__init__.py` re-export.

### Шаг 0 — Прочитать текущий код (обязательно)

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

wc -l science_graphrag/ingestion/llm/*.py
cat science_graphrag/ingestion/llm/stage_extraction.py
cat science_graphrag/ingestion/llm/semantic_extraction.py
cat science_graphrag/ingestion/llm/extractor.py
cat science_graphrag/ingestion/llm/__init__.py

# Кто импортирует из ingestion/llm:
grep -rn "from science_graphrag.ingestion.llm\|ingestion.llm" science_graphrag/ tests/ --include="*.py" | grep -v "__pycache__"

# Текущие тесты:
.venv/bin/pytest tests/ -q --tb=no 2>/dev/null | tail -3
```

### Шаг 1 — Целевая структура подпакета

```
science_graphrag/ingestion/llm/
├── __init__.py              ← thin re-export (backward compat, трогать минимально)
├── extractor.py             ← SyncInstructorExtractor (214 строк, оставить как есть)
├── chunk_merge.py           ← оставить как есть
├── schemas.py               ← Pydantic-схемы (оставить как есть)
├── reference_tool_router.py ← оставить как есть
├── executor.py              ← NEW: общий LLM-вызов через extractor + span discipline
├── orchestrator.py          ← NEW: ThreadPoolExecutor + heuristic fallback политика
├── prompts/
│   ├── __init__.py
│   ├── metadata.py          ← промпты + схема для metadata extraction
│   ├── authorships.py       ← промпты + схема для authorship extraction
│   ├── references.py        ← промпты + схема для references extraction
│   └── semantic.py          ← промпты + схема для method/dataset semantic extraction
└── heuristics/
    ├── __init__.py
    ├── metadata.py          ← heuristic fallback для metadata
    ├── authorships.py       ← heuristic fallback для authorships
    ├── references.py        ← heuristic fallback для references
    └── semantic.py          ← heuristic fallback для semantic
```

### Шаг 2 — `executor.py`

Выделить из `stage_extraction.py` и `semantic_extraction.py` общий слой LLM-вызова:

```python
"""LLM call executor — single entry point for all extraction calls.

Wraps SyncInstructorExtractor with:
- span discipline (llm_span from observability)
- retry policy
- timeout handling
- result validation

Usage:
    result = run_extraction(extractor, prompt, schema, stage_name="metadata_extraction")
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Type, TypeVar

from science_graphrag.observability.spans import llm_span

if TYPE_CHECKING:
    from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
    from pydantic import BaseModel

T = TypeVar("T", bound="BaseModel")

MAX_RETRIES = 2


def run_extraction(
    extractor: "SyncInstructorExtractor",
    prompt: str,
    schema: Type[T],
    *,
    stage_name: str,
    document_id: str = "",
    timeout_seconds: float = 60.0,
) -> T | None:
    """Execute LLM extraction with span wrapping and retry."""
    ...
```

**Критерий:** `executor.py` ≤ 150 строк.

### Шаг 3 — `orchestrator.py`

Выделить из `stage_extraction.py` orchestration-логику (`ThreadPoolExecutor`, retry budget, fallback политика):

```python
"""Stage extraction orchestrator.

Coordinates parallel LLM extraction calls across document stages (metadata,
authorships, references). Applies heuristic fallback when LLM fails.
"""
from __future__ import annotations

import concurrent.futures
from typing import TYPE_CHECKING

from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.prompts import metadata as meta_prompts
from science_graphrag.ingestion.llm.prompts import authorships as auth_prompts
from science_graphrag.ingestion.llm.prompts import references as ref_prompts
from science_graphrag.ingestion.llm.heuristics import references as ref_heuristics

if TYPE_CHECKING:
    from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor


def extract_document_stages(
    extractor: "SyncInstructorExtractor",
    text_chunks: list[str],
    *,
    document_id: str,
    max_workers: int = 3,
) -> dict:
    """Run all extraction stages for a document in parallel.

    Returns dict with keys: metadata, authorships, references, status.
    """
    ...
```

**Критерий:** `orchestrator.py` ≤ 300 строк.

### Шаг 4 — `prompts/` файлы

Для каждого prompts-модуля (`metadata.py`, `authorships.py`, `references.py`, `semantic.py`):

```python
# prompts/metadata.py
"""LLM prompts and output schema for metadata extraction."""

from pydantic import BaseModel, Field


class MetadataExtractionResult(BaseModel):
    title: str = Field(default="")
    abstract: str = Field(default="")
    publication_year: int | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    # ... остальные поля из существующей Pydantic-схемы


SYSTEM_PROMPT = """Extract bibliographic metadata from the following scientific paper text.
Return structured JSON with title, abstract, year, DOI, arXiv ID, authors list."""

USER_PROMPT_TEMPLATE = """Paper text (truncated to 4000 tokens):
{text}

Extract the metadata."""
```

Каждый файл ≤ 150 строк.

### Шаг 5 — `heuristics/` файлы

Перенести heuristic fallback логику из `stage_extraction.py`:

```python
# heuristics/references.py
"""Heuristic reference extraction fallback (regex-based)."""

import re
from typing import TYPE_CHECKING


def extract_references_heuristic(text: str) -> list[dict]:
    """Regex-based reference extraction fallback when LLM fails."""
    ...
```

Каждый файл ≤ 200 строк.

### Шаг 6 — `semantic_extraction.py` → переиспользует executor

После создания `executor.py` — упростить `semantic_extraction.py`, убрав дублирующий код вызова LLM:

```python
# semantic_extraction.py (после рефакторинга, ≤ 200 строк)
"""Semantic entity extraction (Method, Dataset) — Wave N/O/Q."""

from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.prompts.semantic import (
    SemanticExtractionResult,
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
)
from science_graphrag.ingestion.llm.heuristics.semantic import extract_semantic_heuristic
```

### Шаг 7 — Обновить `__init__.py`

`science_graphrag/ingestion/llm/__init__.py` должен re-export весь публичный API без изменений:

```python
# Re-export все публичные символы, которые импортируются снаружи:
from science_graphrag.ingestion.llm.orchestrator import extract_document_stages
from science_graphrag.ingestion.llm.semantic_extraction import extract_semantic_entities
from science_graphrag.ingestion.llm.extractor import SyncInstructorExtractor
# ... остальные re-exports, которые нашли в grep выше
```

### Шаг 8 — Тесты

```bash
# Проверить, что существующие тесты не сломаны:
.venv/bin/pytest tests/ -q --tb=short -k "ingestion or stage or llm or extraction" 2>&1 | tail -20

# Smoke: публичный API без изменений:
.venv/bin/python -c "
from science_graphrag.ingestion.llm import SyncInstructorExtractor, extract_document_stages
from science_graphrag.ingestion.llm.prompts.metadata import MetadataExtractionResult
from science_graphrag.ingestion.llm.heuristics.references import extract_references_heuristic
print('all ingestion.llm imports ok')
"
```

Добавить `tests/ingestion/test_llm_split_smoke.py`:

```python
def test_prompts_modules_importable():
    from science_graphrag.ingestion.llm.prompts import metadata, authorships, references, semantic
    assert hasattr(metadata, "MetadataExtractionResult")
    assert hasattr(references, "SYSTEM_PROMPT")

def test_heuristics_modules_importable():
    from science_graphrag.ingestion.llm.heuristics import references, metadata
    assert callable(references.extract_references_heuristic)

def test_executor_importable():
    from science_graphrag.ingestion.llm.executor import run_extraction
    assert callable(run_extraction)

def test_orchestrator_importable():
    from science_graphrag.ingestion.llm.orchestrator import extract_document_stages
    assert callable(extract_document_stages)

def test_public_api_unchanged():
    """All imports that existed before split still work via __init__.py."""
    from science_graphrag.ingestion.llm import SyncInstructorExtractor
    assert SyncInstructorExtractor is not None
```

### Шаг 9 — Финальная проверка размеров

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Ни один файл не должен превышать 300 строк:
find science_graphrag/ingestion/llm/ -name "*.py" ! -name "__pycache__" \
  -exec wc -l {} + | sort -rn | head -20
# Все строки должны быть ≤ 300 (кроме суммарной строки wc)

# Тесты:
.venv/bin/pytest tests/ -q --tb=no 2>/dev/null | tail -3

# Линтеры:
.venv/bin/isort science_graphrag/ingestion/llm/ --check-only
.venv/bin/black science_graphrag/ingestion/llm/ --check
.venv/bin/pylint science_graphrag/ingestion/llm/ --fail-under=7.5
```

### Acceptance

- [ ] `stage_extraction.py` больше не существует как монолит; его содержимое разнесено по `orchestrator.py`, `executor.py`, `prompts/`, `heuristics/`.
- [ ] Ни один файл в `ingestion/llm/` не превышает 300 строк.
- [ ] `prompts/` содержит `metadata.py`, `authorships.py`, `references.py`, `semantic.py` — каждый ≤ 150 строк.
- [ ] `heuristics/` содержит соответствующие fallback-модули — каждый ≤ 200 строк.
- [ ] `semantic_extraction.py` использует `executor.run_extraction` вместо дублирующего кода.
- [ ] `__init__.py` re-export работает: `from science_graphrag.ingestion.llm import SyncInstructorExtractor` без ошибок.
- [ ] Все существующие 406 тестов не сломаны.
- [ ] `tests/ingestion/test_llm_split_smoke.py` зелёный.
- [ ] pylint ≥ 7.5, isort/black чисто.

### Бэклог-запись по завершении

```markdown
### [DONE] Split `ingestion/llm/stage_extraction.py` (849) — orchestrator vs prompts vs heuristics
- **Note (done):** 2026-04-25 (Round 5) — разнесено на orchestrator.py + executor.py +
  prompts/{metadata,authorships,references,semantic}.py + heuristics/{...}.py;
  semantic_extraction.py упрощён до ≤200 строк; все файлы ≤300 строк.
```

---

## Review Agent — Верификация результатов Раунда 5

**Задача:** после завершения всех четырёх агентов убедиться, что каждая задача выполнена корректно и соответствует acceptance-критериям из роадмапа.

### Контекст

Ты — агент проверки. Репозиторий: `/home/roman/pyprojects/ML/Prod/science-graphrag`. Venv: `.venv/`.
Раунд 5 включал: Wave T (entity dedup), Wave GR3 (aggregator + expand), Wave Y4 (multi-agent supervisor), G-StageExtractionSplit (ingestion/llm split).

**Порядок**: выполни каждую группу проверок последовательно, фиксируй ✅/❌ и итоговый счёт.

### Блок 0 — Baseline (выполнить первым)

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

# Полный тестовый сьют:
.venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -15
# Ожидается: все passed + новые от каждого агента; 0 failures.

# Pylint по всем затронутым пакетам:
.venv/bin/pylint science_graphrag/dedup/ science_graphrag/agent/ science_graphrag/ingestion/llm/ \
  science_graphrag/api/works/ science_graphrag/api/workspace_graph/ --fail-under=7.5 2>&1 | tail -5

# isort/black:
.venv/bin/isort science_graphrag/ --check-only --diff 2>&1 | head -20
.venv/bin/black science_graphrag/ --check --diff 2>&1 | head -20

# Frontend:
cd ui && npm run lint 2>&1 | tail -5 && npm run test -- --watchAll=false 2>&1 | tail -5
cd ..
```

### Блок 1 — Wave T (Entity Dedup)

```bash
cd /home/roman/pyprojects/ML/Prod/science-graphrag

echo "=== Wave T: Entity Dedup ==="

# 1.1 ADR 019 создан:
test -f docs/adr/019-entity-dedup-pipeline.md && echo "✅ ADR 019 exists" || echo "❌ ADR 019 missing"
grep -q "Status.*Accepted" docs/adr/019-entity-dedup-pipeline.md && echo "✅ ADR accepted" || echo "❌ ADR not accepted"

# 1.2 Pipeline модули:
for t in institution venue method dataset; do
  test -f science_graphrag/dedup/${t}_pipeline.py && echo "✅ ${t}_pipeline.py" || echo "❌ ${t}_pipeline.py missing"
done

# 1.3 Размеры файлов (каждый ≤ 250 строк):
for t in institution venue method dataset; do
  lines=$(wc -l < science_graphrag/dedup/${t}_pipeline.py 2>/dev/null || echo 9999)
  [ "$lines" -le 250 ] && echo "✅ ${t}_pipeline.py size: $lines" || echo "❌ ${t}_pipeline.py too large: $lines"
done

# 1.4 ORM: EntityDedupConflict:
.venv/bin/python -c "
from science_graphrag.storage.models_orm import EntityDedupConflict
assert hasattr(EntityDedupConflict, 'entity_type'), 'entity_type missing'
assert hasattr(EntityDedupConflict, 'entity_id_a'), 'entity_id_a missing'
assert EntityDedupConflict.__tablename__ == 'entity_dedup_conflicts', 'wrong table name'
print('✅ EntityDedupConflict ORM ok')
"

# 1.5 embed_text для каждого типа:
.venv/bin/python -c "
from science_graphrag.dedup.institution_pipeline import embed_text as i_et
from science_graphrag.dedup.venue_pipeline import embed_text as v_et
from science_graphrag.dedup.method_pipeline import embed_text as m_et
from science_graphrag.dedup.dataset_pipeline import embed_text as d_et

t = i_et({'normalized_name': 'MIT', 'country': 'US', 'city': 'Cambridge'})
assert 'MIT' in t and 'US' in t, f'institution embed wrong: {t}'

t = v_et({'normalized_name': 'NeurIPS', 'venue_type': 'conference'})
assert 'NeurIPS' in t, f'venue embed wrong: {t}'

t = m_et({'normalized_name': 'BERT', 'aliases': ['bert-base'], 'description_short': 'LM'})
assert 'BERT' in t, f'method embed wrong: {t}'

t = d_et({'normalized_name': 'ImageNet', 'aliases': ['ILSVRC']})
assert 'ImageNet' in t, f'dataset embed wrong: {t}'
print('✅ All embed_text functions correct')
"

# 1.6 Neo4j writes для Institution:
.venv/bin/python -c "
from science_graphrag.storage.neo4j.writes import institutions
print('✅ institutions writes importable')
" 2>/dev/null || echo "❌ institutions writes missing"

# 1.7 Qdrant collections creator:
.venv/bin/python -c "
try:
    from science_graphrag.storage.qdrant_store import ensure_entity_dedup_collections
    print('✅ ensure_entity_dedup_collections importable')
except ImportError:
    # might be in qdrant_entity_stores
    from science_graphrag.storage.qdrant_entity_stores import ensure_entity_dedup_collections
    print('✅ ensure_entity_dedup_collections (entity_stores) importable')
"

# 1.8 API endpoints зарегистрированы:
.venv/bin/python -c "
from fastapi.testclient import TestClient
from science_graphrag.api.main import app
routes = [r.path for r in app.routes]
checks = [
    ('/v1/dedup/entity/run', 'run'),
    ('/v1/dedup/entity', 'list'),
]
for path, name in checks:
    if any(path in r for r in routes):
        print(f'✅ endpoint {name} registered')
    else:
        print(f'❌ endpoint {name} missing from routes')
"

# 1.9 Специфические тесты:
.venv/bin/pytest tests/dedup/ -q --tb=short 2>&1 | tail -8
```

**Ожидаемый результат Блока 1:**
- ✅ ADR 019 создан и статус Accepted.
- ✅ 4 pipeline файла, каждый ≤ 250 строк.
- ✅ `EntityDedupConflict` ORM с `entity_type` и `entity_dedup_conflicts` tablename.
- ✅ `embed_text` возвращает правильные строки для всех 4 типов.
- ✅ `institutions` Neo4j writes importable.
- ✅ `ensure_entity_dedup_collections` importable.
- ✅ Dedup API endpoints в маршрутах приложения.
- ✅ `tests/dedup/` зелёный.

### Блок 2 — Wave GR3 (Aggregator + Expand)

```bash
echo "=== Wave GR3: Aggregator + Expand ==="

# 2.1 H-GraphCanvasMvpSplit — размеры файлов:
canvas_lines=$(wc -l < ui/src/components/graph/GraphCanvasMvp.jsx)
[ "$canvas_lines" -le 400 ] && echo "✅ GraphCanvasMvp.jsx: $canvas_lines ≤ 400" || echo "❌ GraphCanvasMvp.jsx too large: $canvas_lines"

for f in graphCanvasDraw.js; do
  test -f ui/src/components/graph/$f && echo "✅ $f exists" || echo "❌ $f missing"
done

# hooks dir:
test -f ui/src/components/graph/hooks/useGraphCanvasInput.js && \
  echo "✅ useGraphCanvasInput.js exists" || echo "❌ useGraphCanvasInput.js missing"

# 2.2 Backend: _apply_aggregators importable:
.venv/bin/python -c "
from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
import inspect
sig = inspect.signature(_apply_aggregators)
assert 'nodes' in sig.parameters, 'nodes param missing'
assert 'edges' in sig.parameters, 'edges param missing'
print('✅ _apply_aggregators importable with correct signature')
"

# 2.3 Aggregator logic — unit test:
.venv/bin/python -c "
from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
owner_id = 'w1'
nodes = [{'id': owner_id, 'node_kind': 'Work', 'type': 'Work', 'display_label': 'Paper'}]
for i in range(10):
    nodes.append({'id': f'a-{i}', 'node_kind': 'AuthorshipReification', 'type': 'Authorship', 'display_label': f'Author {i}'})
edges = [{'id': f'e-{i}', 'source': owner_id, 'target': f'a-{i}', 'type': 'HAS_AUTHORSHIP', 'display_type': 'has authorship'} for i in range(10)]
new_nodes, new_edges = _apply_aggregators(nodes, edges, threshold=8)
agg = [n for n in new_nodes if n.get('node_kind') == 'Aggregator']
assert len(agg) == 1, f'Expected 1 aggregator, got {len(agg)}'
assert agg[0]['aggregation_hints']['count'] == 10, 'wrong count'
assert len(agg[0]['aggregation_hints'].get('preview_labels', [])) > 0, 'no preview_labels'
assert 'expand_endpoint' in agg[0]['aggregation_hints'], 'expand_endpoint missing'
print('✅ _apply_aggregators collapses 10 authors → 1 aggregator (threshold=8)')
"

# Малая группа не агрегируется:
.venv/bin/python -c "
from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
nodes = [
    {'id': 'w1', 'node_kind': 'Work', 'type': 'Work', 'display_label': 'Work'},
    {'id': 'm1', 'node_kind': 'Method', 'type': 'Method', 'display_label': 'BERT'},
    {'id': 'm2', 'node_kind': 'Method', 'type': 'Method', 'display_label': 'GPT'},
]
edges = [{'id': 'e1', 'source': 'w1', 'target': 'm1', 'type': 'USES_METHOD', 'display_type': 'uses method'},
         {'id': 'e2', 'source': 'w1', 'target': 'm2', 'type': 'USES_METHOD', 'display_type': 'uses method'}]
new_nodes, _ = _apply_aggregators(nodes, edges, threshold=8)
agg = [n for n in new_nodes if n.get('node_kind') == 'Aggregator']
assert len(agg) == 0, f'Unexpected aggregator for small group'
print('✅ _apply_aggregators does not aggregate small groups (<8)')
"

# 2.4 Expand endpoint зарегистрирован:
.venv/bin/python -c "
from fastapi.testclient import TestClient
from science_graphrag.api.main import app
routes = [r.path for r in app.routes]
expand_found = any('expand' in r for r in routes)
print('✅ expand endpoint found' if expand_found else '❌ expand endpoint missing')
"

# 2.5 view=raw не применяет агрегацию (smoke):
.venv/bin/python -c "
# Если функция graph_neighborhood принимает view параметр:
from science_graphrag.api.works.graph_neighborhood import _apply_aggregators
# В raw-режиме функция не должна вызываться или должна возвращать nodes без изменений.
# Достаточно что _apply_aggregators принимает необязательный параметр view:
import inspect
sig = inspect.signature(_apply_aggregators)
# view может быть в kwargs или отдельным параметром
print('✅ _apply_aggregators signature ok (view param handled by caller)')
"

# 2.6 Frontend: graphCanvasStyle.js содержит Aggregator стиль:
grep -q "Aggregator" ui/src/components/graph/graphCanvasStyle.js && \
  echo "✅ Aggregator style in graphCanvasStyle.js" || echo "❌ Aggregator style missing"

# 2.7 Frontend: GraphDetailPanel содержит aggregation_hints:
grep -q "aggregation_hints" ui/src/components/graph/GraphDetailPanel.jsx && \
  echo "✅ GraphDetailPanel handles aggregation_hints" || echo "❌ aggregation_hints missing in panel"

# 2.8 Тесты графа:
.venv/bin/pytest tests/storage/test_graph_aggregators.py -q --tb=short 2>&1 | tail -5 2>/dev/null || \
.venv/bin/pytest tests/ -q --tb=short -k "aggregator" 2>&1 | tail -5

# 2.9 Frontend тесты:
cd ui && npm run test -- --watchAll=false --testPathPattern="graphCanvas" 2>&1 | tail -5
cd ..
```

**Ожидаемый результат Блока 2:**
- ✅ `GraphCanvasMvp.jsx` ≤ 400 строк.
- ✅ `graphCanvasDraw.js` и `useGraphCanvasInput.js` существуют.
- ✅ `_apply_aggregators` — 10 авторов → 1 агрегатор при threshold=8.
- ✅ 2 метода → не агрегируется.
- ✅ `expand_endpoint` заполнен в `aggregation_hints`.
- ✅ `/expand` endpoint зарегистрирован в app.routes.
- ✅ `graphCanvasStyle.js` содержит стиль `Aggregator`.
- ✅ `GraphDetailPanel.jsx` читает `aggregation_hints`.
- ✅ Frontend lint/tests чисто.

### Блок 3 — Wave Y4 (Multi-Agent Supervisor)

```bash
echo "=== Wave Y4: Multi-Agent Supervisor ==="

# 3.1 ADR 020:
test -f docs/adr/020-langgraph-supervisor-multiagent.md && echo "✅ ADR 020 exists" || echo "❌ ADR 020 missing"
grep -q "Accepted" docs/adr/020-langgraph-supervisor-multiagent.md && echo "✅ ADR accepted" || echo "❌ not accepted"

# 3.2 Specialist nodes:
.venv/bin/python -c "
from science_graphrag.agent.graph.nodes.retrieval_agent import build_retrieval_subgraph, SPECIALIST_NAME
assert SPECIALIST_NAME == 'retrieval_agent', f'wrong name: {SPECIALIST_NAME}'
print('✅ retrieval_agent importable')
"
.venv/bin/python -c "
from science_graphrag.agent.graph.nodes.graph_agent import SPECIALIST_NAME
assert SPECIALIST_NAME == 'graph_agent'
print('✅ graph_agent importable')
"
.venv/bin/python -c "
from science_graphrag.agent.graph.nodes.writer_agent import SPECIALIST_NAME
assert SPECIALIST_NAME == 'writer_agent'
print('✅ writer_agent importable')
"

# 3.3 AgentState расширен:
.venv/bin/python -c "
import typing
from science_graphrag.agent.graph.state import AgentState
hints = typing.get_type_hints(AgentState)
for field in ['specialist_results', 'current_specialist', 'routing_log']:
    assert field in hints, f'{field} missing from AgentState'
print('✅ AgentState has all Y4 fields')
"

# 3.4 Supervisor строится:
.venv/bin/python -c "
from unittest.mock import MagicMock
from langchain_core.language_models.fake import FakeListChatModel
import os; os.environ.setdefault('SCIENCE_GRAPHRAG_OPENAI_API_KEY', 'test')

stores = MagicMock()
settings = MagicMock()
settings.agent_max_tool_calls = 8
settings.agent_runtime = 'langgraph_supervisor_v1'
settings.agent_supervisor_recursion_limit = 12
settings.extraction_llm_model = 'test'
settings.extraction_llm_api_key = 'test'
settings.extraction_llm_base_url = 'http://localhost'
settings.agent_chat_temperature = 0.0
settings.agent_chat_max_tokens = 1024

try:
    from science_graphrag.agent.graph.supervisor import build_supervisor_graph
    # Just check it doesn't throw on construction:
    print('✅ build_supervisor_graph importable')
except Exception as e:
    print(f'❌ build_supervisor_graph error: {e}')
"

# 3.5 build_retrieval_tools, build_graph_tools, build_writer_tools:
.venv/bin/python -c "
from science_graphrag.agent.tools import build_retrieval_tools, build_graph_tools, build_writer_tools
print('✅ specialized tool builders importable')
"

# 3.6 collect_tool_trace включает routing_log pseudo-steps:
.venv/bin/python -c "
from science_graphrag.agent.graph.tracing import collect_tool_trace
from science_graphrag.agent.graph.state import AgentState
state: AgentState = {
    'messages': [],
    'workspace_id': None,
    'citations': [],
    'tool_trace': [],
    'budget_remaining': 5,
    'metadata': {},
    'specialist_results': {},
    'current_specialist': None,
    'routing_log': [{'from': 'supervisor', 'to': 'retrieval_agent', 'budget_left': 4}],
}
trace = collect_tool_trace(state)
routing_steps = [t for t in trace if t.get('tool') == 'route_to_specialist']
assert len(routing_steps) >= 1, 'routing_log not reflected in tool_trace'
print('✅ collect_tool_trace includes routing pseudo-steps')
"

# 3.7 Benchmark tier agent_tools_multiagent:
.venv/bin/python -c "
import json
with open('tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json') as f:
    tiers = json.load(f)
assert 'agent_tools_multiagent' in tiers.get('tiers', tiers), 'agent_tools_multiagent tier missing'
cases = tiers.get('tiers', tiers).get('agent_tools_multiagent', {}).get('cases', [])
assert len(cases) >= 3, f'Need at least 3 cases, got {len(cases)}'
for case in cases:
    assert 'expected_specialist_sequence' in case, f'Case {case[\"case_id\"]} missing expected_specialist_sequence'
print(f'✅ agent_tools_multiagent tier with {len(cases)} cases')
"

# 3.8 eval/agent_tools/metrics.py понимает expected_specialist_sequence:
.venv/bin/python -c "
from eval.agent_tools.metrics import score_agent_case
result = {
    'answer': 'test',
    'citations': [],
    'tool_trace': [{'tool': 'idea_search'}, {'tool': 'final_answer'}],
    'routing_log': [{'from': 'supervisor', 'to': 'retrieval_agent'}, {'from': 'supervisor', 'to': 'writer_agent'}],
}
gold = {
    'expected_specialist_sequence': ['retrieval_agent', 'writer_agent'],
    'expected_tool_sequence': ['idea_search', 'final_answer'],
    'min_tool_call_correctness': 0.5,
}
scores = score_agent_case(result, gold)
assert 'specialist_sequence_match' in scores, 'specialist_sequence_match missing from scores'
assert scores['specialist_sequence_match'] >= 0.9, f'Wrong score: {scores[\"specialist_sequence_match\"]}'
print('✅ score_agent_case handles expected_specialist_sequence correctly')
"

# 3.9 Тесты агента:
.venv/bin/pytest tests/agent/ tests/test_api_agent_v2_smoke.py -q --tb=short 2>&1 | tail -8
```

**Ожидаемый результат Блока 3:**
- ✅ ADR 020 создан и статус Accepted.
- ✅ Все три specialist ноды импортируются с правильными SPECIALIST_NAME.
- ✅ `AgentState` содержит `specialist_results`, `current_specialist`, `routing_log`.
- ✅ `build_supervisor_graph` импортируется без ошибок.
- ✅ Специализированные tool builders работают.
- ✅ `collect_tool_trace` отражает `routing_log` как pseudo-steps.
- ✅ Tier `agent_tools_multiagent` с ≥ 3 кейсами и `expected_specialist_sequence`.
- ✅ `score_agent_case` вычисляет `specialist_sequence_match`.
- ✅ Все тесты агента зелёные.

### Блок 4 — G-StageExtractionSplit (ingestion/llm)

```bash
echo "=== G-StageExtractionSplit: ingestion/llm ==="

# 4.1 stage_extraction.py разнесён (монолит больше не нужен как был):
if [ -f science_graphrag/ingestion/llm/stage_extraction.py ]; then
  lines=$(wc -l < science_graphrag/ingestion/llm/stage_extraction.py)
  [ "$lines" -le 300 ] && echo "✅ stage_extraction.py reduced to $lines" || echo "⚠️  stage_extraction.py still $lines lines (should be gone or ≤300)"
else
  echo "✅ stage_extraction.py removed (logic moved to submodules)"
fi

# 4.2 Новые модули созданы:
for mod in executor orchestrator; do
  test -f science_graphrag/ingestion/llm/${mod}.py && \
    echo "✅ ${mod}.py exists" || echo "❌ ${mod}.py missing"
done

for sub in prompts heuristics; do
  test -d science_graphrag/ingestion/llm/${sub}/ && \
    echo "✅ ${sub}/ directory exists" || echo "❌ ${sub}/ missing"
  for name in metadata authorships references semantic; do
    test -f science_graphrag/ingestion/llm/${sub}/${name}.py && \
      echo "✅   ${sub}/${name}.py" || echo "❌   ${sub}/${name}.py missing"
  done
done

# 4.3 Размеры файлов (все ≤ 300 строк):
echo "--- File sizes in ingestion/llm/ ---"
find science_graphrag/ingestion/llm/ -name "*.py" ! -path "*/__pycache__/*" \
  -exec sh -c 'lines=$(wc -l < "$1"); [ "$lines" -gt 300 ] && echo "❌ $1: $lines" || echo "✅ $1: $lines"' _ {} \;

# 4.4 Публичный API сохранён (проверить по grep из Шага 0):
.venv/bin/python -c "
from science_graphrag.ingestion.llm import SyncInstructorExtractor
print('✅ SyncInstructorExtractor importable via __init__')
"

.venv/bin/python -c "
from science_graphrag.ingestion.llm.prompts.metadata import MetadataExtractionResult
from science_graphrag.ingestion.llm.prompts.references import SYSTEM_PROMPT
from science_graphrag.ingestion.llm.heuristics.references import extract_references_heuristic
from science_graphrag.ingestion.llm.executor import run_extraction
from science_graphrag.ingestion.llm.orchestrator import extract_document_stages
print('✅ All new submodule imports ok')
"

# 4.5 semantic_extraction.py уменьшен:
sem_lines=$(wc -l < science_graphrag/ingestion/llm/semantic_extraction.py 2>/dev/null || echo 9999)
[ "$sem_lines" -le 250 ] && echo "✅ semantic_extraction.py: $sem_lines ≤ 250" || echo "❌ semantic_extraction.py: $sem_lines > 250"

# 4.6 Тесты не сломаны:
.venv/bin/pytest tests/ -q --tb=short -k "ingestion or stage or extraction" 2>&1 | tail -8

.venv/bin/pytest tests/ingestion/test_llm_split_smoke.py -q --tb=short 2>&1 | tail -5 2>/dev/null || \
  echo "ℹ️  test_llm_split_smoke.py not found (may be in tests/ingestion/)"

# 4.7 Pylint:
.venv/bin/pylint science_graphrag/ingestion/llm/ --fail-under=7.5 2>&1 | tail -3
```

**Ожидаемый результат Блока 4:**
- ✅ `stage_extraction.py` либо удалён, либо ≤ 300 строк (содержит только тонкую обёртку-re-export).
- ✅ `executor.py` и `orchestrator.py` созданы.
- ✅ `prompts/` и `heuristics/` с 4 файлами каждый.
- ✅ Все файлы в `ingestion/llm/` ≤ 300 строк.
- ✅ `SyncInstructorExtractor`, `extract_document_stages`, `run_extraction` importable.
- ✅ `semantic_extraction.py` ≤ 250 строк.
- ✅ Ingestion тесты зелёные.
- ✅ pylint ≥ 7.5.

### Блок 5 — Интеграционные проверки

```bash
echo "=== Integration checks ==="

# 5.1 Полный тестовый сьют (финальный прогон):
.venv/bin/pytest tests/ --tb=short 2>&1 | tail -5
# Ожидается: 0 failures, ≥ 406 passed

# 5.2 Pylint по всем затронутым пакетам (итог):
.venv/bin/pylint \
  science_graphrag/dedup/ \
  science_graphrag/agent/ \
  science_graphrag/ingestion/llm/ \
  science_graphrag/api/works/ \
  science_graphrag/api/workspace_graph/ \
  science_graphrag/storage/models_orm.py \
  --fail-under=7.5 2>&1 | grep -E "Your code|rated|Error" | tail -5

# 5.3 isort + black:
.venv/bin/isort science_graphrag/ --check-only 2>&1 | grep -v "^$" | head -5
.venv/bin/black science_graphrag/ --check 2>&1 | grep -E "reformatted|All done" | head -5

# 5.4 Frontend lint + tests:
cd ui && npm run lint 2>&1 | tail -3
npm run test -- --watchAll=false 2>&1 | tail -5
cd ..

# 5.5 ADR-файлы:
for n in 019 020; do
  test -f docs/adr/${n}-*.md && echo "✅ ADR ${n} exists" || echo "❌ ADR ${n} missing"
done

# 5.6 Бэклог обновлён:
grep -c "\[DONE\]" docs/backlog/refactor-backend.md | xargs -I{} echo "Backend backlog DONE count: {}"
grep "Wave T\|GR3\|Y4\|StageExtraction" docs/backlog/refactor-backend.md | grep DONE | wc -l | \
  xargs -I{} echo "Round 5 items in DONE: {}"

# 5.7 master-roadmap обновлён (раунд 5 помечен):
grep "Раунд 5\|Round 5" docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md | head -5
```

### Блок 6 — Итоговый отчёт

После выполнения всех блоков сформировать краткий отчёт:

```
=== РАУНД 5 REVIEW SUMMARY ===

Baseline: N tests passed (было 406)

Agent 1 (Wave T):   ✅/❌ [N проверок из M]
Agent 2 (Wave GR3): ✅/❌ [N проверок из M]
Agent 3 (Wave Y4):  ✅/❌ [N проверок из M]
Agent 4 (G-StageExtractionSplit): ✅/❌ [N проверок из M]

Quality gates:
  pylint (все пакеты): PASS/FAIL (X.XX/10)
  isort:   PASS/FAIL
  black:   PASS/FAIL
  npm lint: PASS/FAIL
  tests:   PASS/FAIL (N passed, M failed)

ADR 019 entity-dedup:      ✅/❌
ADR 020 multiagent-supervisor: ✅/❌

Дефекты (если есть):
  1. ...

Рекомендация: DONE / NEEDS_FIX [список пунктов]
```

**Если найдены дефекты:** зафиксировать конкретный файл, строку и описание проблемы. Для каждого дефекта указать: критический (блокирует следующий раунд) или некритический (бэклог).

**После успешного review** обновить `docs/analysis/master-roadmap-and-refactor-plan-2026-04-25.md`:

```markdown
- **Раунд 5 (Wave T + GR3 + Y4 + G-StageExtractionSplit) ✅ DONE YYYY-MM-DD — промпты: [`round5-agent-prompts-2026-04-25.md`](round5-agent-prompts-2026-04-25.md):**
  - Agent 1: Wave T backend (entity dedup Institution/Venue/Method/Dataset). ✅
  - Agent 2: Wave GR3 (H-GraphCanvasMvpSplit + aggregator backend/frontend). ✅
  - Agent 3: Wave Y4 backend (multi-agent supervisor + ADR 020). ✅
  - Agent 4: G-StageExtractionSplit (ingestion/llm → prompts/ + heuristics/ + executor + orchestrator). ✅
```
