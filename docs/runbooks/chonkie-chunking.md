# Chonkie chunking rollout

This runbook covers baseline, success criteria, identity strategy, A/B evaluation, and operational rollout for `SCIENCE_GRAPHRAG_CHUNKING_ENGINE=chonkie_recursive`.

## Baseline (legacy engine)

The legacy path lives in `science_graphrag/ingestion/chunking.py`:

- Section boundaries from ATX Markdown headings (`#` … `######`) via `_heading_sections`.
- Within each section, paragraph packing under an approximate token budget (`approx_tokens`, ~4 characters per token).
- Optional overlap between consecutive chunks in the same section via `_overlap_tail` and `overlap_prev` / `overlap_next`.
- Stable `chunk_fingerprint` from `section_path`, normalized body text, and `index_in_section`.

**Baseline metrics to capture before comparing engines** (on a fixed sample of `normalized.md` artifacts):

- Chunks per document (count).
- Distribution of chunk text length (min / median / p95).
- Share of chunks with `overlap_prev` (legacy only; Chonkie path currently keeps overlap flags false unless extended later).

**Retrieval baseline**: run the portable retrieval tier (cases without hard-coded `required_chunk_fingerprints`) using `science-graphrag-retrieval-benchmark` and record pass rate and key metrics from each case’s `gold.json`.

## Success criteria (“definition of better”)

1. **Correctness**: all unit and integration tests pass; ingest produces Qdrant payloads with required chunk fields.
2. **No silent regressions**: merge-safe retrieval suite does not regress vs legacy baseline on the same re-indexed corpus.
3. **Quality**: on the chosen A/B document set, either improved retrieval scores (per-case `passed`, hit counts, answer metrics in gold) or neutral scores with a documented structural win (e.g. fewer pathological splits).

## Identity strategy (compatibility-first, Variant A)

Default `chonkie_recursive` implementation:

- Keeps `_heading_sections` for `section_path` (same strings as legacy).
- Uses Chonkie `RecursiveChunker` **only inside each section block** to choose split boundaries.
- Keeps `_fingerprint`, `_normalize_for_fingerprint`, `dedupe_chunks_for_embedding`, and `DocumentChunk` field semantics unchanged.
- `overlap_tokens` is accepted for API compatibility but **not** applied in the Chonkie path yet (chunks are contiguous; `overlap_prev` / `overlap_next` are false). Extending overlap to match legacy is a follow-up.

**Variant B (migration-first)** — changing fingerprint rules or section policy — requires re-indexing Qdrant, refreshing retrieval gold that references `required_chunk_fingerprints`, and re-running or backfilling claims evidence. Do not enable without an explicit migration plan.

## A/B evaluation (honest comparison)

1. Use **two separate** Qdrant collection names (or two isolated environments), e.g. `chunks_legacy` vs `chunks_chonkie`.
2. Re-ingest the **same** normalized documents under each configuration (`SCIENCE_GRAPHRAG_CHUNKING_ENGINE=legacy` vs `chonkie_recursive`).
3. Run `science-graphrag-retrieval-benchmark` on **portable** cases: `required_chunk_fingerprints` empty or absent, or `contract_only` flows that do not depend on historical fingerprints.
4. For cases with non-empty `required_chunk_fingerprints`, either exclude from A/B or **regenerate gold** after re-chunking.
5. Compare JSON reports with `science-graphrag-benchmark-compare` where applicable.

## Rollout and configuration

| Setting | Meaning |
|--------|---------|
| `SCIENCE_GRAPHRAG_CHUNKING_ENGINE` | `chonkie_recursive` (default) or `legacy` |
| `SCIENCE_GRAPHRAG_CHUNKING_CHONKIE_RECIPE` | Recipe name passed to `RecursiveChunker.from_recipe` (default `markdown`) |
| `SCIENCE_GRAPHRAG_CHUNKING_CHONKIE_LANG` | Recipe language code (default `en`) |
| `SCIENCE_GRAPHRAG_CHUNKING_CHONKIE_MIN_CHARACTERS_PER_CHUNK` | Chonkie `min_characters_per_chunk` (default `24`) |

**Dependencies**: `chonkie` and `jsonschema` are required for `chonkie_recursive` (recipes validate via jsonschema).

**Operational steps to switch production corpus**

1. Decide collection strategy (new collection vs full re-index in place).
2. Set `SCIENCE_GRAPHRAG_CHUNKING_ENGINE=chonkie_recursive`, run ingest / backfill for all documents.
3. If fingerprints changed (not the case for Variant A as implemented: same formula, different splits may still change fingerprints — **splits change text bodies, so fingerprints will change**). Under the current Variant A, section paths match legacy but **chunk text and boundaries differ**, so `chunk_fingerprint` values **will** change vs legacy for the same document. Treat rollout like any chunk-boundary change: re-embed Qdrant, refresh fingerprint-dependent gold, and re-run claims if you rely on stable fingerprints across releases.

**Clarification**: Variant A preserves the *formula* for fingerprints, not the *values* across engines. Comparing legacy vs Chonkie on the same document will produce different fingerprints whenever chunk text differs. For strict citation regression against old fingerprints, use `legacy` or regenerate gold after moving to `chonkie_recursive`.

## Code entry points

- `chunk_document_for_retrieval(..., engine=...)` in `science_graphrag/ingestion/chunking.py`
- `chunk_document_for_retrieval_from_settings(text, settings)` for pipeline and resume paths
- Ingest: `science_graphrag/ingestion/_pipeline_impl.py`, `science_graphrag/ingestion/resume_ingest.py`
- Stage helper: `science_graphrag/ingestion/stages/chunking.py`
