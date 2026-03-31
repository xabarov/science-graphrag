# Pilot checklist (Phase 7)

Use for a narrow scientific subdomain before widening scope.

## Preconditions

- [ ] Ingestion succeeds on 10–50 representative PDFs (metadata + references + optional semantic layer).
- [ ] Neo4j dedup audit acceptable or manual merges documented.
- [ ] Layer-1 and graph benchmarks green on merge-safe tier; nightly integration passes on target branch.

## Product checks

- [ ] **Navigation**: locate works by title/DOI/arXiv in Neo4j or forthcoming UI.
- [ ] **Retrieval**: `/v1/query` returns chunks with `work_id` / `chunk_fingerprint` for traceability.
- [ ] **Graph context**: methods and datasets appear for ingested works when semantic stage ran with LLM.
- [ ] **Latency**: median query under agreed budget on pilot hardware.

## Safety

- [ ] Answers labeled as non-generative concatenation when no second-stage LLM is enabled.
- [ ] Log retention and PII review for captured abstracts/authorship text.

## Exit

- [ ] Capture qualitative researcher feedback (useful / misleading citations).
- [ ] File backlog items: ontology expansion, merge CI graph case, idea-assist (post-MVP).
