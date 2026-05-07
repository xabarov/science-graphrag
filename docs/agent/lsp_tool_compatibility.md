# `lsp_tool` compatibility boundary

## What is supported

- **Transport:** stdio JSON-RPC to a language server process started by the agent host (read-only from the product perspective).
- **Operations:** a **fixed allowlist** exposed as the `lsp_tool` LangChain tool (e.g. `workspace_symbol`, `definition`, `references`) — see `science_graphrag/agent/tools/lsp_surface.py`.
- **Budgets:** request/response size limits, per-call timeouts, and **degraded** markers when the server is slow, partial, or unreachable. These surface as `lsp_audit` SSE hints and roll up into `run_metadata.lsp_audit_summary` for trace review.

## What is explicitly *not* promised

- **Not every LSP server:** behaviour differs widely; we do not guarantee universal coverage.
- **No arbitrary LSP surface:** unsupported methods return typed errors / `lsp_unconfigured` style outcomes rather than raw protocol dumps.
- **No write/edit/refactor:** navigation and inspection only; the tool is not a code editor.

## Eval / benchmark lane

- Tier key: **`agent_tools_lsp`** in `tests/fixtures/benchmarks/agent_tools_v1/case_tiers.json`.
- Run (mock CI-safe):  
  `science-graphrag-agent-benchmark tests/fixtures/benchmarks/agent_tools_v1 --suite --tier agent_tools_lsp --mock-runtime`
- Live runs require a working LSP server configuration in `Settings` and are optional for CI.

## Trace review

- Prefer **`run_metadata.lsp_audit_summary`** (aggregated) over scraping raw SSE rows for acceptance checks.
