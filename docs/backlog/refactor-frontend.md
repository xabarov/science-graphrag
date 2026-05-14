# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Completed (archive)

Длинная таблица закрытых тем (2026-04 — 2026-05-14) **убрана**: она дублировала git-историю, спеки и ADR и не продвигала открытые задачи. Детали — в `docs/specs/`, `docs/analysis/`, ADR, коммитах.

**Что ещё полезно помнить при планировании:** волна **WF-2026-05 по Ask** (session model/storage, оркестратор + вспомогательные хуки + `askPanelOrchestrationContract`, scroll/empty в треде, шард тестов `AskAnswerPanel`) закрыта **2026-05-14**. Follow-up этой же даты: каталог `components/work/ask` разложен по доменам (`shell/`, `session/`, `orchestration/`, `chat/`, `answer/`, `forms/`) + добавлен фасад `ask/index.js` для стабильного публичного входа. **2026-05-14 (second pass):** `askSessionPolicy` / `askSessionDigest` / `askSessionConstants`; публичный слой `components/work/agent/index.js` для Ask↔Agent; оркестратор разнесён (`askAgentUiErrors`, `useAskPanelClipboard`, `useAskPanelStreamArtifacts`, `askPanelScopePresentation`); `ChatContextPicker*` + `typedBlocks/*`; Vitest для новых границ. **2026-05-14 (landscape audit):** обновлён **Queue** в этом файле — открытые волны G1→S (graph input → workspace/flow shell → workspace store/page → benchmark inspector → ask → settings) + P2 react-refresh; см. разделы «Глубокий аудит» и «План волн».

### [DONE] Ask domain after reorg — tighten module contracts and file size
- **Area:** [`components/work/ask/session/askSessionState.js`](../../ui/src/components/work/ask/session/askSessionState.js), [`components/work/ask/chat/ChatContextPicker.jsx`](../../ui/src/components/work/ask/chat/ChatContextPicker.jsx), [`components/work/ask/orchestration/useAskPanelOrchestration.js`](../../ui/src/components/work/ask/orchestration/useAskPanelOrchestration.js), [`components/work/ask/chat/ChatTypedBlocks.jsx`](../../ui/src/components/work/ask/chat/ChatTypedBlocks.jsx)
- **Issue:** Reorg to `shell/session/orchestration/chat/answer/forms` is done and improves navigability, but several modules remain dense (~328–377 LOC) with mixed responsibilities (state transitions + persistence + URL sync + rendering policy).
- **Proposal:** Continue split by seam: `askSessionState` -> session-store adapter vs scope/session migration policy; `ChatContextPicker` -> selection model + rendering; `useAskPanelOrchestration` -> URL/session sync vs submit orchestration; keep public boundary via `ask/index.js` and document it in rule `frontend-ask-boundary.mdc`.
- **Acceptance:** targeted modules trend below ~300 LOC (or have explicit submodule boundaries); no external deep-imports bypassing `ask/index.js`; ask test suite + `askFlowCompatibility` green.
- **Raised:** 2026-05-14 (post-reorg architecture pass)
- **Done:** 2026-05-14 — policy/digest/constants split from `askSessionState`; Ask imports agent via `work/agent/index.js`; orchestration helpers extracted; `ChatContextPicker` + article dialog + `useChatContextArticleSearch`; typed blocks under `chat/typedBlocks/` with barrel `ChatTypedBlocks.jsx`; new unit tests; `npm run lint` + vitest (`ask/`, `askFlowCompatibility`, agent index + explain auto-open) green.

## Queue

Карточки ниже — **только открытая** работа (P0/P1/P2). Краткий контекст закрытых волн — в **Completed (archive)** выше; полная история — в git и продуктовых спеках.

Priorities: **P0** = user-visible risk or scaling ceiling; **P1** = maintainability / files over ~400 LOC or tangled hooks; **P2** = polish and optional depth.

Backend-only follow-ups (dedup HTTP removal, Agent V2 locale) live in [`refactor-backend.md`](./refactor-backend.md); do not track duplicate narratives here.

