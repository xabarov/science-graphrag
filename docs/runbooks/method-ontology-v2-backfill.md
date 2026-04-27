# Runbook: Method ontology v2 — backfill and rollout

**Scope:** After deploying ADR 023 (rich `Method` fields, `MethodEvidence`, ingest-time merges), existing Neo4j workspaces may still have legacy `:Method` nodes without `normalized_name`, `aliases`, or rich descriptions.

## Preconditions

- Neo4j schema applied (`ensure_schema` / API startup) so `MethodEvidence` constraint exists.
- Backup or snapshot Neo4j volume before bulk graph mutations.

## What to backfill

| Target | Action |
|--------|--------|
| `Method.normalized_name` | Set from normalized surface of `name` when null or empty. |
| `Method.aliases` | Optionally merge extraction-time aliases from latest ingested semantic artifact (if stored offline); otherwise leave for re-ingest. |
| `description_markdown` / `description_plaintext` | Re-run semantic stage for documents (`science-graphrag ingest` on corpus subset) or a dedicated LLM summarization job (not shipped by default). |

## Recommended rollout order

1. **Pilot workspace** — pick one workspace id; run read-only Cypher counts of `Method` nodes missing `normalized_name`.
2. **Dry-run Cypher** — `MATCH (m:Method) WHERE m.normalized_name IS NULL SET m.normalized_name = toLower(trim(m.name))` (adapt to your normalization helper; keep consistent with `normalize_method_surface` in code).
3. **Re-ingest** — safest path for rich text: re-run ingest for member works so `sync_work_semantic_layer` rebuilds `USES_METHOD`, `MethodEvidence`, and v2 fields.
4. **Dedup review** — open `/v1/dedup/entity?entity_type=method` for remaining conflicts after ingest merges.

## Rollback

- Property-only backfill: restore DB snapshot or reverse with `REMOVE m.normalized_name` only if needed.
- If auto-merge created wrong canonical: use entity dedup UI to **skip** future merges; manual graph fix may require `merge_method_into_canonical` in reverse (not automated — restore from backup).

## Metrics

- Ingest job fields: `ingest_method_dedup_auto_merged`, `ingest_method_dedup_llm_merged`, `ingest_entity_dedup_conflicts_enqueued` (see `_pipeline_impl.py`).

## References

- [ADR 023](../adr/023-method-ontology-v2-rich-description-and-canonicalization.md)
- [Analysis roadmap](../analysis/method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md)
