# ADR 008 — Epistemic / claims ontology (Wave H1, gated)

## Status

Accepted (scaffold) — 2026-04-19

## Context

North-star product includes claim-level reasoning. Layer-1/2 scholarly backbone and semantic `Method`/`Dataset` are stable enough to plan the next slice, but expanding Neo4j without benchmark coverage caused ontology drift in earlier projects.

## Decision

Introduce a **gated** epistemic slice (`Claim`, `Evidence`, optional `Contradiction`) documented in [specs/ontology-claims-v1.md](../specs/ontology-claims-v1.md). No merge-blocking extraction until:

1. At least one benchmark case in `tests/fixtures/benchmarks/` (new family or extension) encodes expected claims; and
2. ADR + spec are merged; and
3. `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` defaults to **false**.

Code entrypoint: `science_graphrag/ingestion/claims/stub.py` (returns empty list) until the real stage lands.

## Consequences

- Product can reference stable module paths without enabling risky extraction.
- Benchmark gate prevents silent graph bloat.
