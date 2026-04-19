# Wave D pilot — exit record

Template for closing the Phase 7 pilot. **Owner** field on the pilot checklist points here.

- **Pilot checklist:** [docs/runbooks/pilot-checklist.md](../runbooks/pilot-checklist.md)
- **Corpus runbook:** [docs/runbooks/pilot-corpus-wave-d.md](../runbooks/pilot-corpus-wave-d.md)

## Decision

| Field | Value |
|-------|-------|
| **Decision** | CONDITIONAL-GO |
| **Date** | 2026-04-06 |
| **Git ref** | Refresh on close of pilot window (record HEAD at sign-off time). |
| **Blockers (if any)** | **Subjective usefulness** (owner rubric below — still pending narrative). **Bulk ingest** row on [pilot-checklist.md](../runbooks/pilot-checklist.md) still requires explicit sign-off if the deployed corpus path or size differs from the environment used for KPI. Engineering: **N≥5 automated citation probes** + latency snapshot — **done** for the 2026-04-06 snapshot; re-run after corpus grows past ~50 works. |

## KPI (start vs end)

| KPI | Start | End | Notes |
|-----|-------|-----|-------|
| Citation correctness (spot-check N) | — | **OK (automated N=5)** | `BASE=… ./scripts/pilot_spot_check.sh` — five fixed queries; structural checks passed on compose-backed API (2026-04-06). Warnings allowed for legacy citations missing `chunk_fingerprint` if `document_id` present. |
| Retrieval trace completeness | — | **OK (spot-check)** | Same run: traces include `hit_count`, `top_hit_scores`, `query_preview`, `retrieval_policy` (e.g. section boost + back-matter deprioritization); `answer_synthesis.second_stage_llm=false` when field present. |
| p95 `POST /v1/query` | — | **~96 ms** | `BASE=http://127.0.0.1:8787 N=40` — p50 ≈ **82 ms**, p95 ≈ **96 ms**, max ≈ **149 ms** (`scripts/pilot_measure_latency.py`). |
| p95 `GET /v1/works` | — | **~34 ms** | Same run — p50 ≈ **18 ms**, p95 ≈ **34 ms**, max ≈ **36 ms**. |
| Subjective usefulness | — | **Rubric ready** | Use 1–5 scores below + free text in *Qualitative notes*; upgrade to **GO** when ≥2 researchers complete the rubric on the signed-off corpus. **Session log:** [wave-d-rubric-session-log.md](wave-d-rubric-session-log.md). |

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

## Subjective usefulness rubric (per researcher)

**Instructions:** duplicate the table per session in [wave-d-rubric-session-log.md](wave-d-rubric-session-log.md); when two sessions are complete, copy aggregate means here and set pilot decision to **GO** if criteria in that file are met.

| Criterion | Score 1–5 | Notes |
|-----------|------------|-------|
| Finding a relevant work from corpus list | — | *pending researcher session* |
| Trust in citations vs chunk text | — | *pending researcher session* |
| Graph neighborhood usefulness for context | — | *pending researcher session* |
| Ask / query answer usefulness (given deterministic or LLM second stage) | — | *pending researcher session* |
| Time saved vs manual PDF reading | — | *pending researcher session* |

**Corpus growth (Wave D3):** target **N≥20–50** works in the pilot lane (see [pilot-corpus-wave-d.md](../runbooks/pilot-corpus-wave-d.md)); after bulk ingest, re-run `pilot_spot_check.sh` + latency script and paste new JSON into this file.

## Qualitative notes

- **What worked for researchers:** *(pilot owner — fill after sessions)*  
  Example prompts: faster orientation on CV object-detection papers; graph tab confirms citation neighborhood; Ask gives scannable excerpts.
- **Misleading citations or gaps:** *(fill)*  
  Note any queries where top citations came from references/bibliography slices or missed the main contribution section.
- **Backlog items filed:** *(link PRs / `docs/backlog/*`)*  
  e.g. second-stage LLM policy, retrieval gold cases, UI workspace persistence.

