# Pilot checklist (Phase 7)

Use for a **narrow scientific subdomain** before widening scope. This document is the **pilot package** (Wave D): preconditions, KPI, and GO / NO-GO for starting and closing the pilot.

## Pilot target (fill in before launch)

| Field | Wave D (2026-04-06) |
|-------|---------------------|
| **Domain** | Computer vision / object detection (aligned with benchmark fixtures) |
| **Corpus size** | 10–50 representative PDFs — ingest and corpus notes: [pilot-corpus-wave-d.md](pilot-corpus-wave-d.md) |
| **Environment** | `docker compose` stack per [deploy.md](deploy.md) (Neo4j, Postgres, Qdrant; optional API on 8787) |
| **Branch / commit** | `e9afc0f9ec1caae718d544607f1f5843a06a6881` (frozen ref for pilot window) |
| **Owner** | Sign-off and KPI capture: [docs/pilot/wave-d-exit-record.md](../pilot/wave-d-exit-record.md) |

## Preconditions (hard)

- [x] **Wave A gate**: `eval/results/benchmark-metrics-summary.md` shows **GO** or **CONDITIONAL-GO** with **documented blockers** per [benchmark-decision-gate.md](benchmark-decision-gate.md). **NO-GO** → do not start pilot; complete Wave A first ([roadmap-next-waves.md](roadmap-next-waves.md)). *Snapshot: **GO** (2026-04-06).*
- [ ] Ingestion succeeds on 10–50 representative PDFs (metadata + references + optional semantic layer). *Procedure:* [pilot-corpus-wave-d.md](pilot-corpus-wave-d.md) (default host corpus path and `./scripts/pilot_ingest_cv_corpus.sh` documented there).
- [ ] Neo4j dedup audit acceptable or manual merges documented (*dedup / merge:* [deploy.md](deploy.md) ingest section).
- [x] Layer-1 and graph benchmarks green on merge-safe tier; nightly integration passes on target branch (`pytest -m integration` when services up).
- [x] **Decision gate artifact**: run `.venv/bin/python scripts/aggregate_benchmark_metrics.py` and commit or archive the resulting `benchmark-metrics-summary.json` / `.md` with the pilot record. *Regenerated 2026-04-06.*

## KPI (record numbers at start and end of pilot)

| KPI | How to measure | Target (set per pilot) |
|-----|----------------|-------------------------|
| Citation correctness | Manual spot-check on N answers (sample from `/v1/query` citations vs chunks) | e.g. ≥ agreed % |
| Retrieval trace completeness | Share of answers where `retrieval_trace` + `chunk_fingerprint` present when expected | e.g. 100% for non-empty retrieval |
| Latency `POST /v1/query` | p50 / p95 on pilot hardware (same load pattern) | e.g. p95 &lt; X ms |
| Latency `GET /v1/works` | p95 list load | e.g. p95 &lt; Y ms |
| Subjective usefulness | Short researcher survey or notes | qualitative |

## Repository automation (Wave D engineering, 2026-04-06)

- [x] **Compose + mini ingest:** `docker compose up -d`; `science-graphrag ingest-corpus` on a 2-PDF smoke directory completed successfully; Neo4j dedup audit reported OK for that run.
- [x] **API smoke:** `tests/test_api_smoke.py` includes mandatory-path sequence + `/v1/benchmark/cases` list (merge CI).
- [x] **UI live surfaces:** `ui/` Workspace / Reader / Graph / Evidence use `GET /v1/works*` against the configured API (same-origin or `VITE_API_BASE_URL`); Ask links citations to Reader/Evidence when `work_id` is present.

## Product checks

- [ ] **Navigation**: locate works by title/DOI/arXiv via `GET /v1/works` / Neo4j or UI (re-validate on **full** pilot corpus after bulk ingest).
- [ ] **Mandatory API path** (see [specs/frontend-ui-api-contracts-v1.md](../specs/frontend-ui-api-contracts-v1.md) *Mandatory API happy-path*): ingest → works → detail → query → chunks completes without 404 on required routes when graph is populated (repeat after full corpus).
- [ ] **Retrieval**: `/v1/query` returns chunks with `work_id` / `chunk_fingerprint` for traceability when hits exist.
- [ ] **Reader API**: `GET /v1/works/{work_id}` and `GET /v1/works/{work_id}/chunks` return stable ids and text for evidence panels.
- [ ] **Graph context**: methods and datasets appear for ingested works when semantic stage ran with LLM.
- [ ] **Latency**: median query under agreed budget on pilot hardware.

## Safety

- [ ] Answers labeled as non-generative concatenation when no second-stage LLM is enabled.
- [ ] Log retention and PII review for captured abstracts/authorship text.

*Engineering note (2026-04-06):* verify `/v1/query` payload and UI Ask page match deployed synthesis mode before pilot users touch the system.

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

**Interim record (2026-04-06):** [docs/pilot/wave-d-exit-record.md](../pilot/wave-d-exit-record.md) updated to **CONDITIONAL-GO** with explicit blockers (full corpus ingest + KPI still open). Replace with final GO/NO-GO when the pilot window closes.

