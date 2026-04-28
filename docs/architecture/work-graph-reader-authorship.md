# Work graph: reader authorship projection

**Scope:** `GET /v1/works/{work_id}/graph` — how **authorship** appears under `view=reader` vs `view=raw`, and how it stays consistent with workspace UX expectations.

**Full analysis (symptoms, root cause, options A–C):** [`docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md).

## Pipeline order (contractual)

Orchestrated in [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) (`_work_graph_neighborhood_payload`); reader authorship projection lives in [`science_graphrag/api/graph_reader_projection/`](../../science_graphrag/api/graph_reader_projection/).

1. Build center `Work` and 1-hop neighbors (optional claims slice merged before authorship enrich).
2. **`enrich_authorship_nodes`** via [`authorship_enrich.py`](../../science_graphrag/api/graph_reader_projection/authorship_enrich.py) (implementation in [`graph_display.py`](../../science_graphrag/api/graph_display.py)) — loads display fields and, when Neo4j has `(Authorship)-[:OF_AUTHOR]->(Author)`, sets **`properties.author_entity_id`** on `Authorship` nodes for collapse.
3. **`view=raw`:** **`strip_reader_only_authorship_properties`** — strip **`author_entity_id`** from `Authorship.properties` (topology-oriented API); **no** collapse.
4. **`view=reader`:** **`collapse_authorship_for_reader_view`** ([`authorship_collapse.py`](../../science_graphrag/api/graph_reader_projection/authorship_collapse.py)) — removes `Authorship` / `HAS_AUTHORSHIP` from the reader-facing graph; adds **`AUTHORED`** edges from the center work to **`Author`** targets.
5. **Optional `include_institutions` (Phase 3):** When the query flag is true, the server loads center-work `(Authorship)-[:AFFILIATED_WITH]->(Institution)` rows (capped) and merges them into the JSON: **`view=reader`** → **`Author–AFFILIATED_WITH–Institution`** after collapse (mapping via **`build_authorship_to_reader_author_map`**, same author resolution as collapse); **`view=raw`** → **`Authorship–AFFILIATED_WITH–Institution`** after the strip step. See ADR 011 addendum and `meta.reader_extra_hops` / `meta.institutions`.
6. **`_enrich_edges_with_display`** — stable edge ids, `display_type`, summaries.

**Neighbor aggregation (historical GR8):** disabled since 2026-04-28 — responses include concrete nodes only (within `neighbor_limit` / fetch ordering). **`meta.neighbor_aggregation`** is **`none`**. The legacy helper **`_apply_aggregators`** remains in code for unit tests only; **`GET /v1/works/{work_id}/graph/expand`** is still available for API compatibility but normal reader payloads no longer emit **`Aggregator`** nodes.

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

**Workspace graph** (`project_workspace_graph`, `view=reader`): the server keeps `:Authorship` and materialized `OF_AUTHOR` where present. **Dense-neighbor aggregation (GR8) is disabled** (2026-04-28): no `Aggregator` nodes; helpers in [`tests/fixtures/work_graph_workspace_authorship_parity.py`](../../tests/fixtures/work_graph_workspace_authorship_parity.py) build a **1-hop induced slice** around the center work and count:

- distinct `Author` ids reached via `HAS_AUTHORSHIP` → `OF_AUTHOR` from that work, plus  
- one slot per `Authorship` incident to the work **without** an `OF_AUTHOR` edge in the payload (matches one synthetic `va:` author on the work graph).

**Standalone work graph** (`work_graph_neighborhood`, `view=reader`): after collapse (no neighbor aggregation), helpers count `AUTHORED` edges from the center work.

**Neighbor caps differ by design:** workspace inner mode ignores `neighbor_limit` (full 1-hop union); the work graph **applies** `neighbor_limit`. Parity assertions run only when `meta.is_truncated` is **false** on the work graph response, **or** they assert weaker invariants (e.g. center `authors_count` from the neighborhood query still matches Neo4j) when truncation is forced.

**Optional debug field:** `GET /v1/works/{work_id}/graph?include_authorship_debug=true` adds `meta.authorship_projection` — one of `native`, `synthesized`, `mixed`, `none` — classifying **post-collapse** `AUTHORED` targets from the center (no PII). Omitted when the flag is false.

## Related code

| Piece | Location |
|-------|----------|
| Work neighborhood (no server-side neighbor aggregation) | `science_graphrag/api/works/graph_neighborhood.py` |
| Reader authorship collapse + synthetic `va:` / `via` + ash→reader author map (institutions) | `science_graphrag/api/graph_reader_projection/authorship_collapse.py` |
| Authorship projection meta (`include_authorship_debug`) | `science_graphrag/api/graph_reader_projection/authorship_meta.py` |
| Stable edge ids (collapse + display pass) | `science_graphrag/api/graph_reader_projection/stable_edge_id.py` |
| Legacy expand helper (optional; payloads no longer carry `Aggregator` from main graph) | `expand_work_aggregator` in `science_graphrag/api/works/graph_neighborhood.py` |
| Authorship batch enrich (call sites use seam) | `science_graphrag/api/graph_reader_projection/authorship_enrich.py` → `graph_display.enrich_authorship_nodes` |
| HTTP query params | `science_graphrag/api/works/router.py` — `get_work_graph`, `expand_aggregator` |
| API spec (tables) | `docs/specs/frontend-ui-api-contracts-v1.md` §4 |
| Manual QA checklist | `docs/runbooks/work-graph-authorship-qa.md` |
| Workspace author UI fallback | `ui/src/components/graph/authorSemanticProjection.js` |
