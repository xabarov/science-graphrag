# ADR 001: Phase 1 technology stack

- **Status**: Accepted
- **Date**: 2026-03-30

## Context

Нужен локально воспроизводимый runnable MVP: ingestion, граф первого слоя, метаданные, векторы чанков.

## Decision

- **Language**: Python 3.11+.
- **Graph**: Neo4j (Cypher, драйвер `neo4j`).
- **Relational metadata**: PostgreSQL + SQLAlchemy 2.x.
- **Blobs**: локальный каталог с content-addressed именами (SHA-256).
- **Vectors**: Qdrant (HTTP API, клиент `qdrant-client`).
- **HTTP к реестрам**: `httpx` (OpenAlex, Crossref, ROR, ORCID — где применимо).
- **PDF text**: `pypdf` (без обязательного OCR на Phase 1).

## Consequences

- `docker-compose.yml` поднимает Neo4j, Postgres, Qdrant.
- Embeddings по умолчанию: **детерминированный hash-вектор** (без torch) для smoke/CI; опционально `pip install ".[embed]"` и `SCIENCE_GRAPHRAG_EMBEDDING_MODEL` для `sentence-transformers`.
- Для прод-качества позже: отдельный ADR на API-эмбеддер или фиксированную self-hosted модель.

## Links

- [phase-1-backbone.md](../architecture/phase-1-backbone.md)
