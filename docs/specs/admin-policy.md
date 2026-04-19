# Admin visibility and roles (UI)

## Current behavior

- **Admin surfaces** (`/admin`, `/admin/benchmarks`, `/admin/settings`, `/admin/diagnostics`) are reachable from the shell when **admin mode** is enabled in the browser. Implementation: [`ui/src/components/layout/adminVisibility.js`](../../ui/src/components/layout/adminVisibility.js) (local storage override + build-time env).
- **No backend RBAC:** hiding admin navigation does not enforce server-side authorization. Anyone who can load the SPA can toggle storage or hit API routes directly unless the API is protected separately.
- **Research-only mode:** when admin mode is off, `/admin/*` shows a controlled message instead of operational tools (see [`App.jsx`](../../ui/src/App.jsx) `AdminRouteShell`).

## Diagnostics and status

- [`DiagnosticsPage`](../../ui/src/pages/DiagnosticsPage.jsx) and [`AdminApiStatusStrip`](../../ui/src/pages/AdminApiStatusStrip.jsx) call read-only endpoints (`GET /health`, `GET /v1/works` with `limit=1`). They must not send secrets in the UI; configuration stays in env / settings flows.

## Optional API admin key (2026-04-19)

When `SCIENCE_GRAPHRAG_ADMIN_API_KEY` is set in the API environment, these routes require header **`X-Admin-Key`** with the same value:

- `/v1/benchmark/*`
- `/v1/settings/*` (read and write)

`GET /health`, `GET /v1/works`, `POST /v1/query`, and `/v1/ask-sessions` are **not** gated by this header (researcher flows stay open unless you add a separate policy).

Merge CI clears the admin key for `tests/test_api_smoke.py` via `tests/conftest.py` so benchmark/settings smoke stays hermetic.

## Future: full backend RBAC

When server-side roles exist beyond a shared admin key:

1. Gate **write** benchmark/settings routes on claims / JWT.
2. Replace or supplement client-only admin mode with session/JWT claims.
3. Keep the route map in sync with enforced API policies (see [`route-map.md`](./route-map.md)).
