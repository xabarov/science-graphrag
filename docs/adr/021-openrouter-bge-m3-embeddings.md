# ADR 021 — OpenRouter `baai/bge-m3` as the canonical embedding provider

## Status

Accepted — 2026-04-25 (implemented in code: `SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL`, `resolve_embedder`, CLI `qdrant-recreate-embedding-collections`)

**Implementation note (2026-04-26):** CI and fresh clones keep `openrouter_embedding_model` **unset** so `resolve_embedder` falls back to `HashEmbeddingProvider` (384-dim) without network. Production / benchmark hosts set `SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL=baai/bge-m3` and `SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_DIM=1024`, then run `science-graphrag qdrant-recreate-embedding-collections` and re-ingest per §Migration plan.

## Context

Current production state (audited 2026-04-25):

- All Qdrant collections (`chunks`, `work_embeddings`, `claims`, `methods`,
  `datasets`, `authors`, `venues`, `institutions`) are created with
  `vector_size = 384` and populated by the deterministic `HashEmbeddingProvider`
  fallback in `science_graphrag/ingestion/embeddings.py`.
- `SCIENCE_GRAPHRAG_EMBEDDING_MODEL` is **not set** in `.env` for the audited hosts;
  only prefixed `SCIENCE_GRAPHRAG_*` keys are read by `Settings`.
- Net effect: vector search across the corpus runs on 956 hash-vectors, which
  explains the volatility and "phantom-green" behaviour seen in BT2 (workspace
  retrieval) and BT4 (hybrid ablation) audits.
- Phase 6.D introduced an OpenRouter-backed `OpenRouterEmbeddingProvider`
  (`science_graphrag/embeddings/openrouter_provider.py`) for the dual-validate
  cascade matcher. It already:
  - implements the historic `EmbeddingProvider` Protocol (`dim`, `embed(texts)`),
  - persists per-text vectors as JSON on disk under
    `eval/dual_validate/embeddings_cache/<model>/`,
  - batches up to 64 inputs per OpenRouter call and retries once on transient
    rate-limit / API errors,
  - lazily discovers `dim` from the first embedding (1024 for `baai/bge-m3`).

## Decision

1. Promote `OpenRouterEmbeddingProvider` from a dual-validate-only helper to the
   **canonical embedding provider** for Qdrant ingestion, retrieval and dedup
   pipelines when explicitly enabled.
2. Production toggle: **`SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL`** (e.g.
   `baai/bge-m3`). Declared width: **`SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_DIM`**
   (default 1024 for `baai/bge-m3`). Disk cache root:
   **`SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_CACHE_ROOT`** (default `./data/embeddings_cache`).
   Credentials / base URL follow `resolve_openrouter_embedding_settings` (same as
   LLM: `SCIENCE_GRAPHRAG_EXTRACTION_LLM_*` or `SCIENCE_GRAPHRAG_BENCHMARK_TEACHER_LLM_*`).
3. Keep **`SCIENCE_GRAPHRAG_EMBEDDING_MODEL`** for **sentence-transformers** only
   (local HuggingFace ids). Selection order in `resolve_embedder`: OpenRouter if
   `openrouter_embedding_model` is set; else sentence-transformers if the model
   loads; else `HashEmbeddingProvider` (CI / smoke when both unset).
4. Recreate Qdrant collections with `vector_size = 1024` and re-ingest the
   pinned corpus (35+ object-detection papers) before any retrieval-side
   benchmarks rerun. Old hash-only collections (`chunks/work_embeddings/claims`)
   are dropped, not migrated.

## Consequences

### Positive

- BT2 / BT4 retrieval finally measures real semantic ranking instead of hash
  collisions. Expected absolute gains: BT4 hybrid mAP +0.2-0.4, BT2 abstain
  recall stable but precision higher.
- Ingestion uses `data/embeddings_cache` by default; eval dual-validate keeps its
  own default under `eval/dual_validate/embeddings_cache` unless overridden.
- ADR 015 (`Work.title_embedding` Neo4j vector index) remains valid; we just
  switch its source vectors from 384 to 1024 dims.

### Negative / risk

- **Hard cutover required**: 1024 ≠ 384, Qdrant collections must be dropped
  and recreated. `chunks` (956 pts) and `work_embeddings` (6 pts) need full
  reingest of the corpus. `claims` (0 pts) is a no-op.
- All retrieval benchmarks (BT1, BT2, BT3, BT4, BT5) need to be re-run; some
  may regress until thresholds are retuned (especially anything that hard-codes
  cosine cut-offs against hash-vector noise).
- Outbound network dependency: ingestion now requires OpenRouter availability.
  Gracefully degrade to `HashEmbeddingProvider` only when explicitly configured
  (CI / offline tests), never silently in production.
- Cost ceiling at current corpus scale (~35 papers × ~30 chunks × ~600 tokens
  ≈ 0.6 M tokens / full reindex): under $0.01 per full reindex. Negligible.

## Out of scope (this ADR)

- Per-collection dimensions (e.g. one model for `chunks`, another for `authors`):
  out of scope. Phase 1 of the migration uses a single model everywhere.
- Embedding quantisation in Qdrant (`scalar`, `binary`): tracked separately if
  storage becomes an issue.
- Replacing OpenRouter with a self-hosted bge-m3 (vLLM / TEI). Decision held
  until first quarterly cost / latency review.

## Migration plan (ops)

Step-by-step runbook (dry-run, recreate, ingest, benchmarks): [`docs/runbooks/phase0-bge-m3-qdrant-cutover.md`](../runbooks/phase0-bge-m3-qdrant-cutover.md).

1. Set `SCIENCE_GRAPHRAG_OPENROUTER_EMBEDDING_MODEL` / `_DIM` in `.env` (see `.env.example`).
2. Run **`science-graphrag qdrant-recreate-embedding-collections --dry-run`**, then without `--dry-run` (drops and recreates
   chunks, work_embeddings, claims, author_embeddings, entity dedup collections).
3. Reingest corpus / `scripts/backfill_work_embeddings.py` as needed.
4. Rerun BT1–BT5 retrieval benchmarks.

Code entrypoints: `resolve_embedder` / `resolve_embedding_dim(settings=...)` in
`science_graphrag/ingestion/embeddings.py`, `recreate_all_embedding_collections` in
`science_graphrag/storage/qdrant_store/recreate_embedding_collections.py`.

## Related

- [`015-neo4j-vector-index-work-title-embedding.md`](015-neo4j-vector-index-work-title-embedding.md)
- [`019-entity-dedup-pipeline.md`](019-entity-dedup-pipeline.md)
- [`../analysis/corpus-gold-pack-v1-2026-04-25.md`](../analysis/corpus-gold-pack-v1-2026-04-25.md) (Phase 6.D)
- [`../analysis/ontology-benchmarks-trust-audit-2026-04-25.md`](../analysis/ontology-benchmarks-trust-audit-2026-04-25.md) (BT2/BT4)
