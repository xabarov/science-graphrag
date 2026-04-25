# ADR 019: Entity Dedup Pipeline — Author / Institution / Venue / Method / Dataset

**Status:** Accepted  
**Date:** 2026-04-25  
**Supersedes:** ADR 009 (author-institution-merge-catalog) — partially; ADR 010 (work-dedup-review-queue) — extension.

## Context

Waves L1 and L2 delivered Work and Author dedup with separate Postgres queue tables.
Wave T generalizes the approach for Institution, Venue, Method, and Dataset and
introduces a unified `entity_dedup_conflicts` queue with `entity_type` to simplify
review APIs and support one UI page with type tabs.

## Decision

1. Use unified Postgres table `entity_dedup_conflicts` (`entity_type` in
   `{work, author, institution, venue, method, dataset}`).
   `WorkDedupConflict` and `AuthorDedupConflict` stay as legacy backward-compatible tables.
2. Introduce per-type dedup pipelines in `science_graphrag/dedup/*_pipeline.py`
   following the established Work/Author scan pattern.
3. Use thresholds:
   - `sim >= 0.95` => auto-merge;
   - `0.80 <= sim < 0.95` => queue for user decision;
   - `sim < 0.80` => skip.
4. Keep dedicated Qdrant collections for entity-level candidate search:
   `institutions`, `venues`, `methods`, `datasets`.
5. For Method and Dataset conflicts, default merge action is alias-merge
   (`aliases[]` update) without destructive node merge.

## Consequences

- Unified API paths for entity review (`/v1/dedup/entity/*`) become possible.
- `workspace_dedup` legacy endpoints for Work/Author stay intact during transition.
- Neo4j write split architecture supports type-specific writes without growing
  monolithic storage modules.
