# Light theme roadmap — 2026-04-27

**Status:** draft — **LT0 (visual contract + inventory) complete as of §10**  
**Scope:** `ui/` application shell, shared components, page surfaces, graph/reader/chat, settings entry point for theme preference  
**Primary context:** `ui/src/main.jsx`, `ui/src/styles.css`, `ui/src/components/common/index.jsx`, `ui/src/components/layout/DashboardLayout/Drawer.jsx`, `ui/src/components/layout/DashboardLayout/DashboardLayout.jsx`, `ui/src/components/work/MarkdownViewCore.jsx`, `ui/src/components/work/PdfViewer.jsx`, `ui/src/components/graph/canvas/graphCanvasStyle.js`

## 1. Why this roadmap exists

The product already has a coherent dark visual language: compact spacing, subdued chrome, thin borders, muted text, and a Cursor-like atmosphere. That gives us a strong design baseline, but the current implementation is effectively **dark-only**:

- `ui/src/main.jsx` hard-codes `palette.mode: "dark"`;
- `ui/src/styles.css` sets `color-scheme: dark`;
- shared primitives such as `ui/src/components/common/index.jsx` encode white-on-dark defaults directly;
- shell/page components such as `ui/src/components/layout/DashboardLayout/Drawer.jsx`, `ui/src/components/layout/DashboardLayout/DashboardLayout.jsx`, `ui/src/pages/SettingsPage/SettingsLayout.jsx`, and `ui/src/components/layout/PageHeader.jsx` use hard-coded dark surfaces and borders;
- content renderers such as `ui/src/components/work/MarkdownViewCore.jsx` and `ui/src/components/work/PdfViewer.jsx` assume dark backgrounds;
- graph rendering in `ui/src/components/graph/canvas/graphCanvasStyle.js` relies on light strokes over dark canvas assumptions.

This means that adding a light theme is not a matter of flipping one MUI switch. We need a small visual system refactor first, then a staged migration of high-value surfaces.

## 2. Current-state analysis

### 2.1 What is already in good shape

The UI already has several properties worth preserving in both themes:

1. Compact layout rhythm and small typography scale.
2. Consistent accent family around muted indigo.
3. Flat surfaces with restrained borders instead of heavy shadows.
4. Clear product hierarchy: shell, page header, cards, controls, inspector panels.
5. Existing `ThemeProvider` in `ui/src/main.jsx`, which gives us a natural insertion point for mode-aware tokens.

### 2.2 What blocks a clean light theme today

The main blockers are structural rather than aesthetic:

1. **Hard-coded dark tokens are spread through components.** Shared buttons, headers, drawers, cards, alerts, and many page panels use literal `rgba(255,255,255,...)`, `#0a0a0a`, `#141414`, and `#1a1a1a`.
2. **There is no semantic token layer.** Components reach for literal colors instead of asking for concepts such as `surface.panel`, `text.secondary`, `border.muted`, or `accent.soft`.
3. **The CSS environment is dark-only.** `color-scheme: dark` in `ui/src/styles.css` will produce incorrect native control behavior in light mode.
4. **Content renderers assume dark contrast.** Markdown headings, inline code, code fences, links, tables, and the PDF viewport all need dedicated light-mode tuning.
5. **Canvas-based views need separate contrast work.** Graph nodes, edge labels, hover/selection states, and dimmed search states need different opacity math on light backgrounds.
6. **There is no user-facing theme preference yet.** The natural home is `GeneralSettingsPanel`, but the app currently persists only locale there.

### 2.3 Highest-risk areas

The migration risk is not evenly distributed. These areas need explicit wave planning:

- **App shell:** `DashboardLayout`, `Drawer`, sticky settings header, page header, action toolbars.
- **Shared component library:** `CursorButton`, `CursorPrimaryButton`, `CursorDangerButton`, `CursorIconButton`, notices, dialogs.
- **Reader/content surfaces:** `MarkdownViewCore`, `PdfViewer`, citation/evidence panels, chat answer cards.
- **Graph surfaces:** `graphCanvasStyle.js` plus graph toolbars, legends, debug/detail panels.
- **Long-tail admin/benchmark pages:** many use dark literals directly and should be migrated after the shell/token foundation is stable.

## 3. Light-theme concept

### 3.1 Product direction

