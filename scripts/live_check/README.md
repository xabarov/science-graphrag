# Live HTTP checks (agent chat / v2)

Reusable checks live in [`http_suite.py`](./http_suite.py). They are invoked from:

- [`agent_v2_http.py`](./agent_v2_http.py) (CLI operator script)
- [`agent_od_workspace_e2e_audit.py`](./agent_od_workspace_e2e_audit.py) — OD workspace questions (`--suite default|heavy|full`), `tool_trace` step counts, optional Phoenix REST audit, Postgres `ingest_jobs` counts; per-case fields include `edge_search_zero_row_max_streak`, `paper_profile_max_consecutive_same_work_id`, `cypher_query_error_count`. `--trace-audit` adds fan-out / span heuristics (including `paper_profile` same-`work_id` streak and multi-step Cypher errors) and **`phoenix_structure_audit`** when Phoenix returns span names (coverage vs `tool_trace`, sequence hints for prompts/tools). Phoenix span **names** are **trace-scoped** (`eval.chat_agent.phoenix_export.extract_span_names_for_trace`) so ingest / unrelated `name` keys in JSON do not pollute the audit sample. **`--markdown-report PATH`** writes a human table (incl. **tool sequence** per case). Env **`AGENT_E2E_PHOENIX_SPAN_CAP`** (default `400`, max `2000`) caps stored span names per case. Exit `1` if any case lacks `final_answer` as last catalog tool or answer too short; `--write-report PATH` appends one JSON line per run for CI artifacts
- [`run_agent_od_phases_audit.sh`](./run_agent_od_phases_audit.sh) — one-shot: `build_research_chat_prompt_bundle.py --evaluate` then `agent_od_workspace_e2e_audit.py --suite full --trace-audit --markdown-report` (output path optional)

**Nightly / optional CI:** run the same script against a live API + OD workspace with secrets (`AGENT_LIVE_BASE`, LLM keys); compose in this repo does not start the API by default on `ubuntu-latest`, so wire `AGENT_LIVE_BASE` to a reachable deployment or keep the job `continue-on-error` until a compose stack is added.
- [`tests/live/test_agent_v2_http_optional.py`](../../tests/live/test_agent_v2_http_optional.py) when `AGENT_LIVE_BASE` is set

### Heavy suite (post–instruction / tool-mix changes)

After prompt or `tool_search` shortlist changes, re-run the strict heavy gate (same workspace resolution as default OD audit):

```bash
AGENT_LIVE_BASE=http://127.0.0.1:18787 AGENT_LIVE_TIMEOUT_SEC=600 \
  .venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py \
  --suite heavy --trace-audit --timeout 600 \
  --markdown-report eval/results/live-heavy-p1-verify-YYYYMMDD.md \
  --write-report eval/results/live-heavy-p1-verify.jsonl
```

Use **`--skip-phoenix`** when validating only HTTP `tool_trace` / answer shape (Phoenix REST is optional for that). If **`graph_ego_methods`** hits **`agent_turn_deadline_exceeded`**, raise **`SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS`** and/or **`AGENT_LIVE_TIMEOUT_SEC`** and re-run — that case is graph-heavy and sensitive to wall-clock under load (see `docs/analysis/agent-heavy-live-trace-audit-and-remediation-2026-04-28.md` §6).

## Minimal environment

| Variable | Purpose |
|----------|---------|
| `AGENT_LIVE_BASE` | API root, e.g. `http://127.0.0.1:8000` or `http://127.0.0.1:18787` when API is mapped from docker compose |
| `AGENT_LIVE_WORKSPACE_ID` | Optional workspace UUID for scoped checks |
| `AGENT_LIVE_TIMEOUT_SEC` | HTTP read timeout (default `240`) |
| `AGENT_E2E_PHOENIX_SPAN_CAP` | Max Phoenix span names stored per case when using `--trace-audit` (default `400`) |

## CH4 strict gate (optional)

Set **`AGENT_LIVE_GATE_CH4=1`** to require, on agent v2 calls that pass `thread_id`:

- sync JSON: `session_init` present in `tool_trace`, and `run_metadata.compaction` includes **`kinds`** (CH5 parity)
- SSE: `context_compacted` in the stream **and** `session_init` in the final `tool_trace`

Pytest: `test_live_agent_v2_gate_ch4_sync_json_with_thread` exercises the sync JSON path; `test_live_agent_v2_gate_ch4_sse` exercises SSE.

Use before release or when validating multi-worker / real LLM stacks where in-process tests are insufficient.

## CH4 multi-turn digest

`check_multi_turn_digest` runs two JSON turns with the same `thread_id` and a client `history_digest` on turn 2. Skip with `AGENT_LIVE_SKIP_MULTI_TURN=1` if the environment is slow or flaky.

## Related spec

[`docs/specs/agent-chat-v1.md`](../../docs/specs/agent-chat-v1.md) — envelope and SSE vocabulary.
