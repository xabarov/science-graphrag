# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Completed (archive)

Summaries only; specs and ADRs hold detail (`graph-ui-plan`, `frontend-ui-api-contracts`, ADR 006/007, ingestion roadmap).

| When | Theme |
|------|--------|
| 2026-04-25 | **Graph:** `GraphCanvasMvp` split (`useGraphCanvasInput`, `graphCanvasDraw`); aggregator rendering + expand; `GraphWorkspacePanel` split (`useGraphWorkspaceData`, side panel, mode switch, debug inspector). |
| 2026-04-25 | **Ask:** `AskPanel` → `useAskSubmit`, `AskSessionControls`, `AskAnswerPanel` (composition shell). |
| 2026-04-25 | **Ingest UI:** `IngestStageStepper` + `useJobStream` (SSE) + polling fallback in workspace ingest. |
| 2026-04-24 | **Workspaces / workspace:** Wave I — `WorkspacesPage` shell + panels; `WorkspacePage` shell + ingest / dedup / paper list extraction. |
| 2026-04-08 | **Graph standalone:** Waves 5–8 (maximize canvas, `graphPageUrl` / focus / detail width, drag gutter, contract + pointer-capture polish). |
| 2026-04-08 | **Graph canvas:** Wave 4.2 z-order; Wave 4.3 React Flow mode; Canvas force layout + quadTree/communities (ADR 007). |
| 2026-04-08 | **API errors:** unified `formatResearchApiError` in `researchApi.js` + tests. |
| 2026-04-26 | **Graph:** Bloom-like overview — type counts + node/edge totals in legend, chip sort frequency/alphabet, canvas edge-label modes (`all` / `interaction` / `adaptive`) + `GraphCanvasViewToolbar`, local node substring search (`graphNodeSearch.js`, `GraphWorkspacePanel`). |
| 2026-04-26 | **Research API (UI):** `services/research/{errors,meta,queryModel,queryHttp,askSessions,agent,ideaAssist,works,graph}.js` + barrel `researchApi.js`; shim `benchmarkSummary.js` removed (`useBenchmarkSummary` → `benchmarkApi.js`). |
| 2026-04-26 | **Benchmark UI:** Compare/Run tabs split — `useCompareTab`, `CompareDeltaTable`, `CompareTabSummarySection`, `benchmarkCompareModel` + vitest; `useRunTab`, `RunTabCurrentRunSection`, `runTabCaseToggle`; workbench run panel → `workbench/BenchmarkWorkbenchRunPanel.jsx` (`WorkbenchRunScopedPanel`). |
| 2026-04-26 | **Workspace UX + ingest dedup (full-stack slice):** full-width `WorkspacePage`; `PageActionToolbar` / `CursorIconAction` / `CopyIdButton` in hero and cards; side panel без smart-dedup poll; удалены `WorkspaceDedupSection`, `DeduplicationPanel`, `WorkDedupReviewDialog`; `IngestConflictReviewCard` + `pending_conflicts_count` на ingest job; икон-действия на Home / Workspaces / Graph / Benchmark / Settings / Diagnostics / Evidence / Admin entry / NotFound / workspace tabs. |
| 2026-04-26 | **Big plan slice (UI / wiring):** `paths.py` import в aggregator; child batch `progress_pct` в `WorkspaceIngestPanel.jsx`; `WorkspaceLayout` / `WorkspaceContextChip`; i18n `settings.ingestion.saveError`; `.env.example` → ADR-021; SSE `/v2/agent/query` (`useAgentStream` + `useAskSubmit`). Backend-only (`EDGE_DISPLAY_TYPE_READER`, dual_validate glue) — см. [`refactor-backend.md`](./refactor-backend.md) Completed. |
| 2026-04-26 | **Former `[DONE]` queue (graph):** double-click fit selection (`graphCanvasCamera`); GR6 canvas uses `displayType`; GR7 `graphLocalize` EN/RU. |
| 2026-04-26 | **Former `[DONE]` queue (benchmark / workspace / reader):** TrustSignalDrillIn; `CaseDetailDialog` → `caseDetail/*` + families registry; slim `WorkspacePage`; `ReaderWorkBody` split; WX1 layout/hero/side panel; WX3 ingest conflicts card; WX4 `PageActionToolbar` / `CursorIconAction`; WX6 smart-dedup surface removal; EF-Cards / EF-Evidence / Reader RX1 + single-column cleanup; `useScienceGraphForceSimulation` → `hooks/graph/`; `Cursor*` on `IngestConflictReviewCard`. |
| 2026-04-27 | **WX5 minimal + shell polish:** [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) (re-export chip) в [`DashboardLayout.jsx`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx) и [`WorkspaceHero.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceHero.jsx); i18n `workspace.hero.switchWorkspaceHint` (EN/RU); chip label без UUID — `shell.workspaceChip.unnamed` когда нет имени ([`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx)); `WorkspaceLayout` — больший `minHeight` grid + flex main. |
| 2026-04-27 | **WX5 empty-state CTA:** кнопка «Новая область» / `workspace.empty.createWorkspace` + `createWorkspace()` и синхрон URL `workspace_id` в [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) empty-state; i18n EN/RU в `partWorkspacePage.js`. |
| 2026-04-27 | **Graph GR-UX1 — command bar:** единая панель [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/WorkspaceGraphToolbar.jsx) — `GraphScopeMenu` / меню узлов / `GraphViewChips` в `toolbar/` (исторически глубина `1°/2°` и `GraphNodeTypesMenu`; **2026-04-27:** глубина workspace убрана, типы — клиентский `GraphNodesVisibilityMenu` + `graphVisibilityFilter`); тултипы stats, локальный поиск + чипы «Детали / Легенда / Диагностика»; [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/GraphWorkspacePanel.jsx) — `Collapse` легенды + `graphEmbeddedLegendOpen`; [`GraphTypeLegend.jsx`](../../ui/src/components/graph/GraphTypeLegend.jsx) — компактный header; i18n `partGraphUi` EN+RU; vitest [`WorkspaceGraphToolbar.test.jsx`](../../ui/src/components/graph/WorkspaceGraphToolbar.test.jsx). |
| 2026-04-27 | **Workspace graph — full 1-hop:** сервер всегда отдаёт полную 1-hop окрестность по всем работам в workspace (`build_from_depth1_rows`, без `depth`/`neighbor_limit`/`node_types` в query); neighbors/expand без лимитов; фронт только фильтрует видимость; pytest + vitest обновлены; ADR 011/012 addendum + `graph-ui-plan` + root-cause analysis. |
| 2026-04-27 | **LT1 appearance foundation:** `ui/src/theme/` — `appearanceMode.js`, `buildAppTheme.js` (`appTokens`), `AppearanceProvider.jsx`, inline first-paint в [`ui/index.html`](../../ui/index.html), [`main.jsx`](../../ui/src/main.jsx) без inline `createTheme`; [`styles.css`](../../ui/src/styles.css) по `html[data-color-scheme]`; [`GeneralSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/GeneralSettingsPanel.jsx) + i18n `partSettings` EN/RU; vitest [`appearanceMode.test.js`](../../ui/src/theme/appearanceMode.test.js). Контракт: [`light-theme-roadmap-2026-04-27.md`](../../docs/analysis/light-theme-roadmap-2026-04-27.md) §10. |
| 2026-04-27 | **Ask:** `AskPanel` → [`useAskPanelOrchestration.js`](../../ui/src/components/work/useAskPanelOrchestration.js) + [`AskPanelChrome.jsx`](../../ui/src/components/work/AskPanelChrome.jsx); shell-only [`AskPanel.jsx`](../../ui/src/components/work/AskPanel.jsx). |
| 2026-04-26 | **Graph standalone — scope bugfix:** кнопка «Граф» на [`WorkPaperCard`](../../ui/src/pages/WorkspacePage/WorkPaperCard.jsx) ведёт на `/graph?work_id=…` без `workspace_id`; [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) больше не подставляет `activeWorkspaceId` в этом случае — иначе [`useGraphWorkspaceData`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) грузил полный workspace graph и игнорировал работу. |

## Queue

Closed items live only in **Completed (archive)** above (no `### [DONE]` bodies here).

### [OPEN] Workspace graph — canvas perf for very large payloads (10k+ edges)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx), [`GraphFlowView.jsx`](../../ui/src/components/graph/GraphFlowView.jsx), [`graphUiLimits.js`](../../ui/src/components/graph/graphUiLimits.js), optional virtualization / level-of-detail
- **Issue:** After **2026-04-27**, the workspace graph API can return the **full** 1-hop union; dense workspaces may stress the canvas (layout + draw cost) even when `capGraphForUi` caps **display** — payload parse and normalization still grow.
- **Proposal:** Profile with a workspace snapshot that has high edge count; consider progressive disclosure, Web Worker normalization, or explicit «load subset» only if product requires server caps again.
- **Acceptance:** documented threshold + measured FPS / interaction budget on a reference workspace; no silent browser tab freeze on load.
- **Raised:** 2026-04-27

### [OPEN] useAgentStream — stable callbacks + abort reason
- **Progress (2026-04-27):** колбэки вынесены в `useRef` + `useEffect`; `stream` стабилен при смене identity колбэков (зависит только от `workspace_id`). Тесты: `useAgentStream.test.js` (rerender + latest `onError`). **Остаётся:** различать причины `AbortError` (навигация / новый submit) для `onError` и «stream ended without final answer».
- **Area:** [`ui/src/hooks/useAgentStream.js`](../../ui/src/hooks/useAgentStream.js)
- **Issue:** `stream` в `useCallback` зависит от нескольких колбэков-ссылок; при `AbortController.abort` нет явного различия между навигацией, HMR reload и новым submit для потребителей `onError`.
- **Proposal:** Паттерн stable callbacks (`useRef` + thin wrapper / `useEvent`), опционально не вызывать `onError` при ожидаемом abort; тест: abort не приводит к ложному «stream ended without final answer» где это нежелательно.
- **Acceptance:** unit-тест на сценарий abort; контракт документирован в комментарии к хуку.
- **Raised:** 2026-04-27

### [OPEN] Agent V2 — EN apology fallback on RU workspace inventory query
- **Progress (2026-04-27):** в user message всегда подмешивается `<active_workspace_id>` из API; `extract_langgraph_answer` берёт текст из tool `final_answer`; усилены промпты retrieval/writer; RU-хинты в `tool_search` / `heuristic_answer_class`. **Остаётся:** прогон `curl`/e2e на реальном workspace и при необходимости принудительный первый tool-call.
- **Area:** [`science_graphrag/api/agent_v2.py`](../../science_graphrag/api/agent_v2.py), цепочка tool selection / system prompt locale
- **Issue:** Запрос вроде «сколько статей в рабочей области?» с валидным `workspace_id` может вернуть `final_answer` на английском с отказом «no necessary tools» вместо осмысленного ответа по данным области.
- **Proposal:** Воспроизвести через `curl` SSE; проверить определение языка ответа, intent/inventory path и доступность тулов для подсчёта работ в workspace.
- **Acceptance:** RU-запрос про объём корпуса области даёт RU-ответ с числом или явным «в области нет работ»; регрессионный тест или зафиксированный benchmark-case по желанию.
- **Raised:** 2026-04-27

### [OPEN] Workspace shell — «Research» chip, dropdown noise, пустая зона под карточками
- **Progress (2026-04-27):** см. Completed (WX5 minimal, empty-state **create workspace** CTA, chip `unnamed`, layout `minHeight`). **2026-04-26:** searchable switcher в popover (фильтр по имени/id), счётчик работ, сортировка, тонкий скролл, компактный футер с иконками — см. [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (~356 LOC; при refactor-pass вынести строку/панель). **Остаётся:** второй ряд контента под карточками (ingest/dedup/illustration), улучшение копирования id из строки списка.
- **Area:** [`DashboardLayout`](../../ui/src/components/layout/DashboardLayout/), [`WorkspaceContextChip`](../../ui/src/components/layout/WorkspaceContextChip.jsx) (или аналог триггера «Research»), [`WorkspaceLayout.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceLayout.jsx) / [`WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** Чип в углу слабо аффордирует «смена области»; в списке под именем длинный UUID — визуальный шум (мы уже убрали id с hero, но chip всё ещё дублирует низкоуровневый id). Под сеткой карточек остаётся большая пустая область — layout не тянет main на высоту viewport / нет явного второго ряда контента (ingest progress, dedup, пустой state illustration).
- **Proposal:** (1) Заменить или дополнить чип: иконка области + короткое имя без UUID в основной строке (id в tooltip / «Копировать id»). (2) Рассмотреть `WorkspaceSwitcher` из backlog WX5 как primary entry. (3) Main column: `flex: 1` + `minHeight` / placeholder или закрепить `IngestConflictReviewCard` / ingest stepper внизу колонки при наличии событий.
- **Acceptance:** скринлист до/после; нет горизонтального «дырявого» ощущения на 1440×900; `npm run lint` зелёный.
- **Raised:** 2026-04-26

### [OPEN] Ingest conflict UI — osint-grade `ConflictResolver` (типы сущностей + inline к job)
- **Area:** [`IngestConflictReviewCard.jsx`](../../ui/src/components/dedup/IngestConflictReviewCard.jsx), [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx), `useJobStream` / ingest job types
- **Issue:** Текущая карточка — упрощённый мастер по **work** парам после завершения job (или при открытой панели). Нет разветвления по author/entity, нет side-by-side «карточек сущности» как в osint `ConflictResolver.jsx`, нет привязки к **активному** стриму ingest (пользователь не видит «решить сейчас», пока job не завершён — если нет pending в очереди).
- **Proposal:** После backend-расширения (см. `refactor-backend.md` — ingest dedup parity): унифицировать модель «конфликт» для UI; для works — расширить карточку (метаданные, score, match keys); при появлении API mid-job — блок поверх `IngestProgressCard` или drawer. Референс UX: `osint-gr/frontend/src/pages/KnowledgeGraphPage/components/ConflictResolver.jsx` + `RightPanel.jsx`.
- **Acceptance:** e2e или component-тест на смену состояний; i18n для новых полей; не деградирует текущий happy path без конфликтов.
- **Raised:** 2026-04-26

### [OPEN] Remove deprecated workspace dedup HTTP surface (after soak)
- **Area:** `science_graphrag/api/workspace_dedup.py` (или аналог), фронт уже не вызывает scan/merge/candidates из `GraphPage` / side panel.
- **Issue:** Backend endpoints `/v1/workspaces/.../dedup/*` остаются для обратной совместимости; мёртвый API усложняет security review.
- **Proposal:** После 1–2 релизов без внешних клиентов — удалить неиспользуемые маршруты или спрятать за feature flag; оставить только то, что использует `IngestConflictReviewCard` (`getWorkspaceSmartDedupConflicts`, `decideWorkspaceSmartDedupConflict`).
- **Acceptance:** grep по `ui/` не находит удалённых путей; OpenAPI / тесты обновлены; CHANGELOG note.
- **Raised:** 2026-04-26

### [OPEN] Graph canvas — Neo4j Browser–grade UX (optional follow-ups)
- **Area:** `GraphCanvasMvp.jsx` / рядом hooks
- **Issue:** В Neo4j Browser ещё есть command bar, стили рёбер по типу, инспектор запросов, контекстное меню, экспорт — не требуются для read-only neighborhood v1.
- **Proposal:** Отдельными маленькими PR: (1) контекстное меню узла (ПКМ): минимум Fit / Center / Copy id; (2) компактная легенда типов рёбер на canvas, согласованная с `GraphTypeLegend`, без поломки режимов подписей рёбер.
- **Acceptance:** по пункту; `npm run lint` / `npm run test` в `ui/`.
- **Raised:** 2026-04-26

### [OPEN] i18n hardcoded copy: HypothesisPanel, IngestionSettings, Workspace dialogs
- **Area:** [`HypothesisPanel.jsx`](../../ui/src/components/work/HypothesisPanel.jsx), [`pages/SettingsPage/IngestionSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/IngestionSettingsPanel.jsx), [`WorkspacePage/WorkspacePage.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePage.jsx)
- **Issue:** В этих модулях встречаются хардкод-строки (`Generating...`, `No candidates`, `Workspace summary`, `Hypothesis / contradiction assist`, `Saving…`, `Save ingestion settings`) — расходится с [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md).
- **Proposal:** Вынести в i18n словари, добавить EN+RU ключи, заменить литералы на `t(...)`.
- **Acceptance:** ESLint i18n-проверка зелёная (если включена); ручной аудит не находит литералов в этих компонентах; `npm run lint` зелёный.
- **Raised:** 2026-04-25

### [OPEN] Wave EF-Reader — RX2 reading affordances (TOC, language banner, copy-id)
- **Area:** новые `ReaderToc.jsx` (или встраивание в header), `ReaderLanguageBanner.jsx`, `ReaderCopyWorkIdButton.jsx`;
  [`ReaderWorkDetailCard.jsx`](../../ui/src/components/work/ReaderWorkDetailCard.jsx),
  [`ReaderPage.jsx`](../../ui/src/pages/ReaderPage.jsx),
  [`ReaderTab.jsx`](../../ui/src/pages/WorkspacePage/tabs/ReaderTab.jsx)
- **Issue:** После RX1 cleanup страница «Чтение» одноколоночная, но без навигации по разделам (TOC), без явного индикатора языка статьи (для будущей кнопки перевода) и без ergonomic copy-кнопки `work_id`. Длинные статьи (`Page width = container width`, ~1000 px) дают comfortable measure только при принудительной 78ch — но без TOC прыгать по секциям трудно. Roadmap RX1 (`docs/analysis/reader-ux-and-translation-roadmap-2026-04-25.md` §1.4–§1.6) предполагает левую/правую полоску либо overlay TOC.
- **Proposal:**
  1. `ReaderToc.jsx` строит дерево из `chunks[].section_path`, рендерит как right-side `position: sticky` panel при `lg+` (collapsible button под header при `<lg`); клик по узлу делает `scrollIntoView` соответствующего markdown-блока (нужно расставить anchor-id из `section_path` в `MarkdownView` / `ReaderMarkdownSourcePanel`).
  2. `ReaderLanguageBanner.jsx` — компактная плашка под `ReaderWorkDetailCard` с `detail.language` (когда backend начнёт отдавать), placeholder при `auto/unknown`; кнопки `Перевести аннотацию / Перевести статью` (отключены до Wave LX-2 backend).
  3. `ReaderCopyWorkIdButton.jsx` — мелкая `IconButton` (small caps `work_id`) рядом с метастрокой; копирует `workId` в clipboard.
  4. Объединить `ReaderTab` + `ReaderPage` через общий контент-компонент: один и тот же layout, разные обвязки header'ом.
- **Acceptance:** `npm run lint` / `vitest run` (новые тесты на `ReaderToc` парсинг section_path) / `npm run build` зелёные; на ноутбуке (1440×900) видны header + TOC + body без горизонтального скролла; в workspace-табе `Reader` тот же body без дубликации детальной шапки.
- **Raised:** 2026-04-26

### [OPEN] Workspace UX — Wave WX2-FE ingest progress card (shimmer + ETA + i18n stages)
- **Area:** новые [`ui/src/components/ingestion/IngestProgressCard.jsx`](../../ui/src/components/ingestion/IngestProgressCard.jsx),
  [`IngestStageRow.jsx`](../../ui/src/components/ingestion/IngestStageRow.jsx);
  [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx);
  [`partWorkspacePage.js`](../../ui/src/i18n/messages/ru/partWorkspacePage.js) (+ EN)
- **Issue:** При активном ingest job UI показывает `<pre>`-блок «Logs» (`Details / Logs` accordion) рядом с
  `IngestStageStepper`. Stepper использует ASCII-символы (`✓ ● ○ ×`), нет общего progress-бара/процента, нет
  shimmer на активной стадии, нет ETA, имена стадий приходят с бэкенда EN-only (`vl_extract`, `embed_chunks`).
  Пользователь не видит «сколько ещё ждать» и не понимает, в какой workspace грузится файл.
- **Proposal:** Новый `IngestProgressCard.jsx`:
  header (filename + size + target workspace name);
  общий `LinearProgress determinate` (значение из `IngestJobView.progress_pct`, fallback — равномерный по `stages.length`);
  список стадий через `IngestStageRow.jsx` (MUI-иконка по статусу: `CheckCircleOutlineOutlinedIcon`/
  `ErrorOutlineOutlinedIcon`/`RotateRightIcon` с `keyframes spin`/`RadioButtonUncheckedOutlinedIcon`;
  локализованное имя через `t("ingest.stage.{name}")`; длительность для завершённых; shimmer-полоса для running);
  ETA-строка из `sum(remaining expected_duration_ms)`;
  «Подробности» accordion свёрнут (внутри — старый `<pre>` с `ingestJob.logs`).
  План: [`docs/analysis/workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.2.
- **Acceptance:** При активном job в UI виден только `IngestProgressCard`; «Logs» свёрнут под «Подробности»;
  активная стадия со shimmer, ETA-строка появляется при ≥ 1 завершённой стадии; на ru-локали имена стадий —
  на русском (`Извлечение текста`, `Чанки и эмбеддинги`); `npm run lint` / `npm run test` / новый
  `IngestProgressCard.test.jsx` зелёные.
- **Synergy:** Backend-сторона `IngestJobView.progress_pct` + `expected_duration_ms` —
  отдельный backend-PR (Wave WX2-BE); UI-сторона работает с fallback при отсутствии полей.
- **Raised:** 2026-04-25

### [OPEN] Workspace UX — Wave WX4 follow-up: ingest panel primary labels + stepper icons
- **Area:** [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx), [`IngestStageStepper`](../../ui/src/components/ingestion/) (или аналог)
- **Issue:** После WX4 основной паттерн навигации — иконки; крупные текстовые «Добавить работу» / drop-zone на ingest остаются намеренно читаемыми; stepper всё ещё может использовать ASCII-маркеры до WX2.
- **Proposal:** По продуктовому решению: либо оставить текст на primary ingest CTA, либо добавить `startIcon` + короткий label; stepper — в WX2-FE.
- **Acceptance:** единый визуальный язык с остальным приложением без потери ясности для upload.
- **Raised:** 2026-04-26

### [OPEN] Workspace UX — Wave WX5 follow-up (searchable list + richer switcher)
- **Area:** [`WorkspaceSwitcher.jsx`](../../ui/src/components/layout/WorkspaceSwitcher.jsx) (реальная обёртка вместо re-export), [`WorkspaceContextChip.jsx`](../../ui/src/components/layout/WorkspaceContextChip.jsx)
- **Progress (2026-04-27):** on-page **«New workspace»** (`workspace.empty.createWorkspace`) в empty-state [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) — создаёт область и обновляет `workspace_id` в URL.
- **Issue:** Список областей в popover по-прежнему не searchable; триггер — старый Chip, не отдельная кнопка h36 из исходного макета.
- **Proposal:** Вынести разметку из `WorkspaceContextChip` в составной `WorkspaceSwitcher` (или расширить chip props); empty state блок на `WorkspacePage` по [`workspace-ux-redesign-2026-04-25.md`](../analysis/workspace-ux-redesign-2026-04-25.md) §3.5.
- **Acceptance:** как в старом OPEN WX5 (megatron CTA + search) **или** осознанно сузить продуктовый scope и обновить ADR/workspace doc.
- **Raised:** 2026-04-27

### [OPEN] Agent query — deprecate or remove `POST /v1/agent/query` (Wave Y6)
- **Area:** `ui` (`useAskSubmit` fallback), `science_graphrag/api` agent routes
- **Issue:** Streaming идёт через `/v2/agent/query` (`useAgentStream`); JSON/v1 fallback ещё живёт в клиенте и на бэкенде.
- **Proposal:** После фиксации v2-only на API — убрать мёртвые пути и обновить тесты/доки.
- **Acceptance:** нет регрессий ask/agent; контракт задокументирован.
- **Raised:** 2026-04-27 (вынесено из архивного пункта SSE)
