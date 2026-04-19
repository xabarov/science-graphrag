# Ontology — claims / epistemic slice (v1 draft, Wave H1)

**Status:** draft — implementation gated by ADR 008 and benchmark cases.

## Goal

Represent **assertions anchored to works/chunks** without collapsing into a free-form chat graph.

## Node types (v1 draft)

| Label | Purpose |
|-------|---------|
| `Claim` | Normalized assertion (short text + optional polarity) |
| `Evidence` | Span/work linkage supporting a claim |
| `Contradiction` | Optional explicit conflict between claims |

## Relationships (sketch)

- `(Claim)-[:SUPPORTED_BY]->(Evidence)`
- `(Evidence)-[:ANCHORED_IN]->(:Work)` or chunk fingerprint linkage
- `(Claim)-[:CONTRADICTS]->(Claim)` when `Contradiction` not used

## Extraction

- Behind `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` (default off).
- Stub: `science_graphrag/ingestion/claims/stub.py`.

## Benchmark gate

No merge-blocking runner until a `tests/fixtures/benchmarks/**` case defines expected claim tuples.

**Implemented (advisory v1):** benchmark family spec and fixtures — [`ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md), `eval/claims/`, `tests/fixtures/benchmarks/claims/`.
