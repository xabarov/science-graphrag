# ADR 018 — Ingest Worker: Redis + Dramatiq

**Date:** 2026-04-25  
**Status:** Accepted  
**Supersedes:** None (extends ADR 001-phase1-stack.md)

## Context

Waves U/V delivered stage visibility and SSE progress. The remaining bottleneck was
that `ingest_document` ran in `threading.Thread` inside the API process.
A restart could kill in-flight work. Horizontal scaling was limited.

Redis was already planned as a shared infra component (pub/sub bus for SSE and future
runtime needs). Adding a Dramatiq actor on top introduces one operational dependency.

## Decision

Add `redis:7-alpine` and a dedicated `worker` (Dramatiq) service to compose stacks.
`ingest_document_actor` becomes the entry point for long-running ingest.
API only enqueues jobs; `threading.Thread` launch is removed from ingest dispatch.
`IngestEventBus` uses Redis pub/sub for live cross-process streaming.
Job state and event history remain in Postgres as source of truth.

## Alternatives Considered

- **Postgres SKIP LOCKED only:** rejected — does not provide live pub/sub for SSE.
- **Celery:** rejected — additional complexity for current scope and load profile.
- **Kafka/Temporal:** rejected — overkill for single queue + worker pipeline.

## Consequences

- API restarts no longer directly terminate worker execution path.
- SSE live updates work across API/worker process boundaries via Redis pub/sub.
- New setting/env var: `SCIENCE_GRAPHRAG_REDIS_URL`.
- Wave W introduces compensation sweep for stale `queued` jobs at worker startup.