**Open queue (2026-05-14 refresh):** ниже — **новые P1/P2** после глубокого прохода по `ui/src` (LOC `wc -l`, без `*.test.*`). Graph canvas controller закрыт; **canvas input (Wave G1) закрыт 2026-05-14**; следующий фокус — **graph workspace/flow shell**, **workspace page + `workspaceStore`**, **benchmark inspector / run-group**, **Ask orchestration**, затем **Settings** и мелкий **react-refresh** долг.

### Глубокий аудит фронтенда (landscape, 2026-05-14)

**Слои и потоки данных**

- **Страницы** (`pages/`): маршруты, табы workspace, Settings/Benchmark/Home — здесь смешиваются роутинг, query-параметры и «толстые» `use*` ядра (`useWorkspacePageCore`, run-tab orchestration).
- **Продуктовые области** (`components/work/`, `components/graph/`): Ask + Agent runtime уже разнесены по доменам (`ask/index.js`, `work/agent/index.js`), но оркестрация сабмита и сессии Ask остаётся узкой полосой риска.
- **Сервисы и IO** (`services/apiClient.js`, `services/researchApi.js`, `utils/workspaceStore.js`): `workspaceStore` — монолит **~399 LOC** поверх `apiClient` (таймауты ingest, workspace CRUD, graph stats); это главный **не-React** кандидат на разрез по доменным модулям (read vs write vs ingest).
- **Граф**: canvas MVP и force-sim уже разложены; **ввод/жесты** — фасад [`useGraphCanvasInput`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasInput.js) + [`hooks/graphCanvasInput/`](../../ui/src/components/graph/canvas/hooks/graphCanvasInput/) (2026-05-14); далее **flow shell** (`GraphFlowView` ~373), **workspace chrome** (`GraphWorkspacePanel` ~390, `WorkspaceGraphToolbar` ~352, `GraphNodeDetailSection` ~343).

**Где сосредоточена сложность (крупнейшие не-тестовые модули, ориентир)**

