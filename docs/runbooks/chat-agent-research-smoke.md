# Research chat — smoke / eval (2026-04-27)

## Preconditions

- API + stores up; `science-graphrag config-check` shows extraction LLM key **SET**.
- Optional chat override: `SCIENCE_GRAPHRAG_CHAT_LLM_MODEL` (e.g. `qwen/qwen3-235b-a22b-2507`). Resolved model is echoed in `run_metadata.resolved_chat_llm_model` on sync JSON and SSE `final_answer`.

## Automated regression

```bash
.venv/bin/pytest tests/test_chat_llm_settings.py tests/test_chat_envelope.py tests/test_api_agent_v2_stream_parity.py -q
```

## Manual 3–5 prompts (workspace with ≥3 papers)

1. Inventory: «What papers are in this workspace?»
2. Graph: «How is work A related to work B?» (replace with real titles/ids).
3. Quotes: «Quote where the authors state …»
4. Synthesis: «Short related-work style summary for topic X in this workspace.»
5. Direct: «Hello, what can you do here?» (expect `product_path` ~ `direct` when no tools).

Watch the UI header: product **progress hint** (not raw SSE counts). Open **Inspect run** for `tool_call` / `tool_result` lines.

## Regression signals

- `warnings` may include `no_final_answer`, `no_citations`, `insufficient_evidence` — treat as quality signals, not transport errors.
- `product_markers` / `product_path` on the final payload describe direct vs tool-assisted completion.
