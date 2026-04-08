# UI Entry Wave Checklist

Manual verification for the Home / Corpus / entry-experience wave.

## Core entry

- Open `/` and confirm `Home` renders instead of redirecting straight to `Corpus`.
- Confirm `Home` shows:
  - `Continue last workspace`
  - `Open corpus`
  - `Admin` entry
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
- Confirm deep links to `Workspace` still work after the `/` route change.
- Confirm there are no dead-end states after opening `Workspace` without a selected work.
- Open an unknown route and confirm the 404 page offers `Home`, `Corpus`, `Continue workspace` (when available), and `Admin`.
- Confirm `Reader`, `Graph`, `Ask`, and `Evidence` now use the same top-level header pattern and no longer look like isolated debug wrappers.
