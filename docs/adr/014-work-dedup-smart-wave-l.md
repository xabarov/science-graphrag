# ADR 014 — Smart dedup (Wave L): embeddings + LLM + Postgres review queue

## Status

Accepted — 2026-04-24

## Context

[ADR 010](010-work-dedup-review-queue.md) scoped a **read-only** work-dedup report; Neo4j still only detected duplicates by **hard keys** (DOI, arXiv, fingerprint). Scholarly corpora need **near-duplicate** detection (preprint vs journal, spelling variants) with **human-in-the-loop** merge, aligned with [workspace experience gap §6 Wave L](../analysis/_archive/workspace-experience-gap-2026-04-24.md).

## Decision

1. **Review queue in Postgres** (not Neo4j): tables `work_dedup_conflicts`, `work_dedup_merge_log`, `author_dedup_conflicts` — created via SQLAlchemy `Base.metadata.create_all` on existing `init_db()` path.
2. **Work summary vectors** in a dedicated Qdrant collection (`qdrant_work_embeddings_collection`, default `work_embeddings`): one point per `work_id`, payload `workspace_ids`, `embedding_model`, `kind=work_summary`.
3. **Scan algorithm**: for each work in a workspace, top-k cosine neighbors within the same workspace collection scope; **low / high** thresholds from `Settings`; middle band uses **LLM judge** (`SyncInstructorExtractor`, same credentials as extraction LLM) when `work_dedup_llm_mode` is `embedding_with_llm`.
4. **Idempotence**: conflict fingerprint = `sha256(sorted(work_id_a, work_id_b))` per `workspace_id`; duplicate fingerprints are skipped on re-scan.
5. **Merge**: reuse `Neo4jGraphStore.merge_work_into_canonical`; **rebind** `HAS_AUTHorship` from drop work to keep work before `DETACH DELETE` (fixes prior block on authored papers). Qdrant: `repoint_work_id_payload` on chunks + work-embedding payload update for `work_id`.
6. **Author dedup (L2)**: separate collection `author_embeddings` + `author_dedup_conflicts`; merge via `merge_author_into_canonical` (rebind `OF_AUTHOR` on `Authorship` nodes).
7. **Institution / Venue (L3)**: API returns **gated** empty result until [merge-catalog-wave-h](../specs/merge-catalog-wave-h.md) + ROR/OpenAlex policy is wired; no silent graph edits.

## Consequences

- New HTTP routes under `/v1/workspaces/{id}/dedup/*` (see [work-dedup-pipeline-v2.md](../specs/work-dedup-pipeline-v2.md)).
- Ingest path gains a **best-effort** work-summary upsert after chunk embedding (same embedder dimension as chunks).
- **Reverse merge** is not automated in v1; `work_dedup_merge_log` records merges for future CLI/admin tooling.

## Related

- Supersedes operational detail of [ADR 010](010-work-dedup-review-queue.md) for automated queue + UI (010 remains valid for CLI report scope).
- Spec: [work-dedup-pipeline-v2.md](../specs/work-dedup-pipeline-v2.md).
