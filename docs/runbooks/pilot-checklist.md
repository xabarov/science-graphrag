# Pilot checklist (Phase 7)

Use for a **narrow scientific subdomain** before widening scope. This document is the **pilot package** (Wave D): preconditions, KPI, and GO / NO-GO for starting and closing the pilot.

## Pilot target (fill in before launch)

| Field | Example / note |
|-------|----------------|
| **Domain** | e.g. computer vision / object detection (aligned with benchmark fixtures) |
| **Corpus size** | 10–50 representative PDFs (same order as roadmap Phase 7) |
| **Environment** | host or VM spec, `docker compose` stack version, API bind |
| **Branch / commit** | git ref frozen for pilot duration |
| **Owner** | who runs checklist and signs off |

## Preconditions (hard)

- [ ] **Wave A gate**: `eval/results/benchmark-metrics-summary.md` shows **GO** or **CONDITIONAL-GO** with **documented blockers** per [benchmark-decision-gate.md](benchmark-decision-gate.md). **NO-GO** → do not start pilot; complete Wave A first ([roadmap-next-waves.md](roadmap-next-waves.md)).
- [ ] Ingestion succeeds on 10–50 representative PDFs (metadata + references + optional semantic layer).
- [ ] Neo4j dedup audit acceptable or manual merges documented.
- [ ] Layer-1 and graph benchmarks green on merge-safe tier; nightly integration passes on target branch (`pytest -m integration` when services up).
- [ ] **Decision gate artifact**: run `.venv/bin/python scripts/aggregate_benchmark_metrics.py` and commit or archive the resulting `benchmark-metrics-summary.json` / `.md` with the pilot record.

## KPI (record numbers at start and end of pilot)

| KPI | How to measure | Target (set per pilot) |
|-----|----------------|-------------------------|
| Citation correctness | Manual spot-check on N answers (sample from `/v1/query` citations vs chunks) | e.g. ≥ agreed % |
| Retrieval trace completeness | Share of answers where `retrieval_trace` + `chunk_fingerprint` present when expected | e.g. 100% for non-empty retrieval |
| Latency `POST /v1/query` | p50 / p95 on pilot hardware (same load pattern) | e.g. p95 &lt; X ms |
| Latency `GET /v1/works` | p95 list load | e.g. p95 &lt; Y ms |
| Subjective usefulness | Short researcher survey or notes | qualitative |

## Product checks

- [ ] **Navigation**: locate works by title/DOI/arXiv via `GET /v1/works` / Neo4j or UI.
- [ ] **Mandatory API path** (see [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) *Mandatory API happy-path*): ingest → works → detail → query → chunks completes without 404 on required routes when graph is populated.
- [ ] **Retrieval**: `/v1/query` returns chunks with `work_id` / `chunk_fingerprint` for traceability when hits exist.
- [ ] **Reader API**: `GET /v1/works/{work_id}` and `GET /v1/works/{work_id}/chunks` return stable ids and text for evidence panels.
- [ ] **Graph context**: methods and datasets appear for ingested works when semantic stage ran with LLM.
- [ ] **Latency**: median query under agreed budget on pilot hardware.

## Safety

- [ ] Answers labeled as non-generative concatenation when no second-stage LLM is enabled.
- [ ] Log retention and PII review for captured abstracts/authorship text.

## Pilot GO / NO-GO (management)

| Decision | When |
|----------|------|
| **GO** | Preconditions met + KPI targets met or waived in writing + no new NO-GO from benchmark gate during pilot window. |
| **CONDITIONAL-GO** | Preconditions met with blockers listed (e.g. semantic gaps) + KPI partially met + explicit follow-up Wave A/B tasks. |
| **NO-GO / stop** | Reference lane breaks, unexplained citation failures above threshold, or `benchmark-metrics-summary` → **NO-GO**. |

## Exit

- [ ] Capture qualitative researcher feedback (useful / misleading citations).
- [ ] File backlog items: ontology expansion, merge CI graph case, idea-assist (post-MVP).
- [ ] Store pilot summary (1–2 pages): dates, KPI table, decision, link to committed `benchmark-metrics-summary` and git ref.
