# Canonical route map and admin visibility

Single reference for user-facing routes, admin nesting, and legacy aliases. Implementation: [`ui/src/App.jsx`](../../ui/src/App.jsx), legacy redirects [`ui/src/routeCompatibility.js`](../../ui/src/routeCompatibility.js), admin flag [`ui/src/components/layout/adminVisibility.js`](../../ui/src/components/layout/adminVisibility.js).

## Shell

All routes below render inside [`DashboardLayout`](../../ui/src/components/layout/DashboardLayout/DashboardLayout.jsx) (sidebar + main). The UI uses **HashRouter** (`#/…` in the URL bar).

## Research surfaces (always visible in sidebar)

| Path | Purpose |
|------|---------|
| `/` | Home entry |
| `/corpus` | Corpus browser |
| `/workspace` | Workspace command center (`?workspace_id=` + optional `work_id`); drawer label **Workspace** opens last/active workspace |
| `/reader` | Standalone reader |
| `/graph` | Standalone graph (sidebar adds `?workspace_id=` when active) |
| `/chat` | Standalone agent chat (canonical; sidebar label **Chat**) |
| `/ask` | Legacy alias → redirects to `/chat` (see `LegacyAskRedirect.jsx`) |
| `/evidence` | Chunk inspection / traceability (deep links from Chat citations or Reader; not a primary sidebar item) |

## Admin surfaces (nested + visibility gate)

| Path | Purpose |
|------|---------|
| `/admin` | Admin hub |
| `/admin/benchmarks` | Benchmarks (lazy-loaded) |
| `/admin/settings` | Settings (lazy-loaded) |
| `/admin/diagnostics` | Diagnostics / health (lazy-loaded) |

When **admin mode is disabled** (local storage / env — see `adminVisibility.js`), `/admin` and children show a controlled fallback instead of full admin content.

## Legacy aliases (301-style redirect in-router)

| Legacy | Canonical |
|--------|-----------|
| `/benchmark` | `/admin/benchmarks` (query string preserved) |
| `/settings` | `/admin/settings` |
| `/diagnostics` | `/admin/diagnostics` |

Redirect builder: `buildLegacyAdminRedirectTarget` in `routeCompatibility.js`.

## API vs UI

- Research API: `/v1/*` (and `GET /health` at API root). UI dev server proxies `/v1` and `/health` to the backend when using Vite defaults in `vite.config.js`.
- Optional `VITE_API_BASE_URL`: must match the host that serves `/v1` and `/health` for diagnostics and live queries.

## Policy (current)

See [`admin-policy.md`](./admin-policy.md) for admin visibility, roles, and future auth notes.

- **Workspace-first:** primary flow is Corpus → Workspace; standalone tools exist for deep links and power users.

For product phases and remaining work, see [`ui-ux-master-plan.md`](./ui-ux-master-plan.md).
