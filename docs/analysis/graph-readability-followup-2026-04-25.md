# Graph readability follow-up — диагноз GR2/GR3 и план Wave GR6–GR12

**Дата:** 2026-04-25
**Статус:** living working doc; продолжение [`_archive/graph-ux-aggregation-roadmap-2026-04-25.md`](_archive/graph-ux-aggregation-roadmap-2026-04-25.md) [HISTORICAL]. Закрывает реальные пробелы между «декларативно done» и «видно пользователю» по треку **E** в [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md).

**Триггер:** Пользователь видит на канвасе сырые `HAS_AUTHORSHIP`, `OF_AUTHOR`, `AFFILIATED_WITH`, нет русской локализации, кучу одиночных дисков `:Authorship` вокруг `:Work` без агрегации, и **верхнюю панель графа** из трёх несогласованных полос: тулбар, отдельная полоса иконок и легенда «Types in view» с непереведёнными `WorkInternal`/`HAS_AUTHORSHIP`/`CITES`. **Дополнительно** (раунд 2026-04-25, скриншоты `assets/image-ab4575…`, `assets/image-5a7c97…`, `assets/image-c032a0…`) — правая панель деталей (`GraphDetailPanel.jsx`) выглядит как «список абзацев»: тип узла идёт текстом без иконки/цвета, метрики цитирований склеены в одну строку, карточки соседей повторяют имя выбранного узла, дублируются три раза для ребра, везде «lateral» вместо direction. Согласно мастер-роадмапу GR1/GR2 «done», но по факту:

1. **GR2 не доехал до UI** — backend отдаёт `display_type`, фронт его игнорирует на канвасе.
2. **GR3 (агрегаторы) сделан** только под `Work` и при `≥ 8` соседях одного `(node_kind, edge_type)`; типичная статья с 4–6 авторами и 5–10 цитированиями не агрегируется → визуально картинка как до GR3.
3. **GR4 (`view=reader`) не реализован** — сами `:Authorship` диски остаются на канвасе всегда.
4. **EN-only display labels** — словарь живёт на бэкенде, поэтому i18n рёбер невозможна без правки контракта.
5. **Верхняя панель распадается на три полосы** — `WorkspaceGraphToolbar`, отдельная икон-полоса (`Sidebar`/`Layers`/`Bug`), `GraphTypeLegend` («Types in view»). Дублируется концепция «фильтр по типу» (toolbar-чипы) ↔ «список присутствующих типов» (legend-чипы), нет tooltips/поиска/reset/preset, нет toggle для `view=reader|raw`, в standalone-графе тулбара вообще нет.
6. **Правая панель деталей не использует уже готовые иконки/цвета типов** (`NODE_TYPE_ICON_MAP` и `NODE_TYPE_STYLES` живут только для канваса/легенды), карточки соседей перегружены повторяющимся текстом и не сгруппированы, edge-инспектор повторяет одну и ту же фразу 3 раза, нет «Properties» секции для рёбер, нет «open by name» на кнопках, нет копирования ID/JSON, нет breadcrumb-навигации, лейблы «lateral»/«WorkInternal» говорят жаргоном.

Этот документ:
- фиксирует диагноз с указанием конкретных файлов и строк;
- расширяет план на Wave GR6 (UI integration GR2), GR7 (i18n graph display), GR8 (smarter aggregation defaults), GR9 (reader view production), **GR10 (Toolbar IA/UX redesign), GR11 (i18n легенды как расширение GR7), GR12 (Right detail panel UX overhaul)**;
- обновляет статус GR2 в `master-roadmap` и записывает open backlog-пункты в `refactor-backend.md` / `refactor-frontend.md`.

**Связанные документы:**

