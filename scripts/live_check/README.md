# Live HTTP checks (agent chat / v2)

Reusable checks live in [`http_suite.py`](./http_suite.py). They are invoked from:

- [`agent_v2_http.py`](./agent_v2_http.py) (CLI operator script)
- [`tests/live/test_agent_v2_http_optional.py`](../../tests/live/test_agent_v2_http_optional.py) when `AGENT_LIVE_BASE` is set

## Minimal environment

| Variable | Purpose |
|----------|---------|
| `AGENT_LIVE_BASE` | API root, e.g. `http://127.0.0.1:8000` |
| `AGENT_LIVE_WORKSPACE_ID` | Optional workspace UUID for scoped checks |
| `AGENT_LIVE_TIMEOUT_SEC` | HTTP read timeout (default `240`) |

## CH4 strict gate (optional)

Set **`AGENT_LIVE_GATE_CH4=1`** to require, on agent v2 calls that pass `thread_id`:

- sync JSON: `session_init` present in `tool_trace`
- SSE: `context_compacted` in the stream **and** `session_init` in the final `tool_trace`

Use before release or when validating multi-worker / real LLM stacks where in-process tests are insufficient.

## CH4 multi-turn digest

`check_multi_turn_digest` runs two JSON turns with the same `thread_id` and a client `history_digest` on turn 2. Skip with `AGENT_LIVE_SKIP_MULTI_TURN=1` if the environment is slow or flaky.

## Related spec

[`docs/specs/agent-chat-v1.md`](../../docs/specs/agent-chat-v1.md) — envelope and SSE vocabulary.