| Band | Примеры путей (LOC, май 2026) | Риск |
| --- | --- | --- |
| **~380–400** | [`workspaceStore.js`](../../ui/src/utils/workspaceStore.js) (~399), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx) (~390), [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) (~381) | смешение API + UI-состояния + навигации; регрессии при ingest/workspace |
| **~340–375** | [`BenchmarkCaseInspectorShell.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx) (~377), [`GraphFlowView.jsx`](../../ui/src/components/graph/flow/GraphFlowView.jsx) (~373), [`useGraphCanvasMvpController.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasMvpController.js) (~355) | долгие файлы = высокая стоимость фич; canvas input вынесен в `hooks/graphCanvasInput/*` + фасад |
| **~290–320** | [`scienceGraphSimulationTickEngine.js`](../../ui/src/hooks/graph/scienceGraphSimulationTickEngine.js) (~319), [`useBenchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunGroup.js) (~315), [`WorkspaceIngestPanel.jsx`](../../ui/src/pages/WorkspacePage/WorkspaceIngestPanel.jsx) (~303), [`GraphCanvasViewToolbar.jsx`](../../ui/src/components/graph/canvas/GraphCanvasViewToolbar.jsx) (~300), [`askSessionState.js`](../../ui/src/components/work/ask/session/askSessionState.js) (~297), [`SettingsPage.jsx`](../../ui/src/pages/SettingsPage.jsx) (~295) | точечные волны или явные подмодули по мере роста |

**Уже стабилизировано (контекст планирования)**

- Graph canvas: `GraphCanvasMvp` shell, `useGraphCanvasMvpController` composition + sub-hooks, force integrator split, draw facade — см. **[DONE]** карточки ниже.
- Ask/Agent: реорг каталога ask, `agentRunViewModel` / `AgentLiveStatus` split — см. archive / **[DONE]**.
- Benchmark catalog/launch/analysis — см. **[DONE]**.

**Технический хвост (не функциональный)**

- ESLint `react-refresh/only-export-components`: [`MarkdownViewCore.jsx`](../../ui/src/components/work/markdown/MarkdownViewCore.jsx), [`TrustSignalPanel.jsx`](../../ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx) — вынести константы/хелперы в соседние `.js` при следующем касании.

### План волн (рекомендуемый порядок рефактор-проходов)

1. **Wave G1 — Graph canvas input** — **[DONE] 2026-05-14** — фасад [`useGraphCanvasInput.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasInput.js) + [`hooks/graphCanvasInput/`](../../ui/src/components/graph/canvas/hooks/graphCanvasInput/); опционально позже: [`GraphCanvasViewToolbar.jsx`](../../ui/src/components/graph/canvas/GraphCanvasViewToolbar.jsx). Vitest: canvas input + draw hit-tests.
2. **Wave G2 — Graph workspace / flow shell** — [`GraphFlowView.jsx`](../../ui/src/components/graph/flow/GraphFlowView.jsx), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx), [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx), [`GraphNodeDetailSection.jsx`](../../ui/src/components/graph/shell/detail/GraphNodeDetailSection.jsx): вынести данные/действия в hooks или `workspace/*` подмодули; не смешивать canvas MVP с layout shell без явной границы.
3. **Wave W — Workspace** — разрезать [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) по табам/ingest/bootstrap; выделить из [`workspaceStore.js`](../../ui/src/utils/workspaceStore.js) доменные клиенты (`workspaceRead`, `workspaceWrite`, `workspaceIngest`) с общим `apiClient` + тонким фасадом `workspaceStore.js`.
4. **Wave B — Benchmark operator UI** — [`BenchmarkCaseInspectorShell.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx), [`useBenchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunGroup.js): презентация vs загрузка данных vs URL/session.
5. **Wave A — Ask (продолжение)** — [`useAskPanelOrchestration.js`](../../ui/src/components/work/ask/orchestration/useAskPanelOrchestration.js), [`askSessionState.js`](../../ui/src/components/work/ask/session/askSessionState.js), при необходимости [`useAskPerformAgentSubmit.js`](../../ui/src/components/work/ask/orchestration/useAskPerformAgentSubmit.js); публичный вход только через [`ask/index.js`](../../ui/src/components/work/ask/index.js).
6. **Wave S — Settings** — инкрементально: [`SettingsPage.jsx`](../../ui/src/pages/SettingsPage.jsx), [`StorageSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/StorageSettingsPanel.jsx), [`LlmSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/LlmSettingsPanel.jsx) (уже частично разнесено — не ломать границы `storage/`).

```mermaid
flowchart LR
  pages[pages]
  work[work_ask_agent]
  graph[graph_canvas_flow]
  services[services_utils]
  pages --> work
  pages --> graph
  pages --> services
  work --> services
  graph --> services
```

### Stage baseline (next structural pass, 2026-05-14)

Pre-refactor line counts (approximate targets ~250–300 LOC per leaf or explicit submodule seams):

| Path | LOC (pre) | LOC (post 2026-05-14 pass) |
| --- | ---: | ---: |
| `ui/src/components/graph/canvas/GraphCanvasMvp.jsx` | 599 | ~196 (shell → [`hooks/useGraphCanvasMvpController.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasMvpController.js); seam map [`canvas/README.md`](../../ui/src/components/graph/canvas/README.md)) |
| `ui/src/components/graph/canvas/hooks/useGraphCanvasMvpController.js` | ~519 | ~355 (composition + [`hooks/useGraphCanvasWorldPositions.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasWorldPositions.js), derived/paint/menu/view-actions) |
| `ui/src/components/graph/canvas/graphCanvasDraw.js` | 514 | 27 (facade → `canvas/draw/*`) |
| `ui/src/hooks/graph/useScienceGraphForceSimulation.js` | 515 | ~187 (+ `scienceGraphSimulationResetPolicy.js`, `scienceGraphSimulationGraphPrep.js`, `scienceGraphSimulationTickEngine.js`, bounds/tune) |
| `ui/src/components/graph/workspace/GraphWorkspacePanel.jsx` | 426 | 390 (+ `graphWorkspacePanelStorage.js`) |
| `ui/src/components/graph/shell/GraphTypeLegend.jsx` | 432 | 262 (+ `GraphTypeLegendCollapses.jsx`, `graphTypeLegendConfig.js`) |
| `ui/src/pages/BenchmarkPage/useRunTab.js` | 287 | 255 (+ `runTab/runTabSingleRunLaunch.js`) |
| `ui/src/pages/BenchmarkPage/catalog/experimentCatalogData.js` | 277 | 37 (facade + `experimentCatalogExperimentsPart*`, bundle, `experimentCatalogDataPacksAndQueries.js`) |

