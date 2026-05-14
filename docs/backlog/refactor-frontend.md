# Frontend refactor backlog

Planned structural work under `ui/` (components, routing, state, API client), not routine ESLint fixes.

## How to use

- Add items during **implementation** when you defer a refactor.
- Execute items in a dedicated **refactor pass** when asked.
- Prefer small vertical slices (one feature area or one layer, e.g. `services/` only).

## Completed (archive)

Длинная таблица закрытых тем (2026-04 — 2026-05-14) **убрана**: она дублировала git-историю, спеки и ADR и не продвигала открытые задачи. Детали — в `docs/specs/`, `docs/analysis/`, ADR, коммитах.

**Что ещё полезно помнить при планировании:** волна **WF-2026-05 по Ask** (session model/storage, оркестратор + вспомогательные хуки + `askPanelOrchestrationContract`, scroll/empty в треде, шард тестов `AskAnswerPanel`) закрыта **2026-05-14**. Follow-up этой же даты: каталог `components/work/ask` разложен по доменам (`shell/`, `session/`, `orchestration/`, `chat/`, `answer/`, `forms/`) + добавлен фасад `ask/index.js` для стабильного публичного входа. **2026-05-14 (second pass):** `askSessionPolicy` / `askSessionDigest` / `askSessionConstants`; публичный слой `components/work/agent/index.js` для Ask↔Agent; оркестратор разнесён (`askAgentUiErrors`, `useAskPanelClipboard`, `useAskPanelStreamArtifacts`, `askPanelScopePresentation`); `ChatContextPicker*` + `typedBlocks/*`; Vitest для новых границ.

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

**Open queue:** дальше по структуре UI — остаётся **P1** карточка по графу (**`GraphCanvasMvp`** и опционально дальнейший split симуляции). Benchmark domain slice и P2 hint закрыты **2026-05-14**. Новый долг — новым scoped-пунктом в Queue.

### Stage baseline (next structural pass, 2026-05-14)

Pre-refactor line counts (approximate targets ~250–300 LOC per leaf or explicit submodule seams):

| Path | LOC (pre) | LOC (post 2026-05-14 pass) |
| --- | ---: | ---: |
| `ui/src/components/graph/canvas/GraphCanvasMvp.jsx` | 599 | 599 (unchanged; next slice) |
| `ui/src/components/graph/canvas/graphCanvasDraw.js` | 514 | 27 (facade → `canvas/draw/*`) |
| `ui/src/hooks/graph/useScienceGraphForceSimulation.js` | 515 | 477 (+ `scienceGraphSimulationBounds.js`, `scienceGraphSimulationTune.js`) |
| `ui/src/components/graph/workspace/GraphWorkspacePanel.jsx` | 426 | 390 (+ `graphWorkspacePanelStorage.js`) |
| `ui/src/components/graph/shell/GraphTypeLegend.jsx` | 432 | 262 (+ `GraphTypeLegendCollapses.jsx`, `graphTypeLegendConfig.js`) |
| `ui/src/pages/BenchmarkPage/useRunTab.js` | 287 | 255 (+ `runTab/runTabSingleRunLaunch.js`) |
| `ui/src/pages/BenchmarkPage/catalog/experimentCatalogData.js` | 277 | 37 (facade + `experimentCatalogExperimentsPart*`, bundle, `experimentCatalogDataPacksAndQueries.js`) |

### P0 — Scaling and reliability

_No open items._

---

### P1 — Module size and coupling

### [OPEN] Graph canvas — remaining large leaf modules
- **Area:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx), [`graphCanvasDraw.js`](../../ui/src/components/graph/canvas/graphCanvasDraw.js), [`useScienceGraphForceSimulation.js`](../../ui/src/hooks/graph/useScienceGraphForceSimulation.js), [`GraphWorkspacePanel.jsx`](../../ui/src/components/graph/workspace/GraphWorkspacePanel.jsx), [`GraphTypeLegend.jsx`](../../ui/src/components/graph/shell/GraphTypeLegend.jsx)
- **Issue:** Folder layout under `components/graph/` is good, but several leaves remain ~400–600 LOC — perf and feature work still land in dense files (not P0 unless perf regressions; P1 for maintainability).
- **Proposal:** Scoped extractions per file (e.g. draw phases from `graphCanvasDraw`, legend sections from `GraphTypeLegend`, simulation tuning from `useScienceGraphForceSimulation`) with existing vitest safety nets.
- **Acceptance:** each targeted file measurably smaller after a pass; no behavior change without explicit product sign-off; graph vitest subset green.
- **Raised:** 2026-05-14 (frontend backlog audit)
- **Progress 2026-05-14:** `graphCanvasDraw` → thin facade + [`canvas/draw/`](../../ui/src/components/graph/canvas/draw/) (constants, label policy, edges/nodes/labels, hit-test); `useScienceGraphForceSimulation` → [`scienceGraphSimulationBounds.js`](../../ui/src/hooks/graph/scienceGraphSimulationBounds.js) + [`scienceGraphSimulationTune.js`](../../ui/src/hooks/graph/scienceGraphSimulationTune.js); `GraphTypeLegend` → [`GraphTypeLegendCollapses.jsx`](../../ui/src/components/graph/shell/GraphTypeLegendCollapses.jsx) + [`graphTypeLegendConfig.js`](../../ui/src/components/graph/shell/graphTypeLegendConfig.js); `GraphWorkspacePanel` → [`graphWorkspacePanelStorage.js`](../../ui/src/components/graph/workspace/graphWorkspacePanelStorage.js). **Remaining:** [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/canvas/GraphCanvasMvp.jsx) ~599 LOC; optional further shrink of `useScienceGraphForceSimulation` integrator body.

