# Agent note token cost — evaluation note (Wave backlog)

## Goal

Quantify extra LLM cost from optional `agent_note` SSE events (`Settings.agent_note_enabled`, `agent_note_max_per_turn`) before enabling them by default.

## Harness (recommended)

1. Fix a benchmark slice: e.g. `tests/fixtures/benchmarks/chat_agent_roadmap/cases*` — pick **50** turns across intents (`inventory`, `grounded_explanation`, `relation_tracing`) with thread ids disabled unless testing memory.
2. Run twice against the **same** stubbed cheap chat model (or recorded mock provider) with identical routing:
   - **A:** `agent_note_enabled=false`
   - **B:** `agent_note_enabled=true`, `agent_note_max_per_turn=2`
3. Record per turn from `run_metadata.usage` (already aggregated in SSE `final_answer`) or from Phoenix spans:
   - `usage.total_tokens` (prompt + completion)
   - wall-clock p50 / p95 for the HTTP/SSE request

## Acceptance metric (from backlog)

Target: ≥80% of runs show predictable overhead (e.g. median Δtokens ≤ X%, latency Δp95 ≤ Y ms) **or** explicit decision to keep default off until product tuning.

## Pilot recommendation

**Default:** keep `agent_note_enabled=false` until a numbered pilot records **live** numbers on production-like models; offline stubs prove wiring only.

## Wave 5 execution snapshot (2026-05-06)

- Added comparator utility: `eval/chat_agent/agent_note_cost_eval.py`.
- Smoke run executed on committed mini artifact (`10` cases):
  - command:
    - `.venv/bin/python eval/chat_agent/agent_note_cost_eval.py --off-json eval/results/current-agent-tools-mini.json --on-json eval/results/current-agent-tools-mini.json --out-json eval/results/agent-note-cost-sample.json --out-md eval/results/agent-note-cost-sample.md`
  - result: `latency_p50=2ms`, `latency_p95=3ms`, token fields unavailable (`tokens_available_rate=0.0`) because this artifact does not contain per-turn usage.

## Decision

Keep `agent_note_enabled=false` by default. The tooling for OFF/ON comparison is now in repo; final go/no-go still requires a dedicated **50-turn live** dual-run with populated `run_metadata.usage.total_tokens`.
