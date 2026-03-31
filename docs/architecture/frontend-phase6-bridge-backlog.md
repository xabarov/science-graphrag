# Frontend Phase 6 bridge backlog

Backlog is split into two synchronized tracks: frontend shell and backend bridge endpoints.

## Track A: frontend shell backlog

## A1. App bootstrap and shell

- [ ] Initialize standalone frontend app in repo root `ui/` (or agreed package path).
- [ ] Set route map for `Workspace`, `Reader`, `Graph`, `Ask`, `Evidence`.
- [ ] Implement reusable layout shell (sidebar, header, content outlet).
- [ ] Add base theme tokens matching current design constraints.

Definition of done:

- app runs locally;
- all routes accessible with placeholder state;
- shell does not depend on missing backend endpoints.

## A2. Query-first integration

- [ ] Create typed API adapter for `POST /v1/query`.
- [ ] Build `Ask` screen with request state, citations panel, graph-context chips.
- [ ] Render retrieval trace (resolved work id, hit count, embedding model label).
- [ ] Add degraded-state UX for empty hits / backend unavailable.

Definition of done:

- user can issue a query and inspect citations + trace end-to-end.

## A3. Mock-driven research surfaces

- [ ] Build `Workspace` with mocked works list/search.
- [ ] Build `Reader` with mocked metadata + chunks.
- [ ] Build `Graph` with mocked neighborhood payload.
- [ ] Build `Evidence` screen focused on citation provenance.
- [ ] Add fixture packs for "semantic available" and "semantic missing" states.

Definition of done:

- all screens are usable with fixtures;
- navigation and IA validated before full API integration.

## A4. Frontend quality gates

- [ ] Add unit tests for route guards, adapters, and state reducers.
- [ ] Add integration tests for `Ask` flow (`POST /v1/query` success/failure).
- [ ] Add basic lint + test checks to CI for frontend package.

## Track B: backend bridge backlog

## B1. Endpoint set for first live UI wave

- [ ] Implement `GET /v1/works` (search/list + pagination).
- [ ] Implement `GET /v1/works/{work_id}` (work card for reader header).
- [ ] Implement `GET /v1/works/{work_id}/graph` (graph neighborhood payload).
- [ ] Implement `GET /v1/works/{work_id}/chunks` (reader/evidence payload).

Definition of done:

- endpoints match `docs/specs/frontend-ui-api-contracts-v1.md`.

## B2. Observability and degraded behavior

- [ ] Ensure explicit degraded flags for missing semantic layer.
- [ ] Return stable ids for traceability (`work_id`, `document_id`, `chunk_fingerprint`).
- [ ] Add response examples to docs and API tests.

## B3. Query payload enrichment (incremental)

- [ ] Extend `/v1/query` trace metadata where cheap and deterministic.
- [ ] Keep backward compatibility for `answer/citations/graph_context/retrieval_trace`.

## Sequencing

1. `A1` and `A2` can start immediately.
2. `A3` runs in parallel with `B1`.
3. `B2` finalization blocks full switch from mocks to live data.
4. `A4` lands before broader pilot usage.
