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
   - Query params: `neighbor_limit` (1–2000), `depth` (1–3, effective hop still 1 until implemented).

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
