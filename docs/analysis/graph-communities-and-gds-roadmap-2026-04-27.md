# Graph communities & Neo4j GDS — план кластеризации, центральности и semantic zoom

**Дата:** 2026-04-27
**Статус:** living working doc, кандидат в треке E (Graph UX). Дополняет, **не заменяет** [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md): тот фокусируется на читаемости подписей и правой панели (Wave GR6–GR12), а здесь — про **структурную читаемость графа** (кластеризация, центральность, semantic zoom).

**Триггер:** На рабочем workspace с ~262 узлами / ~279 рёбер канвас выглядит «паутиной»: типы видны (легенда), отдельные авторы и работы — тоже, но **сообществ (тем, направлений, школ) глазом не различить**. Force-симуляция уже даёт легкую группировку через cluster-attraction, но нигде нет визуального ключа «вот эти узлы — один кластер»: ни цвета, ни обводки, ни подписи. Параллельно у нас есть `Settings.gds_enabled` и тонкая обёртка `_cypher_gds.py`, но **алгоритмы Neo4j GDS не используются вовсе** — даже Louvain/Leiden, даже PageRank.

**Что закрывает этот план:**
- одна полноценная серверная кластеризация (Leiden / Louvain) вместо фронтового union-find на одном edge-type;
- центральность узлов (PageRank/ArticleRank) для размера и сортировки;
- визуальное отображение сообществ на канвасе (цвет + hull-обводка + легенда);
- иерархический semantic zoom: на низком zoom видно «континенты» (supernodes-сообщества), при zoom-in они раскрываются;
- (опционально) layout по эмбеддингам узлов (FastRP + UMAP), сохраняющий семантическую близость.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`graph-readability-followup-2026-04-25.md`](./graph-readability-followup-2026-04-25.md) | Wave GR6–GR12 — читаемость подписей, тулбар, правая панель |
| [`../adr/011-graph-live-ux-and-payload.md`](../adr/011-graph-live-ux-and-payload.md) | Контракт payload `display_label / subtitle / display_type / node_kind` |
| [`../adr/012-workspace-graph-projection.md`](../adr/012-workspace-graph-projection.md) | Workspace 1-hop проекция, GDS-fallback |
| [`../specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) | Контракт API ↔ UI, normalize, лимиты |
| [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) | Здесь добавляем backlog GR-COM (см. §6.2) |
| [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | Здесь добавляем backlog GR-COM (см. §6.3) |
| [Neo4j GDS Louvain](https://neo4j.com/docs/graph-data-science/current/algorithms/louvain) / [Leiden](https://neo4j.com/docs/graph-data-science/current/algorithms/leiden/) / [Community Detection](https://neo4j.com/docs/graph-data-science/current/algorithms/community/) | Алгоритмы и контракт `mutate`/`write`/`stream` |
| [ZMLT, Luca et al., 2019](https://export.arxiv.org/pdf/1906.05996v2.pdf) / [Context-KG, 2026](https://www.arxiv.org/pdf/2604.10384) | Multi-level / focus+context для больших KG |

---

## 1. Диагноз: что есть, чего нет

### 1.1 Текущая «кластеризация» на фронте — это union-find на одном edge-type, не community detection

```9:58:ui/src/components/graph/canvas/physics/scienceHybridCommunities.js
export function detectScienceHybridCommunities(nodes, links) {
  ...
  const SEMANTIC_EDGE_TYPES = new Set(["HAS_AUTHORSHIP", "OF_AUTHOR", "AUTHORED"]);
  links.forEach((l) => {
    const t = l.type == null ? "" : String(l.type);
    if (!SEMANTIC_EDGE_TYPES.has(t)) return;
    if (!ids.has(l.source) || !ids.has(l.target)) return;
    union(l.source, l.target);
  });
```

То есть «семантический кластер» в нашем смысле — это **связная компонента по рёбрам авторства**, без учёта `USES_METHOD`, `EVALUATED_ON`, `CITES`, `PUBLISHED_IN`. Кластеры выходят слишком крупные и не отражают тематические сообщества (а только «соавторские когорты»).

LPA в [`structuralCommunities.js`](../../ui/src/components/graph/canvas/physics/structuralCommunities.js) реализован, но **нигде не вызывается** (`grep detectCommunities` по `ui/` находит только сам файл и его тест). Это мёртвый код.

### 1.2 Кластеры влияют только на физику, нигде не визуализируются

Hybrid-кластеры используются единственным образом:

```298:319:ui/src/hooks/graph/useScienceGraphForceSimulation.js
if (communitiesRef.current && communityMap.size > 0) {
  const nodeCluster = getNodeCluster(node.id, communitiesRef.current);
  if (nodeCluster) {
    const clusterNodes = communityMap.get(nodeCluster) || [];
    clusterNodes.forEach((otherId) => {
      ...
      const communityForce = dist * CLUSTER_ATTRACTION_STRENGTH * coolingTemperatureRef.current;
```

`CLUSTER_ATTRACTION_STRENGTH = 0.0003` ([`simConstants.js`](../../ui/src/components/graph/canvas/physics/simConstants.js)). Никакого цвета по кластеру, никакой подписи, никакой обводки. Юзер видит «магнитное» поведение, но не понимает, **что за кластер**.

### 1.3 Backend GDS-обвязка есть, но без алгоритмов

```16:21:science_graphrag/api/workspace_graph/_cypher_gds.py
def gds_runtime_available(session: Any) -> bool:
    try:
        session.run("RETURN gds.version() AS v").consume()
        return True
    except Exception:
        return False
```

`_cypher_gds.py` использует только `gds.graph.project.cypher` + `gds.graph.relationshipStream` — это «GDS как кэш проекции», не «GDS как алгоритмы». Нигде не вызываются `gds.louvain.*`, `gds.leiden.*`, `gds.pageRank.*`, `gds.fastRP.*`, `gds.nodeSimilarity.*`.

`Settings.gds_enabled = False` по умолчанию ([`config.py:462-468`](../../science_graphrag/config.py)). В docker-compose плагин GDS присутствует.

### 1.4 Нет центральности

Размер узла — константа `NODE_RADIUS = 12`. PageRank/ArticleRank/Degree не считаются ни на бэке, ни на фронте. Пользователь не видит, какая работа в текущем подграфе самая «востребованная», какой автор — самый цитируемый.

### 1.5 Нет multi-level visualization

Aggregator есть только локально: per-Work и при ≥ 8 соседях одного `(node_kind, edge_type)` ([`apply_workspace_aggregators`](../../science_graphrag/api/workspace_graph/projection.py)). Это **не** иерархический zoom: на любом масштабе показывается один и тот же набор узлов, просто с разным масштабом точек.

Состояние уровня индустрии: ZMLT/GraphMaps/Cosmograph/yFiles используют **multi-level layouts** с persistence (узлы и рёбра не пропадают между уровнями) и precomputed-сообществами. У нас это всё «на бумаге» — Leiden/Louvain дают `includeIntermediateCommunities: true` практически бесплатно, но мы их не используем.

### 1.6 Layout — только force/circle

В canvas-режиме два layout-mode: `force` и `circle` ([`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx)). Нет:
- layout по эмбеддингам узлов (FastRP/Node2Vec → UMAP/t-SNE → 2D),
- иерархического (radial / Sugiyama) для деревьев цитирований,
- layout «по сообществам» (узлы одного community собраны в локальный force-блок, блоки — в общий force).

### 1.7 Сводка: пять отсутствующих слоёв

| Слой | Текущее состояние | Что нужно |
|------|-------------------|-----------|
| Алгоритм сообществ | union-find по 3 edge-types на фронте | Leiden / Louvain (бэкенд GDS), все семантические рёбра, кэш в Neo4j как property |
| Центральность узла | константа | PageRank / ArticleRank, кэш в Neo4j; в UI — размер, сортировка |
| Цветовая схема | по `node_kind` (форма-тип) | + по `community_id` (тема), переключатель |
| Hull / region rendering | нет | convex/concave hull для каждого community, alpha-fill + label |
| Multi-level | нет | hierarchical Leiden, API zoom-level, supernodes на низком zoom |

---

## 2. Wave GR-COM-1 — short horizon (1–2 дня, frontend-only)

**Цель:** дать пользователю **визуальную кластеризацию прямо сейчас**, без backend-изменений и без зависимости от GDS. Использовать уже реализованный, но мертвый LPA + покрасить узлы.

**Принцип:** не претендовать на «правильный» Leiden — у нас уже есть LPA и connected-components-by-authorship, **их достаточно для бóльшей читаемости на 100–500 узлах**. Серверный Leiden появится в Wave GR-COM-2.

### 2.1 Чеклист (frontend)

- [ ] **Активировать LPA** в [`useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js): новая функция `detectCommunitiesForUi(nodes, links, options)` в [`physics/structuralCommunities.js`](../../ui/src/components/graph/canvas/physics/structuralCommunities.js) → принимает hybrid-кластеры (для тяжёлой связности через авторство) **и** LPA-кластеры (для тематической связности через `USES_METHOD`, `EVALUATED_ON`, `CITES`, `PUBLISHED_IN`), мерджит: hybrid имеет приоритет, LPA дробит крупные hybrid-кластеры внутри себя на подкластеры если LPA-метка отличается у > 30% узлов.
- [ ] **Цветовая палитра по communityId** — новый модуль [`physics/communityPalette.js`](../../ui/src/components/graph/canvas/physics/communityPalette.js) с детерминированным `colorForCommunity(communityId, appearance)`: HSL по hash(id) с фиксированной saturation/lightness под темную/светлую тему, чтобы цвета были стабильны между прогонами. Палитра ограничена ~16 цветами — большие community-id маппятся в общий нейтральный «прочее».
- [ ] **Режим раскраски `colorBy`** — новый prop `colorBy: "type" | "community"` для [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx) с persist в LS (`graphCanvasColorBy`). По умолчанию — `type` (не ломаем существующее поведение).
- [ ] **Drawing path** — в [`graphCanvasDraw.js drawNodes`](../../ui/src/components/graph/canvas/graphCanvasDraw.js) принимать `colorBy` и `nodeCommunityMap`. Для `colorBy=community`: fill = `colorForCommunity(communityId)`, обводка = текущий цвет по типу (с alpha 0.5), форма = текущая (по типу). Это даёт ровно нужный продукт: «цвет = тема, форма = роль узла».
- [ ] **Hulls (опционально, behind toggle)** — модуль [`graphCanvasDrawCommunityHulls.js`](../../ui/src/components/graph/canvas/graphCanvasDrawCommunityHulls.js): для каждого community с ≥ 3 узлами строим convex hull через [d3-polygon](https://github.com/d3/d3-polygon) (~6KB gzipped, новая зависимость), рендерим полупрозрачным fill (`alpha=0.06`) с pad 24 world-units и тонким stroke (`alpha=0.25`). Подпись `Cluster #N · k узлов` рисуется в центре hull. Включается отдельным toggle в `GraphCanvasViewToolbar`.
- [ ] **Toolbar UI** — в [`GraphCanvasViewToolbar.jsx`](../../ui/src/components/graph/canvas/GraphCanvasViewToolbar.jsx) добавить группу «Раскраска»: `<ToggleButtonGroup value={colorBy}>` с пунктами «по типу» / «по сообществу». Отдельный switch «Контуры сообществ» (только активен, когда `colorBy=community`).
- [ ] **Легенда** — в [`GraphTypeLegend.jsx`](../../ui/src/components/graph/shell/GraphTypeLegend.jsx) добавить вторую сворачиваемую секцию «Сообщества (N)»: список топ-N (по размеру) сообществ с цветным кружком, счетчиком узлов и preview из 2–3 представительных меток (можно взять `displayLabel` 3 случайных / самых-цитируемых-в-топологии узлов). Activates когда `colorBy=community`.
- [ ] **i18n** — ключи `graph.community.colorByType` / `graph.community.colorByCluster` / `graph.community.toggleHulls` / `graph.community.legendTitle` / `graph.community.legendItem.label` (с `{{count}}`) в EN+RU `partGraphUi.js`.
- [ ] **Тесты:**
  - `src/components/graph/canvas/physics/communityPalette.test.js` — детерминированность цветов, симметрия light/dark.
  - `src/components/graph/canvas/physics/structuralCommunities.test.js` — расширить под новый `detectCommunitiesForUi`.
  - `ui/src/components/graph/canvas/graphCanvasDraw.test.js` — рендер с `colorBy=community` использует палитру.

### 2.2 Acceptance

1. На workspace 100+ узлов user видит 5–15 цветных «облаков», совпадающих визуально с тем, как force-симуляция и так группирует.
2. Toggle «Контуры сообществ» рисует hull-фон под каждым облаком с подписью.
3. Легенда показывает топ-сообществ с preview-метками.
4. EN/RU локали покрыты.
5. Performance: на 500 узлах FPS не падает ниже 30 (LPA до 10 итераций детерминирован, hull считается только на изменение `topologySignature`).
6. Поведение по умолчанию (`colorBy=type`) не меняется — regression-safe.

### 2.3 Ориентир

1 frontend-PR, ~1.5 дня (с тестами), без backend.

---

## 3. Wave GR-COM-2 — middle horizon (5–8 дней, backend-first)

**Цель:** перейти с фронтового LPA на **серверный Leiden + PageRank** через Neo4j GDS, кэшировать результаты в Neo4j как свойства узлов, отдавать в payload, использовать в UI для размера, цвета, фильтра.

### 3.1 Backend (3–4 дня)

#### 3.1.1 Новый модуль `science_graphrag/api/workspace_graph/communities.py`

```python
def compute_workspace_communities(
    session: Any,
    workspace_id: str,
    *,
    algorithm: Literal["leiden", "louvain"] = "leiden",
    edge_weights: dict[str, float] | None = None,
    include_intermediate: bool = True,
    write_property: str = "leiden_community_id",
    pagerank_property: str = "page_rank",
) -> dict[str, Any]:
    """
    Project workspace subgraph into GDS, run Leiden + PageRank, write results back to Neo4j as
    node properties, drop projection. Returns: { modularity, communities_count, sizes, ... }.
    """
```

Контракт проекции:
- **Узлы:** все узлы 1-hop окрестности от `(:Workspace {id: $wid})-[:CONTAINS]->(:Work)`, типы `Work`, `Author`, `Method`, `Dataset`, `Venue`, `Institution`. `Authorship`-reified отбрасываются (заменяются на virtual edge `Work-AUTHORED-Author`). `Claim` — отдельным флагом `include_claims`.
- **Рёбра:** undirected (требование Leiden/Louvain), типы из whitelist `{HAS_AUTHORSHIP, OF_AUTHOR, AFFILIATED_WITH, CITES, PUBLISHED_IN, USES_METHOD, EVALUATED_ON, TRAINED_OR_TESTED_ON}`. Веса по таблице `EDGE_WEIGHTS_DEFAULT` (см. §3.4 Open Q1).
- **Алгоритм:** `gds.leiden.write` с `relationshipWeightProperty="weight"`, `includeIntermediateCommunities=true`, `maxLevels=4`. Fallback на `gds.louvain.write`, если Leiden недоступен (см. Open Q2).
- **PageRank:** `gds.pageRank.write` с `relationshipWeightProperty="weight"`, `dampingFactor=0.85`. Записывается в свойство `page_rank`.
- **Idempotency:** в начале — `gds.graph.drop(workspace_projection_name, false)`. В finally — `drop` повторно. Сама запись в Neo4j через `write` идемпотентна (overwrite property).

#### 3.1.2 Триггеры пересчёта

- **После ingest workspace:** в [`ingest/_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py) после успешного `add_work_to_workspace` — async-задача `recompute_communities(workspace_id)`. **Не блокирует** ingest.
- **По расписанию:** Dramatiq-периодик каждые 6 часов (см. Open Q3).
- **По запросу:** новый CLI `science-graphrag recompute-communities <workspace_id> [--algorithm leiden|louvain]` для оператора.
- **Pre-flight skip:** если `not settings.gds_enabled` или `not gds_runtime_available` → log-warning и тихий skip; payload отдаётся без community-полей (UI fallback на Wave 1 LPA).

#### 3.1.3 Расширение payload

В [`workspace_graph/projection.py`](../../science_graphrag/api/workspace_graph/projection.py) `node_dict_from_neo`:

```python
center_props["community_id"] = props.get("leiden_community_id")  # int | None
center_props["community_path"] = props.get("leiden_community_path")  # list[int] | None
center_props["page_rank"] = props.get("page_rank")  # float | None
```

В `meta` агрегата:

```python
meta["communities"] = {
    "algorithm": "leiden",
    "modularity": float,                     # из последнего пересчёта
    "count": int,                            # число community
    "computed_at": str,                      # ISO timestamp
    "size_distribution": {community_id: count},
    "stale": bool,                           # true, если payload собирается без актуального пересчёта
}
```

#### 3.1.4 Тесты

- `tests/api/workspace_graph/test_communities.py`:
  - на 50-узловом fixture (`tests/fixtures/graph/workspace_50nodes.json`) — modularity > 0.3.
  - стабильность: два прогона подряд дают идентичные ID (с фиксированным `randomSeed`).
  - изоляция: `recompute_communities(ws_a)` не трогает `ws_b`.
  - GDS-not-available: pipeline продолжает работать, payload без community-полей, `meta.communities.stale=true`.
- `tests/cli/test_recompute_communities.py`:
  - CLI выводит `modularity`, `count`, `computed_at`.
  - non-zero exit при ошибке проекции.

#### 3.1.5 Инфраструктура

- **`Settings.communities_*`:**
  - `communities_algorithm: Literal["leiden", "louvain"] = "leiden"`,
  - `communities_recompute_interval_hours: int = 6`,
  - `communities_edge_weights_json: str = ""` (override через env/.env, дефолт — `EDGE_WEIGHTS_DEFAULT` в коде).
- **`docker-compose.yml`:** ingest worker уже подключён к Neo4j; флаг `SCIENCE_GRAPHRAG_GDS_ENABLED=1` добавить в `.env.example` с комментарием «требует neo4j-graph-data-science плагин».
- **`config-check`:** в `science-graphrag config-check` добавить строку `gds: enabled / available / version`.

### 3.2 Frontend (2–3 дня)

#### 3.2.1 Размер узла по PageRank

- В [`graphSimulationAdapter.js buildSimulationState`](../../ui/src/components/graph/model/graphSimulationAdapter.js) пробрасывать `page_rank` в `SimNode`.
- В [`graphCanvasDraw.js drawNodes`](../../ui/src/components/graph/canvas/graphCanvasDraw.js): `radius = NODE_RADIUS * (1 + PR_BOOST * normalize(pageRank))`, где `normalize` — min-max по текущему displayGraph, `PR_BOOST = 1.2` (clamp в [10, 32]).
- Toggle «Размер по важности» в `GraphCanvasViewToolbar` (persist `graphCanvasSizeByPageRank`).

#### 3.2.2 Server-side communityId с graceful fallback

- В [`graphViewState.js normalizeGraphPayload`](../../ui/src/components/graph/model/graphViewState.js) — нормализовать `properties.community_id` → `node.communityId`, `properties.community_path` → `node.communityPath`, `properties.page_rank` → `node.pageRank`.
- В `useScienceGraphForceSimulation`: если у ≥ 80% узлов есть `communityId` от сервера — **использовать его** вместо LPA. Иначе — Wave 1 LPA fallback. Логировать в `meta.communities_source: "server" | "client_lpa"`.
- В `GraphTypeLegend` секция «Сообщества» при `server`-источнике показывает дополнительный бейдж «modularity {value}» из `meta.communities.modularity`.

#### 3.2.3 Фильтр по сообществу

- В [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx) (или новой обёртке `GraphTopBar` из GR10) — `<Select>` «Сообщество: Все / #1 (32 узла) / #2 (24 узла) / …». При выборе один — фильтр в [`graphVisibilityFilter.js`](../../ui/src/components/graph/model/graphVisibilityFilter.js) скрывает все, кроме выбранного community и его 1-hop окрестности.

#### 3.2.4 Hulls с серверной стабильностью

- Тот же `graphCanvasDrawCommunityHulls.js` из Wave 1, но теперь подпись «Сообщество #N» заменяется на детерминированный label из метаданных:
  - сначала пробуем `meta.communities.labels[community_id]` (см. Open Q4 — нужен ли LLM-генерируемый label),
  - иначе — top-3 `displayLabel` представительных узлов (по PageRank внутри community).

#### 3.2.5 Тесты

- `ui/src/components/graph/model/graphSimulationAdapter.test.js` — `buildSimulationState` пробрасывает `pageRank` / `communityId`.
- `ui/src/components/graph/model/graphViewState.test.js` — `normalizeGraphPayload` сохраняет `community_id`.
- `tests/hooks/graph/useScienceGraphForceSimulation.test.js` (новый) — выбор source `server` vs `client_lpa`.

### 3.3 Acceptance (Wave GR-COM-2)

1. CLI `science-graphrag recompute-communities <wid>` записывает в Neo4j свойства `leiden_community_id` / `leiden_community_path` / `page_rank` для всех узлов 1-hop окрестности; modularity > 0.3 на корпусном тестовом workspace.
2. UI на этом workspace показывает цветные сообщества с server-side стабильными ID; при повторе ingest той же работы окраска не «прыгает».
3. Размер узла на канвасе отражает PageRank (визуально: top-cited работа крупнее в 1.5–2 раза).
4. Фильтр «Сообщество: #N» скрывает остальное.
5. Когда `gds_enabled=false` или плагин не установлен — UI не падает: рисуется Wave 1 fallback (LPA + размер-константа).
6. Pytest зелёный, vitest зелёный.

### 3.4 Open questions для Wave GR-COM-2

#### Q1. Какие веса рёбер использовать для Leiden?

| Edge type | Семантика | Предлагаемый вес |
|-----------|-----------|------------------|
| `HAS_AUTHORSHIP` / `OF_AUTHOR` / `AUTHORED` | Авторство | 1.0 |
| `AFFILIATED_WITH` | Аффилиация | 0.5 |
| `CITES` | Цитирование | 0.7 |
| `PUBLISHED_IN` | Площадка публикации | 0.3 |
| `USES_METHOD` | Метод | 0.8 |
| `EVALUATED_ON` / `TRAINED_OR_TESTED_ON` | Датасет | 0.6 |

**Аргумент:** авторство держит соавторские когорты, методы и цитирование — тематические сообщества; venue даёт слабую связку «школа», но не должна доминировать. **Альтернативы:** все веса = 1.0 (тогда сообщества будут больше управляться плотностью, чем семантикой); веса из настроек (`Settings.communities_edge_weights_json`); веса по `confidence`/`year` (для CITES — затухание во времени).

**Предложение:** в первой итерации фиксированные веса в коде + опция override через env.

#### Q2. Leiden или Louvain первым?

- **Leiden:** точнее, гарантирует connected communities ([Traag et al.](https://neo4j.com/docs/graph-data-science/current/algorithms/leiden/)), доступен в GDS 2.x.
- **Louvain:** быстрее, проще, есть на любом GDS, но может давать «несвязные» community.

**Предложение:** Leiden как default (`Settings.communities_algorithm="leiden"`), Louvain как fallback при `randomSeed` нестабильности или ошибке плагина. Оба алгоритма поддерживают одинаковый контракт `mutate`/`write` — переключение тривиально.

#### Q3. Когда пересчитывать?

- **После каждого `add_work_to_workspace`:** консистентно, но дорого если в workspace 1000 работ (Leiden ~секунды-десятки секунд).
- **По cron/Dramatiq каждые 6h:** дёшево, но «свежий ingest» 10 минут будет без обновлённых сообществ.
- **Lazy при первом запросе графа после ingest:** триггер ленивый, но добавляет latency на первый view.

**Предложение:** `recompute` async-задача после `add_work_to_workspace` (не блокирует ingest, в фоне). Дополнительно — Dramatiq-периодик каждые 6h как safety net. Ручной CLI/endpoint — для оператора. Если задача в очереди — UI получает `meta.communities.stale=true` и показывает badge «обновляется».

#### Q4. Нужен ли LLM-сгенерированный label для community?

«Сообщество #3 (32 узла) — `XRAG, mBART, NLLB, …`» против «Сообщество #3 — *Multilingual translation models*».

- **За LLM-label:** UX качественнее, юзер сразу понимает тему.
- **Против:** доп. вызов LLM, стоимость, шум при нестабильных кластерах, требует новой инфраструктуры.

**Предложение:** в Wave GR-COM-2 — **без LLM**, top-3 representative по PageRank как label. LLM-label — отдельный backlog item Wave GR-COM-2.5 (опциональный спайк): после стабилизации Leiden запросить LLM «дай 2-3 слова на тему этих 10 заголовков», закэшировать в Neo4j (`Community {id, label, computed_at}`).

#### Q5. Совместимость с существующей aggregator-логикой

`apply_workspace_aggregators` ([`workspace_graph/projection.py`](../../science_graphrag/api/workspace_graph/projection.py)) сейчас сворачивает `(Work, kind, edge_type)` если соседей ≥ 8.

**Предложение:** оставить как есть — это **дополняющая** механика, работает **внутри** одного Work-узла. Community — между узлами, агрегатор — внутри узла. Они не конфликтуют. Возможно, в Wave GR-COM-3 introduce **community-level aggregator** (свернуть всё сообщество в supernode на низком zoom), это уже надстройка.

#### Q6. Скоп projection — Work-only или полный?

- **Work-only:** дешевле, Leiden работает быстрее, но теряем кластеризацию по методам/датасетам.
- **Полный (Work + Author + Method + Dataset + Venue + Institution + Authorship-virtual):** богаче, более семантически осмысленно, дороже.

**Предложение:** полный (без Authorship-reified — заменяем virtual `Work-AUTHORED-Author`). Это даёт настоящее тематическое сообщество. На корпусе ~5k работ (~80k узлов) Leiden справляется за десятки секунд.

#### Q7. Изоляция между workspace

Сообщества в workspace A не должны влиять на workspace B. Но узлы могут принадлежать обоим (один Author может быть в нескольких workspace).

**Предложение:** хранить community как массив по workspace: вместо `node.leiden_community_id` (скаляр) — `node.leiden_communities: dict[workspace_id, community_id]`. На write-time всегда указываем target workspace. UI читает `properties.community_id` с уже отфильтрованным значением для текущего ws (преобразование в `workspace_graph/projection.py`).

**Альтернатива (упрощение):** один community_id на узел, обновляется последним пересчитавшим workspace. Дешевле, но кросс-workspace несостоятельность. Допустимо для MVP.

---

## 4. Wave GR-COM-3 — long horizon (10–15 дней, semantic zoom + embeddings)

**Цель:** доехать до multi-level visualization уровня ZMLT/GraphMaps + опциональный layout по эмбеддингам узлов. **Не блокирует Wave GR-COM-2.**

### 4.1 Hierarchical communities

**Backend:**

1. Использовать `gds.leiden.write` с `includeIntermediateCommunities: true` — записываем массив `leiden_community_path: [L0, L1, L2, L3]`.
2. На каждом уровне считать «представителя» — узел с max PageRank внутри community (свойство `level_N_representative_id`).
3. Новый эндпоинт `GET /v1/workspaces/{id}/graph?zoom_level=L0|L1|L2|full`:
   - **L0:** только supernodes (по одному на community верхнего уровня), с агрегированными edges (`bundled_weight = sum(intra)`, `target_communities`).
   - **L1, L2:** раскрытые subclusters, edges детализируются.
   - **full:** текущее поведение.

**Frontend:**

1. `GraphCanvasMvp` слушает текущий zoom; при кросс-thresholds (например, scale < 0.3 → L0; 0.3–1 → L1; >1 → full) делает debounced fetch с новым `zoom_level`.
2. **Smooth transitions:** на L0 показаны 5 supernodes; при zoom-in supernode «расцветает» в свои узлы. Координаты узлов внутри supernode пересчитываются локально, но мировые координаты persistent (после zoom-up координаты сохраняются — нет «подпрыгивания»).
3. **Edge bundling между supernodes:** на L0 рисуем aggregated edges толщиной `log(bundled_weight)`, цветом зависящим от dominantного edge-type внутри bundle.
4. **Mini-map** в углу: показывает все supernodes и текущий viewport rect.

### 4.2 Embedding-based layout (опциональный спайк)

**Backend:**

1. `gds.fastRP.write` с `embeddingDimension=64`, `iterationWeights=[0, 0, 1.0, 1.0]`, weights как у Leiden — записывает `node.fastrp_embedding: list[float]`.
2. Postprocess on Python side: UMAP (новая зависимость `umap-learn`) даёт 2D-координаты `umap_x, umap_y` (per-workspace).
3. Записываем обратно в Neo4j как property; в payload отдаём.

**Frontend:**

1. Новый layout-mode `"semantic"` в `GraphCanvasMvp` (наряду с `force` и `circle`). Когда выбран — узлы располагаются по `umap_x/umap_y`, force отключён.
2. UX: «методы похожие по применению — рядом» вне зависимости от плотности рёбер. Это особенно полезно для Method/Dataset узлов: в force-режиме они растягиваются по топологии, а в semantic — собираются в семантические подкластеры.

### 4.3 Acceptance (Wave GR-COM-3)

1. На большом workspace (≥ 1000 узлов) при максимальном zoom-out видно ≤ 10 supernodes с подписями; при zoom-in они раскрываются с persistence координат.
2. Mini-map показывает viewport.
3. Layout-mode `semantic` доступен для workspace с расчитанными UMAP-координатами; при отсутствии — disabled с tooltip «Запустите recompute-communities --with-embeddings».

### 4.4 Зависимости и риски Wave GR-COM-3

- **GR-COM-3 зависит от GR-COM-2:** intermediate communities Leiden и PageRank нужны как основа.
- **UMAP добавляет новую Python-зависимость** (`umap-learn` ~50MB, BSD). Альтернатива — t-SNE (`scikit-learn`, уже есть) или нативный `gds.alpha.tsne` (если включен в инсталляции).
- **Edge bundling с GPU-акселерацией невозможен в нашем CPU/Canvas движке** — рендер bundled-edges на canvas ограничен ~5000 рёбрами на L0 (ок для типичного workspace).

---

## 5. (Опционально, отдельная развилка) Замена рендера на WebGL

При корпусе 5k+ статей (~80k узлов в полной 1-hop окрестности) наш CPU/Canvas начнёт деградировать. Вариант:

- **[`@cosmos.gl/graph`](https://github.com/cosmosgl/graph)** v2.6.1+ — GPU force-симуляция, native Point Clustering force, 100k+ узлов, MIT-license.
- **Sigma.js v3** — WebGL2 rendering с custom shaders, более «классический» API.

**Что менять:** `GraphCanvasMvp.jsx` + `useScienceGraphForceSimulation.js` заменяются на адаптер вокруг cosmos.gl. Hull-rendering, custom labels, edge-icon-stripes, search-highlight — придётся реализовать поверх их API.

**Оценка:** ~1–2 недели на полноценный switchover, не считая регрессий.

**Предложение:** не делать сейчас. Добавить отдельный backlog item «Workspace graph — WebGL renderer evaluation» с триггером «когда workspace регулярно превышает 2000 узлов в payload или FPS < 20 на reference workspace».

---

## 6. Связь с master-roadmap и backlog

### 6.1 Обновления master-roadmap

В [`master-roadmap-and-refactor-plan-2026-04-25.md`](./master-roadmap-and-refactor-plan-2026-04-25.md):

- **§2 таблица треков, строка E (Graph UX):** дополнить
  ```
  + Wave GR-COM-1 (frontend LPA + цвет по community + hulls)
  → Wave GR-COM-2 (Neo4j GDS Leiden + PageRank, server-side, кэш в Neo4j)
  → Wave GR-COM-3 (hierarchical / semantic zoom / FastRP+UMAP layout, опционально)
  ```
- **§3 граф зависимостей:** добавить
  ```
  GR-COM-1 (parallel) → GR-COM-2 (after GR-COM-1, требует gds_enabled) → GR-COM-3 (after GR-COM-2)
  GR-COM-1/2 параллельны GR10/GR12 (toolbar, detail panel) — разные файлы
  ```
- **§4.5 Track E:** добавить пункт «Communities + GDS — отдельная под-волна, реализует кластерное представление графа, центральность, multi-level zoom».

### 6.2 Backlog backend (`docs/backlog/refactor-backend.md`)

Добавить в Queue:

```markdown
### [OPEN] Graph communities — Wave GR-COM-2 server-side Leiden + PageRank via Neo4j GDS
- **Area:** новый `science_graphrag/api/workspace_graph/communities.py`,
  правки в `science_graphrag/api/workspace_graph/projection.py`,
  `science_graphrag/api/workspace_graph/cypher.py`,
  `science_graphrag/ingestion/_pipeline_impl.py` (post-ingest trigger),
  `science_graphrag/cli/main.py` (`recompute-communities`),
  `science_graphrag/config.py` (`Settings.communities_*`)
- **Issue:** Кластеризация графа сейчас выполняется на фронте через union-find по 3 edge-types
  (`HAS_AUTHORSHIP`/`OF_AUTHOR`/`AUTHORED`); тематические сообщества (методы, датасеты, школы)
  не выделяются. PageRank/центральность не считаются — размер узла на канвасе константа.
  `Settings.gds_enabled` есть, но GDS используется только как кэш проекции work↔work, без алгоритмов.
- **Proposal:** новый модуль `communities.py` с функцией `compute_workspace_communities(session, wid, *,
  algorithm="leiden", weights, include_intermediate=true)`; писать `leiden_community_id`,
  `leiden_community_path`, `page_rank` как property узлов в Neo4j (idempotent через `gds.*.write`,
  `gds.graph.drop` в finally); расширить payload `node.properties.community_id/community_path/page_rank`
  и `meta.communities = {algorithm, modularity, count, computed_at, size_distribution, stale}`;
  trigger — async после `add_work_to_workspace` + Dramatiq-периодик 6h + CLI
  `science-graphrag recompute-communities`. Graceful skip при `gds_enabled=false`.
- **Acceptance:** modularity > 0.3 на тестовом 50-node fixture; стабильность ID между прогонами
  с фиксированным `randomSeed`; payload-контракт расширен аддитивно; UI рисует server-side ID
  при наличии и fallback на client LPA при отсутствии.
- **Raised:** 2026-04-27 (см. graph-communities-and-gds-roadmap-2026-04-27.md §3.1)

### [OPEN] Graph communities — Wave GR-COM-3 hierarchical zoom + FastRP/UMAP layout
- **Area:** `science_graphrag/api/workspace_graph/communities.py` (intermediate communities),
  новый `science_graphrag/api/workspace_graph/zoom_level.py` (L0/L1/L2 supernodes),
  новый `science_graphrag/api/workspace_graph/embeddings.py` (FastRP + UMAP).
- **Issue:** Граф плоский; на больших workspace (1000+ узлов) нет multi-level navigation; layout
  только force/circle, не отражает семантическую близость.
- **Proposal:** `gds.leiden.write` с `includeIntermediateCommunities=true`; новый эндпоинт
  `?zoom_level=L0|L1|L2|full`; supernodes на L0 + edge bundling. Опционально — `gds.fastRP.write`
  + UMAP postprocess + property `umap_x/umap_y` как координаты для нового layout-mode "semantic".
- **Acceptance:** L0 показывает ≤ 10 supernodes с подписями; semantic layout доступен и стабилен
  между прогонами; UMAP-зависимость документирована в `pyproject.toml`.
- **Raised:** 2026-04-27 (см. graph-communities-and-gds-roadmap-2026-04-27.md §4)
- **Blocked by:** GR-COM-2 (нужны intermediate communities + PageRank как основа).
```

### 6.3 Backlog frontend (`docs/backlog/refactor-frontend.md`)

Добавить в Queue:

```markdown
### [OPEN] Graph communities UI — Wave GR-COM-1 color-by-community + hulls (frontend-only)
- **Area:** `ui/src/components/graph/canvas/physics/structuralCommunities.js` (расширить),
  новый `ui/src/components/graph/canvas/physics/communityPalette.js`,
  новый `ui/src/components/graph/canvas/graphCanvasDrawCommunityHulls.js`,
  правки `ui/src/components/graph/canvas/graphCanvasDraw.js`,
  `ui/src/components/graph/canvas/GraphCanvasViewToolbar.jsx`,
  `ui/src/components/graph/shell/GraphTypeLegend.jsx`,
  `ui/src/hooks/graph/useScienceGraphForceSimulation.js`,
  i18n `partGraphUi.js`. Возможна новая зависимость `d3-polygon` (~6KB).
- **Issue:** Сейчас кластеры детектируются (union-find по `HAS_AUTHORSHIP`-рёбрам), но влияют
  только на физику — нет цвета, обводки, легенды. LPA в `structuralCommunities.js` реализован,
  но мёртв (нигде не вызывается).
- **Proposal:** активировать LPA как дополнение к hybrid (LPA дробит крупные кластеры
  внутри hybrid); новый toggle `colorBy: "type" | "community"` с persist в LS;
  детерминированная HSL-палитра по hash(community_id); опциональные hulls (convex hull
  через `d3-polygon`, alpha-fill + label); легенда с топ-сообществами и preview.
- **Acceptance:** на workspace 100+ узлов видны 5–15 цветных «облаков»; toggle hulls рисует
  обводки; легенда показывает preview-метки; FPS не падает на 500 узлах; default behaviour
  (`colorBy=type`) regression-safe; EN/RU локали покрыты.
- **Raised:** 2026-04-27 (см. graph-communities-and-gds-roadmap-2026-04-27.md §2)
- **Independent of GR-COM-2 backend** — даёт первичный UX-эффект уже сейчас.

### [OPEN] Graph communities UI — Wave GR-COM-2 server-side ids + size-by-PageRank + filter
- **Area:** `ui/src/components/graph/model/graphViewState.js` (нормализация community/pageRank),
  `ui/src/components/graph/model/graphSimulationAdapter.js`,
  `ui/src/components/graph/canvas/graphCanvasDraw.js` (size scaling),
  `ui/src/hooks/graph/useScienceGraphForceSimulation.js` (server vs client source),
  `ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx` (Select community filter),
  `ui/src/components/graph/model/graphVisibilityFilter.js`.
- **Issue:** Когда GR-COM-2 backend рендерит community/pageRank в payload, фронт должен это
  использовать (а не LPA fallback из GR-COM-1).
- **Proposal:** нормализовать `community_id`/`community_path`/`page_rank` в нормализаторе;
  при ≥ 80% покрытии узлов — server source, иначе fallback на client LPA; size = `NODE_RADIUS *
  (1 + 1.2 * normalize(pageRank))`; Select filter «Сообщество: Все / #N». Hull-метка использует
  `meta.communities.labels[id]` если есть.
- **Acceptance:** при ingest workspace с GDS ON цвета и размеры стабильны между загрузками
  страницы; фильтр по сообществу работает; при GDS OFF — graceful fallback на GR-COM-1.
- **Raised:** 2026-04-27 (см. graph-communities-and-gds-roadmap-2026-04-27.md §3.2)
- **Blocked by:** GR-COM-2 backend (payload-контракт с `community_id`).

### [OPEN] Graph communities UI — Wave GR-COM-3 semantic zoom + supernodes + semantic layout
- **Area:** `ui/src/components/graph/canvas/GraphCanvasMvp.jsx` (zoom level binding),
  новый `ui/src/components/graph/GraphMiniMap.jsx`,
  `ui/src/components/graph/canvas/graphCanvasDraw.js` (edge bundling),
  правки `ui/src/components/graph/workspace/hooks/useGraphWorkspaceData.js` (zoom_level fetch).
- **Issue:** Граф плоский — на больших workspace всё равно «паутина». Нет multi-level
  navigation, mini-map, edge bundling, semantic layout.
- **Proposal:** при scale < 0.3 — fetch `?zoom_level=L0` (supernodes); smooth transitions
  при zoom-in (raised then expanded); mini-map в углу; новый layout-mode "semantic"
  использующий `umap_x/umap_y` из payload.
- **Acceptance:** на workspace 1000+ узлов user видит ≤ 10 supernodes на максимальном zoom-out;
  edge bundling без visual clutter; mini-map отражает viewport.
- **Raised:** 2026-04-27 (см. graph-communities-and-gds-roadmap-2026-04-27.md §4)
- **Blocked by:** GR-COM-3 backend (intermediate communities + UMAP coordinates).
```

### 6.4 Параллельность с другими волнами

| Wave | Конфликт по файлам с другими | Можно ли делать параллельно |
|------|------------------------------|------------------------------|
| **GR-COM-1** | Минимально пересекается с GR12 (правая панель) — там может появиться `colorBy`-toggle. С GR10 (toolbar) — добавление toggle «Раскраска» в toolbar логично делать после GR10a. | Параллельно с GR6/GR7/GR8/GR9; после GR10a — лучше |
| **GR-COM-2 backend** | `science_graphrag/api/workspace_graph/projection.py` пересекается с GR8 (smarter aggregation). Нужна координация: GR-COM-2 расширяет `node.properties`, GR8 трогает `apply_workspace_aggregators`. | Параллельно с GR8, но мерджить аккуратно |
| **GR-COM-2 frontend** | Минимально с GR12 (panel), полностью независим от GR9 (reader view) | Параллельно с GR9/GR10/GR12 |
| **GR-COM-3 backend** | Изолирован в новых модулях | Полностью параллелен |
| **GR-COM-3 frontend** | `GraphCanvasMvp.jsx` пересекается с любыми правками канваса (GR6/GR-COM-1/GR-COM-2) | После GR-COM-2 frontend |

---

## 7. Чем конкретно помогает Neo4j

Neo4j (через расширение **GDS — Graph Data Science Library**) даёт **три категории алгоритмов**, и каждая закрывает один из наших разрывов из §1.7:

### 7.1 Community Detection

[Алгоритмы](https://neo4j.com/docs/graph-data-science/current/algorithms/community/): Louvain, Leiden, Label Propagation, Weakly Connected Components, K-1 Coloring, Modularity Optimization, Speaker-Listener LPA, Triangle Count.

**Главное преимущество перед фронтовым LPA:**
- Запускается на **полном** workspace-графе (не только UI-cap), включая узлы за `GRAPH_UI_MAX_NODES`.
- Качество (modularity) выше: Leiden оптимизирует целевую функцию итеративно с merge-split-refine, против простого «пересчитай метку соседей» в LPA.
- **Иерархия:** intermediate communities → multi-level zoom без отдельного спайка.
- **Кэш:** результат — это property узлов в Neo4j, переиспользуется между всеми API-запросами и API-клиентами (UI, CLI, бенчмарки).

### 7.2 Centrality

[Алгоритмы](https://neo4j.com/docs/graph-data-science/current/algorithms/centrality/): PageRank, ArticleRank, Betweenness, Degree, Closeness, HITS, Eigenvector.

**Применения:**
- Размер узла на канвасе.
- Сортировка `displayLabel` в фильтрах и легенде.
- Стратификация supernodes (top-N по PR в L0).
- **PageRank-aware aggregator:** в существующем `apply_workspace_aggregators` соседи внутри агрегатора сортируются по PR, в `preview_labels` попадают самые важные.
- Метрика «узел-мост» (Betweenness) для подсказок типа «через эту работу проходят 38% связей сообщества» в правой панели деталей.

### 7.3 Node Embeddings + Similarity

[Алгоритмы](https://neo4j.com/docs/graph-data-science/current/algorithms/node-embeddings/): FastRP, GraphSAGE, Node2Vec, HashGNN.

**Применения:**
- **Семантический layout** (FastRP → UMAP → 2D, см. §4.2).
- **«Похожие работы» без явных рёбер:** даже если две статьи не цитируют друг друга, их FastRP-вектора могут быть близки → новая фича в правой панели «Похожие в этом workspace» (top-5 по cosine similarity).
- **ML-ready features** для будущих задач: link prediction (предсказывать «кто процитирует кого»), классификация Method-узлов, рекомендация работ для добавления в workspace.

### 7.4 Что есть уже сейчас

- `Settings.gds_enabled` ([config.py:462-468](../../science_graphrag/config.py)) — feature flag, default `False`.
- `gds_runtime_available(session)` + `gds_graph_drop(session, graph_name)` ([_cypher_gds.py:16-28](../../science_graphrag/api/workspace_graph/_cypher_gds.py)).
- В docker-compose — Neo4j с GDS-плагином (нужно подтвердить — см. §8 шаг 1).

То есть инфраструктурно мы готовы — нужно только написать вызовы алгоритмов и расширить payload.

---

## 8. Следующие шаги (порядок)

1. **Подтвердить, что GDS-плагин действительно установлен** в текущем docker-compose:
   ```bash
   docker compose exec neo4j cypher-shell -u neo4j -p $NEO4J_PASS \
     "RETURN gds.version() AS v"
   ```
   Если `Unknown function 'gds.version'` — добавить плагин в `docker-compose.yml` (`NEO4J_PLUGINS=["graph-data-science"]`) или поднять Neo4j enterprise. Решение оформляется отдельным runbook `docs/runbooks/neo4j-gds-setup.md`.
2. **PR #1 (GR-COM-1, frontend, ~1.5 дня):** активация LPA + `colorBy`-toggle + детерминированная палитра + опциональные hulls + легенда. **Начинать после GR6** (canvas displayType fix), чтобы не конфликтовать в `graphCanvasDraw.js`.
3. **PR #2 (GR-COM-2 backend Phase A, ~2 дня):** новый `communities.py` с Leiden+PageRank, idempotent, через CLI `recompute-communities`. Без триггера в ingest — оператор вызывает руками.
4. **PR #3 (GR-COM-2 backend Phase B, ~1 день):** триггер async после `add_work_to_workspace` + Dramatiq-периодик. Расширение payload `community_id` / `page_rank` / `meta.communities`.
5. **PR #4 (GR-COM-2 frontend, ~2 дня):** server-side нормализация + size-by-PageRank + filter по сообществу + переключение source server/LPA.
6. **PR #5 (GR-COM-2.5 LLM-labels, опционально, ~1 день):** запросить LLM «дай 2-3 слова на тему этих 10 заголовков», закэшировать в Neo4j. Activate в hull-подписях.
7. **PR #6 (GR-COM-3 backend, ~3 дня):** intermediate communities + zoom_level endpoint + bundled edges aggregation. Опционально — FastRP + UMAP в отдельной фазе.
8. **PR #7 (GR-COM-3 frontend, ~3 дня):** zoom-binding + supernodes на L0 + smooth transitions + mini-map. Опционально — semantic layout-mode.

**MVP срез (если бюджет 1 спринт):** PR #1 + PR #2 + PR #4 — это даёт 80% эффекта (видны цветные сообщества, размер по важности, серверная стабильность ID). PR #3 (триггеры) — критичен для production, но временно можно оператором через CLI. PR #5+ — полировка и большие графы.

---

## 9. Что закрывается этим планом (итог для пользователя)

После прохождения GR-COM-1 + GR-COM-2 (+ опционально GR-COM-3) пользователь, открывая workspace-граф:

- **видит цветные «облака» сообществ** — каждый кластер раскрашен, hull-обводка с подписью, легенда показывает топ-сообщества с preview-метками;
- **размер узла отражает важность** — самая цитируемая работа в workspace заметнее в 1.5–2 раза, доминирующий метод (типа `Transformer`/`BERT`) выделяется визуально;
- **может фильтровать по сообществу** — Select «Сообщество: #N» оставляет только узлы выбранного кластера и их 1-hop окрестность;
- **на максимальном zoom-out** видит ≤ 10 supernodes (Wave 3) — «континенты» тем, при zoom-in они раскрываются с persistence координат;
- **на больших workspace** (1000+ узлов) граф остаётся читаемым, не превращается в «hairball»;
- **не сталкивается с регрессиями:** при `gds_enabled=false` или отсутствующем плагине UI fallback на client LPA, при отсутствии `community_id` в payload — на старое поведение по `node_kind`.

И структурно:
- Кластеризация и центральность считаются **один раз на бэке**, не пересчитываются в браузере на каждом ре-рендере.
- Результат — это **shared state в Neo4j**, переиспользуется UI/CLI/бенчмарками.
- Компонента force-симуляции упрощается: cluster-attraction теперь использует **полноценные** community, а не union-find на одном edge-type.