### P0 — Scaling and reliability

_No open items._

---

### P1 — Module size and coupling

### [DONE] Graph canvas — `useGraphCanvasInput` decomposition (Wave G1)
- **Area:** [`hooks/useGraphCanvasInput.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasInput.js) (facade) + [`hooks/graphCanvasInput/`](../../ui/src/components/graph/canvas/hooks/graphCanvasInput/) (`hoverPick`, `pointerDown`, `pointerMove`, `pointerUp`, `clickSelection`, `hitTestContext`, `constants`); seam table in [`canvas/README.md`](../../ui/src/components/graph/canvas/README.md).
- **Issue:** After `useGraphCanvasMvpController` split, pointer/drag/hover/selection and label-bridge logic remain in one dense hook — highest coupling with physics pause and `activeForLabelSetRef`.
- **Proposal:** Split by seam (e.g. pointer session + drag, hover pick queue, selection dispatch) with unchanged public contract to `useGraphCanvasMvpController`; extend canvas vitest where behavior is currently implicit.
- **Acceptance:** hook(s) at most ~300 LOC each or explicit submodules; graph canvas hook tests + existing draw/hit-test suite green.
- **Raised:** 2026-05-14 (post-controller decomposition audit)
- **Done:** 2026-05-14 — facade composes submodules; public API unchanged for `useGraphCanvasMvpController`; Vitest for `hoverPick` (RAF vs drag-moved), `pointerMove` (threshold / pan / hover delegate), `pointerUp` (`dispatchGraphCanvasPointerUp` when idle), `hitTestContext`, integration tap→`onCanvasClick`; `npm run lint` (no new errors).

### [OPEN] Graph workspace / flow shell — panel, toolbar, flow view, node detail
- **Area:** [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx), [`WorkspaceGraphToolbar.jsx`](../../ui/src/components/graph/workspace/WorkspaceGraphToolbar.jsx), [`GraphFlowView.jsx`](../../ui/src/components/graph/flow/GraphFlowView.jsx), [`GraphNodeDetailSection.jsx`](../../ui/src/components/graph/shell/detail/GraphNodeDetailSection.jsx)
- **Issue:** Each file ~340–390 LOC — layout, data hooks, and chrome evolve together; risk of duplicating canvas contracts when adding filters or detail panes.
- **Proposal:** Extract `use*` data hooks and presentational sections per file; keep graph/canvas vs workspace shell boundary documented (extend [`canvas/README.md`](../../ui/src/components/graph/canvas/README.md) or add `workspace/README.md` if a second seam map helps).
- **Acceptance:** measurable LOC drop per slice or documented submodule map; workspace/graph vitest where present stays green.
- **Raised:** 2026-05-14 (frontend landscape audit)

### [OPEN] Workspace page — `useWorkspacePageCore` + `workspaceStore` API surface
- **Area:** [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx), [`utils/workspaceStore.js`](../../ui/src/utils/workspaceStore.js)
- **Issue:** Page core ~381 LOC orchestrates navigation, ingest, papers, errors; `workspaceStore` ~399 LOC bundles many HTTP entrypoints — hard to test in isolation and easy to regress ingest timeouts vs reads.
- **Proposal:** Slice `useWorkspacePageCore` by concern (bootstrap vs ingest vs papers/summary); split `workspaceStore` into focused modules + thin re-export facade (same import path for callers).
- **Acceptance:** no single file above ~320 LOC without explicit submodule seams; targeted workspace page tests + smoke paths for ingest/workspace load unchanged.
- **Raised:** 2026-05-14 (frontend landscape audit)

### [OPEN] Benchmark — case inspector shell + run-group hook
- **Area:** [`BenchmarkCaseInspectorShell.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx), [`useBenchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunGroup.js)
- **Issue:** Inspector shell ~377 LOC; run-group hook ~315 LOC — operator UI and polling/state interleave.
- **Proposal:** Extract data hooks (`useBenchmarkCaseInspector*` already partial — extend), split shell sections; isolate run-group polling/prefs behind a narrow hook API.
- **Acceptance:** vitest under `pages/BenchmarkPage/` green; inspector usable with same routes/query contract.
- **Raised:** 2026-05-14 (frontend landscape audit)

### [OPEN] Ask — orchestration + session state (post-reorg continuation)
- **Area:** [`useAskPanelOrchestration.js`](../../ui/src/components/work/ask/orchestration/useAskPanelOrchestration.js), [`askSessionState.js`](../../ui/src/components/work/ask/session/askSessionState.js), optionally [`useAskPerformAgentSubmit.js`](../../ui/src/components/work/ask/orchestration/useAskPerformAgentSubmit.js)
- **Issue:** Orchestration and session policy remain dense (~270–297 LOC); prior **[DONE]** card already scoped further splits.
- **Proposal:** URL/session sync vs submit pipeline vs stream artifacts; keep imports via [`ask/index.js`](../../ui/src/components/work/ask/index.js); align with rule `frontend-ask-boundary.mdc` when added.
- **Acceptance:** modules trend to at most ~280 LOC or explicit seams; `ask` vitest + `askFlowCompatibility` green.
- **Raised:** 2026-05-14 (deep audit; continues 2026-05-14 Ask **[DONE]** intent)

### [OPEN] Settings — page + storage/LLM panels (incremental)
- **Area:** [`SettingsPage.jsx`](../../ui/src/pages/SettingsPage.jsx), [`StorageSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/StorageSettingsPanel.jsx), [`LlmSettingsPanel.jsx`](../../ui/src/pages/SettingsPage/LlmSettingsPanel.jsx)
- **Issue:** Shell and panels ~284–295 LOC each — acceptable but will grow with new backends; no structural map beyond `storage/` subtrees yet.
- **Proposal:** Incremental extraction only when touching settings (avoid wide refactor); prefer hooks `use*SettingsPanel` per tab.
- **Acceptance:** touched files shrink or gain submodule; `vitest` for `pages/SettingsPage/` green.
- **Raised:** 2026-05-14 (landscape audit)

