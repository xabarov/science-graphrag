# Wave D pilot — exit record

Template for closing the Phase 7 pilot. **Owner** field on the pilot checklist points here.

- **Pilot checklist:** [docs/runbooks/pilot-checklist.md](../runbooks/pilot-checklist.md)
- **Corpus runbook:** [docs/runbooks/pilot-corpus-wave-d.md](../runbooks/pilot-corpus-wave-d.md)

## Decision

| Field | Value |
|-------|-------|
| **Decision** | CONDITIONAL-GO |
| **Date** | 2026-04-06 |
| **Git ref** | `08009844b35c2a552ffef3c44dd7cafab644d593` (update when pilot window closes on a newer commit) |
| **Blockers (if any)** | Formal **10–50 PDF** bulk ingest on the default host corpus path may still need explicit sign-off in the checklist; **latency KPI** and a **single-query trace spot-check** recorded below (2026-04-06). Citation spot-check over N≥5 answers and subjective usefulness still open for owner. Product checks on pilot checklist remain partly manual. |

## KPI (start vs end)

| KPI | Start | End | Notes |
|-----|-------|-----|-------|
| Citation correctness (spot-check N) | — | — | Still: sample N≥5 from `/v1/query` vs chunks after pilot workload is frozen. |
| Retrieval trace completeness | — | **OK (spot-check)** | 2026-04-06, `POST /v1/query` probe (`object detection benchmark`, top_k=3): `hit_count=3`, all citations have `work_id` + `chunk_fingerprint`; trace includes `top_hit_scores`, `query_preview`, `answer_synthesis.second_stage_llm=false`. |
| p95 `POST /v1/query` | — | **~96 ms** | `BASE=http://127.0.0.1:8787 N=40` — p50 ≈ **82 ms**, p95 ≈ **96 ms**, max ≈ **149 ms** (`scripts/pilot_measure_latency.py`). |
| p95 `GET /v1/works` | — | **~34 ms** | Same run — p50 ≈ **18 ms**, p95 ≈ **34 ms**, max ≈ **36 ms**. |
| Subjective usefulness | — | — | Short researcher notes or survey. |

## Automated measurement snapshot (2026-04-06T22:47+03:00)

- **API:** `http://127.0.0.1:8787` (compose `api` + data plane).
- **Corpus signal at measure time:** `GET /v1/works?limit=1` → `total` = **38** works (sanity only; not a substitute for checklist ingest sign-off).
- **Raw latency JSON:**

```json
{
  "base": "http://127.0.0.1:8787",
  "works": {"n": 40, "p50_ms": 18.32, "p95_ms": 33.72, "max_ms": 35.54},
  "query": {"n": 40, "p50_ms": 81.85, "p95_ms": 96.00, "max_ms": 149.30}
}
```

## Integration / live services

**Full** happy-path and `pytest -m integration` require **live** Neo4j, Qdrant, Postgres (and LLM for semantic parity). Merge CI and `tests/test_api_smoke.py` cover contracts on mocks only — do not treat them as a substitute for compose-backed integration when signing off KPI that depend on retrieval and graph context.

**Wave D engineering slice (2026-04-06):** merge CI adds a **monkeypatched** sequence test (`works` → detail → chunks → `query`) and live-filesystem smoke for `GET /v1/benchmark/cases`. UI pages Workspace / Reader / Graph / Evidence call live `/v1/works*` when the API is available.

## Qualitative notes

- What worked for researchers:
- Misleading citations or gaps:
- Backlog items filed:
