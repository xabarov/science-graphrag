# Runbook: backup and restore

## Postgres

- Logical backup: `pg_dump` of database `science_graphrag` (or name from `POSTGRES_DB`).
- Restore: `psql` / `pg_restore` into empty database with same role permissions as `SCIENCE_GRAPHRAG_DATABASE_URL`.

## Neo4j

- Use Neo4j Admin `neo4j-admin database dump` (Enterprise/appropriate edition) or scheduled filesystem snapshots of `data/databases` per Neo4j operations guide.
- For dev, `neo4j-wipe` CLI destroys all nodes; **never** run in production without confirmation.

## Qdrant

- Backup `storage` directory for Qdrant or use snapshot API (`/collections/{name}/snapshots`) per Qdrant version docs.
- Collection name default: `SCIENCE_GRAPHRAG_QDRANT_COLLECTION` (`chunks`).

## Blob and artifact roots

- `SCIENCE_GRAPHRAG_BLOB_ROOT`: raw stored files (SHA-addressable).
- `SCIENCE_GRAPHRAG_ARTIFACT_ROOT`: generated `article.md`, `extraction_diagnostics.json`.
- Include both in filesystem backups if reproducibility of ingestion matters.

## Key material

- Store LLM and optional VL API keys in secret manager; **do not** commit `.env`.
- Rotate keys if benchmarks or logs may have leaked prompts with sensitive metadata.
