# Work graph: reader authorship projection

**Scope:** `GET /v1/works/{work_id}/graph` — how **authorship** appears under `view=reader` vs `view=raw`, and how it stays consistent with workspace UX expectations.

**Full analysis (symptoms, root cause, options A–C):** [`docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md).

## Pipeline order (contractual)

Implemented in [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) (`_work_graph_neighborhood_payload`):

1. Build center `Work` and 1-hop neighbors (optional claims slice merged before authorship enrich).
2. **`enrich_authorship_nodes`** ([`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py)) — loads display fields and, when Neo4j has `(Authorship)-[:OF_AUTHOR]->(Author)`, sets **`properties.author_entity_id`** on `Authorship` nodes for collapse.
3. **`view=raw`:** strip **`author_entity_id`** from `Authorship.properties` (topology-oriented API); **no** collapse, **no** neighbor aggregation.
4. **`view=reader`:** **`collapse_authorship_for_reader_view`** — removes `Authorship` / `HAS_AUTHORSHIP` from the reader-facing graph; adds **`AUTHORED`** edges from the center work to **`Author`** targets.
5. **`_enrich_edges_with_display`** — stable edge ids, `display_type`, summaries.
6. **`view=reader` only:** **`_apply_aggregators`** — dense same-kind neighborhoods may collapse into an **`Aggregator`** node (expand via `GET /v1/works/{work_id}/graph/expand`).

## Virtual authors and `via`

When the payload has **`HAS_AUTHORSHIP`** but no **`OF_AUTHOR`** edge for an authorship row, collapse still resolves an author target using, in order:

- **`OF_AUTHOR`** edges present in the JSON payload (if materialized), or  
- **`author_entity_id`** on the `Authorship` node after enrich, or  
- a stable synthetic **`Author.id`** with prefix **`va:`** (SHA-256 digest of center work id + authorship id + fixed salt).

Virtual **`AUTHORED`** edges carry **`via`**: `["HAS_AUTHORSHIP","OF_AUTHOR"]` when linked through payload topology, or `["HAS_AUTHORSHIP","enriched_authorship"]` when resolved from enrich / surrogate.

## Raw topology and `OF_AUTHOR`

When Neo4j links `(Authorship)-[:OF_AUTHOR]->(Author)`, the work-graph builder may **materialize** the `Author` node and **`OF_AUTHOR`** edge in the JSON neighborhood (both views) so raw consumers see the same topology as the graph store; reader collapse still deduplicates to `AUTHORED` for UX.

## Parity tests: work graph vs workspace payload (Phase 3)

Automated checks compare **logical author slots** for the same `Work` id, not identical JSON shapes.

**Workspace graph** (`project_workspace_graph`, `view=reader`): the server keeps `:Authorship` and materialized `OF_AUTHOR` where present; **Authors are not aggregated** in workspace projection (`apply_workspace_aggregators` skips `Author` / `Authorship`). Helpers in [`tests/fixtures/work_graph_workspace_authorship_parity.py`](../../tests/fixtures/work_graph_workspace_authorship_parity.py) build a **1-hop induced slice** around the center work and count:

- distinct `Author` ids reached via `HAS_AUTHORSHIP` → `OF_AUTHOR` from that work, plus  
- one slot per `Authorship` incident to the work **without** an `OF_AUTHOR` edge in the payload (matches one synthetic `va:` author on the work graph).

**Standalone work graph** (`work_graph_neighborhood`, `view=reader`): after collapse and **optional** neighbor aggregation, helpers count:

- `AUTHORED` edges from the center when no `Aggregator` with `aggregator_kind=author_of_work` is present, else  
- `aggregation_hints.count` on that author aggregator (same logical cardinality as pre-aggregate `AUTHORED` count).

**Neighbor caps differ by design:** workspace inner mode ignores `neighbor_limit` (full 1-hop union); the work graph **applies** `neighbor_limit`. Parity assertions run only when `meta.is_truncated` is **false** on the work graph response, **or** they assert weaker invariants (e.g. center `authors_count` from the neighborhood query still matches Neo4j) when truncation is forced.

**Optional debug field:** `GET /v1/works/{work_id}/graph?include_authorship_debug=true` adds `meta.authorship_projection` — one of `native`, `synthesized`, `mixed`, `none` — classifying **post-collapse, pre-aggregator** `AUTHORED` targets from the center (no PII). Omitted when the flag is false.

## Related code

| Piece | Location |
|-------|----------|
| Neighborhood + collapse + aggregators | `science_graphrag/api/works/graph_neighborhood.py` |
| Aggregator expand (incl. author / `AUTHORED`) | `expand_work_aggregator` in `science_graphrag/api/works/graph_neighborhood.py` |
| Authorship batch enrich | `science_graphrag/api/graph_display.py` — `enrich_authorship_nodes` |
| HTTP query params | `science_graphrag/api/works/router.py` — `get_work_graph`, `expand_aggregator` |
| API spec (tables) | `docs/specs/frontend-ui-api-contracts-v1.md` §4 |
| Manual QA checklist | `docs/runbooks/work-graph-authorship-qa.md` |
| Workspace author UI fallback | `ui/src/components/graph/authorSemanticProjection.js` |