| Документ | Что в нём |
|----------|-----------|
| [`_archive/graph-ux-aggregation-roadmap-2026-04-25.md`](_archive/graph-ux-aggregation-roadmap-2026-04-25.md) | [HISTORICAL] Исходный план Wave GR1–GR5, контракт UI ↔ API |
| [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md) | Карта треков и параллельности; нуждается в правке статуса GR2 |
| [`../adr/011-graph-live-ux-and-payload.md`](../adr/011-graph-live-ux-and-payload.md) | Контракт `display_label / subtitle / display_type / node_kind` |
| [`../adr/005-authorship-reified-node.md`](../adr/005-authorship-reified-node.md) | `:Authorship` остаётся reified в Neo4j |
| [`../specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md) | Контракт i18n EN/RU в `ui/src/i18n/` |
| [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) | Backlog для GR2/GR4/GR5/GR6 backend-частей |
| [`../backlog/refactor-frontend.md`](../backlog/refactor-frontend.md) | Backlog для UI-частей GR2/GR3/GR4 + локализация |

---

## 1. Диагноз: что именно не работает

### 1.1 Bug: канвас рисует `edge.type`, а не `edge.displayType`

`science_graphrag/api/graph_display.py` — словарь `EDGE_DISPLAY_TYPE_RAW` корректно отображает `HAS_AUTHORSHIP → "authored by"`, `OF_AUTHOR → "is author of"`, `CITES → "cites"`, и т. д. Этот `display_type` уезжает в payload (`_enrich_edges_with_display` в `science_graphrag/api/works/graph_neighborhood.py` и аналог в `science_graphrag/api/workspace_graph/projection.py`).

Frontend-нормализатор `ui/src/components/graph/model/graphViewState.js` правильно достаёт его в `edge.displayType`:

```113:120:ui/src/components/graph/model/graphViewState.js
  const normalizedEdges = rawEdges.map((edge, index) => {
    const e = edge && typeof edge === "object" ? /** @type {Record<string, unknown>} */ (edge) : {};
    const src = e.source == null ? "" : String(e.source);
    const tgt = e.target == null ? "" : String(e.target);
    const typ = e.type == null ? "edge" : String(e.type);
    const eid = e.id == null ? `edge-${index}` : String(e.id);
    const displayType = pickStringField(e, ["display_type", "displayType"], typ.replace(/_/g, " ") || "related");
```

Боковая панель и React Flow адаптер используют `displayType`:

```285:290:ui/src/components/graph/shell/GraphDetailPanel.jsx
              {(relatedEdges || []).map((edge) => {
                const otherId = edge.source === selectedNode.id ? edge.target : edge.source;
                const other = nodeMap.get(otherId);
                const dispType = edge.displayType || String(edge.type || "").replace(/_/g, " ");
```

```60:66:ui/src/components/graph/flow/graphFlowAdapter.js
  return rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.displayType || e.type,
```

**Но канвас — нет:**

```106:128:ui/src/components/graph/canvas/graphCanvasDraw.js
  for (const edge of edges) {
    const p0w = positions.get(edge.source);
    const p1w = positions.get(edge.target);
    if (!p0w || !p1w) continue;
    const p0 = worldToScreen(p0w.x, p0w.y, scale, tx, ty);
    const p1 = worldToScreen(p1w.x, p1w.y, scale, tx, ty);
    const elabel = edgeTypeCanvasLabel(edge.type);
    if (!elabel || elabel === "—") continue;
    ...
    ctx.fillText(elabel, midX, midY);
  }
```

Строка 112 `edgeTypeCanvasLabel(edge.type)` подаёт raw Neo4j-тип (`HAS_AUTHORSHIP`), и `edgeTypeCanvasLabel` ничего не делает кроме truncation:

```135:141:ui/src/components/graph/canvas/graphCanvasStyle.js
export function edgeTypeCanvasLabel(edgeType) {
  return truncateCanvasLabel(edgeType == null ? "" : String(edgeType).trim(), EDGE_LABEL_MAX);
}
```

**Это и есть «ребра имеют наименование прямо из neo4j»** — Wave GR2 прошла по бэкенду, но в default-визуализации (Canvas) **не применяется**.

### 1.2 i18n рёбер архитектурно невозможна сейчас

Backend хардкодит **EN-строки** в `EDGE_DISPLAY_TYPE_RAW`:

```19:35:science_graphrag/api/graph_display.py
EDGE_DISPLAY_TYPE_RAW: dict[str, str] = {
    "HAS_AUTHORSHIP": "authored by",
    "OF_AUTHOR": "is author of",
    ...
}
```

Те же строки уезжают в `display_type`, `summary`, `source_label`, и в текст агрегатора (`f"{count} {node_kind.lower()} of Work"`). UI-локаль не учитывается — значит даже если канвас начнёт показывать `displayType`, он будет **только по-английски**.

`ui/src/i18n/messages/{en,ru}/partGraphUi.js` уже содержит локализацию **узлов** (`graph.wsToolbar.nodeType.Work` → «Работа»/«Work»), но **рёбра не покрыты вовсе**.

Аналогичная ситуация с `node.subtitle` и `node.displayLabel` — backend всегда строит на EN (`"Author"`, `"Author #1 · IBM Research"`, `"8 authors"`).

### 1.3 Агрегаторы редко срабатывают

```19:19:science_graphrag/api/works/graph_neighborhood.py
AGGREGATOR_THRESHOLD = 8
```

```56:77:science_graphrag/api/works/graph_neighborhood.py
def _apply_aggregators(
    work_id: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    threshold: int = AGGREGATOR_THRESHOLD,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ...
    for edge in edges:
        ...
        for owner_id, neighbor_id in ((src_id, tgt_id), (tgt_id, src_id)):
            owner = node_by_id.get(owner_id)
            neighbor = node_by_id.get(neighbor_id)
            if not owner or not neighbor:
                continue
            if str(owner.get("type") or "") != "Work":
                continue
            neighbor_kind = str(neighbor.get("node_kind") or neighbor.get("type") or "Node")
            key = (owner_id, neighbor_kind, edge_type)
```

**Ограничения текущей реализации:**

1. **Threshold 8** — для типичной статьи с 4–7 соавторами и 5–10 цитированиями группа никогда не достигает порога.
2. **Только `Work` как owner** — `:Author` с 12 соавторами, `:Institution` с 30 публикациями — **не** агрегируются.
3. **Группировка по `(owner, kind, edge_type)`** — `:Authorship` соседи `Work` через `HAS_AUTHORSHIP` агрегируются отдельно от `:Author` через две прыжка — это два разных edge_type, поэтому даже на 10 авторах эффект не аддитивен.
4. **Нет cap-агрегации.** Если `is_truncated=true` и `:Work` цитирует 50 работ, а в payload влезло 12 — агрегатор не строится, потому что раньше отработал `LIMIT`.
5. **Нет агрегации «прочего»** — все «остальные» соседи одного типа можно сворачивать в `+N more` независимо от `edge_type`, но это не реализовано.

### 1.4 Reader view не реализован

```280:282:science_graphrag/api/works/graph_neighborhood.py
    view: str = "reader",
```

Параметр `view` есть в подписи функции, но единственное, на что он влияет — включение/выключение `_apply_aggregators`:

```425:426:science_graphrag/api/works/graph_neighborhood.py
    if str(view or "reader").strip().lower() != "raw":
        nodes, edges = _apply_aggregators(work_id, nodes, edges, threshold=AGGREGATOR_THRESHOLD)
```

**`:Authorship`-узлы и `HAS_AUTHORSHIP`/`OF_AUTHOR`-рёбра возвращаются всегда**, виртуальные `Work –[AUTHORED]→ Author` рёбра не строятся. Это и есть Wave GR4, всё ещё `[OPEN]` в backlog.

### 1.5 Верхняя панель графа: три несогласованных полосы и пробелы IA/UX

**Симптом (по скриншоту `assets/image-89eb621b-3b7b-4654-b864-c8172d887841.png`):** над канвасом стоят подряд

1. чёрная плашка-тулбар с заголовком «Граф рабочей области», mode-кнопками `ВНУТРЕННИЙ / ОБЪЕДИНЕНИЕ +1 / СЕМАНТИКА / ПОЛНЫЙ`, depth `ГЛУБИНА 1 / ГЛУБИНА 2`, switch «Внешние», чипами «Типы узлов» и stats справа;
2. полоса иконок Sidebar / Layers / Bug;
3. блок «Types in view» с группами `Nodes` / `Edges` и **сырыми EN-метками** `WorkInternal`, `WorkExternal`, `Method`, `Dataset`, `AuthorshipReification`, `Venue`, `CITES`, `HAS_AUTHORSHIP`, `PUBLISHED_IN`, `USES_METHOD`, `EVALUATED_ON`, `CONTAINS`.

**Конкретные пробелы (по коду):**

1. **Дублирующиеся «панели типов» с разными ролями.** В `ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx:201-227` чипы — это **серверный фильтр** (`nodeTypesCsv` уезжает в API). В `ui/src/components/graph/shell/GraphTypeLegend.jsx:81-114` чипы — **информационный список** того, что фактически есть в payload. Визуально это «два ряда чипов с иконками», пользователь не различает.
2. **MUI `ToggleButton` с дефолтным uppercase.** `WorkspaceGraphToolbar.jsx:163-179` использует `<ToggleButton>` без `textTransform: 'none'` — отсюда `ВНУТРЕННИЙ`/`ОБЪЕДИНЕНИЕ +1`. Это нарушает Cursor-стиль (`.cursorrules`: «❌ textTransform: 'uppercase'») и расходится с `GraphViewModeSwitch.jsx`, где уже используются `CursorSmallButton`.
3. **Нет tooltips ни на одном элементе тулбара.** `mode`-кнопки, `depth`, switch «Внешние», чипы — без подсказок. Mode «Объединение +1» / «Семантика» без расшифровки непрозрачен даже автору.
4. **Полоса иконок занимает отдельную строку.** `GraphWorkspacePanel.jsx:167-220` рисует `Sidebar`/`Layers`/`Bug` отдельным `<Box>`, при этом `Layers` показан только в `standalone` режиме, а `Bug` — только когда `!labMode`. Эти 1–3 иконки логичнее встроить в правый край тулбара.
5. **`GraphViewModeSwitch` (Cards/Graph/Flow) — четвёртая полоса.** Рендерится отдельно в `GraphWorkspacePanel.jsx:166`. Логически это «как показать граф» — должен сидеть в той же панели, что и фильтры «что показывать».
6. **`GraphTypeLegend` в embedded-режиме не сворачивается.** `GraphWorkspacePanel.jsx:223-229`: `<Collapse>` обёртка применяется только при `standalone`. В embedded — занимает место постоянно.
7. **В standalone (graph для одной работы) тулбара нет вовсе.** `GraphWorkspacePanel.jsx:165` — `<WorkspaceGraphToolbar … />` рендерится только при `wsId`. У страницы `/graph?work_id=…` нет ни фильтра типов, ни depth-toggle (он живёт **отдельно** в `GraphPage.jsx:94-100` как URL-параметр `graph_depth`, без UI).
8. **Нет ключевых функций.** Отсутствуют: поиск по узлу (для больших графов критично), reset-to-defaults, save-preset, export (PNG/JSON), fit-to-screen / zoom-controls в быстром доступе, toggle `view: reader | raw` (нужен для GR9), override `aggregator_threshold` (нужен для GR8).
9. **Stats-строка обрывается.** На скриншоте справа: «2 стат · 8 авт · 27 ребер · цит.» — последний фрагмент `n внеш. цит.` обрезан, потому что считаемая ширина контейнера не учитывает wrap. `WorkspaceGraphToolbar.jsx:230-244` рендерит stats как right-aligned `<Typography>` с `flexShrink: 0` без tooltip и без compact-режима.
10. **Чип-фильтр всегда показывает 6 типов**, даже если в текущем workspace нет `Method`/`Dataset`. `NODE_TYPE_OPTIONS` в `WorkspaceGraphToolbar.jsx:15` хардкоднут. Нет «снять все» / «выбрать все».

### 1.6 Правая панель деталей: иконки не используются, информация дублируется, edge-инспектор перегружен

**Симптомы (по скриншотам `assets/image-ab4575…`, `assets/image-5a7c97…`, `assets/image-c032a0…`):**

- Над «Details» сразу идёт текст `WorkInternal` синим цветом (выглядит как ссылка, но кликом ничего не делает); внизу — крупный заголовок узла; под ним строкой `internal int cites: 0 ext cites: 1` (три разных слова склеены без визуальной структуры).
- В «Connections» 8 одинаковых карточек «lateral», каждая повторяет имя текущего узла (`XRAG: Cross-lingual Retrieval-Augmented Generation —[evaluated on]→ XOR QA`). 5 рядом стоящих `evaluated on` — без группировки.
- Для ребра «Relationship» полная фраза `Gemma —[contains]→ Research` напечатана трижды: в заголовочном `<Typography>`, в чипе `contains`, и снова в `summary` поле raw-JSON. Кнопки `Open source / Open target` — без имён узлов.
- У Dataset «News Crawl» подзаголовок `Dataset` дублирует тип `Dataset`.
- Toggle Raw JSON у узла — кнопка, у ребра — `<Accordion>`. Несогласованно.

**Конкретные пробелы (по коду `ui/src/components/graph/shell/GraphDetailPanel.jsx` и `graphInspectorModel.js`):**

1. **Иконки/цвета типов не используются.** В `ui/src/components/graph/canvas/graphCanvasStyle.js:31-42` уже есть готовый `NODE_TYPE_ICON_MAP` (`ArticleOutlinedIcon` для `Work`, `PersonOutlinedIcon` для `Author`, `StorageOutlinedIcon` для `Dataset`, `PsychologyOutlinedIcon` для `Method`, `MenuBookOutlinedIcon` для `Venue`, `AccountBalanceOutlinedIcon` для `Institution`, `LinkOutlinedIcon` для `Authorship`, `OpenInNewOutlinedIcon` для `WorkExternal`) и `NODE_TYPE_STYLES` с цветами. Их использует только `GraphTypeLegend.jsx` и канвас. `GraphDetailPanel.jsx:184-186` рендерит лишь `<Typography>{selectedNode.nodeKind || selectedNode.type}</Typography>` синим цветом — без иконки и без цветового ключа.

2. **`WorkInternal` рендерится как camelCase-жаргон.** Backend отдаёт `node_kind = "WorkInternal"` для удобства типизации; UI должен показывать `[icon Article] Work · internal` (тип + бейдж membership), не как одно слово. Аналогично `WorkExternal`, `AuthorshipReification`.

3. **Subtitle дублирует type.** `GraphDetailPanel.jsx:190-192` всегда печатает `subtitle`, даже если он равен типу или displayLabel. Для Dataset `News Crawl` приходит `subtitle = "Dataset"` — это шум, надо подавлять `subtitle === type || subtitle === nodeKind || subtitle === displayLabel`.

4. **Метрики цитирований склеены в плоскую строку.** `GraphDetailPanel.jsx:198-215` рендерит `workspaceMembership` / `int cites` / `ext cites` как три `<Typography>` подряд через `flex-wrap`. Нужны **stat-чипы с иконками**: `[CallReceivedIcon] int cites: 0`, `[CallMadeIcon] ext cites: 1`, плюс новая «degree: N связей в текущем виде» (которой сейчас нет вообще).

5. **«Connections» дублирует `selectedNode.displayLabel` в каждой карточке.** `GraphDetailPanel.jsx:299-304`: `readableLine` собирается через `humanEdgeSummary` (`graphInspectorModel.js:31-45`) как `${sourceLabel} —[type]→ ${targetLabel}` — для текущего узла источник/цель **уже** заголовок панели. Получается «XRAG —[evaluated on]→ XOR QA» в каждой строке. Должно быть просто «evaluated on → XOR QA» (или «← evaluated on от XOR QA» для incoming).

6. **«lateral» — мистическое слово.** `science_graphrag/api/workspace_graph/projection.py:148` ставит `edge.direction = "lateral"` для рёбер workspace-проекции, у которых нельзя однозначно определить направление относительно центра. UI (`graphInspectorModel.js:99`) пробрасывает строку как есть, и `GraphDetailPanel.jsx:280-282` рендерит её строчными буквами. Для пользователя это шум — нужно скрывать значение, когда оно `lateral`, или заменять на нейтральное «связь».

7. **Нет группировки соседей по типу ребра.** Для XRAG со скриншота — 5 «evaluated on», 1 «uses method», 1 «cites», 1 «evaluated on (XRAG self?)» — все 8 идут плоским списком. Нужны collapsible-секции `▾ evaluated on (5) / uses method (1) / cites (1)`.

8. **Нет иконки типа узла-соседа в карточке.** `GraphDetailPanel.jsx:283-298` рисует только `ArrowForwardIcon` + chip с типом ребра + текстовое имя соседа. Глаз не цепляется за «работа vs автор vs метод» — нужна `[icon] Имя` слева, та же иконка из `NODE_TYPE_ICON_MAP`.

9. **Нет фильтра/поиска по соседям.** При 30+ связях единственный способ найти конкретного — глазами скроллить.

10. **Нет «open neighbour»-tooltip с типом и кратким описанием.** Hover на карточку соседа сейчас просто меняет border-color; мог бы показывать tooltip с `displayLabel + subtitle + nodeKind`, чтобы не нужно было кликать ради превью.

11. **Edge-инспектор: тройное дублирование информации.** `GraphDetailPanel.jsx:131-148`:
    - строка 132: «Relationship» (заголовок)
    - строка 133-136: `selectedEdgeReadable` («Gemma —[contains]→ Research»)
    - строка 137-139: chip `contains`
    - строка 141-142: «Open source», «Open target» — без имён узлов
    Должно быть: одна большая «карта ребра» — `[icon source] Gemma → [edge-icon][edge-label] contains → [icon target] Research`, источник/цель кликабельны, кнопки именованы (`Открыть Gemma` / `Открыть Research`).

12. **У ребра нет секции «Properties».** У `CITES` бывает `year`/`weight`, у `OF_AUTHOR` — `author_position`, `is_corresponding`, `raw_affiliation`, у виртуального `AUTHORED` (GR9) — `via: ["HAS_AUTHORSHIP","OF_AUTHOR"]` + те же `author_position`/`raw_affiliation`. Сейчас `selectedEdge.raw.properties` (если бы оно было) скрыто в Advanced JSON — пользователь ничего не видит, пока не раскроет.

13. **Кнопки `Open source / Open target` — без имён узлов** (`GraphDetailPanel.jsx:141-142`). Должны быть `Открыть Gemma` / `Открыть Research` или хотя бы `Открыть источник: Gemma` / `Открыть цель: Research`.

14. **Inconsistent Raw JSON UI.** Узел: кнопка-toggle `Show advanced (raw JSON)` (`GraphDetailPanel.jsx:344-368`). Ребро: `<Accordion>` (`GraphDetailPanel.jsx:372-407`). Должно быть одно решение — `<Accordion>` для обоих, плюс кнопка «Скопировать JSON».

15. **Нет breadcrumb-навигации (back/forward).** Клик на соседа в Connections мгновенно переключает selection — пользователь теряет контекст «откуда пришёл». Нужна мини-история (`history.push(nodeId)`) с кнопкой `←` сверху панели.

16. **Нет «copy id»** для отладки. Сейчас id виден строчкой `id: e_3347020ff3460d096e0b29` (`GraphDetailPanel.jsx:144-146`) с моноширинным шрифтом, но не копируется в один клик.

17. **Нет «open in main view»** для Work-узла (ссылка на страницу работы `/works/{id}`).

18. **`directionHint` локализуется неправильно.** Хардкод EN `"outgoing"` / `"incoming"` / `"lateral"` (`graphInspectorModel.js:54-59`) рендерится как есть. Должно быть `t("graph.detail.direction.outgoing"/"incoming")` через `graphLocalize.js` (тот же модуль, что GR7).

19. **Нет skeleton/empty-state иллюстрации.** Когда ничего не выбрано — голый текст «Select a node or an edge…» (`GraphDetailPanel.jsx:115-127`). Можно показать маленький SVG/иконку «↗ кликни узел» / «↘ кликни ребро» с подсказками типов.

20. **Aggregator-секция (`GraphDetailPanel.jsx:152-183`) — без иконки и без бейджа `count` крупно.** Сейчас `Aggregator` пишется текстом сверху, имя — большим шрифтом, потом kind строчкой. Лучше: `[GroupOutlinedIcon] {count} {kind-label}`, кнопка «Раскрыть» внизу.

21. **Truncation alert (`GraphDetailPanel.jsx:93-113`) говорит API-жаргоном.** Для пользователя «Increase `neighbor_limit` on the API query» — бессмысленная фраза. Должно быть «Показано {x} из {y} связей. Используйте поиск / фильтр / нажмите “Развернуть”» с кнопкой действия (если возможно — увеличить limit на лету).

22. **Нет sticky-заголовка панели.** При скролле в длинном списке Connections заголовок (`displayLabel + nodeKind`) уходит за край — пользователь забывает, на каком узле он находится.

23. **Нет keyboard shortcut hints.** `Esc` для clear, `←/→` для history — нигде не подсказано.

24. **A11y.** `<Typography component="h2">Details` — единственный заголовок; «Key properties» / «Connections» — это `<Typography>` без ролей. Карточки соседей — `<button>` без `aria-describedby` для `directionHint`. Color contrast 0.45 alpha на `#1a1a1a` — около 3.5:1, ниже WCAG AA для текста.

### 1.7 Расхождение в роадмапе

[`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md):

```
| **E** | Graph UX aggregation | ... | GR1 done, GR2 done, GR3..GR5 open | ...
```

[`refactor-backend.md`](../backlog/refactor-backend.md):

```
### [OPEN] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
```

На самом деле:
- **GR2 backend done** — `node_kind`, `display_type`, prioritized LIMIT и `meta.skipped_by_kind` доставлены.
- **GR2 frontend NOT done** — канвас игнорирует `displayType`; легенда не использует `node_kind` для группировки.
- **GR3 backend done**, но **с дефолтами слишком высокого порога**.
- **GR4 not started** — параметр-заглушка, нет виртуальных рёбер.
- **GR5 not started** — счётчики не персистятся.

**Действие:** мастер-роадмап обновить как `GR2 partial (backend done, UI integration pending → Wave GR6)`.

---

## 2. План Wave GR6–GR12

Дополнительные волны идут **за** GR1–GR5 в одном треке E. Нумерация — GR6+, чтобы не переписывать историю и сохранить трасеабилити с уже завершёнными PR.

### 2.1 Wave GR6 — UI integration GR2 (срочный пользовательский фикс)

**Цель:** ребра на канвасе должны называться человечески, как боковая панель и Flow-режим. Это самая громкая жалоба пользователя — закрывается 1 PR за пол-дня.

**Чеклист (frontend):**

- [ ] [`ui/src/components/graph/canvas/graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js) line 112: `edgeTypeCanvasLabel(edge.type)` → `edgeTypeCanvasLabel(edge.displayType || edge.type)`. Эта же правка снимает дубли «raw vs side-panel» — поведение Flow и Canvas сравняется.
- [ ] [`ui/src/components/graph/canvas/graphCanvasStyle.js`](../../ui/src/components/graph/canvas/graphCanvasStyle.js): расширить `edgeTypeCanvasLabel(edgeType, opts?)` так, чтобы вход — уже готовая `displayType` (без преобразований), но при пустоте — fallback на raw `type` с замены `_` на пробел.
- [ ] Обновить unit-тесты: [`graphCanvasDraw.test.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.test.js) — добавить кейс «edge с displayType=`authored by` → bbox-метрика рисуется».
- [ ] Verify: `cd ui && npm run lint && npm test`.

**Acceptance:**

1. На канвасе `/graph?work_id=…` ребра показывают `authored by` / `is author of` / `cites` вместо `HAS_AUTHORSHIP` / `OF_AUTHOR` / `CITES`.
2. Боковая панель и канвас визуально согласованы.

**Ориентир:** 1 frontend-PR, < 1 дня, без backend-изменений.

### 2.2 Wave GR7 — i18n graph display (EN/RU для рёбер и подписей агрегаторов)

**Цель:** русская локаль показывает «цитирует», «является автором», «8 авторов» вместо EN-строк.

#### 2.2.1 Decision: где локализовать?

Есть два варианта:

| Вариант | Плюсы | Минусы |
|---------|-------|--------|
| **A. UI переводит по `edge.type`** (raw key как identifier) | Backend не меняется, контракт стабилен; UI владеет всем переводом | UI должен повторить словарь типов; фолбэк на `displayType` если `type` не в словаре |
| **B. Backend отдаёт `display_type_key` (`"edge.authored_by"`)** | Идентификатор стабилен, EN/RU/любая локаль на стороне UI; backend больше не «отвечает» за человечность | Меняется payload-контракт (аддитивно), нужно обновить ADR 011 |

**Рекомендация:** комбинированный вариант **A + opt-in B**. На первом проходе делаем A (быстро, без правки контракта), на втором проходе — `display_type_key` как **аддитивное** поле для будущих типов рёбер (`SUPPORTS`, `MENTIONS`, новые claim-edges из Wave O), чтобы UI всегда мог переводить по ключу, а не по строке.

#### 2.2.2 Чеклист (frontend, вариант A)

- [ ] Добавить ключи в [`ui/src/i18n/messages/en/partGraphUi.js`](../../ui/src/i18n/messages/en/partGraphUi.js) и [`ui/src/i18n/messages/ru/partGraphUi.js`](../../ui/src/i18n/messages/ru/partGraphUi.js):
  - `graph.edgeType.HAS_AUTHORSHIP` / `graph.edgeType.OF_AUTHOR` / `graph.edgeType.AFFILIATED_WITH` / `graph.edgeType.CITES` / `graph.edgeType.PUBLISHED_IN` / `graph.edgeType.USES_METHOD` / `graph.edgeType.EVALUATED_ON` / `graph.edgeType.TRAINED_OR_TESTED_ON` / `graph.edgeType.SUPPORTS` / `graph.edgeType.CONTRADICTS` / `graph.edgeType.MENTIONS` / `graph.edgeType.AGGREGATED`.
  - `graph.nodeKind.AuthorshipReification` / `graph.nodeKind.WorkInternal` / `graph.nodeKind.WorkExternal` / `graph.nodeKind.Aggregator`.
  - `graph.aggregator.label.authors_of_work`, `graph.aggregator.label.cites_external` (с `{{count}}`).
- [ ] Создать [`ui/src/components/graph/graphLocalize.js`](../../ui/src/components/graph/model/graphLocalize.js) с функциями `localizeEdgeType(edge, t)`, `localizeNodeKind(node, t)`, `localizeAggregatorLabel(node, t)` — единая точка локализации для канваса, Flow и боковой панели.
- [ ] Поправить [`graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js): вместо `edgeTypeCanvasLabel(edge.type)` → `edgeTypeCanvasLabel(localizeEdgeType(edge, t))`. Поскольку модуль не реактовский, передавать `t` через props в `<GraphCanvasMvp>` и пробрасывать в `drawLabels`.
- [ ] Тоже самое в [`graphFlowAdapter.js`](../../ui/src/components/graph/flow/graphFlowAdapter.js) и [`GraphDetailPanel.jsx`](../../ui/src/components/graph/shell/GraphDetailPanel.jsx) — заменить inline-формирование label на `localizeEdgeType` / `localizeNodeKind`.
- [ ] Обновить легенду [`GraphTypeLegend.jsx`](../../ui/src/components/graph/shell/GraphTypeLegend.jsx) — показывать локализованные имена типов рёбер при hover/expand.
- [ ] Тесты: `ui/src/components/graph/model/graphLocalize.test.js` (или совместно в `ui/src/components/graph/canvas/graphCanvasDraw.test.js`).

#### 2.2.3 Чеклист (backend, опциональная фаза B — только если будем расширять словарь)

- [ ] В `science_graphrag/api/graph_display.py` рядом с `EDGE_DISPLAY_TYPE_RAW` добавить `EDGE_DISPLAY_TYPE_KEY: dict[str, str] = {"HAS_AUTHORSHIP": "authored_by", ...}`.
- [ ] Расширить `_enrich_edges_with_display` так, чтобы edge получал `display_type_key`.
- [ ] Обновить ADR 011 — пометить новое поле как additive, не ломающее старых клиентов.
- [ ] **Если** делаем эту фазу — `compute_node_display` возвращает `display_subtitle_key` (`"node.work.with_year"` + `vars: {year}`), `_apply_aggregators` пишет `display_label_key`/`display_label_vars`. Это полная развязка контента и локали.
- [ ] Acceptance: тесты на пустые/неизвестные ключи (UI делает fallback на `display_type`/`display_label`).

**Acceptance:**

1. При переключении локали из header → ru → ребра подписаны как «цитирует», «является автором», «опубликовано в», «использует метод».
2. Узлы-агрегаторы показывают «8 авторов работы» / «12 внешних цитирований», а не «8 author of Work».
3. EN-локаль работает идентично сегодняшнему поведению (regression-safe).

**Ориентир:** UI-PR ~1 день (вариант A). Backend-PR ~0.5 дня (вариант B, опционально).

### 2.3 Wave GR8 — Smarter aggregation defaults

**Цель:** превратить «теоретический» агрегатор в инструмент, реально применимый к типичной статье. Пример пользователя — `:Work` с 6 `:Authorship`, и эта группа сейчас **не** агрегируется. Должна.

**Чеклист (backend):**

- [ ] В [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py): сделать порог **per-kind**:
  ```python
  AGGREGATOR_THRESHOLDS: dict[str, int] = {
      "AuthorshipReification": 4,  # типичная статья 4-6 авторов уже сворачивается
      "Author": 4,
      "Institution": 5,
      "Venue": 5,
      "Work": 8,  # цитирования — позже сворачиваются
  }
  ```
- [ ] Расширить `_apply_aggregators`:
  - [ ] разрешить owner-типы `Work`, `Author`, `Institution`, `Venue` (не только `Work`);
  - [ ] добавить query-параметр `aggregator_threshold` для override per-request (default per-kind);
  - [ ] добавить query-параметр `aggregator_disabled_kinds` (CSV: `Work,Method`) для опций «не агрегируй цитирования» / «не агрегируй методы»;
  - [ ] ввести **cap-aware aggregation**: если `meta.skipped_by_kind[X] > 0`, добавить агрегатор «`+N more X`» к owner-узлу, **даже если** в payload уже < threshold (показываем пользователю, что данные есть, но скрыты по лимиту);
  - [ ] `aggregation_hints` дополнить полем `summary_label_key` (из GR7 фазы B), чтобы UI рендерил локализованную подпись.
- [ ] Аналогичные правки в [`science_graphrag/api/workspace_graph/projection.py`](../../science_graphrag/api/workspace_graph/projection.py) (`apply_workspace_aggregators`).
- [ ] Дописать `_apply_aggregators` для **двух-хоп-цепочки** (`Work → Authorship → Author`): когда `view=raw` (или GR4 не активен), считать число `Author` через все `:Authorship` под одним `:Work` и при превышении порога схлопывать «`8 authors`» сразу, не оставляя `:Authorship` диски на канвасе. Это частично имитирует GR4 для тех, кто остался на raw.
- [ ] Тесты:
  - [ ] `tests/api/test_aggregator_thresholds.py` — кейсы `Work` × 4 авторов → агрегатор; `Work` × 3 авторов → не агрегируется.
  - [ ] Кейс `:Author` с 7 публикациями → агрегатор «7 publications».
  - [ ] Кейс с `is_truncated=true` → cap-агрегатор присутствует.

**Чеклист (frontend):**

- [ ] [`graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js): улучшить визуал агрегатора — больший радиус (`NODE_RADIUS * 1.4`), пунктирный stroke (уже есть), цифра `+N` уже рисуется. Добавить hover-tooltip «Click to expand».
- [ ] [`GraphDetailPanel.jsx`](../../ui/src/components/graph/shell/GraphDetailPanel.jsx): показывать список preview labels из `aggregation_hints.preview_labels` (уже частично сделано) и кнопку `t("graph.aggregator.expand")`.

**Acceptance:**

1. Типичная карточка с 5 авторами, 8 цитированиями и 1 venue **по умолчанию** показывает агрегатор «5 авторов», ребра CITES напрямую, и venue.
2. При cap-truncation в `meta` появляется счётчик-агрегатор «+N hidden authors», даже если показано всего 2.
3. На пустом workspace (1 работа, 0 цитат) — агрегаторов нет (regression-safe).

**Ориентир:** backend-PR ~1.5 дня (с тестами), frontend-PR ~0.5 дня.

### 2.4 Wave GR9 — Reader view с виртуальными `AUTHORED` рёбрами

**Цель:** доехать до полностью прочитываемого графа без `:Authorship`-дисков по умолчанию. Это тот самый Wave GR4, который остался `[OPEN]`. Переименован в GR9 для согласованности нумерации follow-up волн.

Чеклист повторяет [§5.4 первого роадмапа](_archive/graph-ux-aggregation-roadmap-2026-04-25.md#54-wave-gr4--viewreader-с-виртуальными-рёбрами-work--author) [HISTORICAL] с уточнением:

- [ ] **Default `view`** — обсудить отдельно (см. §3 ниже). Предлагается:
  - `/v1/works/{id}/graph?view=reader` — default `reader` (UI не передаёт ничего, получает свернутый граф).
  - `/v1/workspaces/{id}/graph?view=reader` — default `reader`.
  - `/v1/works/{id}/graph?view=raw` — для `science_graphrag/api/graph_snapshot_diff.py` и benchmark `graph_v1`.
- [ ] **Совместимость с GR8.** Reader-view → `:Authorship` отсутствует → агрегатор работает уже по `Author` (per-kind threshold = 4, см. GR8).
- [ ] **Контракт ребра `AUTHORED`:** `via: ["HAS_AUTHORSHIP","OF_AUTHOR"]`, `properties: { author_position, is_corresponding, raw_affiliation, institution_id? }`.
- [ ] **Edge-инспектор:** [`GraphDetailPanel.jsx`](../../ui/src/components/graph/shell/GraphDetailPanel.jsx) — секция «Trace via» при `via.length > 0`.
- [ ] **Toggle в UI:** [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx) — `Authorship details: collapsed | shown` (persist `localStorage.graphAuthorshipDetailMode`).
- [ ] Тесты: `tests/api/test_graph_view_reader.py` — симметрия `Work` и `Author` множества между raw и reader, разница только в рёбрах/`Authorship`-узлах.

**Acceptance:** см. оригинальный пункт. Дополнительно — `node_kind: "AuthorshipReification"` отсутствует в payload при `view=reader`.

**Ориентир:** backend-PR ~2 дня + frontend-PR ~1 день.

### 2.5 Wave GR10 — Toolbar IA & UX upgrade (единая верхняя панель)

**Цель:** убрать визуальный распад верхней зоны на три полосы, дать tooltips, поиск, reset, преды́сы (presets), сделать тот же тулбар доступным в standalone-графе работы. Без backend-изменений.

#### 2.5.1 Целевая IA: одна панель управления вместо трёх блоков

| Сейчас (3 полосы) | Предложение (1 панель из 2 секций) |
|-------------------|-------------------------------------|
| `WorkspaceGraphToolbar` (mode/depth/external/types/stats) | **Левая секция (filters)**: mode + depth + external + types + view (reader/raw) + threshold-меню |
| Полоса иконок (`Sidebar`/`Layers`/`Bug`) | **Правая секция (view & actions)**: view-mode (Cards/Graph/Flow), search, fit-to-screen, export, reset, sidebar/layers/diag, stats-summary |
| `GraphTypeLegend` («Types in view») | **Под панелью**, сворачиваемая везде; **читать-только**, без чипов-кнопок (избегаем дубля с серверным фильтром) |

Единая панель = один компонент-обёртка `GraphTopBar`, в нём `<GraphFiltersGroup>` слева и `<GraphViewActionsGroup>` справа. Существующие подкомпоненты (`WorkspaceGraphToolbar`, `GraphViewModeSwitch`, иконки из `GraphWorkspacePanel`) переезжают внутрь.

#### 2.5.2 Чеклист (frontend, новый компонент `GraphTopBar.jsx`)

- [ ] Создать [`ui/src/components/graph/GraphTopBar.jsx`](../../ui/src/components/graph/GraphTopBar.jsx) — обёртка с двумя секциями. Принимает все props текущего `WorkspaceGraphToolbar` плюс `vizMode/onVizModeChange`, `detailsVisible/onDetailsToggle`, `legendOpen/onLegendToggle`, `diagnosticsOpen/onDiagnosticsToggle`, `onSearch`, `onReset`, `onExport`, `onFitToScreen`.
- [ ] Перенести логику `WorkspaceGraphToolbar.jsx` в `GraphFiltersGroup.jsx` (левая секция). Заменить `<ToggleButton>` на `CursorSmallButton` с `ACTIVE_SX` (как в `GraphViewModeSwitch.jsx:6`) — снимает uppercase-проблему и приводит к Cursor-стилю.
- [ ] Перенести `GraphViewModeSwitch.jsx` (Cards/Graph/Flow) и икон-полосу из `GraphWorkspacePanel.jsx:167-220` в `GraphViewActionsGroup.jsx` (правая секция). Удалить отдельный `<Box>` с иконками из `GraphWorkspacePanel`.
- [ ] Оставить `WorkspaceGraphToolbar.jsx` как тонкую обёртку над `GraphFiltersGroup` для обратной совместимости тестов (`WorkspaceGraphToolbar.test.js` проверяет публичный экспорт `graphToolbarLocalStorageKey`).

#### 2.5.3 Чеклист (frontend, недостающие функции)

- [ ] **Tooltips на всех элементах filter-секции.** Под каждый `mode` — пояснение (`graph.wsToolbar.modeTooltip.inner_only`/`union_1hop`/`semantic_layer`/`full`), под `depth` — `graph.wsToolbar.depthTooltip.{1,2}`, под switch «Внешние» — `graph.wsToolbar.externalTooltip`, под чипы — `graph.wsToolbar.nodeTypeTooltip.{Work,Author,…}` («Показать/скрыть узлы типа Работа»).
- [ ] **Search-поле** — `<TextField size="small">` с `SearchOutlinedIcon`. По вводу делает highlight всех узлов с подстрокой в `display_label`/`title`/`name`. Подключаем через новый `useGraphSearch(displayGraph, query)` хук (clientside, без API). Persist последнего запроса не нужен.
- [ ] **Reset-кнопка** — `<CursorIconButton>` с `RestartAltOutlinedIcon` и tooltip `graph.wsToolbar.resetTooltip`. Сбрасывает `mode`/`depth`/`includeExternal`/`nodeTypesCsv` к дефолтам **и чистит соответствующие LS-ключи** (`workspaceGraph{Mode,Depth,IncludeExternal,NodeTypes}:<wid>`).
- [ ] **Save preset** (опционально, см. §3 вопрос #6) — кнопка «Сохранить вид как...» сохраняет текущий `value` в `workspaceGraphPreset:<wid>:<name>`; меню `<Popover>` со списком пресетов. Полезно «По умолчанию» / «Только Work+Author» / «Полный со всеми типами». Можно отложить на отдельный мини-PR, если scope большой.
- [ ] **Sidebar/Layers/Diagnostics иконки** уже есть в `GraphWorkspacePanel.jsx:167-220`, перенести как есть в `GraphViewActionsGroup`. Сделать `Layers` доступным **и в embedded** (сейчас только standalone) — т.е. legend сворачивается всегда.
- [ ] **Stats**: переделать в hover-tooltip на `<Chip icon={<InfoOutlinedIcon/>} label={"2 · 8 · 27"} />`. Полная строка («2 статьи · 8 авторов · 27 рёбер · 12 внешних цитирований») — в tooltip. Решает overflow-кейс из §1.5 п. 9.
- [ ] **Чипы типов: dynamic + чек-«все».** Перебирать `NODE_TYPE_OPTIONS` пересечённый с `presentKinds` (как делает `GraphTypeLegend`); добавить компактную ссылку «Сбросить» / «Все» рядом с группой чипов.
- [ ] **Удалить лишний title.** `Typography "Граф рабочей области"` (`WorkspaceGraphToolbar.jsx:153-155`) убрать — дублирует `<PageHeader>` страницы; aria-label оставить на `<Box role="toolbar">`.
- [ ] **Persist расширений в LS:** `workspaceGraphFiltersOpen:<wid>` (полный/коллапс панели на мобиле), `workspaceGraphLegendOpen:<wid>`. Контракт ключей — продлевает `Wave J` (см. `WorkspaceGraphToolbar.test.js`).

#### 2.5.4 Чеклист (frontend, standalone parity)

- [ ] **Подать `GraphTopBar` в standalone-графе работы** (`GraphPage.jsx`). Сейчас в standalone (`mode="standalone"` в `GraphWorkspacePanel.jsx:165`) тулбар не рендерится. Привязать к URL-параметрам:
  - `mode/depth/includeExternal/nodeTypesCsv` — пробросить через query-параметры `?graph_mode=…&graph_depth=…&graph_external=…&graph_types=…` или короче через единый `?graph=…` (json-encoded).
  - Это закрывает существующий backlog: «depth для standalone живёт только в URL» (`GraphPage.jsx:94-100`).
- [ ] **`view=reader|raw` toggle** — добавить как новый `mode`-параметр для GR9 (см. §2.4): отдельный switch «Reader-вид» рядом с «Внешние», persist `workspaceGraphView:<wid>`.

#### 2.5.5 Чеклист (frontend, GR8/GR9 surface area)

- [ ] **Меню «Параметры агрегации»** (`<Popover>` за иконкой `<TuneOutlinedIcon>`): override `aggregator_threshold` (slider 0–20, default 4 для авторов / 8 для work, см. §2.3) и чекбоксы «Не агрегировать» по kinds (`Author`, `Method`, `Work`).
- [ ] **Toggle reader/raw** — описан в §2.5.4. В UI это switch + бейдж «Тех. вид» при `view=raw`, чтобы пользователь не запутался.

#### 2.5.6 Acceptance

1. Над канвасом — **одна** панель из двух секций; полоса иконок и `GraphViewModeSwitch` исчезают как самостоятельные блоки.
2. Hover на любую кнопку filter-секции даёт человекочитаемую подсказку.
3. Поле поиска по `display_label` подсвечивает совпадающие узлы (зелёный outline в canvas, в `GraphTypeLegend` бейдж «N matches»).
4. Кнопка `Reset` возвращает дефолты И чистит LS-ключи (проверяется тестом).
5. Standalone-страница `/graph?work_id=…` показывает тот же `GraphTopBar` с filter+view секциями; depth-toggle и фильтр типов синхронизируются с URL.
6. `GraphTypeLegend` сворачивается и в embedded, и в standalone.
7. Mode-кнопки **не uppercased**.
8. Stats отображены как chip с tooltip; нет overflow-обрезания.

#### 2.5.7 Тесты

- [ ] `tests/components/graph/GraphTopBar.test.jsx` — рендер обеих секций, Reset чистит LS, search dispatches правильный callback.
- [ ] `tests/components/graph/GraphFiltersGroup.test.jsx` — переключатели mode/depth/types вызывают `onChange` и `localStorage.setItem`.
- [ ] Расширить `WorkspaceGraphToolbar.test.js`: убедиться, что `graphToolbarLocalStorageKey` всё ещё экспортируется (контракт), плюс новые ключи `workspaceGraphView:<wid>`, `workspaceGraphPreset:<wid>:<name>`.

**Ориентир:** frontend-PR разбить на 2:
- **PR 10a (~1 день):** `GraphTopBar` + перенос существующих компонентов + tooltips + удаление дубль-чипов в legend.
- **PR 10b (~0.5 дня):** Search + Reset.
- **PR 10c (~1 день, опционально):** Save-preset + standalone parity.

### 2.6 Wave GR11 — Localization верхней панели и легенды (расширение GR7)

**Цель:** убрать оставшиеся EN-строки в `GraphTypeLegend`, групповых заголовках и kind-метках. GR7 фаза A покрыла **edge-types** и **node-kinds в подписях** (через `localizeEdgeType`/`localizeNodeKind`), но **сама легенда всё ещё рендерит сырые kind-метки** (`WorkInternal`, `AuthorshipReification`) и хардкодит EN-заголовки `Types in view` / `Nodes` / `Edges` / `Works` / `Semantic` / `People` / `Context`.

#### 2.6.1 Чеклист (frontend)

- [ ] Локализовать заголовки в `GraphTypeLegend.jsx`:
  - `graph.legend.title` → «Типы в этом представлении» / «Types in view»
  - `graph.legend.sectionNodes` / `graph.legend.sectionEdges`
  - `graph.legend.group.Works` / `graph.legend.group.Semantic` / `graph.legend.group.People` / `graph.legend.group.Context`
  - description-подписи групп (`Research papers`, `Methods & Datasets`, …) — `graph.legend.groupDesc.*`.
- [ ] Локализовать kind-чипы — заменить `label={kind}` (`GraphTypeLegend.jsx:106`) на `label={t(\`graph.nodeKind.${kind}\`, kind)}`. Использовать те же ключи, которые GR7 фаза A добавляет для канваса (`graph.nodeKind.WorkInternal/WorkExternal/AuthorshipReification/Aggregator`).
- [ ] Локализовать edge-чипы — заменить `label={edgeType}` (`GraphTypeLegend.jsx:128`) на `localizeEdgeType({type: edgeType}, t)` (общий хелпер из GR7 `graphLocalize.js`).
- [ ] Tooltips для toolbar (см. §2.5.3) — добавить ключи в EN/RU `partGraphUi.js`:
  - `graph.wsToolbar.modeTooltip.inner_only` («Только статьи внутри текущей рабочей области, без внешних» / «Only papers inside the current workspace, no external»)
  - `graph.wsToolbar.modeTooltip.union_1hop`, `graph.wsToolbar.modeTooltip.semantic_layer`, `graph.wsToolbar.modeTooltip.full`
  - `graph.wsToolbar.depthTooltip.1` / `graph.wsToolbar.depthTooltip.2`
  - `graph.wsToolbar.externalTooltip` («Включить внешние работы…»)
  - `graph.wsToolbar.nodeTypeTooltip.{Work,Author,Method,Dataset,Venue,Institution}`
  - `graph.wsToolbar.searchPlaceholder` / `graph.wsToolbar.resetTooltip` / `graph.wsToolbar.exportTooltip` / `graph.wsToolbar.fitToScreenTooltip` / `graph.wsToolbar.viewReaderTooltip` / `graph.wsToolbar.viewRawTooltip` / `graph.wsToolbar.aggregatorTuneTooltip`.
- [ ] Stats-tooltip: `graph.wsToolbar.statsTooltip.full` ({{works}} статей · {{authors}} авторов · {{edges}} рёбер · {{ext}} внешних цитирований).

#### 2.6.2 Acceptance

1. На русской локали в верхней панели нет ни одной EN-строки (включая «Types in view», «Nodes», «Edges»).
2. Чип `WorkInternal` подписан как «Внутренняя работа», `AuthorshipReification` — «Авторство», `Method` — «Метод», `CITES` — «цитирует» и т.д.
3. EN-локаль работает идентично сегодняшнему поведению (regression-safe).

**Ориентир:** frontend-PR ~0.5 дня (вместе с PR 10a, либо отдельно если PR 10a уже мерджится).

### 2.7 Wave GR12 — Right detail panel UX overhaul (иконки, sub-панели, информативность, цвета)

**Цель:** превратить «список абзацев» в структурированный инспектор: каждый узел/ребро открывается с цветной плашкой типа и иконкой; метрики — отдельные stat-чипы; соседи сгруппированы по типу ребра, с иконкой-узла и направлением; edge-инспектор не дублирует информацию; Raw JSON — единая accordion-секция с copy. Без backend-изменений (контракт ADR 011 уже даёт всё нужное).

#### 2.7.1 Целевая IA правой панели

```
┌──────────────────────────────────────────────────┐
│ [←] [→]  Details                          [⋯]    │ ← Sticky header bar: история + меню действий
├──────────────────────────────────────────────────┤
│ [📄] Work · internal · 2024            [📋] id   │ ← Type plate (icon + цветной фон + бейджи) + copy id
│ XRAG: Cross-lingual Retrieval-Augmented…         │ ← Title (truncate=2 строки)
│ Aleksei Smirnov, Maria Petrova · IBM Research    │ ← Subtitle (если ≠ типу/displayLabel)
├──────────────────────────────────────────────────┤
│ [↘ 0] int cites   [↗ 1] ext cites   [⊕ 8] degree│ ← Stat-чипы (только для Work)
│ [ Open work page → ]   [ Expand external (+1) ]  │ ← Контекстные actions
├──────────────────────────────────────────────────┤
│ ▾ Properties (3)                                  │ ← Collapsible sub-panel (счётчик)
│   year      2024                                  │
│   doi       10.xxxx/yyy                           │
│   url       https://…                             │
├──────────────────────────────────────────────────┤
│ ▾ Connections (8)               [🔍 фильтр…]     │ ← Collapsible + клиентский filter input
│   evaluated on (5)                          [▾] │
│     [📊] XOR QA                                   │
│     [📊] Wiki 2024                                │
│     [📊] News Crawl                               │
│     ...                                            │
│   uses method (1)                            [▾] │
│     [🧠] XRAG                                     │
│   cites (1)                                  [▾] │
│     [📄] Untitled work · external                 │
├──────────────────────────────────────────────────┤
│ ▸ Advanced (raw JSON)                  [📋 Copy] │ ← Единая accordion-секция, default closed
└──────────────────────────────────────────────────┘
```

Для **ребра** (replaces скриншот 3 «Gemma → Research»):

```
┌──────────────────────────────────────────────────┐
│ [←]  Relationship                         [⋯]    │
├──────────────────────────────────────────────────┤
│ [📚] Gemma   →   [🔗] contains   →   [📁] Research│ ← «Карта ребра»: source-icon + edge-icon + target-icon
├──────────────────────────────────────────────────┤
│ [ Открыть Gemma →]    [ Открыть Research →]      │ ← Кнопки с именами
├──────────────────────────────────────────────────┤
│ ▾ Properties (2)                                  │ ← Только если у ребра есть props
│   year         2024                                │
│   confidence   0.92                                │
├──────────────────────────────────────────────────┤
│ ▾ Trace via (2)                                   │ ← Только для виртуальных рёбер из GR9 (`via.length>0`)
│   HAS_AUTHORSHIP                                   │
│   OF_AUTHOR                                        │
├──────────────────────────────────────────────────┤
│ ▸ Advanced (raw JSON)                  [📋 Copy] │
└──────────────────────────────────────────────────┘
```

Для **агрегатора** (полировка существующей секции `GraphDetailPanel.jsx:152-183`):

```
┌──────────────────────────────────────────────────┐
│ [👥] Aggregator · 5 authors of Work               │ ← Иконка GroupOutlinedIcon + count + kind
│ Aleksei Smirnov, Maria Petrova, …                 │ ← preview_labels
├──────────────────────────────────────────────────┤
│ [ Раскрыть все 5 →]                               │
└──────────────────────────────────────────────────┘
```

#### 2.7.2 Цвет/иконка по типу — единая таблица

Используем уже существующие `NODE_TYPE_ICON_MAP` и `NODE_TYPE_STYLES` из `ui/src/components/graph/canvas/graphCanvasStyle.js`. Дополняем мини-словарём для edge-типов (новый `EDGE_TYPE_ICON_MAP`):

| node_kind / edge_type | icon (MUI) | base color (источник `NODE_TYPE_STYLES`) |
|----------------------|------------|------------------------------------------|
| `Work` / `WorkInternal` | `ArticleOutlinedIcon` | indigo `rgba(99,102,241,…)` |
| `WorkExternal` | `OpenInNewOutlinedIcon` | indigo dimmed |
| `Author` | `PersonOutlinedIcon` | violet `rgba(168,85,247,…)` |
| `AuthorshipReification` | `LinkOutlinedIcon` | slate `rgba(148,163,184,…)` |
| `Method` | `PsychologyOutlinedIcon` | green `rgba(34,197,94,…)` |
| `Dataset` | `StorageOutlinedIcon` | amber `rgba(251,191,36,…)` |
| `Venue` | `MenuBookOutlinedIcon` | sky `rgba(56,189,248,…)` |
| `Institution` | `AccountBalanceOutlinedIcon` | pink `rgba(244,114,182,…)` |
| `Aggregator` | `GroupOutlinedIcon` | indigo dashed |
| edge `CITES` | `FormatQuoteOutlinedIcon` | text 0.7 |
| edge `HAS_AUTHORSHIP` / `OF_AUTHOR` / `AUTHORED` | `PersonOutlinedIcon` (small) | violet 0.7 |
| edge `AFFILIATED_WITH` | `AccountBalanceOutlinedIcon` (small) | pink 0.7 |
| edge `PUBLISHED_IN` | `MenuBookOutlinedIcon` (small) | sky 0.7 |
| edge `USES_METHOD` | `PsychologyOutlinedIcon` (small) | green 0.7 |
| edge `EVALUATED_ON` / `TRAINED_OR_TESTED_ON` | `StorageOutlinedIcon` (small) | amber 0.7 |
| edge `CONTAINS` / `MENTIONS` / `SUPPORTS` / `CONTRADICTS` | `LinkOutlinedIcon` (small) | text 0.6 |

**Правило цвета type-плашки в шапке:** `backgroundColor` = base.fill, `border` = base.stroke, `color` = base.stroke с alpha 0.95. Это **тот же** контракт, что использует `getScienceGraphLegendNodeChipSx` — гарантирует визуальное соответствие с канвасом и легендой.

#### 2.7.3 Архитектура: разбивка `GraphDetailPanel.jsx` на под-компоненты

`GraphDetailPanel.jsx` сейчас 412 строк и смешивает 7 разных view-моделей. По правилу `refactor-rhythm-and-backlog.mdc` — это уже структурный долг, поэтому в рамках GR12 разбиваем:

- [ ] [`ui/src/components/graph/detail/GraphDetailHeader.jsx`](../../ui/src/components/graph/detail/GraphDetailHeader.jsx) — sticky-заголовок: history `[←][→]` + «Details» + actions menu (`[⋯]` с «Copy id», «Copy JSON», «Open in main view»).
- [ ] [`ui/src/components/graph/detail/GraphDetailNodePlate.jsx`](../../ui/src/components/graph/detail/GraphDetailNodePlate.jsx) — type-плашка: иконка + цветной фон + `t(graph.nodeKind.${kind})` + бейдж membership + год (если `Work`) + title + subtitle (suppressed if equals type/displayLabel).
- [ ] [`ui/src/components/graph/detail/GraphDetailStats.jsx`](../../ui/src/components/graph/detail/GraphDetailStats.jsx) — stat-чипы для `Work`: `[CallReceivedIcon]` int cites, `[CallMadeIcon]` ext cites, `[HubOutlinedIcon]` degree, плюс контекстные кнопки `Expand external (+N)` и `Open work page →` (новая, ведёт на `/works/{id}`).
- [ ] [`ui/src/components/graph/detail/GraphDetailProperties.jsx`](../../ui/src/components/graph/detail/GraphDetailProperties.jsx) — collapsible-секция «Properties (N)»; default open if N>0, header `<button>` + `expand more` icon, использует `formatPropertyLabel`/`formatPropertyValue` из старого файла (вынести как утилиту в `ui/src/components/graph/detail/properties.js`).
- [ ] [`ui/src/components/graph/detail/GraphDetailConnections.jsx`](../../ui/src/components/graph/detail/GraphDetailConnections.jsx) — `▾ Connections (N)` с клиентским filter input, группировка по `displayType` (внутри группы сортировка по `directionHint` (incoming/outgoing/lateral) и затем `otherLabel`), сворачиваемые группы. Использует `<NeighbourCard>` под-компонент с `[icon] otherLabel` + direction stripe слева.
- [ ] [`ui/src/components/graph/detail/GraphDetailEdgeMap.jsx`](../../ui/src/components/graph/detail/GraphDetailEdgeMap.jsx) — «карта ребра»: `[icon] source · [edge-icon] type · [icon] target` (заменяет 4 разных `<Typography>` блока в текущем коде). Используется только когда `selectedEdge` активен.
- [ ] [`ui/src/components/graph/detail/GraphDetailAggregator.jsx`](../../ui/src/components/graph/detail/GraphDetailAggregator.jsx) — иконка `GroupOutlinedIcon` + bold count + kind-label + preview list + кнопка «Раскрыть».
- [ ] [`ui/src/components/graph/detail/GraphDetailRawJson.jsx`](../../ui/src/components/graph/detail/GraphDetailRawJson.jsx) — единый `<Accordion>` с кнопкой «📋 Copy» в `AccordionSummary`, для и узла, и ребра.
- [ ] [`ui/src/components/graph/detail/GraphDetailEmpty.jsx`](../../ui/src/components/graph/detail/GraphDetailEmpty.jsx) — пустой стейт с маленькой схематикой («↗ кликни узел / ↘ кликни ребро»).
- [ ] [`ui/src/components/graph/detail/useGraphDetailHistory.js`](../../ui/src/components/graph/detail/useGraphDetailHistory.js) — хук для history `[←][→]` навигации (`pushSelection({nodeId|edgeId})`, `back()`, `forward()`, persisted в state, не в URL).
- [ ] `GraphDetailPanel.jsx` остаётся тонкой обёрткой (50–80 строк), композитит выше перечисленные компоненты.

#### 2.7.4 Чеклист (frontend, sub-panel за sub-panel)

##### A. Header & node plate

- [ ] **Header bar.** `GraphDetailHeader` с back/forward кнопками (disabled если history пуста), заголовок `t("graph.detail.title")`, кнопка-меню `<IconButton>` → `<Menu>` с пунктами:
  - Copy id
  - Copy raw JSON
  - Open in main view (только для `Work`, ссылка на `/works/{id}`)
  - Clear selection (Esc-эквивалент)
- [ ] **Node plate.** Заменить `GraphDetailPanel.jsx:184-192`:
  ```jsx
  <Box sx={{ display: "flex", gap: 1, alignItems: "center", p: 1, borderRadius: "6px", ...plateColorSx }}>
    {KindIcon ? <KindIcon sx={{ fontSize: "1rem" }} /> : null}
    <Typography sx={typeChipSx}>{t(`graph.nodeKind.${nodeKind}`, nodeKind)}</Typography>
    {membership ? <Chip label={t(`graph.workspaceMembership.${membership}`, membership)} size="small" /> : null}
    {year ? <Typography sx={metaSx}>· {year}</Typography> : null}
  </Box>
  <Typography sx={{ fontSize: "1rem", fontWeight: 600, mt: 0.75 }}>{displayLabel}</Typography>
  {subtitle && subtitle !== nodeKind && subtitle !== displayLabel ? (
    <Typography sx={subtitleSx}>{subtitle}</Typography>
  ) : null}
  ```
  где `plateColorSx` строится из `NODE_TYPE_STYLES[nodeKind]`.
- [ ] **Год** парсить из `properties.year` или из `subtitle` (regex `\b(19|20)\d{2}\b`); если не нашли — не показывать.

##### B. Stats для Work

- [ ] Заменить inline-блок `GraphDetailPanel.jsx:198-215` на `<GraphDetailStats>` со stat-чипами:
  - `[CallReceivedIcon] int cites: {n}` (indigo) — `internalCiteCount`
  - `[CallMadeIcon] ext cites: {n}` (amber) — `externalCiteCount`
  - `[HubOutlinedIcon] degree: {n}` (text 0.7) — длина `relatedEdges`
- [ ] `internalCiteCount` / `externalCiteCount` сейчас приходят с backend — убедиться, что `Author` тоже получает «h-index», «publications». Если нет — пометить как backlog (см. §3 #11).

##### C. Properties

- [ ] Под-компонент `GraphDetailProperties` с counter в заголовке `▾ Properties ({Object.keys(properties).length})`. Default open if N>0, иначе hidden целиком (без «No structured properties on this node» — это тоже шум).
- [ ] Per-property: первый колонка — label `formatPropertyLabel(k)`, моноширинный values для `id`/`url`/`doi`, plain для остального. Для длинных URL — truncate с `title` tooltip.

##### D. Connections (главный фикс)

- [ ] **Группировка по displayType.** В `GraphDetailConnections`:
  ```js
  const grouped = groupBy(rows, (row) => row.edge.displayType || row.edge.type);
  ```
  Сортировка групп: сначала по `directionHint` приоритету (`outgoing > incoming > lateral`), потом по count desc, потом alphabet.
- [ ] **Заголовок группы** (`▾ evaluated on (5)`) — collapsible, default open if `total ≤ 12`, иначе закрыт.
- [ ] **NeighbourCard** — заменить `GraphDetailPanel.jsx:283-305` на:
  ```jsx
  <button onClick={…}>
    <Box sx={{ display: "flex", gap: 0.75, alignItems: "center" }}>
      {NeighbourIcon ? <NeighbourIcon sx={{ fontSize: "0.9rem", color: nodeColor }} /> : null}
      <Typography sx={{ fontSize: "0.8125rem", fontWeight: 500, flex: 1 }}>{otherLabel}</Typography>
      {directionHint && directionHint !== "lateral" ? (
        <Typography sx={{ fontSize: "0.65rem", color: "rgba(255,255,255,0.4)" }}>
          {t(`graph.detail.direction.${directionHint}`)}
        </Typography>
      ) : null}
    </Box>
    {otherSubtitle ? <Typography sx={subtitleMutedSx}>{otherSubtitle}</Typography> : null}
  </button>
  ```
  - `lateral` направление **скрывается** (нейтрально для пользователя).
  - `otherSubtitle` берётся из `lookup.get(otherId)?.subtitle` — добавить в `graphInspectorModel.js:buildNodeLookup` (там сейчас уже есть `subtitle` в map, нужно прокинуть в row).
- [ ] **Filter input** — `<TextField size="small" placeholder={t("graph.detail.filterPlaceholder")} />` со встроенным `<SearchOutlinedIcon>`, фильтрует rows по `otherLabel` substring (case-insensitive). Persist последнего значения **не** нужен.
- [ ] **Empty state** для группы после фильтра — «Нет совпадений / No matches».
- [ ] Удалить старую ветку `relatedEdges` фолбэка (`GraphDetailPanel.jsx:308-342`) — `relatedEdgeRows` всегда заполнен в современном коде.

##### E. Edge inspector

- [ ] **Edge map** (`GraphDetailEdgeMap`) заменяет тройное дублирование `GraphDetailPanel.jsx:131-148`:
  ```jsx
  <Box sx={{ display: "grid", gridTemplateColumns: "auto auto auto auto auto", alignItems: "center", gap: 0.75 }}>
    <SourceIcon sx={iconSx} />
    <Typography>{sourceLabel}</Typography>
    <Box sx={{ display: "flex", alignItems: "center", gap: 0.25 }}>
      <ArrowRightAltIcon /><EdgeIcon /><Typography sx={edgeChipSx}>{displayType}</Typography><ArrowRightAltIcon />
    </Box>
    <TargetIcon sx={iconSx} />
    <Typography>{targetLabel}</Typography>
  </Box>
  ```
- [ ] **Кнопки с именами:** `Открыть {sourceLabel}` / `Открыть {targetLabel}`. Если имя длиннее 24 chars — truncate `…`.
- [ ] **Edge properties.** Если `selectedEdge.raw.properties` имеет ключи — рендерить `<GraphDetailProperties>` так же, как для узла. Используем тот же sub-компонент.
- [ ] **Trace via** — секция показывается **только** если `selectedEdge.raw.via && Array.isArray(via) && via.length > 0` (это контракт GR9 для виртуальных `AUTHORED`-рёбер). Список `via` — chips с raw type + tooltip с `t(\`graph.edgeType.${type}\`)`.

##### F. Aggregator

- [ ] Заменить `GraphDetailPanel.jsx:152-183` на `GraphDetailAggregator` с иконкой `GroupOutlinedIcon` + большой счётчик `{count}` + локализованным kind-label через `localizeAggregatorLabel` (из GR7).
- [ ] preview_labels — двухколоночная сетка вместо плоского `<List>`, по 4–6 видимых, остальные «+ ещё N».

##### G. Empty state

- [ ] `GraphDetailEmpty` — крошечный SVG с двумя стрелками («Click node ↗ / Click edge ↘») и подсказкой про Esc/←/→. Используем уже импортированные иконки `ArrowOutwardIcon` и `ArrowDownwardIcon`.

##### H. Truncation alert

- [ ] Перевести «Increase neighbor_limit on the API query» → `t("graph.detail.truncationHint")` с человекочитаемым текстом «Показано {x} из {y}; используйте поиск или фильтр выше». Если есть API-возможность увеличить лимит на лету — кнопка «Загрузить ещё». Если нет — без кнопки, только текст.

##### I. Raw JSON

- [ ] Единый `GraphDetailRawJson` — `<Accordion>` для node И edge (унифицирует `GraphDetailPanel.jsx:344-368` и `:372-407`). В `AccordionSummary` справа — `<IconButton>` с `<ContentCopyOutlinedIcon>` и tooltip `t("graph.detail.copyJsonTooltip")`. Click копирует `JSON.stringify(raw, null, 2)` в clipboard.
- [ ] Простая подсветка ключей цветом (regex `"key":` → indigo) — без полноценного syntax-highlighter, чтобы не тащить новую зависимость. Если хотим библиотеку — отдельный backlog.

##### J. History navigation

- [ ] `useGraphDetailHistory({ selectedNodeId, selectedEdgeId, onSelectNode, onSelectEdge })`:
  - стек `past[]` / `future[]`
  - `pushSelection({ nodeId, edgeId })` — кладёт текущее в past, очищает future, ставит новое
  - `back()` / `forward()` — двигают между past/future
  - возвращает `{ canBack, canForward, back, forward }`
- [ ] В `GraphDetailHeader` — `[←]` `[→]` кнопки, disabled при `!canBack`/`!canForward`.

##### K. i18n keys (расширяет GR7+GR11)

Добавить в `ui/src/i18n/messages/{en,ru}/partGraphUi.js`:

- `graph.detail.title`, `graph.detail.empty.title`, `graph.detail.empty.hint.node`, `graph.detail.empty.hint.edge`
- `graph.detail.section.properties`, `graph.detail.section.connections`, `graph.detail.section.advanced`, `graph.detail.section.traceVia`
- `graph.detail.stats.intCites`, `graph.detail.stats.extCites`, `graph.detail.stats.degree`
- `graph.detail.action.openSource`, `graph.detail.action.openTarget` (с `{{name}}`), `graph.detail.action.openInMainView`, `graph.detail.action.copyId`, `graph.detail.action.copyJson`, `graph.detail.action.expandExternal` (с `{{count}}`), `graph.detail.action.aggregatorExpand` (с `{{count}}`)
- `graph.detail.direction.outgoing` («исходящее» / «outgoing»), `graph.detail.direction.incoming` («входящее» / «incoming») — `lateral` **не** локализуем, потому что скрываем
- `graph.detail.filterPlaceholder` («Поиск по соседям…» / «Search neighbours…»)
- `graph.detail.truncationHint` (с `{{count}}`/`{{shown}}`)
- `graph.detail.copyJsonTooltip`
- `graph.workspaceMembership.internal` («внутренняя») / `graph.workspaceMembership.external` («внешняя»)

#### 2.7.5 Acceptance

1. **Идентичность узла** видна с одного взгляда: иконка типа из `NODE_TYPE_ICON_MAP` + цветной фон из `NODE_TYPE_STYLES`, согласованный с канвасом и легендой; для `WorkInternal` — два бейджа `Работа` + `внутренняя`, не одно слово.
2. Subtitle подавляется, когда `subtitle === nodeKind || subtitle === displayLabel`.
3. Stat-чипы отображают int/ext cites и degree через иконки и цветовое кодирование, не плоской строкой.
4. **Connections сгруппированы по типу ребра**, group header показывает count и сворачивается; в каждой карточке соседа есть **иконка типа узла** и его subtitle; имя выбранного узла **больше не дублируется** в каждой карточке.
5. `lateral` direction скрыт; `outgoing`/`incoming` локализованы.
6. **Edge inspector** — одна «карта ребра» с тремя элементами (source-icon · edge · target-icon), без тройного повторения текста; кнопки `Открыть Gemma` / `Открыть Research` несут имя; есть секция «Properties» (если есть props) и «Trace via» (если есть `via`).
7. **Raw JSON** — единый Accordion и для узла, и для ребра, с кнопкой «Копировать JSON».
8. **History** — кнопки `←`/`→` навигации между ранее открытыми selections.
9. **Filter** в Connections фильтрует по `otherLabel` substring, без серверного запроса.
10. **A11y:** заголовки секций — `<h3>`, карточки — `<button aria-describedby>`, контраст текста ≥ WCAG AA.
11. **Empty state** — иллюстрация со стрелками вместо голого текста.
12. **Russian локаль** — нет EN-строк в правой панели (`Details`/`Key properties`/`Connections`/`Show advanced`/`Open source` все локализованы).
13. `GraphDetailPanel.jsx` ≤ 100 строк, остальные обязанности — в `detail/`.
14. Регрессий нет: `WorkspaceGraphPanel`/`GraphPage` не падают при `selectedNode=null`/`selectedEdge=null`.

#### 2.7.6 Тесты

- [ ] `tests/components/graph/detail/GraphDetailNodePlate.test.jsx` — рендер плашки с правильной иконкой по `nodeKind`; subtitle suppression; year extraction.
- [ ] `tests/components/graph/detail/GraphDetailConnections.test.jsx` — группировка по `displayType`; filter by substring; client-side; lateral hidden.
- [ ] `tests/components/graph/detail/GraphDetailEdgeMap.test.jsx` — рендер «карты ребра» для разных `edge.type`.
- [ ] `tests/components/graph/detail/GraphDetailRawJson.test.jsx` — accordion раскрывается; copy кнопка вызывает `navigator.clipboard.writeText`.
- [ ] `tests/components/graph/detail/useGraphDetailHistory.test.js` — push/back/forward инвариантa.
- [ ] Расширить `ui/src/components/graph/model/graphInspectorModel.test.js` — `relatedEdgeRows` теперь пробрасывает `otherSubtitle` (новое поле).
- [ ] Visual regression (если есть playwright story) — снимки правой панели для `Work`, `Author`, `Dataset`, `Aggregator`, `Edge`.

#### 2.7.7 PR breakdown

- **PR 12a (~1 день):** разбиение `GraphDetailPanel.jsx` на `detail/` под-компоненты (без UX-изменений). Технический рефакторинг под `refactor-rhythm-and-backlog.mdc`. После него все остальные PR ложатся в маленькие диффы.
- **PR 12b (~1 день):** `GraphDetailNodePlate` + `GraphDetailStats` + suppress subtitle + i18n ключи. Закрывает «иконки/цвета/жаргон».
- **PR 12c (~1.5 дня):** `GraphDetailConnections` с группировкой, иконкой соседа, filter, hide lateral. Самое заметное улучшение.
- **PR 12d (~1 день):** `GraphDetailEdgeMap` + edge properties + кнопки с именами + Trace via. Совпадает с GR9 (`via`-секция).
- **PR 12e (~0.5 дня):** `GraphDetailRawJson` (унификация) + copy + history navigation + empty state иллюстрация.
- **PR 12f (~0.25 дня):** truncation alert текст + a11y-фиксы (h3 секции, aria-describedby, контраст).

Если бюджет один день — оставляем 12a + 12b + 12c (это ≈ 3.5 дня), остальное в backlog.

#### 2.7.8 Зависимости и параллельность

| Wave | Зависит от | Не блокируется |
|------|-----------|----------------|
| **GR12 общий** | GR7 (нужны i18n-ключи `graph.nodeKind.*`/`graph.edgeType.*`) | можно делать после/одновременно с GR7 фазой A; до GR7 — рендерим raw `displayType` как fallback |
| **PR 12d Trace via** | GR9 (контракт `edge.via`) | если GR9 ещё не готов — рендерим placeholder «Trace via not available» |
| **PR 12b stats** | (опционально) backend `Author.publications`, `degree` поля | если их нет — показываем только то, что есть |

**Параллельно с другими треками:**
- GR12 vs GR10 (toolbar) — разные файлы (`detail/` vs `toolbar/`), не конфликтуют. Можно делать одной командой в одном спринте.
- GR12 vs Track B (LangGraph) — независимы.

**Ориентир:** 4–5 дней frontend-работы суммарно (без visual regression). Минимально-полезный кусок — PR 12a+12b+12c, ≈ 3.5 дня, закрывает 80% жалоб пользователя на правую панель.

---

## 3. Открытые вопросы (нужно решение перед стартом)

1. **Default `view`** — `reader` или `raw`?
   - **Аргумент за `reader`-default:** UX чище, агрегация «Authorship under Work» работает естественно.
   - **Аргумент за `raw`-default + UI-toggle на reader:** сохраняется backward-совместимость для прямых API-клиентов (CLI, OpenAPI explorer) и benchmark fixtures.
   - **Предложение:** `reader`-default для UI-эндпоинтов (`/v1/works/{id}/graph`, `/v1/workspaces/{id}/graph`), `raw`-fixed для `graph_snapshot_diff` и любых тестов.

2. **i18n стратегия — фаза B (`display_type_key`) делать ли сейчас?**
   - **За:** делает API локаль-независимым на будущее; UI единообразно работает с любыми новыми типами рёбер из Wave O (claims).
   - **Против:** меняет контракт payload, нужно обновить ADR 011 и доку для агентов.
   - **Предложение:** в этой итерации делаем только фазу A. Если в Wave O появятся новые edge-types — заводим фазу B отдельным ADR.

3. **Aggregator threshold — централизованная конфигурация или per-endpoint?**
   - **Предложение:** хранить в `science_graphrag/api/graph_display.py` рядом с `_NODE_KIND_PRIORITY` как `DEFAULT_AGGREGATOR_THRESHOLDS: dict[str, int]`; query-параметр `aggregator_threshold` — int override применяется ко всем kinds.

4. **Cap-aware агрегатор — как считать `+N hidden`?**
   - Нужен дополнительный Cypher для `count(distinct neighbor_id) by labels(n)` за пределами LIMIT (часть метаданных уже считается в `kind_distribution`).
   - **Предложение:** переиспользовать `kind_distribution` из существующего payload — добавить cap-агрегатор только если `kind_distribution[kind] - len(visible_of_kind) >= 1`.

5. **GR2 фронт-часть — отдельный PR или вместе с GR7?**
   - **Предложение:** GR6 (фикс канваса на `displayType`) — отдельный микро-PR, мерджим в день обнаружения; GR7 (i18n) — за ним отдельным PR на 1 день.

6. **Save-preset в GR10 — делать сейчас или отложить?**
   - **За:** аналитики переключаются между «Work+Author» и «Полный» десятки раз; reset-кнопки недостаточно.
   - **Против:** добавляет ещё один LS-контракт (`workspaceGraphPreset:<wid>:<name>`), требует UI поверх `<Popover>`.
   - **Предложение:** PR 10c делаем после 10a/10b как опциональный мини-фичу; не блокируем основной редизайн.

7. **Куда положить switch `view: reader | raw` — в filter-секцию рядом с «Внешние», или в actions-секцию?**
   - **За filter-секцию:** это конфигурация запроса (как `mode`/`depth`/`includeExternal`), логически там.
   - **За actions-секцию:** это «как смотрю», ближе к view-mode (Cards/Graph/Flow).
   - **Предложение:** в filter-секцию, **левее** «Внешние», с бейджом «Тех.» при `view=raw`. Reader/raw влияет на payload, как mode/depth — поэтому он filter, а не view-action.

8. **`GraphTypeLegend` после редизайна — оставлять как отдельный сворачиваемый блок или встроить в panel-popover «Что в графе»?**
   - **За отдельный блок (как сейчас, плюс collapse в embedded):** видно по умолчанию, легко глянуть распределение.
   - **За popover:** освобождает 50–80px вертикали, но прячет полезную информацию.
   - **Предложение:** оставить блок, добавить collapse везде; chip-кнопочность убрать (только чтение). Это уже отражено в §2.5.1.

9. **Поиск по узлам — клиентский или серверный?**
   - **Клиентский (`useGraphSearch`):** быстро, без backend, но работает только по уже подгруженному `displayGraph` (после UI-cap).
   - **Серверный:** для больших workspace может найти узлы за пределами cap; но требует нового endpoint.
   - **Предложение:** в GR10b клиентский. Серверный поиск — отдельный backlog-пункт после Wave G (workspace graph split).

10. **GR12 — разбивать `GraphDetailPanel.jsx` сейчас или позже?**
    - **За разбивку (PR 12a):** файл уже 412 строк и нарушает порог `~400+` из `refactor-rhythm-and-backlog.mdc`; 7 view-моделей в одном файле = когнитивная нагрузка для будущих PR.
    - **Против:** дополнительный технический PR без user-visible эффекта; диффы 12b–12f можно положить и в монолит.
    - **Предложение:** делаем 12a первым отдельным PR; гарантирует, что 12b/12c не превратятся в 600-строчные мега-диффы.

11. **Author/Method/Dataset stat-чипы — нужен ли backend для подсчётов?**
    - Сейчас `internalCiteCount`/`externalCiteCount` приходят только для `Work` (`graph_neighborhood.py:_enrich_work_with_counts`).
    - Для `Author` — публикации, h-index; для `Dataset`/`Method` — число использующих работ; для `Venue`/`Institution` — публикации/авторы.
    - **Против сразу:** требует backend-расширения, новый payload-контракт.
    - **Предложение:** в GR12 рендерим только то, что уже есть; «Author publication count» — отдельный backend-backlog (см. §4.2 ниже).

12. **History navigation — local hook или URL?**
    - **Local (`useGraphDetailHistory`):** не светит ID в URL, не ломает навигацию страницы; но теряется при refresh.
    - **URL (`?selected=…&history=…`):** shareable links, persistent; но загрязняет URL.
    - **Предложение:** local в GR12. Если пользователю нужен shareable selection — отдельный backlog (см. ADR-кандидат «graph deep links»).

13. **Edge `Properties` секция — какие поля скрывать как «технические»?**
    - У ребра в `raw.properties` могут быть `id`/`source_id`/`target_id`/`updated_at` — это шум.
    - **Предложение:** whitelist «полезных» полей в `graphLocalize.js`: `year`, `weight`, `confidence`, `author_position`, `is_corresponding`, `raw_affiliation`, `institution_id`. Остальное — только в Raw JSON.

---

## 4. Связь с существующим планом

### 4.1 Обновления master-roadmap

В [`master-roadmap-and-refactor-plan-2026-04-25.md`](master-roadmap-and-refactor-plan-2026-04-25.md):

| Раздел | Было | Стало |
|--------|------|-------|
| §2 таблица треков, строка E | `GR1 done, GR2 done, GR3..GR5 open. Текущая волна: Wave GR3` | `GR1 done, GR2 partial (backend done; UI integration via Wave GR6/GR7 pending), GR3 done with caveats (high threshold, Work-only owner), GR4..GR5 open, GR10/GR11/GR12 — UI follow-ups. Текущая волна: Wave GR6 (UI fix) → GR7/GR11 (i18n) → GR10 (toolbar IA/UX) → GR12 (right detail panel UX) → GR8 (smarter aggregation) → GR9 (reader view).` |
| §3 граф зависимостей | Линия `Wave GR1 (done) ── GR2 (display_type/node_kind) ── GR3 (aggregator) ── GR4 (reader view) ── GR5 (counters)` | Добавить ветку `... ── GR6 (UI fix on canvas) ── GR7 (i18n graph) ── GR10 (toolbar IA/UX) ── GR11 (i18n легенды) ── GR12 (right detail panel) ── GR8 (smarter aggregation defaults) ── GR9 (reader view = old GR4) ── GR5 (counters)`. GR10/GR11/GR12 параллельны GR8/GR9 backend; GR12 зависит только от GR7 фазы A (общие хелперы локализации) — иначе можно делать параллельно с GR10. |
| §4.5 Track E | Добавить пункты GR6/GR7/GR8/GR9/**GR10/GR11/GR12** как «follow-up к GR2/GR3 + переименование GR4 → GR9 + редизайн верхней панели + полное покрытие легенды локализацией + перепроектирование правой панели деталей (иконки, sub-panels, информативность, цвета)» с обратной совместимостью |
| §5 Спринт S3 | В строку «P4 Track E: Wave GR2» добавить «+ Wave GR6 (frontend integration) + Wave GR10a (GraphTopBar shell) + Wave GR12a (split GraphDetailPanel)» — закрывает пользователя за один спринт и снимает структурный долг 412-строчного `GraphDetailPanel.jsx` |
| §5 Спринт S4 | Добавить «Wave GR10b (search + reset) + Wave GR11 (legend i18n) + Wave GR12b/12c (node plate + connections grouping)» — это даёт MVP правой панели с иконками/группировкой |
| §5 Спринт S6 | Заменить «Wave GR4 (`view=raw|reader`)» → «Wave GR9 (`view=raw|reader`) + Wave GR8 (smarter aggregation) + Wave GR10c (preset + standalone parity для view=reader) + Wave GR12d (edge map + Trace via для виртуальных AUTHORED)» |

### 4.2 Backlog backend

Добавить в [`refactor-backend.md`](../backlog/refactor-backend.md):

```markdown
### [PARTIAL] Graph readability — Wave GR2 node_kind + semantic display_type + prioritized LIMIT
- **Note (partial):** 2026-04-25 — backend часть доставлена (`graph_display.py`, `_enrich_edges_with_display`,
  `node_kind_priority`, `meta.skipped_by_kind`); UI integration вынесен в Wave GR6/GR7.

### [OPEN] Graph readability — Wave GR8 smarter aggregation defaults (per-kind thresholds, non-Work owners, cap-aware)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_display.py`
- **Issue:** AGGREGATOR_THRESHOLD=8 + Work-only owner → типичная статья (4-6 авторов) не агрегируется;
  cap-truncation не отображается в графе.
- **Proposal:** per-kind thresholds (`AuthorshipReification`/`Author`=4, `Work`=8); allow `Author`/`Institution`/`Venue` owners;
  cap-aware aggregator от `kind_distribution`; query params `aggregator_threshold`/`aggregator_disabled_kinds`.
- **Acceptance:** статья с 5+ авторами агрегируется по умолчанию; `is_truncated=true` показывает `+N hidden`-агрегатор.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §2.3)

### [OPEN] Graph readability — Wave GR9 reader view virtual AUTHORED edges (renamed from GR4)
- **Area:** `science_graphrag/api/works/graph_neighborhood.py`,
  `science_graphrag/api/workspace_graph/projection.py`, `science_graphrag/api/graph_snapshot_diff.py`
- **Issue:** `view` параметр существует, но влияет только на агрегацию; `:Authorship` всегда возвращается.
- **Proposal:** `view=reader` по-настоящему скрывает `:Authorship` и `HAS_AUTHORSHIP`/`OF_AUTHOR`, добавляет
  виртуальные `Work –[AUTHORED]→ Author` с `via` trace; `view=raw` сохраняется для snapshot-тестов.
- **Acceptance:** payload в reader не содержит `node_kind: AuthorshipReification`; pytest-симметрия Work/Author множеств.
- **Raised:** 2026-04-25 (renamed from GR4)
```

### 4.3 Backlog frontend

Добавить в [`refactor-frontend.md`](../backlog/refactor-frontend.md):

```markdown
### [OPEN] Graph UI — Wave GR6 use displayType on canvas (Wave GR2 follow-up)
- **Area:** `ui/src/components/graph/canvas/graphCanvasDraw.js`, `ui/src/components/graph/canvas/graphCanvasStyle.js`,
  `ui/src/components/graph/canvas/graphCanvasDraw.test.js`
- **Issue:** Канвас рисует raw `edge.type` (`HAS_AUTHORSHIP`), игнорируя `edge.displayType` от backend.
- **Proposal:** `edgeTypeCanvasLabel(edge.displayType || edge.type)`; sync с поведением Flow и боковой панели.
- **Acceptance:** ребра подписаны человеческими типами; unit-тест `graphCanvasDraw.test.js` покрывает displayType.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §2.1)

### [OPEN] Graph UI — Wave GR7 i18n EN/RU for graph edges, node kinds, aggregator labels
- **Area:** `ui/src/i18n/messages/en/partGraphUi.js`, `ui/src/i18n/messages/ru/partGraphUi.js`,
  новый `ui/src/components/graph/graphLocalize.js`, `graphCanvasDraw.js`, `graphFlowAdapter.js`,
  `GraphDetailPanel.jsx`, `GraphTypeLegend.jsx`
- **Issue:** `display_type` приходит EN с backend; русская локаль не покрывает рёбра/агрегаторы.
- **Proposal:** локализация по `edge.type` (raw key) через `t("graph.edgeType.HAS_AUTHORSHIP")` и
  `localizeNodeKind`/`localizeAggregatorLabel`; единый модуль `graphLocalize.js`.
- **Acceptance:** при смене локали на ru ребра «цитирует», узлы «8 авторов»; EN regression-safe.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §2.2)

### [OPEN] Graph UI — Wave GR10 toolbar IA/UX redesign (single GraphTopBar, tooltips, search, reset, preset, standalone parity)
- **Area:** новый `ui/src/components/graph/GraphTopBar.jsx` + `GraphFiltersGroup.jsx` + `GraphViewActionsGroup.jsx`,
  правки в `WorkspaceGraphToolbar.jsx`, `GraphWorkspacePanel.jsx`, `GraphViewModeSwitch.jsx`,
  `GraphTypeLegend.jsx`, `pages/GraphPage.jsx`
- **Issue:** Верхняя панель распадается на 3 несогласованные полосы (toolbar / icon-row / legend).
  Нет tooltips/search/reset/preset, mode-кнопки uppercased (нарушает `.cursorrules`),
  legend сворачивается только в standalone, в standalone-графе работы тулбара нет вовсе,
  `view: reader|raw` toggle/aggregator threshold override отсутствуют, stats-overflow обрезает «внеш. цит.».
- **Proposal:** одна обёртка `GraphTopBar` с filter-секцией (mode/depth/external/types/view/threshold)
  и actions-секцией (vizMode/search/reset/export/fit/sidebar/layers/diag/stats-chip);
  заменить `<ToggleButton>` на `CursorSmallButton`; tooltips на всех контролах;
  реиспользовать тот же тулбар в standalone-графе (`GraphPage.jsx`) с URL-синком;
  `GraphTypeLegend` — read-only, сворачиваемая везде, без чипов-кнопок (избегаем дубля с серверным фильтром).
- **Acceptance:** одна панель из двух секций; `Reset` чистит LS-ключи (тест); search подсвечивает узлы по
  `display_label`; standalone-страница имеет идентичный toolbar; EN regression-safe;
  все mode-кнопки `textTransform: 'none'`.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §2.5)

### [OPEN] Graph UI — Wave GR11 toolbar/legend localization (extension of GR7)
- **Area:** `ui/src/components/graph/shell/GraphTypeLegend.jsx`,
  `ui/src/i18n/messages/en/partGraphUi.js`, `ui/src/i18n/messages/ru/partGraphUi.js`
- **Issue:** GR7 фаза A покрывает рёбра в подписях, но `GraphTypeLegend` всё ещё хардкодит
  EN-заголовки `Types in view`, `Nodes`, `Edges`, групповые `Works/Semantic/People/Context`,
  и kind-чипы `WorkInternal`/`AuthorshipReification`. Tooltips для toolbar mode/depth не локализованы.
- **Proposal:** ключи `graph.legend.title/sectionNodes/sectionEdges/group.*/groupDesc.*`,
  `graph.wsToolbar.modeTooltip.*` / `depthTooltip.*` / `externalTooltip` / `nodeTypeTooltip.*` /
  `searchPlaceholder` / `resetTooltip` / `exportTooltip` / `viewReaderTooltip` / `viewRawTooltip` /
  `aggregatorTuneTooltip` / `statsTooltip.full`. Использовать общие хелперы `localizeEdgeType`/`localizeNodeKind` из GR7.
- **Acceptance:** на ru-локали в верхней панели нет EN-строк; EN regression-safe.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §2.6)

### [OPEN] Graph UI — Wave GR12 right detail panel UX overhaul (icons, sub-panels, grouping, edge map, history)
- **Area:** разбить `ui/src/components/graph/shell/GraphDetailPanel.jsx` (412 строк, нарушает порог
  `~400+` из `refactor-rhythm-and-backlog.mdc`) на новый каталог `ui/src/components/graph/detail/`:
  `GraphDetailHeader.jsx`, `GraphDetailNodePlate.jsx`, `GraphDetailStats.jsx`,
  `GraphDetailProperties.jsx`, `GraphDetailConnections.jsx`, `GraphDetailEdgeMap.jsx`,
  `GraphDetailAggregator.jsx`, `GraphDetailRawJson.jsx`, `GraphDetailEmpty.jsx`,
  `useGraphDetailHistory.js`, `properties.js`. Правки в `graphInspectorModel.js`
  (прокинуть `otherSubtitle` в `relatedEdgeRows`), `graphCanvasStyle.js` (добавить
  `EDGE_TYPE_ICON_MAP`), i18n `partGraphUi.js`.
- **Issue:** Текущая правая панель не использует уже существующие `NODE_TYPE_ICON_MAP`/`NODE_TYPE_STYLES`
  (live только на канвасе и в легенде); тип идёт текстом-«ссылкой» без иконки/цвета;
  `WorkInternal`/`AuthorshipReification` рендерятся как camelCase-жаргон;
  subtitle дублирует тип; метрики цитирований склеены в плоскую строку без иконок;
  карточки соседей в Connections повторяют имя выбранного узла, не сгруппированы по типу ребра,
  без иконки соседа и без фильтра; везде вылазит «lateral» (workspace direction-fallback).
  Edge-инспектор повторяет одну фразу 3 раза, кнопки `Open source/Open target` без имён, нет секции
  «Properties» и «Trace via» (для виртуальных AUTHORED-рёбер из GR9). Toggle Raw JSON несогласован
  (button vs Accordion); нет «Copy id» / «Copy JSON»; нет history (`←/→`) navigation; пустой
  стейт — голый текст; truncation alert говорит API-жаргоном.
- **Proposal:** структурированный инспектор по IA из §2.7.1 — type plate с иконкой+цветом,
  stat-чипы для Work, collapsible-секции `Properties (N)` и `Connections (N)` с группировкой
  по `displayType` и client-side filter, «карта ребра» с source/edge/target иконками, edge
  properties whitelist (`year`/`weight`/`confidence`/`author_position`/`is_corresponding`/
  `raw_affiliation`/`institution_id`), единый `Accordion` для Raw JSON с copy, history hook,
  empty-state иллюстрация, hide `lateral`, локализация direction.
- **Acceptance:** см. §2.7.5 acceptance list — type plate с иконкой/цветом, subtitle suppression,
  grouped connections с neighbour-icons, edge map без дублирования, единый Raw JSON Accordion,
  history navigation, фильтр по соседям, нет EN-строк на ru-локали, `GraphDetailPanel.jsx` ≤ 100 строк.
- **Raised:** 2026-04-25 (см. graph-readability-followup-2026-04-25.md §1.6 + §2.7)
```

### 4.4 Зависимости

| Wave | Зависит от | Не блокируется |
|------|-----------|----------------|
| **GR6** | — | можно делать прямо сейчас |
| **GR7** | GR6 (после фикса канвас уже рендерит displayType, локализация заменяет источник) | i18n storage |
| **GR8** | (опционально) GR7 фаза B (для `summary_label_key`) | можно без B — sites сделают локализацию по `aggregator_kind` |
| **GR9** | GR8 (cap-агрегаторы по Author работают и в reader) | можно параллельно с GR8 backend, но раньше — мало смысла, агрегация в reader всё ещё низкого качества |
| **GR10a** (TopBar shell + tooltips) | GR7 (для tooltips на edge/node-type подписях; не строгое требование, можно делать параллельно) | независим от GR8/GR9 backend |
| **GR10b** (search + reset) | GR10a | — |
| **GR10c** (preset + standalone parity + view=reader switch) | GR10a + GR9 backend (для switch reader/raw, иначе switch будет no-op) | можно делать UI-only под фиче-флагом |
| **GR11** (i18n легенды + tooltips) | GR10a (тогда есть что локализовать в новых tooltips) и GR7 фаза A | можно слить с GR10a одним PR, чтобы не делать русскую локаль второй итерацией |
| **GR12a** (split `GraphDetailPanel`) | — | технический рефакторинг, без UX-изменений |
| **GR12b** (node plate + stats + i18n) | GR7 фаза A (ключи `graph.nodeKind.*`); GR12a | без GR7 — рендерим raw `nodeKind` как fallback, не блокирует |
| **GR12c** (connections grouping + filter + neighbour icons + hide lateral) | GR12a; GR7 фаза A (для локализации direction) | независим от GR10 |
| **GR12d** (edge map + edge Properties + Trace via) | GR12a; **Trace via — GR9** (контракт `edge.via`) | если GR9 ещё не готов — секция Trace via скрыта, остальное работает |
| **GR12e** (unified Raw JSON + history + empty state) | GR12a | — |
| **GR12f** (truncation alert + a11y) | GR12a | — |

### 4.5 Параллельность с другими треками

- **GR6/GR7/GR8/GR9/GR10/GR11/GR12 vs Track B (LangGraph)** — независимы по файлам, можно параллельно.
- **GR8 backend vs G-WorkspaceGraphSplit** — split уже сделан, GR8 правит подмодуль `api/workspace_graph/projection.py`.
- **GR9 backend vs `graph_snapshot_diff.py`** — GR9 явно сохраняет `view=raw` для совместимости snapshots, конфликта нет.
- **GR10 vs `useGraphWorkspaceData`** — GR10 не меняет hook, только обёртку `WorkspaceGraphToolbar` и места, куда её рендерят. `useGraphWorkspaceData` (см. `GraphWorkspacePanel.jsx:32`) остаётся источником истины для filter-секции.
- **GR10 vs Track J (settings/persistence)** — продлевает контракт `workspaceGraph*:<wid>` ключей; новый ключ `workspaceGraphView:<wid>` добавлять симметрично.
- **GR10c standalone parity vs `GraphPage.jsx`** — требует синка с `mergeTraceabilityParams` и `preserveGraphPageOptionalParams` (см. `GraphPage.jsx:84-100`); по тем же правилам, как сейчас сохраняется `graph_depth`.
- **GR12 vs GR10** — разные файлы (`detail/` vs новый `GraphTopBar`), не конфликтуют. Можно делать одной фронт-командой одним спринтом, разбив PR между подкомандами.
- **GR12 vs GR9** — `GR12d` (edge map + Trace via) — единственный кусок GR12, который синтегрирован с GR9; до выхода GR9 секция «Trace via» рендерится только когда `edge.raw.via?.length > 0` (всегда `false` в текущем payload), поэтому остальные PR GR12 (a/b/c/e/f) никак не блокируются.
- **GR12 vs Track J** — `useGraphDetailHistory` хранит state локально (без LS/URL), новых persistence-ключей не вводит. Если решим persist history — отдельный backlog после Wave J.

---

## 5. Что закрывается этим плану (итог для пользователя)

После прохождения GR6 + GR7 + GR8 + GR9 + **GR10 + GR11 + GR12** пользователь, открывая `/graph` или Workspace → Graph:

- **видит читаемые подписи рёбер** на канвасе (`is author of`, `cites`, `published in`), а **не** `HAS_AUTHORSHIP`/`OF_AUTHOR`/`CITES`;
- **на русской локали** видит «является автором», «цитирует», «опубликовано в», узлы «8 авторов работы», и легенду «Типы в этом представлении» / «Узлы» / «Рёбра» / «Внутренняя работа» вместо EN-строк;
- **типичная статья с 5 авторами** показана как `Work` + один агрегатор «5 авторов» + цитирования + venue, **а не** 5 одиночных `:Authorship`-дисков;
- **в reader-view** (default для UI) `:Authorship` дисков нет вовсе — есть `Work –[AUTHORED]→ Author`;
- **верхняя панель** — одна цельная зона из двух секций (filters + view-actions) с tooltips, поиском по узлам, Reset-кнопкой и опциональными пресетами; четыре полосы (toolbar / icon-row / view-mode / legend) превращаются в одну панель + сворачиваемую легенду; standalone-граф работы получает идентичный интерфейс;
- **правая панель деталей** — тип узла открывается с цветной плашкой и иконкой (та же иконка/цвет, что на канвасе); метрики цитирований — отдельные stat-чипы; соседи в Connections сгруппированы по типу ребра, имеют иконки своего типа и фильтр поиска; для ребра — компактная «карта ребра» с тремя элементами (источник · тип · цель) вместо тройного дублирования; кнопки `Открыть Gemma` / `Открыть Research` несут имя; есть секция «Properties» и «Trace via» для виртуальных AUTHORED-рёбер; единый Accordion для Raw JSON с «Копировать»; `←/→` навигация между selections; нет «lateral», «WorkInternal»-жаргона; пустой стейт — иллюстрация со стрелками;
- **mode-кнопки** не uppercased (соответствуют Cursor-стилю); stats-overflow исчез (chip-with-tooltip);
- **бенчмарки и snapshot-тесты не сломаны** — `view=raw` остаётся источником истины для них;
- **контракт API расширен аддитивно** — старые клиенты продолжают работать с EN-строками через `display_type`;
- **persist-контракт** `workspaceGraph*:<wid>` продлён аддитивно (новые ключи `View`, `Preset:<name>`); существующие LS-значения совместимы;
- **структурный долг снят:** `GraphDetailPanel.jsx` (412 строк, 7 view-моделей в одном файле) разнесён в `detail/` подкаталог; ни один файл правой панели не превышает порог `~250+` строк по гайду из `refactor-rhythm-and-backlog.mdc`.

---

## 6. Следующие шаги (порядок)

1. **PR #1 (GR6, frontend, ~0.5 дня):** правка `graphCanvasDraw.js` + тест. Закрывает основной user-visible bug.
2. **PR #2 (GR7 фаза A, frontend, ~1 день):** `graphLocalize.js` + ключи в `partGraphUi.js`. Закрывает «нет русской локализации» рёбер/узлов.
3. **PR #3 (master-roadmap + backlog, ~10 минут):** обновить статусы и добавить Wave GR6/GR7/GR8/GR9/GR10/GR11/GR12 (этот документ + правки в роадмапе и обоих backlog-файлах).
4. **PR #4 (GR10a + GR11 объединённо, frontend, ~1.5 дня):** `GraphTopBar` shell, перенос `WorkspaceGraphToolbar`/`GraphViewModeSwitch`/icon-row в две секции, tooltips для всех контролов, замена `<ToggleButton>` на `CursorSmallButton`, локализация легенды, stats-chip с tooltip. Закрывает «верхняя панель распадается + EN в легенде» одним PR.
5. **PR #5 (GR12a, frontend, ~1 день):** разбить `GraphDetailPanel.jsx` на `detail/` подкаталог (под-компоненты + `useGraphDetailHistory` + `properties.js`); сам `GraphDetailPanel.jsx` — тонкая обёртка ≤ 100 строк; UX без изменений. Снимает структурный долг и разблокирует малые диффы PR #6/#7.
6. **PR #6 (GR12b, frontend, ~1 день):** `GraphDetailNodePlate` (иконка + цветная плашка + бейдж membership + год) + `GraphDetailStats` (stat-чипы int/ext cites + degree) + suppression subtitle == type/displayLabel + i18n ключи `graph.nodeKind.*`/`graph.detail.*`. Закрывает «WorkInternal жаргон / иконки нет / метрики плоской строкой».
7. **PR #7 (GR12c, frontend, ~1.5 дня):** `GraphDetailConnections` с группировкой по `displayType`, иконками типа узла-соседа, фильтром, скрытием `lateral`-направления; пробросить `otherSubtitle` в `relatedEdgeRows` (`graphInspectorModel.js`). Самое заметное визуальное улучшение.
8. **PR #8 (GR10b, frontend, ~0.5 дня):** Search-поле + Reset-кнопка + тесты на LS-cleanup в верхнем тулбаре (independently of GR12 connections-фильтра).
9. **PR #9 (GR8 backend, ~1.5 дня):** per-kind thresholds, cap-aware агрегация, query params, тесты.
10. **PR #10 (GR8 frontend, ~0.5 дня):** hover-tooltip + улучшение визуала агрегатора + использование `aggregation_hints.preview_labels` + меню «Параметры агрегации» в actions-секции; обновить `GraphDetailAggregator` под GR12-сетку.
11. **PR #11 (GR9 backend, ~2 дня):** виртуальные `AUTHORED`-рёбра, симметричные тесты `view=raw`/`view=reader`.
12. **PR #12 (GR9 + GR10c + GR12d frontend, ~2 дня):** switch `view: reader|raw` в filter-секции `GraphTopBar`, `GraphDetailEdgeMap` (карта ребра без дублирования) + edge `Properties` whitelist + секция `Trace via` для виртуальных AUTHORED, standalone-parity (тулбар на `/graph?work_id=…`), URL-синк.
13. **PR #13 (GR12e, frontend, ~0.5 дня):** unified `GraphDetailRawJson` Accordion (узел + ребро) с copy-кнопкой, `useGraphDetailHistory` + `←/→` навигация в header, empty-state иллюстрация.
14. **PR #14 (GR12f, frontend, ~0.25 дня):** truncation alert текст + a11y фиксы (h3 секции, aria-describedby, контраст ≥ WCAG AA).
15. **PR #15 (опционально GR7 фаза B, ~0.5 дня):** `display_type_key` / `display_label_key` в API, ADR 011 update.
16. **PR #16 (опционально GR10c preset, ~0.5 дня):** save-preset через `<Popover>` + `workspaceGraphPreset:<wid>:<name>` LS-контракт.
