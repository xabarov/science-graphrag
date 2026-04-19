# Ontology expansion — Wave H backlog (post-benchmark gate)

**Depends on:** stable Phase 4 suites and Wave E/F quality gates ([roadmap](../roadmap.md), [roadmap-next-waves](../runbooks/roadmap-next-waves.md)).

## O1 — Epistemic / claims layer (Neo4j)

- **Entities (draft):** `Claim`, `Evidence`, optional `Contradiction` edges between claims.
- **Spec:** [ontology-claims-v1.md](ontology-claims-v1.md), ADR [008-ontology-claims-wave-h.md](../adr/008-ontology-claims-wave-h.md); code stub `science_graphrag/ingestion/claims/stub.py`.
- **Benchmark (advisory v1):** [ontology-claims-benchmark-v1.md](../benchmarks/ontology-claims-benchmark-v1.md), CLI `science-graphrag-claims-benchmark`, fixtures `tests/fixtures/benchmarks/claims/`.
- **Rule:** no new node types without at least one **benchmark case** or pilot rubric row.

## O2 — Author / institution merge catalog

- **Inputs:** Crossref, ORCID, expanded ROR usage (see Phase 1 deferred items in roadmap).
- **Deliverable:** [merge-catalog-wave-h.md](merge-catalog-wave-h.md), ADR [009-author-institution-merge-catalog.md](../adr/009-author-institution-merge-catalog.md), CLI `science-graphrag merge-catalog-audit` (pointer only until clients land).

## O3 — Automatic `Work` dedup merge

- **Today:** Neo4j audit detects duplicate clusters; merge is manual / CLI-assisted; reporting: `science-graphrag work-dedup-report` ([work-dedup-queue-v1.md](work-dedup-queue-v1.md), ADR [010-work-dedup-review-queue.md](../adr/010-work-dedup-review-queue.md)).
- **Target:** safe auto-merge when DOI + OpenAlex id + fingerprint agree under configurable policy; human review queue for ambiguous clusters.

## Sequencing

1. Close teacher-gold audit and retrieval benchmark scaffold ([retrieval-eval-v1.md](../benchmarks/retrieval-eval-v1.md)).
2. O1 spec + minimal extraction stage behind feature flag.
3. O2 registry clients (rate limits + cache).
4. O3 automation last (highest operational risk).
