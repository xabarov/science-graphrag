# UI Entry Wave Checklist

Manual verification for the Home / Corpus / entry-experience wave.

## Core entry

- Open `/` and confirm `Home` renders instead of redirecting straight to `Corpus`.
- Confirm `Home` shows:
  - `Continue last workspace`
  - `Open corpus`
  - `Admin` entry when admin mode is enabled
  - `Recent works`
- With empty local state, confirm the page explains there is no saved workspace yet.

## Continue flow

- Open a work in `Workspace`.
- Navigate between tabs and return to `Home`.
- Confirm `Continue last workspace` opens the last `work_id` and the latest saved tab.

## Corpus flow

- Open `Corpus` from `Home`.
- Confirm `Open workspace` is the strongest CTA on each work card.
- Confirm `Recent works` / continue section appears above the main list.
- Search for a nonsense query and confirm the no-results copy is distinct from the empty-corpus copy.

## Admin flow

- Open `/admin` from `Home`.
- Confirm cards for `Benchmarks`, `Settings`, and `Diagnostics` are visible.
- Open canonical admin routes and confirm each renders with clear return paths:
  - `/admin/benchmarks`
  - `/admin/settings`
  - `/admin/diagnostics`
- Open old direct routes and confirm they still work as compatibility aliases:
  - `/benchmark`
  - `/settings`
  - `/diagnostics`
- Confirm old admin URLs preserve query params when redirected, for example `/benchmark?tab=workbench`.
- With admin mode disabled, confirm:
  - `Home` hides admin entry cards/buttons;
  - sidebar hides the admin group;
  - direct `/admin/*` routes show a controlled fallback instead of raw content.

## Navigation consistency

- Confirm sidebar contains `Home`, `Corpus`, `Workspace`, direct tools, and admin tools.
- When admin mode is disabled, confirm sidebar still keeps a clear primary research flow without leaving an empty admin gap.
- Confirm deep links to `Workspace` still work after the `/` route change.
- Confirm there are no dead-end states after opening `Workspace` without a selected work.
- Open an unknown route and confirm the 404 page offers `Home`, `Corpus`, `Continue workspace` (when available), and `Admin` only when admin mode is enabled.
- Confirm `Reader`, `Graph`, `Chat`, and standalone `/evidence` use the same top-level header pattern and no longer look like isolated debug wrappers (Evidence is not a primary sidebar item; reach it from citations or Reader trace).

## Ask and Evidence flow

- Open standalone `/ask` without `work_id` and confirm the page reads as a global or paper-scoped research surface, not as workspace-only mode.
- Run a question with no `work_id` and confirm the answer block explains that the result is global.
- Run a question with a selected `work_id` and confirm the answer block explains that the result is paper-scoped.
- Reopen `Ask` and confirm recent questions can be restored into the form.
- In **Ask session**, create a **New session**, rename it via **Session title** (blur to save), switch **Session** dropdown, and confirm **Recent in this session** only shows turns for the active session.
- Open **Workspace → Ask** for a work and confirm sessions are separate from standalone `/ask` (different scope).
- Copy the URL while on Ask with a selected session and confirm **`ask_session=`** is present; reload and land on the same session; switch to another workspace tab and confirm `ask_session` is stripped from the query string.
- From an answer citation, jump into `Workspace`, `Reader`, `/evidence` (chunk inspection), and `Graph` and confirm traceability context is preserved (`workspace_id` + chunk fingerprint where applicable).
- On **Workspace → Graph**, narrow the viewport below the `md` breakpoint and confirm the graph/cards column stacks above the detail panel without unusable horizontal scroll.
- From `Reader` or `Evidence`, confirm there is a clear path back into `Ask` to continue the question flow.
- Trigger a degraded response fixture or low-context answer and confirm the degraded-state copy is visible and understandable.

### Ask answer explanation (Phase 5)

- After a successful query, confirm the **Why this answer** list appears above the answer body with plain-language bullets (query mode, evidence pack, quality, graph context).
- Without opening **Show advanced JSON**, confirm you can tell whether the run was corpus-wide, paper-scoped, or workspace session.
- Expand **Show advanced JSON** only when needed and confirm raw retrieval trace still matches the summary lines.
