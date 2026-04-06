# Wave D pilot — exit record

Template for closing the Phase 7 pilot. **Owner** field on the pilot checklist points here.

- **Pilot checklist:** [docs/runbooks/pilot-checklist.md](../runbooks/pilot-checklist.md)
- **Corpus runbook:** [docs/runbooks/pilot-corpus-wave-d.md](../runbooks/pilot-corpus-wave-d.md)

## Decision

| Field | Value |
|-------|-------|
| **Decision** | CONDITIONAL-GO |
| **Date** | 2026-04-06 |
| **Git ref** | `b2886bc66e2c2d4676be38b5915f71082fc63bed` (refresh when pilot window closes) |
| **Blockers (if any)** | **Subjective usefulness** (owner notes / survey). **Bulk ingest** row on [pilot-checklist.md](../runbooks/pilot-checklist.md) still requires explicit sign-off if the deployed corpus path or size differs from the environment used for KPI. Engineering: **N≥5 automated citation probes** + latency snapshot below; `retrieval_trace.retrieval_policy` available for pilot debugging. |

## KPI (start vs end)

| KPI | Start | End | Notes |
|-----|-------|-----|-------|
| Citation correctness (spot-check N) | — | **OK (automated N=5)** | `BASE=… ./scripts/pilot_spot_check.sh` — five fixed queries; structural checks passed on compose-backed API (2026-04-06). Warnings allowed for legacy citations missing `chunk_fingerprint` if `document_id` present. |
| Retrieval trace completeness | — | **OK (spot-check)** | Same run: traces include `hit_count`, `top_hit_scores`, `query_preview`, `retrieval_policy` (e.g. section boost + back-matter deprioritization); `answer_synthesis.second_stage_llm=false` when field present. |
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

## Spot-check script (N≥5)

```bash
# API must serve /v1/query (e.g. compose on 8787)
BASE=http://127.0.0.1:8787 ./scripts/pilot_spot_check.sh
```

Writes JSON summary to stdout; exit code 0 means all probes passed structural gates. Use with the same corpus you are signing off for the pilot.

## Qualitative notes

- What worked for researchers:
- Misleading citations or gaps:
- Backlog items filed:
