# Manual QA: work graph authorship (reader view)

Use after changes to [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) or authorship enrich ([`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py)).

## Preconditions

- API + Neo4j running; pick a **`Work`** with **≥7** distinct authors in the graph (`authors_count` on work detail or Neo4j).
- Optional: work with **many citations** / dense 1-hop neighborhood so `neighbor_limit` stress applies.

## Steps

1. Open **`GET /v1/works/{work_id}/graph?neighbor_limit=200&include_claims=true&view=reader`** (defaults match UI if query params omitted except `include_claims` when testing claims).
2. In the UI: **`/graph?work_id=…`** — enable **Author** in the type filter / legend; confirm **individual `Author` nodes** (or as many as fit under **`neighbor_limit`**) — not an empty author layer. **Server-side neighbor aggregation is off** (2026-04-28): there is no “N authors” `Aggregator` placeholder from the API.
3. Optional: **`GET /v1/works/{work_id}/graph?view=raw`** — confirm `Authorship` and `HAS_AUTHORSHIP` remain; **`author_entity_id`** must not appear on `Authorship.properties` (see integration tests).

## References

- Contract write-up: [`docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md)
- Architecture summary: [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md)