### [DONE] Graph canvas — `useGraphCanvasMvpController` decomposition (sub-hooks + tests)
- **Area:** [`hooks/useGraphCanvasMvpController.js`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasMvpController.js) + [`canvas/README.md`](../../ui/src/components/graph/canvas/README.md)
- **Issue:** After `GraphCanvasMvp` shell split, orchestration still lived in one ~520 LOC hook.
- **Proposal:** Split by seam: derived model, world/sim buffers + lifecycle, paint controller, context menu, view actions, pure node-click routing; keep `invokeCanvasRedrawRef` bridge and hook order (force sim before topology reseed) intact.
- **Acceptance:** explicit submodule boundaries + seam map updated; targeted vitest (controller smoke, view-actions restart, routing, storage dense-hint, derived pure helpers) + simulation contract tests green.
- **Raised:** 2026-05-14 (post GraphCanvasMvp / force-sim split)
- **Done:** 2026-05-14 — controller ~355 LOC as composition layer; new modules under `hooks/`; `npm run lint` on touched files + vitest graph/sim subset green.

### [DONE] Graph canvas — remaining large leaf modules (MVP + force integrator)
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx), [`graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js), [`useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx), [`GraphTypeLegend.jsx`](../../ui/src/components/graph/shell/GraphTypeLegend.jsx)
- **Issue:** Folder layout under `components/graph/` is good, but several leaves remain ~400–600 LOC — perf and feature work still land in dense files (not P0 unless perf regressions; P1 for maintainability).
- **Proposal:** Scoped extractions per file (e.g. draw phases from `graphCanvasDraw`, legend sections from `GraphTypeLegend`, simulation tuning from `useScienceGraphForceSimulation`) with existing vitest safety nets.
- **Acceptance:** each targeted file measurably smaller after a pass; no behavior change without explicit product sign-off; graph vitest subset green.
- **Raised:** 2026-05-14 (frontend backlog audit)
- **Progress 2026-05-14:** `graphCanvasDraw` → thin facade + [`canvas/draw/`](../../ui/src/components/graph/canvas/draw/) (constants, label policy, edges/nodes/labels, hit-test); `useScienceGraphForceSimulation` → [`scienceGraphSimulationBounds.js`](../../ui/src/hooks/graph/scienceGraphSimulationBounds.js) + [`scienceGraphSimulationTune.js`](../../ui/src/hooks/graph/scienceGraphSimulationTune.js); `GraphTypeLegend` → [`GraphTypeLegendCollapses.jsx`](../../ui/src/components/graph/shell/GraphTypeLegendCollapses.jsx) + [`graphTypeLegendConfig.js`](../../ui/src/components/graph/shell/graphTypeLegendConfig.js); `GraphWorkspacePanel` → [`graphWorkspacePanelStorage.js`](../../ui/src/components/graph/workspace/graphWorkspacePanelStorage.js).
- **Done:** 2026-05-14 — `GraphCanvasMvp` → thin shell + [`useGraphCanvasMvpController`](../../ui/src/components/graph/canvas/hooks/useGraphCanvasMvpController.js); seam map [`canvas/README.md`](../../ui/src/components/graph/canvas/README.md); force hook → [`scienceGraphSimulationResetPolicy.js`](../../ui/src/hooks/graph/scienceGraphSimulationResetPolicy.js) + [`scienceGraphSimulationGraphPrep.js`](../../ui/src/hooks/graph/scienceGraphSimulationGraphPrep.js) + [`scienceGraphSimulationTickEngine.js`](../../ui/src/hooks/graph/scienceGraphSimulationTickEngine.js); vitest `src/hooks/graph/*Simulation*.test.js` + graph canvas/shell subset green.

