# Graph navigation dead-end: HashRouter conflict analysis and remediation plan

**Date:** 2026-04-28  
**Scope:** frontend navigation around standalone `GraphPage`, route state, hash-based deep links, and shell consistency under `ui/`.  
**Related:** [`graph-work-vs-workspace-unification-dry-plan-2026-04-28.md`](./graph-work-vs-workspace-unification-dry-plan-2026-04-28.md), [`docs/backlog/refactor-frontend.md`](../backlog/refactor-frontend.md).

---

## 1. Executive summary

Observed symptom: after opening the `Граф` surface, users report that they cannot reliably move to other tabs / sections.

This is **not** explained by product intent in the current code. `GraphPage` is mounted inside the same top-level shell as the rest of the app, so it should remain navigable through the shared drawer and route model.

The main issue is a **navigation boundary conflict**:

1. the app uses **`HashRouter`** for primary routing;
2. **(Phase 1 done, 2026-04-28)** Standalone graph selection is no longer written with manual `replaceState` on the hash; [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) uses React Router `setSearchParams` (see §2.2 and Phase 1 below). *Historical root cause:* the graph page used to treat the hash as private UI transport alongside the router.
3. the workspace-era concept of `tab=graph` still exists in compatibility code and tests;
4. the graph surface itself has already been promoted to a **standalone route** (`/graph`).

That combination historically created a fragile state model where one mechanism (`location.hash`) could serve **two different responsibilities** (routing vs graph selection). **Phase 1 (2026-04-28)** removes that split for standalone graph selection by routing `node` / `edge` updates only through React Router `searchParams`. **Phase 2 (2026-04-28)** aligns IA (standalone tool links + legacy `tab=` redirect). **Phase 3 (2026-04-28)** and **Phase 4 (2026-04-28)** — central routing helpers + shell smoke tests; prod-only issues (canvas overlays, real API) still benefit from the manual QA paths in test file headers.

So the immediate symptom is a navigation bug, but the underlying cause was an **architectural problem in the frontend routing layer** (being closed incrementally; graph selection path is addressed in Phase 1).

---

## 2. What the code says today

### 2.1 `GraphPage` is not a separate app

`GraphPage` is rendered inside the shared `DashboardLayout` route tree, not outside the shell:

- `ui/src/main.jsx` uses `HashRouter`
- `ui/src/App.jsx` mounts `/graph` under `<Route element={<DashboardLayout />}>`
- `ui/src/components/layout/DashboardLayout/DashboardLayout.jsx` always renders the shared drawer + outlet

Conclusion: the graph screen is supposed to participate in normal shell navigation.

### 2.2 Graph selection and the router (historical vs current)

**Historical (pre–Phase 1, 2026-04-28):** standalone graph selection was updated through `replaceHashTraceabilitySelection()` in `ui/src/components/work/traceabilityState.js`, which bypassed React Router and used `window.history.replaceState(...)` on the hash, plus a custom event so consumers could re-read the URL. Under `HashRouter` that coupled route transport and selection in one fragile string.

**Current:** [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) writes `node` / `edge` only through **`setSearchParams` + `mergeTraceabilityParams(..., { includeTab: false })` with `{ replace: true }`**, so React Router owns location state. The old helper and `useHashTraceabilityGraphSelection` were removed (see Phase 1 below).

### 2.3 Legacy workspace-tab values (compatibility-only after Phase 2, 2026-04-28)

`ui/src/pages/WorkspacePage/utils/workContext.js` keeps **`WORKSPACE_TAB_SLUGS`** and **`normalizeWorkspaceTab`** so old `tab=` query strings and traceability parsing remain valid; workspace shell links omit `tab=` (`buildWorkspacePath` ignores the tab argument).

**Phase 2:** in-app navigation uses standalone routes (`READER_PATH` / `GRAPH_PATH` / `CHAT_PATH` in [`paths.js`](../../ui/src/routes/paths.js)); legacy `/workspace?tab=reader|graph|ask` is **`replace` redirected** via [`legacyWorkspaceTabRedirectTarget`](../../ui/src/components/work/traceabilityState.js) in [`useWorkspacePageCore.jsx`](../../ui/src/pages/WorkspacePage/useWorkspacePageCore.jsx). Deprecated [`buildWorkspaceTracePath`](../../ui/src/components/work/traceabilityState.js) remains for tests and rare compatibility.

Product routes:

- `/workspace`
- `/reader`
- `/graph`
- `/chat`
- `/evidence`

---

## 3. Root cause analysis

## 3.1 Primary cause

The standalone graph route is implemented on top of a router that uses `#...` for navigation, while graph selection also stores its own state in `#...`.

