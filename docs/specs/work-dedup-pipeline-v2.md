# Work dedup pipeline v2 (Wave L)

**Status:** implemented (2026-04-24).  
**Supersedes** operational parts of [work-dedup-queue-v1.md](work-dedup-queue-v1.md) for smart dedup; key-only clusters remain available via `GET .../deduplication-candidates`.

## Goals

- Detect **near-duplicate** `Work` nodes inside a workspace using **embedding similarity** + optional **LLM judge**.
- Persist **review queue** in Postgres with idempotent **fingerprint** per workspace + pair.
- Apply merges through existing Neo4j merge + Qdrant repoint helpers.

## Data stores

| Store | Role |
|-------|------|
| Qdrant `work_embeddings` | Vector per `work_id`, payload `workspace_ids`, `embedding_model`, `kind=work_summary` |
| Qdrant `author_embeddings` | Vector per `author_id` (L2) |
| Postgres `work_dedup_conflicts` | Pending / resolved work pairs |
| Postgres `author_dedup_conflicts` | Pending / resolved author pairs |
| Postgres `work_dedup_merge_log` | Audit trail after successful work merge |

## Fingerprint

`sha256_hex(workspace_id + "|" + min(work_id_a,work_id_b) + "|" + max(...))` — unique per undirected pair within a workspace.

## HTTP API (workspace-scoped)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/v1/workspaces/{workspace_id}/dedup/scan` | Start background scan → `{ "job_id": "..." }` |
| `GET` | `/v1/ingest/jobs/{job_id}` | Poll scan job (reuses ingest job registry shape where possible) |
| `GET` | `/v1/workspaces/{workspace_id}/dedup/conflicts` | Query `status` (`pending`, `all`), `limit`, `offset` |
| `POST` | `/v1/workspaces/{workspace_id}/dedup/conflicts/{conflict_id}/decide` | Body: `decision`: `merge_a` \| `merge_b` \| `merge` \| `keep_separate` \| `skip`; with `merge`, set `keep_work_id` to `work_id_a` or `work_id_b` (alias for `merge_a` / `merge_b`) |
| `GET` | `/v1/workspaces/{workspace_id}/dedup/audit` | Recent rows from `work_dedup_merge_log` |
| `POST` | `/v1/workspaces/{workspace_id}/dedup/authors/scan` | Author dedup scan (L2) |
| `GET` | `/v1/workspaces/{workspace_id}/dedup/authors/conflicts` | List author conflicts |
| `POST` | `/v1/workspaces/{workspace_id}/dedup/authors/conflicts/{id}/decide` | Author merge / skip |
| `POST` | `/v1/workspaces/{workspace_id}/dedup/institutions/scan` | **Gated** — returns `gated: true` + message |

## Settings (`/v1/settings`)

Snapshot includes `work_dedup` object with effective thresholds and collection names (from `SCIENCE_GRAPHRAG_*` env).

## Workspace-tagged chunks (Wave K3)

Chunk points carry payload `workspace_ids` (array). Workspace-scoped `POST /v1/query` filters with `MatchAny` on that field. If the filter returns no hits while Neo4j still lists member works, the retriever retries once with `work_id IN (members)` and records `retrieval_trace.workspace_scope_payload_miss` (see [frontend-ui-api-contracts-v1.md](./frontend-ui-api-contracts-v1.md) §1).

## Merge semantics

- **Work**: `merge_a` keeps `work_id_a`, drops `work_id_b`; `merge_b` the inverse. **`merge` + `keep_work_id`** (must equal one side) is an equivalent alias for clients that prefer a single canonical id.
- **Author**: same pattern for `author_id_a` / `author_id_b`.
- After successful work merge: chunks + work-embedding payloads repointed; drop work removed from workspace membership.

## Non-goals (v1)

- Full **undo** / reverse-merge in API (log only).
- Institution merge automation (L3 gated).