The light theme should be a **true sibling** of the current dark theme, not an inversion:

- keep the same compact, technical, low-noise personality;
- preserve the existing indigo accent family;
- avoid sterile pure-white enterprise styling;
- preserve thin separators and flat surfaces;
- keep strong scanability for dense research/admin interfaces.

In short: **calm editorial light theme**, not glossy SaaS white.

### 3.2 Visual principles

1. Use **layered neutrals**, not one flat white background. The shell, page canvas, cards, overlays, and code/content blocks should each have their own subtle step.
2. Keep **contrast in text first**, not through stronger borders everywhere.
3. Preserve the current **compactness and information density**; light mode should not introduce more padding or larger controls.
4. Use accent color sparingly for selection, active states, and key affordances; do not flood large surfaces with blue.
5. Treat **content-heavy surfaces** differently from control-heavy surfaces. Markdown, code, graphs, and PDFs need dedicated contrast tuning.

### 3.3 Proposed light palette direction

The exact palette should be validated visually during implementation, but the direction should be:

- `app background`: very light neutral, slightly cool, not pure white
- `sidebar / secondary chrome`: subtly darker than the main canvas
- `panel / card`: near-white
- `border`: low-contrast slate/gray alpha instead of white alpha
- `primary text`: dark slate, high readability
- `secondary text`: same hue family at lower opacity
- `muted text`: still readable in dense tables and inspector UI
- `accent`: same indigo family as dark theme, tuned for lighter backgrounds
- `danger / warning / success`: restrained, low-saturation fills with darker text

A plausible first-pass direction:

- main canvas around `#f5f7fb`
- secondary shell around `#eef2f7`
- card/panel around `#ffffff`
- primary text around `rgba(15, 23, 42, 0.92)`
- secondary text around `rgba(15, 23, 42, 0.62)`
- border around `rgba(15, 23, 42, 0.10)`
- accent background around `rgba(99, 102, 241, 0.10)`
- accent text/stroke around `rgba(79, 70, 229, 0.88)`

The important part is not these exact numbers; it is the **semantic layering model**.

## 4. Target implementation architecture

### 4.1 Theme modes

The product should support three appearance modes:

1. `dark`
2. `light`
3. `system`

`system` should map to `prefers-color-scheme`, while explicit `dark` and `light` override it.

### 4.2 Preference storage

Theme preference should live with other UI-level preferences in the browser, not in server settings:

- first implementation: local persistence only, similar to locale and sidebar width state;
- entry point: `GeneralSettingsPanel`;
- no backend dependency required;
- if we later need profile sync, we can add it without blocking the initial rollout.

This keeps the first wave focused and avoids unnecessary API work.

### 4.3 Semantic token layer

Before broad page migration, we should introduce semantic tokens that hide the raw color values. Suggested families:

- `surface.app`
- `surface.sidebar`
- `surface.panel`
- `surface.panelAlt`
- `surface.overlay`
- `surface.code`
- `surface.accentSoft`
- `border.default`
- `border.strong`
- `text.primary`
- `text.secondary`
- `text.muted`
- `text.accent`
- `state.success`
- `state.warning`
- `state.danger`
- `graph.node.*` and `graph.edge.*` where necessary

These can be implemented either as:

1. MUI theme extensions with a custom `theme.appTokens`, or
2. CSS variables generated from the active theme and consumed from `sx`.

For this codebase, the most practical route is:

- keep MUI as the source of truth;
- add a compact custom token object on the theme;
- optionally expose a few CSS variables for non-MUI and imported CSS needs.

**Decision to lock before implementation:** `theme.appTokens` should be the single source of truth. If CSS variables are introduced, they should be generated from the resolved theme at the app root and treated as transport for external CSS, not as a second token definition system.

### 4.3.1 First paint and persistence contract

To avoid a visible flash between `system`, `dark`, and `light`, the implementation should define the initial mode before the main React tree paints.

Recommended contract:

1. store appearance under one browser key, for example `ui.appearanceMode`;
2. allowed values: `dark`, `light`, `system`;
3. on boot, resolve the effective mode from local storage plus `prefers-color-scheme`;
4. apply root-level mode markers and `color-scheme` immediately;
5. let React hydrate against the already resolved effective mode.

This should be treated as part of the foundation phase, not a later polish task.