That makes the graph page depend on a shared global resource (`window.location.hash`) that should belong only to the router.

## 3.2 Secondary cause

The app is between two information architectures:

- **old model:** workspace-centric tabs (`tab=graph`, `tab=reader`, `tab=ask`);
- **new model:** standalone tool surfaces with dedicated routes.

The migration is only partially complete:

- routes already moved;
- compatibility layer remains;
- tests still assert legacy tab behavior;
- graph deep-link state still assumes hash-level control.

## 3.3 Why this surfaces specifically on `Graph`

Other pages mostly use `useSearchParams()` in the normal router flow.

`GraphPage` is special because it needs:

- deep links to selected nodes and edges;
- frequent interaction updates from canvas / side panel;
- persistence of focus context between graph interactions.

That led to a local optimization which is reasonable in isolation, but unsafe in combination with `HashRouter`.

---

## 4. Is this architectural or just a bug?

It is **both**, but primarily an **architectural issue with a user-facing bug symptom**.

### Why it is more than a local bug

- The problem is not isolated to one broken button or one missing `Link`.
- The failure comes from the contract between routing, deep-linking, and graph-local state.
- The code currently mixes active product routes with compatibility-era tab semantics.
- The same underlying conflict can keep reappearing as regressions in navigation, browser history, deep links, or selection restore.

### Why it is not a full rewrite situation

- The shell structure is already sound.
- The standalone route split is directionally correct.
- Most of the problem is concentrated in the navigation/state boundary around `GraphPage`.

So this is a **medium-sized architectural cleanup**, not a platform rewrite.

---

## 5. Desired target architecture

The frontend should converge on the following contract:

1. **Router owns navigation state.**
   - Route identity lives in React Router only.

2. **Graph owns graph selection state.**
   - Node / edge selection should not compete with router transport.

3. **Legacy workspace tabs remain compatibility-only.**
   - They may be parsed for old URLs, but they should not remain first-class internal abstractions.

4. **Standalone tools are explicit.**
   - `Workspace` is a corpus/workspace shell.
   - `Reader`, `Graph`, `Chat`, `Evidence` are tool surfaces with their own routes.

5. **Deep-link behavior is documented.**
   - If graph selection is preserved in the URL, it should be done through a single documented mechanism that does not fight the router.

---

## 6. Remediation plan

### Phase 0 — Stabilize and reproduce

**Status:** [DONE] 2026-04-28

**Goal:** capture the exact user-visible failure and prevent more silent regressions.

Tasks:

