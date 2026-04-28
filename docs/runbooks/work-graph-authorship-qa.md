# Manual QA: work graph authorship (reader view)

Use after changes to [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) or authorship enrich ([`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py)).

## Preconditions

- API + Neo4j running; pick a **`Work`** with **≥7** distinct authors in the graph (`authors_count` on work detail or Neo4j).
- Optional: work with **many citations** / dense 1-hop neighborhood so `neighbor_limit` stress applies.

## Steps

1. Open **`GET /v1/works/{work_id}/graph?neighbor_limit=200&include_claims=true&view=reader`** (defaults match UI if query params omitted except `include_claims` when testing claims).
2. In the UI: **`/graph?work_id=…`** — enable **Author** in the type filter / legend; confirm author nodes or an **Aggregator** (“N authors”) appear (not an empty author layer).
3. **Aggregator expectation:** default per-kind threshold for authors is **4** (`KIND_AGG_THRESHOLDS["author"]` in `graph_neighborhood.py`). With ≥7 authors, you may see **one Aggregator** instead of seven separate nodes — that is expected; use **expand** on the aggregator to list individuals.
4. Optional: `**GET /v1/works/{work_id}/graph?view=raw**` — confirm `Authorship` and `HAS_AUTHORSHIP` remain; **`author_entity_id`** must not appear on `Authorship.properties` (see integration tests).

## References

- Contract write-up: [`docs/analysis/work-graph-authorship-reader-contract-2026-04-28.md`](../analysis/work-graph-authorship-reader-contract-2026-04-28.md)
- Architecture summary: [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md)
