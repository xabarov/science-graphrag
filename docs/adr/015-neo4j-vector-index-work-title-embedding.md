# ADR 015 — Neo4j vector index for `Work.title_embedding` (Wave Q2, optional)

## Status

Accepted — 2026-04-25

## Context

Wave Q already ships `QdrantWorkEmbeddingStore` (`work_embeddings`) for work-level similarity and dedup-assisted retrieval.  
For Wave R tool-use experiments we also need an **in-graph** similarity primitive to compare:

- Qdrant `work_embeddings` lookup, and
- Neo4j-native vector search on `:Work`.

The roadmap marked this branch optional (Wave Q2) and requested a low-risk additive path.

## Decision

1. Add optional Neo4j vector index:
   - `work_title_emb` on `(:Work).title_embedding`,
   - dimensions `384`, cosine similarity.
2. Keep Qdrant as primary production path; Neo4j vector index is **additional**, not a replacement.
3. `Neo4jGraphStore.ensure_schema()` attempts index creation and degrades gracefully on engines without vector-index support.
4. Reuse existing backfill script:
   - `scripts/backfill_work_embeddings.py --target neo4j --apply`
   - writes vectors to `Work.title_embedding`.

## Consequences

- Enables A/B experiments for Wave R tools (`in-graph vector` vs `Qdrant work_embeddings`) without migration risk.
- Keeps operational simplicity: if vector index is unavailable on a specific Neo4j build, the system remains functional.
- Preserves current Qdrant-first architecture and decision gate semantics.

## Related

- [`014-work-dedup-smart-wave-l.md`](014-work-dedup-smart-wave-l.md)
- [`../analysis/ontology-benchmarks-roadmap-2026-04-24.md`](../analysis/ontology-benchmarks-roadmap-2026-04-24.md) (Wave Q)
- [`../runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md)