### 4.4 Component migration strategy

Shared primitives must stop owning dark-specific colors directly. Instead, they should derive from semantic tokens:

- buttons and icon buttons from `ui/src/components/common/index.jsx`
- dialog surfaces such as `ui/src/components/feedback/dialogPaperSx.js`
- global focus ring in `ui/src/styles.css`
- page-level headers and shell containers

Only after this layer is stable should page-level migration begin.

## 5. Roadmap

### Phase LT0 — Visual contract and token inventory

**Goal:** define the minimum viable light-theme system before editing dozens of files.

**Completion:** deliverables for this phase are recorded in **§10** (inventory, LT1 token table, normative contracts, LT1 scope boundary, hand-off checklist).

Tasks (all addressed in §10):

1. Inventory existing dark literals in shared shell and top-traffic pages.
2. Define the initial semantic token map for dark and light.
3. Decide whether code highlighting and markdown content get dedicated light assets.
4. Approve the product direction: `dark | light | system`, browser-local persistence.

Exit criteria:

- token vocabulary agreed;
- first-pass light palette approved;
- rollout order frozen.

### Phase LT1 — Theme foundation

**Goal:** make the application capable of switching themes without visual corruption.

Tasks:

1. Replace the single hard-coded theme in `ui/src/main.jsx` with a mode-aware theme factory.
2. Add appearance preference state and persistence.
3. Make `ui/src/styles.css` dynamic instead of `color-scheme: dark`.
4. Define first-paint behavior so `system`/`light`/`dark` do not flash through the wrong mode on load.
5. Add theme selection to `GeneralSettingsPanel` and i18n labels for it in both EN and RU.
6. Introduce shared semantic tokens on the MUI theme.

Exit criteria:

- app can switch dark/light/system at runtime;
- first paint resolves to the correct effective mode without a visible theme flash;
- native inputs/scrollbars/focus behavior follow the active mode;
- no backend changes required.

### Phase LT2 — Shared shell and primitives

**Goal:** migrate the components that define the visual baseline for the whole app.

Tasks:

1. Tokenize `CursorButton` family and shared icon actions.
2. Migrate shell containers: `DashboardLayout`, `Drawer`, page header, sticky settings header, common cards, inline notices, dialogs.
3. Remove the most common white-on-dark literals from shared utility files.
4. Verify hover/active/focus states in both themes.

Exit criteria:

- shell chrome looks coherent in both themes;
- main navigation, settings layout, headers, and dialogs no longer rely on dark literals.

### Phase LT3 — Primary user journeys

**Goal:** make the most frequently used product paths production-ready in light mode.

Priority surfaces:

1. Workspace/chat flow.
2. Reader/content flow.
3. Workspaces listing and action panels.
4. Settings/general admin flow.

Tasks:

1. Migrate chat composer, answer cards, status chips, and thread surfaces.
2. Rework markdown prose styles and choose a light syntax-highlighting theme.
3. Tune PDF viewer chrome and surrounding surfaces.
4. Update workspace collection cards, recent panels, and filters.

Exit criteria:

- the main end-to-end workflow is usable and visually intentional in light mode;
- no unreadable prose/code blocks;
- no “dark island” components inside primary pages.

### Phase LT4 — Graph and advanced/admin surfaces

**Goal:** finish specialized surfaces that need mode-specific contrast logic.

Tasks:

1. Rebalance graph node fills, strokes, hover, selection, and dimming logic.
2. Migrate graph legends, toolbars, side panels, and inspectors.
3. Migrate benchmark/admin/diagnostics long-tail views.
4. Review table-heavy pages for border density and muted-text legibility.

Exit criteria:

- graph is readable on light canvas;
- admin/benchmark pages no longer look partially dark-themed;
- advanced workflows are mode-consistent.

### Phase LT5 — Verification and rollout

**Goal:** ensure the light theme is not just present, but operationally safe.

Tasks:

1. Manual verification across both modes and both locales.
2. Add focused tests where value is high:
   - theme preference persistence
   - settings control behavior
   - representative component rendering in both modes
3. Audit contrast on key text, chips, buttons, tables, links, and disabled states.
4. Run a quick visual regression pass on the main routes.

Exit criteria:

- light mode is considered supported rather than experimental;
- no critical contrast or unreadable content regressions remain.

