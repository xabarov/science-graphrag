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

**Next step:** wire eval runner flag `--agent-note-on` into `eval/chat_agent/runner.py` (or dedicated smoke batch) and attach CSV summaries under `eval/results/` when executing the 50-turn batch.
