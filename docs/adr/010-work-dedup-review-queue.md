# ADR 010 — Work dedup review queue (Wave H3, gated)

## Status

Accepted (scaffold) — 2026-04-19

## Context

Neo4j exposes duplicate `Work` clusters via `Neo4jGraphStore.find_work_dedup_violations()`. Manual `merge-work` exists; automation needs human review.

## Decision

1. Operator command `science-graphrag work-dedup-report` lists clusters (JSON or text).
2. Automated merge / queue persistence waits for policy in [specs/work-dedup-queue-v1.md](../specs/work-dedup-queue-v1.md) and benchmark/pilot gates.

## Consequences

- Safe read-only reporting today; no silent graph edits.