- [x] Reproduce the issue from the drawer and from paper-row actions.
  - **Comment:** Deterministic **manual QA** steps (paths A/B: drawer → graph → leave; workspace paper-row → graph → leave) are documented in the file header of [`ui/src/graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx). Use them when validating prod-only behaviour; the automated harness does not replace a human pass on the full shell.
- [x] Add a focused frontend test that covers:
  - open `/graph`;
  - update graph selection;
  - navigate to another primary route;
  - confirm navigation still succeeds.
  - **Comment:** Implemented as [`ui/src/graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx): `HashRouter` (same `future` flags as [`ui/src/main.jsx`](../../ui/src/main.jsx)) + graph selection update via `useSearchParams` / `mergeTraceabilityParams` (same contract as post–Phase 1 [`GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx)) + `Link` to `/chat`, with assertions on both `window.location.hash` and `useLocation().pathname` via a small `PathnameEcho` helper. This is **variant B** (minimal route tree, not full `DashboardLayout` / `GraphPage`).
- [x] Confirm whether the failure is:
  - blocked click handling,
  - broken `Link`,
  - stale router location,
  - bad hash mutation,
  - or browser-history pollution.
  - **Comment:** The isolated test **passes** in CI (jsdom): `Link` after a selection URL update does not break `HashRouter` in this minimal setup. **Triage bias:** if users still hit a dead-end on the real graph surface, prioritise **blocked click handling** (canvas/modal/pointer-events), **stale router state in the full shell**, or **deployment `basename` / `/ui/`** differences; basic hash query parsing remains covered by [`ui/src/components/work/traceabilityState.test.js`](../../ui/src/components/work/traceabilityState.test.js). The automated test does **not** set Vite `base: "/ui/"` — add a dedicated smoke later if prod issues persist only under static mount.

Acceptance:

- [x] one deterministic reproduction case exists in test or documented manual QA steps.

### Phase 1 — Stop using hash as a dual-purpose channel

**Status:** [DONE] 2026-04-28

**Goal:** remove the main architectural conflict.

**What we implemented**

- [x] **Router-owned selection URL:** [`ui/src/pages/GraphPage.jsx`](../../ui/src/pages/GraphPage.jsx) updates `node` / `edge` only via `setSearchParams((prev) => mergeTraceabilityParams(prev, …, { includeTab: false }), { replace: true })`. Functional `setSearchParams` avoids stale closures on rapid canvas clicks. **`includeTab: false`** keeps standalone `/graph?…` URLs from gaining a workspace `tab=` query (see `buildTraceabilityParams` default in [`traceabilityState.js`](../../ui/src/components/work/traceabilityState.js)).
- [x] **Removed dual-purpose hash writes:** deleted `replaceHashTraceabilitySelection`, `readTraceabilityGraphSelectionFromHash`, `mergeTraceabilityStateWithHashSelection`, `TRACEABILITY_HASH_SELECTION_EVENT`, and the `useHashTraceabilityGraphSelection` hook module (`ui/src/components/work/useHashTraceabilityGraphSelection.js`, removed). Selection deep links still use the same query keys (`node`, `edge`); they are now always driven through React Router’s search params under `HashRouter`.
- [x] **Tests:** [`graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx) uses the same contract as `GraphPage`; [`traceabilityState.test.js`](../../ui/src/components/work/traceabilityState.test.js) includes a merge case for `{ includeTab: false }` on graph-like URLs.

Preferred direction (original menu — **choice**):

- [x] move graph selection off raw `window.location.hash` mutation / manual `replaceState` on the route payload;
- [x] keep route changes inside React Router state;
- [x] use: **`searchParams` via the router with `replace: true`** per selection update. *Deferred unless profiling requires it:* debounced `setSearchParams` only (see comment in `GraphPage.jsx` next to selection handlers).
- [ ] not in this slice: in-memory selection + only an explicit “copy deep link” action as the sole URL writer.

Decision note:

- [x] **`HashRouter` remains** for deployment; graph-local selection **no longer** bypasses the router or pretends to own hash transport outside RR.
- [ ] **`BrowserRouter`** migration stays a **separate project** (unchanged).

Acceptance:

- [x] No `GraphPage` selection path depends on `window.history.replaceState(...nextHash...)` for routine clicks (verified in code review; guard test in `graphNavigationHashRouter.test.jsx`).

### Phase 2 — Finish the IA migration

**Status:** [DONE] 2026-04-28

**Goal:** make the current product model explicit in code.

Tasks:

- [x] reduce `WORKSPACE_TAB_SLUGS` to compatibility-only handling (documented in `workContext.js`; slugs kept for legacy URL parse + redirect);
- [x] remove internal dependencies that still treat `graph` / `ask` / `reader` as workspace shell tabs (UI links use `buildStandaloneTracePath` / `buildStandaloneChatPath`; `buildWorkspaceTracePath` marked `@deprecated`);
- [x] review tests that encode the old mental model and rewrite them around canonical routes (`traceabilityState.test.js`, `askFlowCompatibility.test.js`, `workContext.test.js`);
- [x] legacy `/workspace?tab=reader|graph|ask` → `legacyWorkspaceTabRedirectTarget` + `replace` navigate in `useWorkspacePageCore.jsx`;
- [x] removed unused `persistWorkspaceTab` / `getLastWorkspaceTab` / `LAST_WORK_TAB_KEY`.

Acceptance:

- [x] the codebase has one clear answer to the question “is Graph a workspace tab or a standalone tool?”: it is a standalone tool.

### Phase 3 — Centralize route + deep-link helpers

**Status:** [DONE] 2026-04-28 — `ui/src/routing/` (`queryKeys.js`, `graphPageQuery.js`, `index.js`), `WORKSPACE_PATH` / `EVIDENCE_PATH` in `paths.js`, `workspacePageUrls` uses canonical traceability builders, parity tests.

**Goal:** remove fragmented URL logic.

Tasks:

- define one small route/deep-link module for:
  - canonical route builders;
  - route compatibility parsing;
  - graph deep-link schema;
  - workspace-context propagation rules.
- document which params are navigation scope vs which are local tool context.

Acceptance:

- URL building for graph navigation is not split across unrelated helpers and ad hoc hash logic.

### Phase 4 — UX hardening

**Status:** [DONE] 2026-04-28

**Goal:** make navigation failures obvious during development and harder to reintroduce.

Tasks:

- [x] add smoke coverage for drawer navigation from `/graph`;
- [x] verify browser back/forward behavior after graph interactions (automated + note below);
- [x] manual validate (local dev + Playwright MCP — 2026-04-28; prod nginx URL shape still worth a smoke):
  - [x] open graph from workspace;
  - [x] pick node/edge (deep link / paper row graph; canvas click not required for this pass);
  - [x] switch to reader/chat/workspaces;
  - [x] refresh;
  - [x] use back button.
- **Manual QA (2026-04-28, Playwright MCP + local Vite):** `npm run dev` (port **5174** when 5173 busy), base `http://127.0.0.1:5174/ui/` + hash routes; API via Vite proxy. **Path A:** `/workspaces` → drawer **Graph** → workspace graph with `node=` in URL → drawer **Chat** (`#/chat?workspace_id=…`) → drawer **Graph** again — shell navigable. **Back:** after graph (`node=`…), **Chat**, browser **Back** restored `#/graph?…&node=…`. **Path B:** `/workspace?workspace_id=…` (Object Detection workspace) → first row **Open paper graph** → `#/graph?work_id=…&workspace_id=…&node=…` → drawer **Reader** — OK; Playwright reported **0 console errors** on Reader transition. **Refresh:** `location.reload()` on graph deep link — same hash/query, graph shell still loads. Vitest variant B + C remain green in CI.

**What we implemented**

- **Variant C (shell):** [`ui/src/graphNavigationDashboardShell.test.jsx`](../../ui/src/graphNavigationDashboardShell.test.jsx) — real `DashboardLayout` + `Drawer`, `HashRouter` with the same `future` flags as [`ui/src/main.jsx`](../../ui/src/main.jsx), graph stub applies `setSearchParams(mergeTraceabilityParams(..., { includeTab: false }), { replace: true })`, then drawer **Chat** link; asserts pathname and hash. Mocks `getWorkspace` / `listWorkspaces` only to avoid network during mount; drawer behavior is production code.
- **Back stack:** second test in the same file — after navigate to `/chat`, `history.back()` returns to `/graph` with `node=n1` still in the hash query, because selection updates used `replace: true` (they do not push separate history entries). Forward is unchanged from default browser stack after one back.

Acceptance:

- [x] Automated guard closes the “stale router vs drawer `Link`” regression class under the real shell layout.
- [x] Back behavior after selection + leave is documented and asserted for the replace-based contract.
- Human checklist above remains for full canvas + API + `/ui/` deployment shape (see header comments in [`graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx)).

---

## 7. Recommended implementation order

For the next working session, the safest order is:

1. ~~reproduce and write the failing navigation test;~~ **Done (Phase 0, 2026-04-28)** — see [`ui/src/graphNavigationHashRouter.test.jsx`](../../ui/src/graphNavigationHashRouter.test.jsx) and Phase 0 notes above.
2. ~~inspect whether direct hash mutation is the immediate trigger;~~ **Done** — isolated repro + Phase 1 code path.
3. ~~replace graph hash mutation with one router-safe mechanism;~~ **Done (Phase 1, 2026-04-28)** — `GraphPage` uses `setSearchParams` / `mergeTraceabilityParams`; see Phase 1 section.
4. then clean up legacy workspace-tab compatibility code;
5. finally tighten docs/tests and manual QA.

This order minimizes the risk of doing a large routing cleanup before the concrete failure mode is pinned down.

---

## 8. Risks and trade-offs

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| Breaking deep links to selected graph nodes | Existing URLs may rely on current hash encoding | Same query keys (`node`, `edge`); Phase 1 keeps them in the router-managed query string under `HashRouter` — bookmarks still work. |
| Re-render churn on graph selection | Direct router updates can be expensive on high-frequency interactions | Use `replace`, debounce, or isolate selection sync from heavy graph recomputation |
| Hidden dependence in tests | Some tests still encode legacy `tab=graph` worldview | Update tests in the same slice as route cleanup |
| Scope creep into full router migration | BrowserRouter migration is tempting but larger | Keep Phase 1 focused on graph/hash conflict first |

---

## 9. Completion definition

This issue should be considered architecturally closed when all of the following are true:

- opening `/graph` does not interfere with switching to other primary routes;
- graph selection no longer depends on direct hash rewriting under `HashRouter`;
- legacy workspace-tab logic is clearly compatibility-only or removed from active flow;
- route/deep-link ownership is documented and enforced by tests;
- graph navigation feels like one surface inside the app shell, not a special isolated mode.

---

## 10. Bottom line

The current user complaint is valid: the graph surface behaves like a trap because the navigation contract around it is structurally fragile.

The correct interpretation is:

- **not** “Graph is intentionally isolated”;
- **not** “just one broken button”;
- **yes** “the routing architecture around graph deep links is only partially migrated and needs closure.”

That makes this a good candidate for a short dedicated frontend refactor pass rather than more point bugfixes around `GraphPage`.
