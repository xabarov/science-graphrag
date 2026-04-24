# ADR 012 — Workspace graph projection (Wave J)

## Status

Accepted (2026-04-24)

## Context

Workspace-scoped graph must show **cross-paper** structure (citations, authorship) without treating the result as an unstructured union of unrelated neighborhoods. Large workspaces (100+ works) need bounded graph size and predictable latency.

## Decision

1. **Primary engine:** Cypher over Neo4j `(:Workspace)-[:CONTAINS]->(:Work)` plus pattern expansions with a hard cap (`MAX_NEIGHBORS_CAP = 300` merged with `neighbor_limit`).
2. **Modes:**
   - `inner_only` — default UX; optional `include_external` to show cited works outside the workspace; optional `external_min_internal_citers` to keep only highly-supported external works.
   - `union_1hop` — legacy per-work 1-hop union (compatibility / debugging).
   - `semantic_layer` / `full` — same projection with semantic edge filter or full adjacency.
3. **Depth:** `depth=1` (single hop from internal works) or `depth=2` (two-hop pattern `Work-[*1..2]-*` with intermediate node constraints). Depth 2 uses the same Cypher path (no mandatory GDS).
4. **GDS:** `SCIENCE_GRAPHRAG_GDS_ENABLED` plus runtime `gds.version()` probe expose `meta.gds_runtime_available`. For **`depth=2`**, workspaces with **>50** internal works, `include_external=false`, non-semantic modes, and `node_types` including `Work`, the API may build an internal **Work–Work** subgraph via `gds.graph.project.cypher` + relationship stream, then merge **HAS_AUTHORSHIP / OF_AUTHOR** rows from Cypher. On any GDS error or empty projection, the handler **falls back** to pure Cypher (`meta.gds_used=false`).
5. **Lazy expand:** `GET /v1/workspaces/{id}/graph/neighbors?node_id=…` returns a capped 1-hop slice for UI merge without reloading the whole workspace graph.

## Consequences

- UI can style `workspace_membership` (`internal` | `external`) and show cite badges computed server-side.
- Benchmark `graph_expectations.workspace` can be compared when snapshots include `workspace_projection` metrics (see `graph_snapshot_diff.py`).
