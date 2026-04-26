# ADR 022: Reader full text from canonical ingest artifacts vs Qdrant chunks

- **Status**: Accepted
- **Date**: 2026-04-26

## Context

The reader UI treated **Qdrant chunk payloads** as the only source of extracted article text. Ingest already writes markdown under `artifact_root`, but paths were partly slug-based and `BlobStore.write_text("extracted.txt", …)` wrote to a **random** `derived/{uuid}/` path with no durable link to `document_id`. The Works API also marked `sources.markdown.available` from **chunk count**, conflating “indexed for retrieval” with “extracted text exists”.

## Decision

1. **Canonical document-scoped artifacts** (under `artifact_root`, relative paths):
   - `ingestion/{document_id}/article.md` — raw VL / PDF extraction (with optional HTML comment header).
   - `ingestion/{document_id}/normalized.md` — normalized body used for LLM extraction and chunking (`strip_repeated_boilerplate(normalize_text(…))`).
2. **Full-text reading** for the UI and new **`GET /v1/works/{work_id}/extracted-body`** prefers `normalized.md`, then `article.md` (header stripped when serving from `article.md`). Legacy per-slug paths under `ingestion/{document_id}/{slug}/article.md` remain readable as a fallback until re-ingest.
3. **Qdrant** remains the source of truth for **vector retrieval**, chunk fingerprints, and citations — not the sole indicator that post-ingest text exists.
4. **No new SQL column** in v1 of this ADR: `document_id` already keys the artifact directory; optional `DocumentRecord.extracted_body_path` remains a future optimization if multi-artifact policies grow.

## Consequences

- Reader and `GET …/sources` can show markdown/text **even when `chunks.total == 0`** (e.g. embed stage failed or Qdrant cleared).
- Operators must treat `artifact_root` as part of backup/restore alongside Postgres blobs and Qdrant.
- See [frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) for API fields and endpoint contract.

## Related

- Ingest: [`science_graphrag/ingestion/_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py)
- Layout constants: [`science_graphrag/ingestion/artifact_layout.py`](../../science_graphrag/ingestion/artifact_layout.py)
- API: [`science_graphrag/api/works/detail.py`](../../science_graphrag/api/works/detail.py), [`science_graphrag/api/works/router.py`](../../science_graphrag/api/works/router.py)
