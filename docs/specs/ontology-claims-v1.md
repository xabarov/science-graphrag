# Ontology — claims / epistemic slice (v1 draft, Wave H1)

**Status:** production implementation **Wave O** — LLM extractor + Neo4j/Qdrant persistence behind `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` (default off); benchmark harness remains regression lock.

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
- Stub (tests / negative): `science_graphrag/ingestion/claims/stub.py`.
- Production: `science_graphrag/ingestion/claims/extractor.py` (`extract_claims_llm`) — evidence quote must be verbatim substring of a source chunk.

## Benchmark gate

No merge-blocking runner until a `tests/fixtures/benchmarks/**` case defines expected claim tuples.

**Implemented (advisory v1):** benchmark family spec and fixtures — [`ontology-claims-benchmark-v1.md`](../benchmarks/ontology-claims-benchmark-v1.md), `eval/claims/`, `tests/fixtures/benchmarks/claims/`. Optional `claim_match_mode=claim_id_or_normalized_text` supports extractor-agnostic scoring (see that doc).

**Extraction contract (Wave O):** [extraction/claims-extraction-v1.md](extraction/claims-extraction-v1.md).