## 6. Special implementation concerns

### 6.1 Markdown and code highlighting

`MarkdownViewCore.jsx` currently imports `github-dark.min.css`. Light mode needs either:

1. a dynamic highlight stylesheet, or
2. a custom code token style that does not depend on a dark-only stylesheet.

This should be treated as a first-class task, not a polishing detail, because it affects evidence readability.

### 6.2 PDF viewer

`PdfViewer.jsx` is currently designed as a dark framed viewport. In light mode we should verify:

- toolbar controls keep sufficient contrast;
- the viewport frame does not disappear into the page background;
- react-pdf text/annotation layers remain legible;
- loading and warning states still fit the lighter surface hierarchy.

### 6.3 Graph contrast math

`graphCanvasStyle.js` uses alpha-based fills and white strokes tuned to dark surroundings. Light mode will need:

- darker default label text;
- darker stroke selection logic;
- adjusted dimming functions;
- possibly separate per-mode token tables for node types.

### 6.4 Native/browser chrome

Because the app uses `color-scheme`, local storage preferences, and imported third-party CSS, we must verify:

- scrollbar appearance;
- focus rings;
- browser default form pieces;
- tooltip/popover contrast;
- third-party content CSS in both themes.

## 7. Recommendation on rollout shape

Do **not** attempt a one-shot repo-wide recolor. The safer order is:

1. token foundation;
2. shared shell;
3. top user journeys;
4. graph/admin tail;
5. verification.

This reduces merge risk, keeps the app usable during the migration, and lets the team validate the visual direction early.

## 8. Definition of done

Light theme should be considered complete only when all of the following are true:

1. A user can choose `dark`, `light`, or `system` from settings.
2. The chosen mode persists locally and applies on reload.
3. Main shell, workspace/chat, reader, settings, and graph are all visually coherent in light mode.
4. Markdown, code blocks, PDFs, tables, chips, and dialogs remain readable.
5. There are no obvious dark-only islands on primary routes.
6. Dark theme quality is preserved; the migration must not regress the existing design language.

## 9. Proposed immediate next actions

If we start implementation next, the first slice should be:

1. add appearance preference plumbing in `ui/src/main.jsx` and `GeneralSettingsPanel`;
2. introduce semantic theme tokens for shell/text/border/surface/accent;
3. migrate `CursorButton` family plus `DashboardLayout`/`Drawer`;
4. only then begin page-level conversion.

That first slice is small enough to review safely and large enough to prove the architectural direction.

## 10. LT0 completion — visual contract, inventory, and LT1 hand-off

This section closes **Phase LT0** from §5: it is the authoritative reference for anyone starting **LT1** implementation.

### 10.1 Inventory methodology

**Scope:** `ui/src/**/*.js`, `ui/src/**/*.jsx`, `ui/src/**/*.css`.

**Heuristic grep** (dark-only literals that must become semantic or palette-driven in later phases):

- hex surfaces: `#0a0a0a`, `#141414`, `#1a1a1a`, `#1c1c1c`;
- white-channel borders/text on dark: `rgba(255, 255, 255, …)` (covers most `sx` borders, muted text, and translucent fills).

**Result (audit date: 2026-04-27):** **133 files** under `ui/src` match at least one of the patterns above.

**Limitations of this inventory:**

- It **does not** list files that only use accent RGBA (e.g. indigo) on top of MUI defaults; LT1 should still align `palette` / components with `appTokens`.
- It **does not** capture third-party CSS (e.g. highlight.js, KaTeX, react-pdf layers) beyond what our components wrap.

### 10.2 Grouping by semantic token family

Use this map when migrating literals → `theme.appTokens` (or derived CSS variables).