### [DONE] Settings / Benchmark — page shell and tab orchestration
- **Area:** [`useRunTab.js`](../../ui/src/pages/BenchmarkPage/useRunTab.js) + [`useBenchmarkServerBenchmarkSnapshot.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkServerBenchmarkSnapshot.js) / [`useBenchmarkRunLabCaseLists.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunLabCaseLists.js) / [`useBenchmarkRunPoll.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunPoll.js) / [`useRunLabExperimentPresetFromUrl.js`](../../ui/src/pages/BenchmarkPage/useRunLabExperimentPresetFromUrl.js), [`StorageBackendSections.jsx`](../../ui/src/pages/SettingsPage/StorageBackendSections.jsx) + [`SettingsPage/storage/`](../../ui/src/pages/SettingsPage/storage/), [`SettingsPage.jsx`](../../ui/src/pages/SettingsPage.jsx) + [`useSettingsPageBootstrap.js`](../../ui/src/pages/SettingsPage/useSettingsPageBootstrap.js) / [`PlaceholderSettingsSection.jsx`](../../ui/src/pages/SettingsPage/PlaceholderSettingsSection.jsx), [`BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) + [`useBenchmarkPageRouting.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkPageRouting.js)
- **Issue:** Page-level modules mix orchestration (state, API, tab wiring) with large inline UI — ~300–390 LOC each and growing risk when adding panels.
- **Proposal:** Extract presentational sections and/or `use*` hooks per tab (Run tab state machine, settings storage sections as composable shells).
- **Acceptance:** each listed file drops below ~300 LOC after a slice or gains a clear sub-module boundary; page behavior unchanged; relevant vitest green.
- **Raised:** 2026-05-14 (frontend backlog audit)
- **Done:** 2026-05-14 — `SettingsPage` bootstrap + placeholder extracted; storage accordions split; `BenchmarkPage` routing in `useBenchmarkPageRouting`; `useRunTab` split into focused hooks; `npm run lint` + `vitest` for `src/pages/SettingsPage/` and `src/pages/BenchmarkPage/` green.

Note: further workspace-page split is tracked as **[OPEN] Workspace page — `useWorkspacePageCore` + `workspaceStore` API surface** (same scope as the former “optional future split” line).

### [DONE] Work/agent runtime presentation split (`agentRunViewModel` + `AgentLiveStatus`)
- **Area:** [`components/work/agent/agentRunViewModel.js`](../../ui/src/components/work/agent/agentRunViewModel.js) (facade) + [`components/work/agent/agentRunViewModel/`](../../ui/src/components/work/agent/agentRunViewModel/), [`components/work/agent/AgentLiveStatus.jsx`](../../ui/src/components/work/agent/AgentLiveStatus.jsx) + adjacent `AgentLiveStatus*.jsx` / `agentLiveStatus*.js` / `useAgentLiveStatusExplainAutoOpen.js`
- **Issue:** `agentRunViewModel.js` was ~966 LOC; `AgentLiveStatus.jsx` ~341 LOC — combined headline, aggregation, presentation, and dense JSX.
- **Proposal:** Split view-model by concern; keep `agentRunViewModel.js` as re-export facade. Extract `AgentLiveStatus` sections (decision block, headline region, chips, stream panels) and keyframes / chrome derivation.
- **Acceptance:** no single work/agent module > ~400 LOC for core runtime presentation; existing tests (`agentRunViewModel*.test.js`, `AgentLiveStatus*.test.jsx`) remain green; adding a new stream event class touches one focused mapper module.
- **Raised:** 2026-05-14 (frontend architecture pass)
- **Done:** 2026-05-14 — split into `streamTaxonomy`, `streamFormat`, `streamAggregation`, `streamHeadline`, `progress`, `explanations`, `presentation`, `runState`; `AgentLiveStatus` shell + subcomponents + `deriveAgentLiveStatusChrome`; `vitest` green for `src/components/work/agent/`.

### [DONE] Benchmark page domain model boundaries (catalog / launch / analysis)
- **Area:** [`pages/BenchmarkPage/catalog/`](../../ui/src/pages/BenchmarkPage/catalog/) (split from [`experimentCatalog.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.js) facade), [`pages/BenchmarkPage/analysis/`](../../ui/src/pages/BenchmarkPage/analysis/) (split from [`benchmarkAnalysisModel.js`](../../ui/src/pages/BenchmarkPage/benchmarkAnalysisModel.js) facade), [`pages/BenchmarkPage/launch/`](../../ui/src/pages/BenchmarkPage/launch/) (prefs + run payload; [`benchmarkLauncherConfig.js`](../../ui/src/pages/BenchmarkPage/benchmarkLauncherConfig.js) re-exports), [`pages/BenchmarkPage/useRunTab.js`](../../ui/src/pages/BenchmarkPage/useRunTab.js)
- **Issue:** Benchmark domain has multiple ~320–488 LOC modules where catalog metadata, launch policy and analysis transforms evolve together; this creates high coupling between UI copy, run controls and result math.
- **Proposal:** Introduce explicit sublayers under `pages/BenchmarkPage/`: `catalog/`, `launch/`, `analysis/` with clear interfaces (pure data contracts for transforms, no UI deps in models). Keep page shells thin and compose these domain modules.
- **Acceptance:** each benchmark domain file <= ~250–300 LOC or explicitly delegated; page shell changes do not require edits in analysis/launcher internals; benchmark tab tests stay green.
- **Raised:** 2026-05-14 (frontend architecture pass)
- **Progress 2026-05-14:** `experimentCatalog` → `catalog/*` + thin facade; `benchmarkAnalysisModel` → `analysis/*` + thin facade; `useRunTab` orchestration hooks extracted; launcher logic → `launch/*` + `benchmarkLauncherConfig.js` facade (~20 LOC).
- **Done:** 2026-05-14 — `experimentCatalogData` split into [`experimentCatalogExperimentsPartA.js`](../../ui/src/pages/BenchmarkPage/catalog/experimentCatalogExperimentsPartA.js) / [`experimentCatalogExperimentsPartB.js`](../../ui/src/pages/BenchmarkPage/catalog/experimentCatalogExperimentsPartB.js) + [`experimentCatalogExperimentsBundle.js`](../../ui/src/pages/BenchmarkPage/catalog/experimentCatalogExperimentsBundle.js) + [`experimentCatalogDataPacksAndQueries.js`](../../ui/src/pages/BenchmarkPage/catalog/experimentCatalogDataPacksAndQueries.js); single-run launch → [`runTab/runTabSingleRunLaunch.js`](../../ui/src/pages/BenchmarkPage/runTab/runTabSingleRunLaunch.js); `vitest` for `src/pages/BenchmarkPage/` green.

