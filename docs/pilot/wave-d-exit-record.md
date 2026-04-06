# Wave D pilot — exit record

Template for closing the Phase 7 pilot. **Owner** field on the pilot checklist points here.

- **Pilot checklist:** [docs/runbooks/pilot-checklist.md](../runbooks/pilot-checklist.md)
- **Corpus runbook:** [docs/runbooks/pilot-corpus-wave-d.md](../runbooks/pilot-corpus-wave-d.md)

## Decision

| Field | Value |
|-------|-------|
| **Decision** | CONDITIONAL-GO |
| **Date** | 2026-04-06 |
| **Git ref** | `e9afc0f9ec1caae718d544607f1f5843a06a6881` (update when pilot window closes on a newer commit) |
| **Blockers (if any)** | Full **10–50 PDF** bulk ingest on default CV corpus not executed in this iteration (mini 2-PDF ingest + compose verified). KPI table (p95 latency, spot-check citations, subjective usefulness) not filled — owner to complete after full corpus. Product checks in pilot checklist remain manual for full graph. |

## KPI (start vs end)

| KPI | Start | End | Notes |
|-----|-------|-----|-------|
| Citation correctness (spot-check N) | — | — | Run after full corpus; sample N answers from `/v1/query` vs `GET /v1/works/{id}/chunks`. |
| Retrieval trace completeness | — | — | Expect `chunk_fingerprint` / `work_id` when hits exist. |
| p95 `POST /v1/query` | — | — | Same hardware + load pattern; e.g. `hey`/`curl` repeated timings or `wrk` against local API. |
| p95 `GET /v1/works` | — | — | Same as above. |
| Subjective usefulness | — | — | Short researcher notes or survey. |

## Integration / live services

**Full** happy-path and `pytest -m integration` require **live** Neo4j, Qdrant, Postgres (and LLM for semantic parity). Merge CI and `tests/test_api_smoke.py` cover contracts on mocks only — do not treat them as a substitute for compose-backed integration when signing off KPI that depend on retrieval and graph context.

**Wave D engineering slice (2026-04-06):** merge CI adds a **monkeypatched** sequence test (`works` → detail → chunks → `query`) and live-filesystem smoke for `GET /v1/benchmark/cases`. UI pages Workspace / Reader / Graph / Evidence call live `/v1/works*` when the API is available.

## Qualitative notes

- What worked for researchers:
- Misleading citations or gaps:
- Backlog items filed:
