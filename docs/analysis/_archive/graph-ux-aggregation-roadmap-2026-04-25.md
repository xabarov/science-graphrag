# [HISTORICAL] Graph UX и агрегация узлов — анализ и план Wave GR1–GR5

> **[HISTORICAL] Перемещён в `_archive/` 2026-04-25.** Wave GR1/GR2/GR3 закрыты (с caveats); Wave GR4 переименован в GR9; продолжение по треку **Graph UX** ведётся в [`../graph-readability-followup-2026-04-25.md`](../graph-readability-followup-2026-04-25.md) (серия GR6–GR12). Сохранён как исходный анализ ontology vs visualization split и контракт UI ↔ API. Внутренние относительные ссылки на `../` могут указывать на устаревшие пути.

**Дата:** 2026-04-25  
**Статус:** [HISTORICAL] — Wave GR1–GR5 закрыты или переименованы; для актуальной работы см. `graph-readability-followup-2026-04-25.md`.  
**Цель (на момент написания):** разобрать визуальные и онтологические проблемы текущего просмотра графа (`/graph`, `WorkspacePage` Graph tab), отделить «оставить как есть в Neo4j» от «улучшить на API/UI», и зафиксировать поэтапный план.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`../adr/002-layer1-graph-model.md`](../adr/002-layer1-graph-model.md) | Канон scholarly backbone (метки, рёбра, индексы) |
| [`../adr/004-ontology-v1-scope.md`](../adr/004-ontology-v1-scope.md) | Scope semantic layer (`Method`, `Dataset`) |
| [`../adr/005-authorship-reified-node.md`](../adr/005-authorship-reified-node.md) | Решение оставить `:Authorship` как reified-узел |
| [`../adr/011-graph-live-ux-and-payload.md`](../adr/011-graph-live-ux-and-payload.md) | Display fields на API + переход на canvas/force по умолчанию |
| [`../adr/012-workspace-graph-projection.md`](../adr/012-workspace-graph-projection.md) | Workspace-scoped граф (Wave J) |
| [`../architecture/authorship-neo4j-queries.md`](../architecture/authorship-neo4j-queries.md) | Разделение «онтология vs визуализация» для авторства |
| [`../specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) | Контракт UI ↔ API + Wave 4.x/5–8 |
| [`workspace-experience-gap-2026-04-24.md`](workspace-experience-gap-2026-04-24.md) | Анализ workspace-сценариев (Wave I–L) |
| [`ontology-benchmarks-roadmap-2026-04-24.md`](../ontology-benchmarks-roadmap-2026-04-24.md) | План онтологии и индексов (Wave M–T) |

---

## 1. Скриншот: что видно сейчас и что с этим не так

На приложенном скриншоте выбран узел типа `Authorship` со следующим заголовком и подписью:

```
Authorship
b240ca79-6dc1-49ec-90c7-acce907439d1:ash:1
```

Из этого и из соседних узлов видно сразу несколько системных проблем визуализации, не зависящих от конкретного workspace или работы:

1. **Сырые UUID в подписи и имени.** `:Authorship` — это reified-узел между `:Work` и `:Author` (см. [ADR 005](../adr/005-authorship-reified-node.md), [authorship-neo4j-queries.md](../architecture/authorship-neo4j-queries.md)). У него **нет** ни `name`, ни `full_name`, ни `title`, и Cypher из `_work_graph_neighborhood_payload` падает в fallback `n.id` ([`science_graphrag/api/works.py`](../../science_graphrag/api/works.py)). UI показывает технический идентификатор `…:ash:1`. Тоже самое — для других служебных промежуточных узлов в будущем.
2. **Дублирование информации, читаемой на ребре, в самом узле.** На рёбрах уже отображены типы `HAS_AUTHORSHIP`, `OF_AUTHOR`, `AFFILIATED_WITH`. Узел `:Authorship` визуально дублирует ту же связь и удлиняет путь от `:Work` до `:Author` без смысловой нагрузки для читателя.
3. **Узлы-«хабы» без сжатия.** В кадре видны несколько `:Authorship` рядом с одной `:Work` (по числу авторов), несколько `:Author` рядом с одним `:Work`, и потенциально много одинаковых `:Institution` — это типичный «звёздный» паттерн, который полезен для запросов, но в визуальном представлении маскирует структуру.
4. **`_OF_AUTHOR`, `HAS_AUTHORSHIP`, `AFFILIATED_WITH` как первичные подписи рёбер.** Это **названия типов рёбер из канона** ([ADR 002](../adr/002-layer1-graph-model.md)) — корректно для запросов, но не нужно показывать как «продукт» неподготовленному пользователю. У нас уже есть `display_type` (snake_case → space), но он по-прежнему совпадает один-в-один с типом.
5. **Внешние/слабые контекстные узлы наравне с целевыми.** `:Venue`, `:Institution`, второстепенные `:Author` рендерятся теми же дисками, что и `:Work` / `:Method` / `:Dataset` — они оттягивают взгляд от того, что и есть «знание».
6. **Workspace-граф визуально не отличает корпус от внешних цитирований.** Палитра уже знает `workspace_membership: internal/external` (см. [`graphCanvasStyle.js`](../../ui/src/components/graph/graphCanvasStyle.js), Wave J), но **в боковой панели** до сих пор «голая» карточка узла без бейджа корпус/внешний и без счётчика связности.
7. **Ребро без агрегации: рёбра в одну и ту же группу не пакетируются.** Если `:Work` цитирует 30 работ, на канвасе появляется 30 рёбер `CITES`. Force-симуляция справляется, но визуально это «куст», в котором не видно структуры (по году, по теме, по venue).

Проблема №1 (`Authorship` с сырым UUID) — самая громкая и сама по себе тривиально лечится на бэкенде; всё остальное — системный класс задач, который требует разделить онтологию и проекцию для UI.

---

## 2. Принципы: что «как есть» в Neo4j, а что улучшать в проекции

В рамках текущего стека есть **три** места, где можно вмешиваться в представление графа. Полезно различать их явно:

| Слой | Что должен делать | Где живёт сейчас |
|------|--------------------|------------------|
| **Neo4j (источник правды)** | Канон онтологии: точные типы, индексы, нормализация. Ничего «для UI». | [`science_graphrag/storage/neo4j_store.py`](../../science_graphrag/storage/neo4j_store.py), [ADR 002](../adr/002-layer1-graph-model.md), [ADR 005](../adr/005-authorship-reified-node.md), [ADR 015](../adr/015-neo4j-vector-index-work-title-embedding.md) |
| **API проекция (для UI)** | `display_label`, `subtitle`, `node_kind`, агрегаторы, виртуальные рёбра. **Не** меняет схему. | [`science_graphrag/api/works.py`](../../science_graphrag/api/works.py) (`_work_graph_neighborhood_payload`), [`science_graphrag/api/workspace_graph.py`](../../science_graphrag/api/workspace_graph.py) |
| **Frontend** | Раскладка, фильтры, hover/zoom-зависимые подписи, «развернуть кластер», collapsible authorship. **Не** изобретает данных, которых нет в API. | [`ui/src/components/graph/`](../../ui/src/components/graph/) |

### 2.1 Что должно остаться в Neo4j «как есть»

- **`:Authorship` как reified-узел.** Это сознательное решение, оно поддерживает `is_corresponding`, `equal_contribution`, `raw_affiliation`, `extraction_confidence` и аккуратно держит «несколько институтов на одного автора в одной публикации». Менять схему ради картинки **нельзя** ([ADR 005, §3.4 будущие поля](../adr/005-authorship-reified-node.md)).
- **Полные имена типов рёбер (`HAS_AUTHORSHIP`, `OF_AUTHOR`, `AFFILIATED_WITH`, `CITES`, `PUBLISHED_IN`, `USES_METHOD`, `EVALUATED_ON`, `TRAINED_OR_TESTED_ON`).** Они оптимальны для Cypher и индексирования; UI всё равно делает свою proекцию.
- **Дополнительные «технические» узлы будущего (`Claim`, `Evidence`, `Section`, `Span`, и т. д., см. [ADR 008](../adr/008-ontology-claims-wave-h.md), [ADR 013](../adr/013-concept-research-topic-ontology-v1-5.md)).** По аналогии с `Authorship` они **не должны** превращаться в плоские атрибуты ради визуального удобства.

### 2.2 Что добавить в Neo4j (поддержка UI и поиска)

Это **дополнения**, а не миграции схемы; они полезны и для запросов, и для рендера.

- **Денормализованные счётчики на `:Work`:** `cites_in_count`, `cites_out_count`, `authors_count`, `internal_workspace_count` (на ingest или nightly). Сейчас UI каждый раз считает сам через `_annotate_membership_and_cites`, что не масштабируется и недоступно за пределами workspace-графа. Денормализация даст:
  - визуальный «вес» узла (radius ∝ log(cites_in)), как в osint-gr;
  - быстрый порядок ранжирования соседей при `is_truncated`;
  - бейдж «много цитирований» в инспекторе.
- **Стабильное `display_name` на `:Author` после канонизации** (Wave T — [`merge-catalog-wave-h.md`](../specs/merge-catalog-wave-h.md)). `full_name` сейчас может расходиться между публикациями.
- **Стабильное `short_name` / `acronym` на `:Institution` и `:Venue`** (необязательно; можно через alias-таблицу) — UI часто хочет короткое имя, а не «University of California, Berkeley, Department of …».
- **Индексы / fulltext** уже описаны в [`ontology-benchmarks-roadmap-2026-04-24.md` §6](../ontology-benchmarks-roadmap-2026-04-24.md) — здесь не дублируем.

### 2.3 Что должна делать API-проекция (между Neo4j и UI)

Текущий `display_label / subtitle / node_kind / display_type / source_label / target_label / summary / direction` ([ADR 011](../adr/011-graph-live-ux-and-payload.md)) — хороший фундамент. Расширения, которые нужны для проблем из §1:

- **Заполнить `display_label` для каждого типа узла**, включая `:Authorship`, **никогда** не возвращая UUID в `display_label`. UUID остаётся в `id` и в `Advanced JSON` инспектора.
- **`node_kind` ≠ `type`.** `type` — лейбл Neo4j (`Work` / `Author` / `Authorship`). `node_kind` — единица отображения, может быть `AuthorshipReification` (для дальнейшего сворачивания), `WorkInternal` / `WorkExternal`, `Aggregator`, `VirtualWorkAuthor` (если будем строить виртуальные рёбра).
- **`aggregation_hints` на узле:** `collapse_with_parent: true` (для `:Authorship`), `aggregator_kind: "authors_of_work"` (для будущих агрегаторов), `weight: <int>` (число «спрятанных» элементов).
- **Виртуальные рёбра по запросу** (`?view=reader`): `Work → Author` напрямую, с `via: "authorship"` и пропсами `author_position`, `is_corresponding`, `affiliation`. Параллельно сохраняем «raw» режим для отладки и графовых тестов (`?view=raw`).
- **Бюджет соседей с приоритизацией.** Сейчас `LIMIT $lim` урезает рёбра «как Cypher вернул»; полезно ранжировать так, чтобы не выбрасывались первые `K` ключевых типов (`Method`, `Dataset`, citation hubs) до того, как уйдут `Authorship`/`Institution` второго порядка.

### 2.4 Что должна делать только UI (без правки бэкенда)

- **Adaptive labelling по zoom**: на zoom-out показывать только подписи `:Work`; при приближении — подписи `Method`/`Dataset`; всегда последними — `Author`/`Institution`/`Venue`.
- **Бандлинг рёбер**: смежные `CITES` от одной `Work` к группе работ можно рендерить как curved bundle (визуально, без изменения данных).
- **Сворачивание «куста» по узлу-владельцу**: один клик «collapse authorship» в инспекторе схлопывает все исходящие `HAS_AUTHORSHIP` от выбранного `:Work` в один служебный диск с числом `N авторов` и списком в боковой панели.
- **Cluster hint по типу/году/workspace_membership**: уже частично сделано через [`scienceHybridCommunities.js`](../../ui/src/components/graph/physics/scienceHybridCommunities.js); расширяем явно (см. §5 Wave GR3).

---

## 3. Конкретные классы проблем + предлагаемое решение

| # | Проблема | Что меняем | Слой | Связанные файлы |
|---|----------|-------------|------|-----------------|
| 1 | `:Authorship` показывается с UUID `…:ash:N` | API: `display_label = f"{author_full_name} ({position})"`, `subtitle = "Authorship"`, опциональный `aggregation_hint: "collapse_with_parent"` | API | [`science_graphrag/api/works.py`](../../science_graphrag/api/works.py) `_neighbor_subtitle_and_properties`, `_append_neighbor_edge`; [`workspace_graph.py`](../../science_graphrag/api/workspace_graph.py) `_node_dict_from_neo` |
| 2 | `Authorship` визуально дублирует ребро `Work–Author` | API режим `?view=reader` строит виртуальное `Work–[AUTHORED]→Author` (с `author_position`, `affiliation`, `is_corresponding` в `properties`); по умолчанию для `/v1/works/{id}/graph` и workspace-графа выбирать **reader** | API + UI flag | `works.py`, `workspace_graph.py`, `frontend-ui-api-contracts-v1.md`, `GraphWorkspacePanel.jsx` |
| 3 | «Куст» соседей одного типа (15 авторов / 30 цитирований / 10 институтов) | API: при `count(neighbors_of_kind) > N` отдавать **узел-агрегатор** (`node_kind: "Aggregator"`, `aggregator_kind`, `count`, превью топ-3); UI: клик по агрегатору `→` `GET .../neighbors?node_id=&aggregator=…` для разворачивания | API + UI | `works.py`, `workspace_graph.py`, `GraphDetailPanel.jsx`, `GraphCanvasMvp.jsx` |
| 4 | Подписи рёбер слишком технические (`HAS_AUTHORSHIP`, `OF_AUTHOR`) | API: словарь `display_type` для UI ([ADR 011](../adr/011-graph-live-ux-and-payload.md) уже даёт строку, но 1:1 с `_`→space); расширить до семантичных переводов: `cites`, `is author of`, `affiliated with`, `evaluated on`, `published in` | API | `works.py` `_display_type` (расширить таблицу) |
| 5 | Контекстные узлы (`Venue`, `Institution`) визуально равны центральным | UI: тонкое стилевое различие («tertiary» tier) + по умолчанию off в `nodeTypesCsv`; легенда показывает «выключено» | UI | `graphCanvasStyle.js`, `WorkspaceGraphToolbar.jsx`, `GraphTypeLegend.jsx` |
| 6 | Внешние работы не отличаются в инспекторе | UI: бейдж `external` + ссылка «Открыть в новом окружении» уже есть для одного-Work-графа; повторно использовать в edge-инспекторе | UI | `GraphDetailPanel.jsx` |
| 7 | Дубликаты `:Author` (та же фамилия из разных публикаций) | Backend: dedup `:Author` по `normalized_name` + `orcid` (Wave T в [`ontology-benchmarks-roadmap-2026-04-24.md` §7](../ontology-benchmarks-roadmap-2026-04-24.md)); UI: индикатор «возможно тот же автор» при `normalized_name` совпадении до канонизации | DB + API | `neo4j_store.py`, `merge-catalog-wave-h.md` |
| 8 | «Звезда» из `CITES` не структурирована | UI (force layout): группировка по `publication_year` / `venue` / community detection поверх `CITES`; визуально — кластер-кольца | UI | `physics/scienceHybridCommunities.js`, `physics/structuralCommunities.js` |
| 9 | API возвращает только 200 соседей без приоритизации | API: ранжировать `LIMIT` так, чтобы `Method`/`Dataset` всегда влезли; добавить `meta.skipped_by_kind` | API | `works.py` |
| 10 | Будущие `Claim`/`Concept`/`ResearchTopic` повторят сценарий «много мелких узлов» | Заранее ввести в API-проекции класс `aggregation_hints` и не плодить на UI special-case-ы | API | `ontology-claims-v1.md`, `013-concept-research-topic-ontology-v1-5.md` |

---

## 4. Контракт UI ↔ API: что нужно дополнить

Все правки — **аддитивные**, старые клиенты должны продолжать работать (как и при [ADR 011](../adr/011-graph-live-ux-and-payload.md)).

### 4.1 Изменения в payload узла

```json
{
  "id": "b240ca79-6dc1-49ec-90c7-acce907439d1:ash:1",
  "type": "Authorship",                 // как сейчас (Neo4j label)
  "node_kind": "AuthorshipReification", // НОВОЕ: подкласс для UI; заменяет дубль `type`
  "label": "Smith, J. (#1)",            // НОВОЕ-ПРИОРИТЕТ: всегда не-UUID
  "display_label": "Smith, J. (#1)",
  "subtitle": "Author #1 · IBM Research",
  "properties": {
    "author_position": 1,
    "raw_affiliation": "IBM Research",
    "is_corresponding": false
  },
  "aggregation_hints": {                // НОВОЕ
    "collapse_with_parent": true,       // UI может сворачивать в parent Work
    "parent_kind": "Work"
  }
}
```

Для агрегатора:

```json
{
  "id": "agg:work:<work_id>:authors",
  "type": "Authorship",                 // или "Author" в reader-mode
  "node_kind": "Aggregator",
  "label": "8 authors",
  "display_label": "8 authors",
  "subtitle": "Click to expand",
  "properties": {},
  "aggregation_hints": {
    "aggregator_kind": "authors_of_work",
    "count": 8,
    "preview_labels": ["Smith J.", "Doe A.", "Lee K."],
    "expand_endpoint": "/v1/works/<work_id>/graph/expand?aggregator=authors"
  }
}
```

### 4.2 Изменения в payload ребра

- Добавить семантичные `display_type` для базовых отношений (см. таблицу в §3, проблема 4).
- В `?view=reader`-проекции для `Work –[AUTHORED]→ Author`:

```json
{
  "id": "e_<sha>",
  "source": "<work_id>",
  "target": "<author_id>",
  "type": "AUTHORED",                   // НОВЫЙ виртуальный тип, помечен `via`
  "display_type": "is author of",
  "summary": "Wei Liu —[is author of]→ Cross-lingual Retrieval…",
  "direction": "outgoing",
  "via": ["HAS_AUTHORSHIP", "OF_AUTHOR"], // НОВОЕ: трасса по schema
  "properties": {
    "author_position": 1,
    "is_corresponding": false,
    "affiliation": "IBM Research"
  }
}
```

### 4.3 Новые query-параметры

- `view=raw|reader` (default `reader` для UI; `raw` для тестов и Neo4j-консистентных снапшотов).
- `collapse=authorship,affiliation,aggregators` (список того, что схлопывать).
- `aggregator_threshold=8` (с какого числа однотипных соседей строить агрегатор).
- `prioritize=Method,Dataset,Work` (что не выбрасывать первым при `LIMIT`).

### 4.4 Согласование с тестами и snapshot-диффом

- [`graph_snapshot_diff.py`](../../science_graphrag/api/graph_snapshot_diff.py) и `graph_v1` бенчмарк-семья **должны работать на `view=raw`**, чтобы не зависеть от UX-эвристик; UI работает на `view=reader`.
- Нормализатор payload-а на UI ([`graphViewState.js`](../../ui/src/components/graph/graphViewState.js)) — проверить, что неизвестные поля (`aggregation_hints`, `via`, `node_kind`) проходят без warn-spam (он уже добавляет в `warnings` только содержательное).

---

## 5. План работ — Wave GR1–GR5

Wave «GR» = Graph Readability (отдельный индекс, чтобы не пересекаться с продуктовыми Wave A–T из [roadmap](../roadmap.md) и [ontology-benchmarks-roadmap](../ontology-benchmarks-roadmap-2026-04-24.md)). Каждая Wave — отдельный refactor pass.

### 5.1 Wave GR1 — `display_label` для всех типов и Authorship-fix (бэкенд, минимальное)

**Цель:** убрать UUID `…:ash:N` с экрана, дать читаемые подписи всем типам узлов «как есть» в текущей схеме, без виртуальных рёбер.

**Чеклист:**

- [x] В `_work_graph_neighborhood_payload` ([`works.py`](../../science_graphrag/api/works.py)) Cypher-запрос соседей:
  - [x] подтянуть `Authorship.author_position`, и `(:Authorship)-[:OF_AUTHOR]->(:Author).full_name` через `OPTIONAL MATCH` или второй проход;
  - [x] подтянуть `Authorship.raw_affiliation` и опционально `(:Authorship)-[:AFFILIATED_WITH]->(:Institution).name`.
- [x] `_neighbor_subtitle_and_properties` для `Authorship`:
  - [x] `display_label = f"{author_short_name} (#{position})"`, fallback `f"Author #{position}"` если имя пустое;
  - [x] `subtitle = f"Author #{position}{' · ' + institution if institution else ''}"`;
  - [x] `properties: { author_position, is_corresponding, raw_affiliation, institution_id? }`.
- [x] Для `:Author` всегда `display_label = full_name`, никогда не UUID.
- [x] Для `:Institution` `display_label = name`, `subtitle = country` (опционально).
- [x] Для `:Venue` `display_label = name`, `subtitle = venue_type or issn or ""` (опционально).
- [x] То же самое для `_node_dict_from_neo` в [`workspace_graph.py`](../../science_graphrag/api/workspace_graph.py).
- [x] Новые pytest-кейсы: `tests/test_works_graph_display.py`, проверка `display_label` ≠ UUID для каждого типа.
- [x] Снимок benchmark `graph_v1` пересобрать, убедиться что diff содержит **только** `display_label`/`subtitle` (структура графа неизменна). *(n/a: `graph_v1` проверяет структурные метрики, не `display_*` поля)*.
- [x] UI smoke в [`GraphDetailPanel.jsx`](../../ui/src/components/graph/GraphDetailPanel.jsx): `display_label` отрисовывается, fallback `label` уже работает.

**Acceptance:** На `/graph?work_id=…` ни один отображаемый узел в боковой панели и на канвасе не имеет в качестве заголовка UUID; технический `id` по-прежнему виден в Advanced JSON.

**Ориентир по объёму:** 1 PR, 1 день, без миграций.

### 5.2 Wave GR2 — `node_kind`, семантичные `display_type`, приоритизация LIMIT

**Цель:** очистить семантику UI-полей, чтобы Wave GR3/GR4 могли строить агрегацию и сворачивание без дальнейших правок API.

**Статус:** in progress (backend + API contract + UI legend).

**Чеклист:**

- [ ] Ввести `node_kind` отдельно от `type`:
  - [ ] `Work` → `node_kind` ∈ `{ "Work", "WorkInternal", "WorkExternal" }` (последние два — только в workspace-проекции, чтобы UI не считал сам).
  - [ ] `Authorship` → `node_kind = "AuthorshipReification"`.
  - [ ] `Aggregator` (зарезервировано под GR3).
- [ ] Расширить `_display_type` ([`works.py`](../../science_graphrag/api/works.py)) словарём:
  - `CITES` → `cites`,
  - `HAS_AUTHORSHIP` → `has authorship` (raw-mode) / `is author of` (reader-mode),
  - `OF_AUTHOR` → `of author` (raw) / скрыть (reader),
  - `AFFILIATED_WITH` → `affiliated with`,
  - `PUBLISHED_IN` → `published in`,
  - `USES_METHOD` → `uses method`,
  - `EVALUATED_ON` → `evaluated on`,
  - `TRAINED_OR_TESTED_ON` → `trained/tested on`.
- [ ] Параметр `prioritize` (default `Method,Dataset,Work`): запрос соседей делится на «приоритетные» и «остальные»; первый блок берёт от лимита `min(K, count_priority)`, остаток отдаётся остальным.
- [ ] `meta.skipped_by_kind: { Authorship: N, Author: M, … }` для прозрачности.
- [ ] UI: легенда показывает значимые `display_type` в hover; `GraphTypeLegend` выводит `node_kind` с группировкой `Work / Semantic / People / Context`.
- [ ] Тесты: contract-тесты на `display_type` маппинг, на приоритизацию `LIMIT`.

**Acceptance:** При `neighbor_limit=10` для работы с 5 методами и 50 авторами в результат попадают **все** методы. Легенда читается без декодера.

**Ориентир:** 1 PR, 1–2 дня.

### 5.3 Wave GR3 — Узлы-агрегаторы (Aggregator) + ленивое разворачивание

**Цель:** убрать «куст» — большие звёзды одного типа подменять одним узлом-агрегатором с `count` и preview.

**Чеклист (бэкенд):**

- [ ] В `_work_graph_neighborhood_payload`/workspace-graph: после построения `nodes`/`edges` пройти по группам соседей одного `node_kind`, привязанным к одному «owner»-узлу через одно и то же ребро, и при `len(group) >= aggregator_threshold` (default 8) подменить группу одним `node_kind: "Aggregator"`.
- [ ] Аггрегаторы по умолчанию для:
  - `Authorship` под одним `Work` (если их N ≥ threshold); preview = первые 3 имени;
  - `Author` под одним `Work` в reader-mode;
  - внешние `Work` под одним `Work` через `CITES` (когда `is_truncated`);
  - `Institution` под одним `Author` (редко, но возможно).
- [ ] Endpoint разворачивания: `GET /v1/works/{work_id}/graph/expand?aggregator_id=…&limit=…` или универсальный параметр `?expand=<aggregator_id>` к существующему `/graph`.
- [ ] `aggregation_hints.expand_endpoint` всегда заполнен, чтобы UI не угадывал URL.
- [ ] Edge от агрегатора к owner: `display_type` = `summary` (`"8 authors of Cross-lingual…"`), `summary` без UUID.

**Чеклист (UI):**

- [ ] `graphViewState.js` пропускает `aggregation_hints` и `node_kind: "Aggregator"` без warn.
- [ ] `graphCanvasStyle.js`: стиль агрегатора (диск с цифрой `+N`, пунктирный stroke).
- [ ] `GraphCanvasMvp.jsx`: клик по агрегатору вызывает API expand, мерджит результат в локальный кэш графа (как уже работает `getWorkspaceGraphNeighbors` для external).
- [ ] `GraphDetailPanel.jsx`: при выбранном агрегаторе показывает список preview + кнопку «Expand all».
- [ ] Бенчмарк `graph_v1`: добавить кейс с большим числом авторов; gold отдельный для `view=raw` и `view=reader`.

**Acceptance:** На работе с 30 авторами по умолчанию вместо 30 узлов отображается один `8 authors` (если threshold=8 → агрегатор «22 more»); клик разворачивает остаток.

**Ориентир:** 2 PR (бэкенд → UI), ~3 дня.

### 5.4 Wave GR4 — `view=reader` с виртуальными рёбрами `Work → Author`

**Цель:** когда пользователю нужен «читаемый» граф, не показывать `Authorship` как отдельный узел вообще.

**Чеклист (бэкенд):**

- [ ] Параметр `view ∈ {raw, reader}` в `/v1/works/{id}/graph` и `/v1/workspaces/{id}/graph`. Default = `reader` для UI, `raw` — для бенчмарков и `graph_snapshot_diff`.
- [ ] В режиме `reader`:
  - [ ] не возвращать `:Authorship` узлы и рёбра `HAS_AUTHORSHIP`/`OF_AUTHOR`;
  - [ ] вместо них — виртуальные рёбра `Work –[AUTHORED]→ Author` с `properties.author_position`, `properties.is_corresponding`, `properties.affiliation`, `via: ["HAS_AUTHORSHIP","OF_AUTHOR"]`;
  - [ ] виртуальные рёбра `Work –[AFFILIATED_THROUGH]→ Institution` (или скрыть и положить institution в свойство `Author` — обсудить отдельно).
- [ ] Тесты: симметрия `view=raw` и `view=reader` (одинаковое множество `Work` и `Author`, разное число рёбер/узлов).
- [ ] Снимок benchmark `graph_v1` остаётся на `view=raw`; новый snapshot для `view=reader` опционален.

**Чеклист (UI):**

- [ ] Тогглер `Authorship details: collapsed | shown` в `WorkspaceGraphToolbar.jsx` (persist `graphAuthorshipDetailMode`).
- [ ] `Aggregator` (GR3) и `view=reader` (GR4) совместимы: reader-mode с >threshold авторов даёт агрегатор `8 authors`.
- [ ] Edge-инспектор для виртуального `AUTHORED` показывает `via` (для трасеабилити).

**Acceptance:** Default-видение `/graph` для типичного workspace показывает `Work ↔ Work (cites)`, `Work → Author` (если ≤ threshold), `Work → Method`, `Work → Dataset`. Никаких `Authorship` дисков на канвасе по умолчанию.

**Ориентир:** 2 PR (бэкенд contract → UI), ~3–4 дня.

### 5.5 Wave GR5 — Денормализованные счётчики, weighted layout, тонкая палитра

**Цель:** дать графу визуальную «глубину» — что важно, а что фоном — без лишних запросов и без ML.

**Чеклист (бэкенд):**

- [ ] На ingest и в фоне (Wave U-аналогичный sweep) считать и хранить на `:Work`:
  - [ ] `cites_in_count`, `cites_out_count`, `authors_count`;
  - [ ] опц. `workspace_count` (`size((w)<-[:CONTAINS]-())`).
- [ ] Прокинуть в `properties` payload-а узла под ключами `cites_in_count`, `cites_out_count`.

**Чеклист (UI):**

- [ ] `graphCanvasStyle.js`: радиус узла `:Work` ∝ `log10(cites_in_count + 1)`; `:Method`/`:Dataset` — фиксированный, но крупнее `:Author`/`:Institution`/`:Venue`.
- [ ] Tier стиля: primary (`Work`/`Method`/`Dataset`), secondary (`Author`), tertiary (`Authorship`/`Venue`/`Institution`) — отличаются opacity и шириной stroke.
- [ ] Adaptive labelling по zoom: `< 0.3` — только `:Work`; `0.3..0.8` — `+ Method/Dataset`; `> 0.8` — все.
- [ ] Cluster hint в `scienceHybridCommunities.js`: учитывать `publication_year` decade и `venue_id` для `:Work`.
- [ ] Edge bundling визуальный для `CITES` от одного `Work` к группе работ (только при force-mode и >K соседей).

**Acceptance:** На сложном workspace (≥ 30 работ) сразу видны «звёзды» — наиболее цитируемые работы; контекст (`Venue`/`Institution`) виден при приближении.

**Ориентир:** 1 backend-PR + 1 UI-PR, ~2 дня каждая.

---

## 6. Что **не** входит в этот план (явно отложено)

- **`Concept` / `ResearchTopic` визуализация** — дождаться [ADR 013](../adr/013-concept-research-topic-ontology-v1-5.md) production-promotion (Wave N→O в [`ontology-benchmarks-roadmap-2026-04-24.md`](../ontology-benchmarks-roadmap-2026-04-24.md)). Когда появятся, агрегация (Wave GR3) переиспользуется как есть.
- **`Claim` / `Evidence` визуализация** — Wave O production-флаг ([ADR 008](../adr/008-ontology-claims-wave-h.md)); отдельная схема рендера.
- **GDS-based community detection** — пока force-симуляция справляется; см. [ADR 012](../adr/012-workspace-graph-projection.md).
- **Server-persisted layout** — оставлено на «когда будет продуктовая надобность» ([graph-ui-plan.md *Layout stack v1*](../specs/graph-ui-plan.md)).
- **Sigma / WebGL рендер** — backlog ([`refactor-frontend.md`](../backlog/refactor-frontend.md)). Не нужен, пока узлов < ~2000 после агрегации (после GR3 типичные значения <300).
- **Полная dedup `:Author`** — у этого плана **зависимость**, но она не блокирующая: даже без полного dedup чтение через `display_label = full_name` уже резко улучшит картинку. Полный merge — в Wave T.

---

## 7. Открытые вопросы (до старта Wave GR3/GR4)

1. **Default `view`.** Стартуем с `reader` сразу для всех клиентов или вводим `?view=reader` opt-in и переводим UI отдельно? Предложение: opt-in на бэкенде (default `raw` для совместимости), `reader` принудительно из UI. Это исключает ломку CLI/snapshot-сценариев.
2. **`aggregator_threshold` (перенесено в GR3).** В GR2 не меняем; параметр и место хранения согласуем перед стартом Wave GR3.
3. **`AUTHORED_THROUGH` или `AFFILIATED_AS_AUTHOR`?** Имя виртуального ребра. Предлагаемое: просто `AUTHORED`, аффилиация — в `properties` ребра или текстом в `summary`.
4. **`Authorship` в edge-инспекторе.** При клике на виртуальное `AUTHORED` показывать «trace via Authorship UUID» в Advanced или скрыть полностью?
5. **Бенчмарк `graph_v1` контракт.** Если `view=raw` остаётся источником истины для тестов, надо ли в gold-payloads явно фиксировать `display_label`? Скорее нет — gold должен оставаться структурным.

---

## 8. Что закрывается этим планом (итог)

После прохождения GR1–GR5 пользователь, открывая `/graph` или Workspace → Graph:

- **не видит UUID** в подписях узлов и рёбер;
- видит читаемые подписи рёбер вместо `HAS_AUTHORSHIP` и т. п.;
- не видит десятков `:Authorship` дисков для работ с большим числом авторов (агрегатор `8 authors` или скрытые в reader-mode);
- сразу замечает, кто из работ — внутренний (workspace), кто — внешний;
- видит «вес» работ через размер узла (наиболее цитируемые крупнее);
- сохраняет полный raw-доступ к UUID и схеме через Advanced JSON и `?view=raw`;
- не теряет совместимости с benchmark `graph_v1` и с прямыми Cypher-запросами в Neo4j.

Все правки **аддитивны** по контракту и **не меняют** канон [ADR 002](../adr/002-layer1-graph-model.md) и [ADR 005](../adr/005-authorship-reified-node.md).

---

## 9. Связанные backlog-записи

После одобрения плана добавить в backlog (формат — см. [`.cursor/rules/refactor-rhythm-and-backlog.mdc`](../../.cursor/rules/refactor-rhythm-and-backlog.mdc)):

- [`refactor-backend.md`](../backlog/refactor-backend.md):
  - `[OPEN] Graph readability — Wave GR1: display_label для Authorship/Author/Institution/Venue` (`science_graphrag/api/works.py`, `workspace_graph.py`).
  - `[OPEN] Graph readability — Wave GR2: node_kind + семантичные display_type + prioritized LIMIT`.
  - `[OPEN] Graph readability — Wave GR3: Aggregator nodes + lazy expand endpoint`.
  - `[OPEN] Graph readability — Wave GR4: view=reader с виртуальным AUTHORED`.
  - `[OPEN] Graph readability — Wave GR5: денормализованные счётчики на :Work`.
- [`refactor-frontend.md`](../backlog/refactor-frontend.md):
  - `[OPEN] Graph UI — Aggregator rendering + expand-on-click` (привязан к GR3).
  - `[OPEN] Graph UI — Reader-mode toggle + tiered styling + adaptive labels` (GR4 + GR5).
- ADR-кандидаты (после согласования open questions §7):
  - `ADR 016: Graph projection — view=raw vs view=reader` (если решим закрепить как контракт).