---

### P2 — Product UX and polish

### [OPEN] ESLint react-refresh — non-component exports in JSX modules
- **Area:** [`MarkdownViewCore.jsx`](../../ui/src/components/work/markdown/MarkdownViewCore.jsx), [`TrustSignalPanel.jsx`](../../ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx)
- **Issue:** `react-refresh/only-export-components` warnings during `npm run lint` — constants/helpers exported next to components break Fast Refresh ergonomics.
- **Proposal:** Move shared helpers/constants to adjacent `*.js` files; keep JSX modules component-only when touched.
- **Acceptance:** warnings cleared for listed files without behavior change; `npm run lint` green on warnings-as-errors if enabled later.
- **Raised:** 2026-05-14 (lint audit)

### [DONE] Document chatDetailLevel default migration to "simple"
- **Area:** [`ui/src/components/work/ask/chat/chatUiPreferences.js`](../../ui/src/components/work/ask/chat/chatUiPreferences.js), [`AgentLiveStatus.jsx`](../../ui/src/components/work/agent/AgentLiveStatus.jsx).
- **Issue:** Default `chatDetailLevel` is `"simple"` in [`useChatDetailLevel`](../../ui/src/components/work/ask/chat/useChatDetailLevel.js); `AgentLiveStatus` now hides the recent-lines / reasoning collapses in this mode (Cursor-like progress, 2026-05-05). Returning users may not realize there is a "Detailed" toggle.
- **Proposal:** add a one-shot tooltip / changelog hint near `ChatDetailLevelToggle` (or in the chat clearance dialog) on the first session after migration; alternatively, default to `"detailed"` for sessions that previously had no preference recorded but only when accessibility / power-user mode is on (decided per UX review).
- **Acceptance:** users can discover the «Подробный» toggle from the Ask chrome without reading docs; localized RU + EN strings; vitest covers the discovery affordance.
- **Raised:** 2026-05-05 (Cursor-like agent progress)
- **Done:** 2026-05-14 — one-shot `Tooltip` on detail toggle when simple + not dismissed; `readChatDetailDiscoveryHintDismissed` / `writeChatDetailDiscoveryHintDismissed` in `chatUiPreferences.js`; auto-dismiss storage when switching to detailed; i18n `chat.chrome.detailDiscoveryHint` (EN/RU); [`AskPanelChrome.detailHint.test.jsx`](../../ui/src/components/work/ask/shell/AskPanelChrome.detailHint.test.jsx).

Other follow-ups only if product revisits: unified ingest conflict **API** + drawer (backend backlog); optional dedicated **run-group** REST if orchestrator exposes it; repeat i18n grep after large UI additions per [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md).
