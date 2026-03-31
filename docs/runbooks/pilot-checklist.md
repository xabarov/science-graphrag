# Pilot checklist (Phase 7)

Use for a narrow scientific subdomain before widening scope.

## Preconditions

- [ ] Ingestion succeeds on 10–50 representative PDFs (metadata + references + optional semantic layer).
- [ ] Neo4j dedup audit acceptable or manual merges documented.
- [ ] Layer-1 and graph benchmarks green on merge-safe tier; nightly integration passes on target branch.
- [ ] **Decision gate**: run `.venv/bin/python scripts/aggregate_benchmark_metrics.py` and confirm `eval/results/benchmark-metrics-summary.md` is **GO** or **CONDITIONAL-GO** with documented blockers (see [benchmark-decision-gate.md](benchmark-decision-gate.md)).
- [ ] **KPI snapshot** (pilot): record citation correctness (manual spot-check), retrieval hit rate on held-out questions, `p95` latency for `POST /v1/query` and `GET /v1/works` on pilot hardware.

## Product checks

- [ ] **Navigation**: locate works by title/DOI/arXiv via `GET /v1/works` / Neo4j or UI.
- [ ] **Retrieval**: `/v1/query` returns chunks with `work_id` / `chunk_fingerprint` for traceability.
- [ ] **Reader API**: `GET /v1/works/{work_id}` and `GET /v1/works/{work_id}/chunks` return stable ids and text for evidence panels.
- [ ] **Graph context**: methods and datasets appear for ingested works when semantic stage ran with LLM.
- [ ] **Latency**: median query under agreed budget on pilot hardware.

## Safety

- [ ] Answers labeled as non-generative concatenation when no second-stage LLM is enabled.
- [ ] Log retention and PII review for captured abstracts/authorship text.

## Exit

- [ ] Capture qualitative researcher feedback (useful / misleading citations).
- [ ] File backlog items: ontology expansion, merge CI graph case, idea-assist (post-MVP).