| Family | Typical literals / patterns in repo | Primary `appTokens` keys (LT1 minimum) |
|--------|-------------------------------------|----------------------------------------|
| **Surface — app canvas** | `#0a0a0a` (main, sticky headers) | `surface.app` |
| **Surface — sidebar** | `#141414` (`Drawer`) | `surface.sidebar` |
| **Surface — panel / card** | `#1a1a1a`, sticky headers, cards | `surface.panel`, `surface.panelAlt` |
| **Surface — nested / viewer** | `#1c1c1c` (`PdfViewer` chrome), `#0a0a0a` in code blocks | `surface.code`, `surface.panelAlt` |
| **Border** | `rgba(255,255,255,0.06–0.18)` | `border.default`, `border.strong` |
| **Text** | `rgba(255,255,255,0.35–0.95)` | `text.primary`, `text.secondary`, `text.muted` |
| **Accent** | `rgba(99,102,241,…)`, `rgba(129,140,248,…)` | `accent.softBg`, `accent.softBorder`, `accent.fg` |
| **Danger** | `rgba(239,68,68,…)` | `state.dangerFg`, `state.dangerBg`, `state.dangerBorder` |
| **Graph** | `graphCanvasStyle.js`, `graphCanvasDraw.js`, toolbar/legend | `graph.*` (separate table; **LT4**, not LT1) |

### 10.3 Migration tier order (for LT1/LT2 planning)

Order reduces merge risk and avoids “dark islands” after the first PR:

| Tier | Area | Representative paths |
|------|------|-------------------------|
| **T0** | Bootstrap / global | `ui/src/main.jsx`, `ui/src/styles.css` |
| **T1** | Shared primitives | `ui/src/components/common/index.jsx`, `ui/src/components/common/CursorIconAction.jsx`, `ui/src/components/feedback/dialogPaperSx.js`, `ui/src/components/feedback/InlineNotice.jsx`, `FeedbackShell` / `FeedbackProvider` |
| **T2** | App shell | `ui/src/components/layout/DashboardLayout/Drawer.jsx`, `DashboardLayout.jsx`, `PageHeader.jsx`, `SettingsLayout.jsx`, `SettingsSectionNav.jsx` |
| **T3** | Primary journeys | Chat: `ChatComposer.jsx`, `ChatMessageThread.jsx`, `AskAnswerPanel.jsx`; Workspaces: `WorkspacesPage.jsx` and `WorkspacesPage/*`; Reader: `ReaderPage.jsx`, `MarkdownViewCore.jsx`, `PdfViewer.jsx` |
| **T4** | Long tail | `pages/BenchmarkPage/**`, `AdminEntryPage.jsx`, `DiagnosticsPage.jsx`, graph detail panels beyond shell |

**LT1 code scope (recommended):** T0 + T1 + **minimal** T2 (enough shell to validate switching) + settings UI for appearance + i18n EN/RU. **Do not** attempt T4 in the same PR as LT1.

### 10.4 Normative — theme modes and persistence

These rules are **locked** for LT1; do not introduce alternate storage without updating this doc.

| Item | Decision |
|------|----------|
| **User-selectable values** | `dark`, `light`, `system` |
| **Effective runtime mode** | `dark` or `light` only (resolved from `system` + `prefers-color-scheme`) |
| **Storage** | Browser only; key **`ui.appearanceMode`** (values: `dark` \| `light` \| `system`). No `/v1/settings` dependency for appearance. |
| **UI entry** | `GeneralSettingsPanel` (alongside locale), EN+RU strings. |
| **Source of truth for colors** | `theme.appTokens` on the MUI theme object. CSS variables, if any, are **derived** from `appTokens` at the app root for third-party CSS — not a second token definition. |

### 10.5 Normative — first paint (no theme flash)

**Problem:** With `system` or saved `light`, the first paint must not briefly show `dark` (or vice versa) before React runs.

**Required behavior:**

1. **Before** `ReactDOM.createRoot(…).render(…)`, read `localStorage.getItem('ui.appearanceMode')` (treat missing/invalid as `system` or product default — recommend default **`system`** to respect OS).
2. Resolve **effective** mode: if stored value is `system`, use `window.matchMedia('(prefers-color-scheme: dark)').matches` → `dark` else `light`.
3. Apply to the document root immediately:
   - `document.documentElement.dataset.colorScheme = '<effective>'` (or equivalent single attribute used consistently);
   - `document.documentElement.style.colorScheme = '<effective>'` so native scrollbars/form controls match;
   - optionally set a minimal class on `<html>` for legacy CSS if needed before LT2 removes hard-coded literals from `styles.css`.
4. React `ThemeProvider` must use the **same** resolved effective mode on first render (re-read storage or consume a tiny shared resolver module used by both the boot snippet and `main.jsx`).

