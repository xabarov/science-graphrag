# Frontend parallel track strategy (Phase 5/6 bridge)

## Context

`science-graphrag` already has a narrow Phase 5 API MVP:

- `GET /health`
- `POST /v1/query`
- static prototype at `/`

Current backend contract is enough for one real query flow, but not enough for full research workspace UX.

## Goal

Run frontend in parallel without blocking on full backend completion:

- implement reusable shell and navigation now;
- validate UX and information architecture with mocks;
- keep one production-backed flow (`POST /v1/query`) connected end-to-end;
- avoid hard coupling to unstabilized data contracts.

## Reuse matrix from osint-gr

### Reuse as pattern

- App shell and route composition
- Layout primitives (sidebar, app bar, content panes)
- Common UI components and style tokens
- API client structure and error handling boundaries
- Chat container behavior (input, message list, retry states)
- Graph canvas/interaction mechanics (zoom, pan, filters as UI pattern)
- Frontend test harness and smoke-style UI tests

Primary references:

- `/home/roman/pyprojects/ML/Prod/osint-gr/frontend/src/App.jsx`
- `/home/roman/pyprojects/ML/Prod/osint-gr/frontend/src/components/layout/DashboardLayout.jsx`
- `/home/roman/pyprojects/ML/Prod/osint-gr/frontend/src/components/features/CompactChat.jsx`
- `/home/roman/pyprojects/ML/Prod/osint-gr/frontend/src/components/features/GraphVisualization.jsx`

### Rebuild for science domain

- Domain workflows and route semantics (corpus/workspace/research tasks)
- Node/edge taxonomy labels and graph legends
- Reader/evidence/citation UX and traceability affordances
- API payload shapes and endpoint mapping
- Product language and i18n keys
- Any "case/investigation/admin benchmark" domain logic from osint-gr

## Delivery waves

## Wave A: shell + mocks + one real flow

- Implement surfaces: `Workspace`, `Reader`, `Graph`, `Ask`, `Evidence`.
- Connect only `Ask` to live `POST /v1/query`.
- Keep other surfaces mock-driven with fixtures.
- Define stable UI state model and URL contract.

Exit criteria:

- screen map and navigation stable;
- no direct dependency on missing backend endpoints;
- query screen returns citations and trace to UI.

## Wave B: full API integration

- Replace mock stores with live API contracts for works/graph/chunks.
- Add empty/degraded states for missing semantic extraction data.
- Harden loading/error behavior and cross-screen deep links.

Exit criteria:

- end-to-end MVP flow from roadmap works on live data:
  ingest corpus -> inspect metadata/graph -> ask grounded question -> inspect citations.

## Guardrails

- Contract-first: frontend and backend sync only through versioned docs.
- No direct copy of osint business entities.
- No backend-driven UI branching without explicit contract fields.
- Keep adapters thin: map backend responses to UI view-models in one layer.
