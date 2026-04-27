# ADR 023 — Method ontology v2: rich description, evidence, canonicalization

**Status:** Accepted  
**Date:** 2026-04-27  
**Related:** [004](004-ontology-v1-scope.md), [019](019-entity-dedup-pipeline.md), [analysis: method ontology roadmap](../analysis/method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md)

## Context

`Method` in ontology v1 is optimized for **name extraction** and thin Neo4j projection (`name`, `description_short`, `schema_version`). The extraction contract already carries `aliases` and `evidence[]`, but persistence and graph API under-used them. Identity is `uuid5("method:" + normalized(name))`, which blocks semantic dedup and creates duplicate pressure across surface forms.

Product and trust goals require:

- **Rich, explainable** method bodies (Markdown/LaTeX-capable) with compact `description_short` for graph chips.
- **Provenance** for descriptions and merges.
- **Two-level dedup**: intra-document mention consolidation, then cross-workspace ingest-time decisions (embedding + optional LLM adjudication + review queue).
- **Real graph merge** for methods (not alias-only) when a canonical decision is taken.

## Decision

1. **Method v2 node fields (Neo4j)** — extend `:Method` with optional fields (backward compatible; `schema_version` on node reflects richness):
   - `normalized_name` — normalized surface for search/dedup (written on ingest).
   - `aliases` — list of strings from extraction + merges.
   - `description_short` — one-line UI (v1 field, retained).
   - `description_markdown` — optional rich body for inspector (Markdown/LaTeX; must follow same sanitization path as Reader).
   - `description_plaintext` — optional normalized plain text for embeddings/search.
   - `method_kind` — optional coarse enum string (e.g. architecture, loss, training_regime).
   - `description_source` — `llm_extracted | synthesized | human_curated | unknown`.
   - `description_confidence` — optional float in \([0,1]\).

2. **MethodEvidence** — introduce optional `:MethodEvidence` nodes linked as `(m:Method)-[:HAS_EVIDENCE]->(e:MethodEvidence)` and `(w:Work {id})-[:HAS_METHOD_EVIDENCE]->(e)` for chunk-anchored quotes. Evidence rows are replaced for a work on semantic re-sync (same boundary as `USES_METHOD` delete for that work).

3. **Intra-document consolidation** — before `sync_work_semantic_layer`, merge chunk-level / redundant method mentions within one `SemanticExtractionV1` using hash-embedding clustering (configurable threshold), unioning aliases and evidence.

4. **Ingest-time method dedup** — extend ingest entity check for `method` only:
   - `sim >= 0.95`: **auto** `merge_method_into_canonical(keep, drop)` with keep rule: prefer existing workspace method id when the pair mixes “new work” and “existing” ids; otherwise deterministic id order.
   - `0.80 <= sim < 0.95`: if `method_ingest_llm_adjudicate` is **true** and LLM credentials exist, run LLM adjudication; on `same_method` merge, on `uncertain` enqueue `EntityDedupConflict` with `check_mode` including LLM metadata in `llm_*` columns; on `distinct` skip. If flag is **false**, behavior matches legacy: enqueue for human review only.
   - `sim < 0.80`: skip.

5. **Scan-time dedup (Wave T)** — `run_method_dedup` uses `merge_method_into_canonical` for auto-merge at `sim >= 0.95` instead of `add_method_alias` on a UUID. API **decide** merge for `entity_type=method` uses `merge_method_into_canonical(keep, drop)` instead of `add_method_alias(keep, drop_id)`.

6. **Migration policy** — no mandatory one-shot DB migration: new fields absent on legacy nodes are optional; readers use `coalesce`. Re-ingest or a future backfill script may populate `normalized_name` / `aliases` / rich descriptions. Changing away from name-derived `Method.id` is **out of scope** for this ADR; a future ADR must define dual-key or remap if id strategy changes.

## Consequences

- Workspace graph and inspectors can expose `description_markdown` and related props when present ([frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) should list them).
- Benchmarks should add families for rich descriptions and ingest duplicate suppression ([method roadmap](../analysis/method-ontology-rich-description-and-dedup-roadmap-2026-04-27.md)).
- False merge remains a **hard** product risk; auto-merge only at high similarity and conservative LLM verdicts.

## References (code)

| Area | Path |
|------|------|
| Semantic models | `science_graphrag/domain/semantic_models.py` |
| Neo4j semantic write | `science_graphrag/storage/neo4j/writes/semantic.py` |
| Ingest entity dedup | `science_graphrag/dedup/entity_ingest_conflict_check.py` |
| Method dedup scan | `science_graphrag/dedup/method_pipeline.py` |
| Entity dedup API | `science_graphrag/api/entity_dedup.py` |