**Implementation note:** In Vite, the most reliable approach is a **small inline `<script>` in `index.html`** that runs before module load, **or** a synchronous top-of-`main.jsx` block before any async imports. Pick one; document it in the LT1 PR.

### 10.6 LT1 minimal `appTokens` table (dark + light)

These are the **minimum** keys LT1 should define so T0–T2 can stop using raw hex/white RGBA. Exact hex values for light may be tuned visually; light column matches §3.3 direction.

| Token | Dark (current intent) | Light (first pass) |
|-------|------------------------|---------------------|
| `surface.app` | `#0a0a0a` | `#f5f7fb` |
| `surface.sidebar` | `#141414` | `#eef2f7` |
| `surface.panel` | `#1a1a1a` | `#ffffff` |
| `surface.panelAlt` | `#1a1a1a` / `#1c1c1c` | `#f8fafc` |
| `surface.code` | `#0a0a0a` (pre blocks) | `#f1f5f9` |
| `border.default` | `rgba(255,255,255,0.08)` | `rgba(15,23,42,0.10)` |
| `border.strong` | `rgba(255,255,255,0.12)` | `rgba(15,23,42,0.14)` |
| `text.primary` | `rgba(255,255,255,0.9)` | `rgba(15,23,42,0.92)` |
| `text.secondary` | `rgba(255,255,255,0.6)` | `rgba(15,23,42,0.62)` |
| `text.muted` | `rgba(255,255,255,0.45)` | `rgba(15,23,42,0.48)` |
| `text.accent` | `rgba(129,140,248,0.95)` | `rgba(79,70,229,0.88)` |
| `accent.softBg` | `rgba(99,102,241,0.15)` | `rgba(99,102,241,0.10)` |
| `accent.softBorder` | `rgba(99,102,241,0.3)` | `rgba(99,102,241,0.22)` |
| `state.dangerFg` | `rgba(239,68,68,0.8)` | `rgba(185,28,28,0.92)` |
| `state.dangerBg` | `rgba(239,68,68,0.08)` | `rgba(239,68,68,0.08)` |
| `state.dangerBorder` | `rgba(239,68,68,0.2)` | `rgba(239,68,68,0.22)` |

**Code highlighting (LT0 decision for LT3):** keep `github-dark.min.css` for dark effective mode; for light effective mode, LT3 must switch to a **light** stylesheet (e.g. `github.min.css`) or a single custom tokenized stylesheet — **not** in LT1 unless scoped to markdown only.

### 10.7 High-risk subsystems — explicit LT1 boundary

The following are **out of scope for the first LT1 PR** (token plumbing + appearance switch only). They stay on the roadmap as LT3/LT4 unless a regression forces a minimal stub.

| Subsystem | Risk | Phase |
|-----------|------|--------|
| **Markdown + highlight.js** | Dark prose + `github-dark` on light background | **LT3** |
| **PDF viewer** | Dark frame, react-pdf text/annotation layers vs page background | **LT3** |
| **Graph canvas** | `graphCanvasStyle.js` stroke/fill math assumes dark canvas | **LT4** |
| **Native / browser chrome** | `color-scheme`, scrollbars, focus ring in `styles.css` | **LT1** must set correctly; **full** polish with all edge cases — **LT5** |
| **Benchmark / admin tail** | 133-file grep hits include many benchmark pages | **LT4** |

### 10.8 LT0 exit checklist (hand-off to LT1)

- [x] **Inventory:** 133 `ui/src` files with dark hex / `rgba(255,255,255,…)` literals (§10.1).
- [x] **Semantic map:** literals grouped into families and `appTokens` keys (§10.2).
- [x] **Migration order:** tiers T0–T4 (§10.3).
- [x] **Modes + storage:** `dark` \| `light` \| `system`, key `ui.appearanceMode`, browser-only (§10.4).
- [x] **First paint contract:** resolve effective mode before React paint (§10.5).
- [x] **LT1 minimal token table:** dark + light columns (§10.6).
- [x] **Highlight strategy:** dark vs light stylesheet decision deferred to LT3 (§10.6).
- [x] **LT1 scope boundary:** markdown/PDF/graph/tail explicitly excluded from first code PR (§10.7).

**Next step:** implement **§5 Phase LT1** using §10.4–§10.6 as the contract; migrate T0→T2 first; then proceed to LT2/LT3 per §5.