### [DONE] Settings / Benchmark — page shell and tab orchestration
- **Area:** [`useRunTab.js`](../../ui/src/pages/BenchmarkPage/useRunTab.js) + [`useBenchmarkServerBenchmarkSnapshot.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkServerBenchmarkSnapshot.js) / [`useBenchmarkRunLabCaseLists.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunLabCaseLists.js) / [`useBenchmarkRunPoll.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunPoll.js) / [`useRunLabExperimentPresetFromUrl.js`](../../ui/src/pages/BenchmarkPage/useRunLabExperimentPresetFromUrl.js), [`StorageBackendSections.jsx`](../../ui/src/pages/SettingsPage/StorageBackendSections.jsx) + [`SettingsPage/storage/`](../../ui/src/pages/SettingsPage/storage/), [`SettingsPage.jsx`](../../ui/src/pages/SettingsPage.jsx) + [`useSettingsPageBootstrap.js`](../../ui/src/pages/SettingsPage/useSettingsPageBootstrap.js) / [`PlaceholderSettingsSection.jsx`](../../ui/src/pages/SettingsPage/PlaceholderSettingsSection.jsx), [`BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) + [`useBenchmarkPageRouting.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkPageRouting.js)
- **Issue:** Page-level modules mix orchestration (state, API, tab wiring) with large inline UI — ~300–390 LOC each and growing risk when adding panels.
- **Proposal:** Extract presentational sections and/or `use*` hooks per tab (Run tab state machine, settings storage sections as composable shells).
- **Acceptance:** each listed file drops below ~300 LOC after a slice or gains a clear sub-module boundary; page behavior unchanged; relevant vitest green.
- **Raised:** 2026-05-14 (frontend backlog audit)
- **Done:** 2026-05-14 — `SettingsPage` bootstrap + placeholder extracted; storage accordions split; `BenchmarkPage` routing in `useBenchmarkPageRouting`; `useRunTab` split into focused hooks; `npm run lint` + `vitest` for `src/pages/SettingsPage/` and `src/pages/BenchmarkPage/` green.

Optional future split: [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx) only when new tabs/flows land (~381 LOC after extractions).

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

### [DONE] Document chatDetailLevel default migration to "simple"
- **Area:** [`ui/src/components/work/ask/chat/chatUiPreferences.js`](../../ui/src/components/work/ask/chat/chatUiPreferences.js), [`AgentLiveStatus.jsx`](../../ui/src/components/work/agent/AgentLiveStatus.jsx).
- **Issue:** Default `chatDetailLevel` is `"simple"` in [`useChatDetailLevel`](../../ui/src/components/work/ask/chat/useChatDetailLevel.js); `AgentLiveStatus` now hides the recent-lines / reasoning collapses in this mode (Cursor-like progress, 2026-05-05). Returning users may not realize there is a "Detailed" toggle.
- **Proposal:** add a one-shot tooltip / changelog hint near `ChatDetailLevelToggle` (or in the chat clearance dialog) on the first session after migration; alternatively, default to `"detailed"` for sessions that previously had no preference recorded but only when accessibility / power-user mode is on (decided per UX review).
- **Acceptance:** users can discover the «Подробный» toggle from the Ask chrome without reading docs; localized RU + EN strings; vitest covers the discovery affordance.
- **Raised:** 2026-05-05 (Cursor-like agent progress)
- **Done:** 2026-05-14 — one-shot `Tooltip` on detail toggle when simple + not dismissed; `readChatDetailDiscoveryHintDismissed` / `writeChatDetailDiscoveryHintDismissed` in `chatUiPreferences.js`; auto-dismiss storage when switching to detailed; i18n `chat.chrome.detailDiscoveryHint` (EN/RU); [`AskPanelChrome.detailHint.test.jsx`](../../ui/src/components/work/ask/shell/AskPanelChrome.detailHint.test.jsx).

Other follow-ups only if product revisits: unified ingest conflict **API** + drawer (backend backlog); optional dedicated **run-group** REST if orchestrator exposes it; repeat i18n grep after large UI additions per [`docs/specs/ui-i18n-guidelines.md`](../specs/ui-i18n-guidelines.md).
