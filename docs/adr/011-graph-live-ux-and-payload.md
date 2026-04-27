# ADR 011: Live graph UX + enriched work graph payload

- **Status:** Accepted
- **Date:** 2026-04-19

## Context

The graph UI was inspection-first: **Cards** defaulted ahead of **Canvas**, circle layout often looked empty at scale, and the detail panel emphasized **raw UUIDs and JSON**. The neighborhood API returned minimal node/edge fields and anonymous edges (no stable `id`), which made URL selection and human-readable panels harder.

## Decision

1. **Backend** — Extend `GET /v1/works/{work_id}/graph` without removing existing keys:
   - Nodes: `display_label`, `subtitle`, `node_kind`, `properties` (small bag), keep `id`, `type`, `label`.
   - Edges: stable `id`, `display_type`, `source_label`, `target_label`, `summary`, `direction`; keep `source`, `target`, `type`.
   - `meta`: `graph_scope`, `neighbor_match_count`, `neighbor_limit_applied`, `is_truncated`, `available_expansions`, depth requested vs effective (multi-hop reserved).
   - Query params: `neighbor_limit` (1–2000), `depth` (1–3, effective hop still 1 until implemented), `prioritize` (CSV, default `Method,Dataset,Work`).

   Wave GR2 semantic mapping (additive):

   | Relation `type` | `display_type` |
   |---|---|
   | `CITES` | `cites` |
   | `HAS_AUTHORSHIP` | `has authorship` |
   | `OF_AUTHOR` | `of author` |
   | `AFFILIATED_WITH` | `affiliated with` |
   | `PUBLISHED_IN` | `published in` |
   | `USES_METHOD` | `uses method` |
   | `EVALUATED_ON` | `evaluated on` |
   | `TRAINED_OR_TESTED_ON` | `trained/tested on` |

2. **Frontend defaults** — Persist `graphVizMode` defaulting to **canvas**; persist `graphCanvasLayoutMode` defaulting to **force**. Cards/Flow remain secondary.

3. **Inspector** — New [`graphInspectorModel.js`](../../ui/src/components/graph/graphInspectorModel.js) builds readable edge rows; [`GraphDetailPanel.jsx`](../../ui/src/components/graph/GraphDetailPanel.jsx) shows overview + properties + clickable connections; raw JSON under Advanced.

4. **Canvas fit** — Clamp post-fit scale with `MIN_FIT_SCALE` in [`GraphCanvasMvp.jsx`](../../ui/src/components/graph/GraphCanvasMvp.jsx) so dense 1-hop graphs do not shrink to invisible dots.

5. **Detail vs canvas consistency** — `deriveInspectorDetail` runs on **`displayGraph`** (post-`capGraphForUi`) so the panel matches what the canvas can show.

## Consequences

- Clients may rely on new display fields; old clients ignoring them still work.
- Edge `id` values are generated server-side; deep links using old synthetic client ids may need re-selection once.
- Multi-hop `depth` > 1 is a contract placeholder until Cypher expansion ships.

## References

- [`science_graphrag/api/works.py`](../../science_graphrag/api/works.py)
- [`science_graphrag/api/main.py`](../../science_graphrag/api/main.py)
- [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md)

## Addendum: Wave GR2 (2026-04-25)

- Added `node_kind` field to all nodes in graph payload. `node_kind` is the
  UI-level semantic subtype and may differ from `type` (Neo4j label).
  Values: `Work | WorkInternal | WorkExternal | AuthorshipReification |
  Author | Method | Dataset | Venue | Institution | Aggregator`.
- Expanded `display_type` for edges: now uses human-readable labels
  (`"cites"`, `"authored by"`, `"affiliated with"`, etc.) instead of
  `_`-separated Neo4j relation names.
- Added prioritized LIMIT: neighbors sorted by `node_kind_priority` before
  truncation. `meta.skipped_by_kind` reports dropped counts per kind.

## Addendum: Workspace graph = full 1-hop union (2026-04-27)

**Scope:** `GET /v1/workspaces/{workspace_id}/graph` and related **`/graph/neighbors`**, **`/graph/expand`** — not the per-work `GET /v1/works/{work_id}/graph` neighborhood (that endpoint **still** documents `neighbor_limit` / `depth` in ADR 011 §Decision).

**Decision:**

1. **Main workspace graph** is always built as the **union of all incident edges** for every internal work in the workspace (same logical shape as the historical **`depth=1`** / `build_from_depth1_rows` path). The **`depth=2`** / `build_from_depth2_rows` branch and optional **GDS** path for workspace canvas are **removed**.
2. **Removed** from the workspace graph HTTP contract: query params **`depth`**, **`neighbor_limit`**, **`node_types`**. Clients must not rely on the server to «thin» the graph by type; use **client-side** visibility ([`graphVisibilityFilter.js`](../../ui/src/components/graph/graphVisibilityFilter.js)).
3. **Neighbors / expand:** no default **row cap** or extra hop via query params; behavior is **1-hop** from the requested node. Very high degree remains an operational concern (documented in `graph-ui-plan.md`).

**Consequences:**

- **Breaking** for any client that appended `depth=` / `neighbor_limit=` / `node_types=` to workspace graph URLs (params are dropped from OpenAPI; unknown params may still be ignored by FastAPI but should be deleted from clients).
- **Reduced ambiguity:** UI «missing methods» / «missing citations» bugs caused by **depth‑2** projection are addressed at the API layer; remaining gaps are ingestion, stubs, or **UI caps** / **hidden types**.

**References:** [`docs/adr/012-workspace-graph-projection.md`](012-workspace-graph-projection.md) addendum, [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) §Workspace graph v2, [`docs/analysis/workspace-graph-methods-citations-root-cause-2026-04-27.md`](../analysis/workspace-graph-methods-citations-root-cause-2026-04-27.md).
