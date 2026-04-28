# Heavy live agent audit: trace analysis and remediation plan

**Date:** 2026-04-28  
**Scope:** Post–phases A/B/C regression check on **three heavy OD workspace scenarios** (multi-tool, graph, mixed retrieval).  
**Workspace (run):** `Object Detection (clean ingested + claims)` (32 works).  
**API:** `http://127.0.0.1:18787` (docker compose dev API port mapping).  
**Phoenix UI:** `http://127.0.0.1:16006` (default `PHOENIX_UI_BASE_URL`).  
**Chat model (run):** `qwen/qwen3-235b-a22b-2507` (from `Settings.chat_llm_model`).

---

## 1. Executive summary

| Case | Script PASS | User-visible outcome | Primary issue class |
|------|-------------|----------------------|---------------------|
| `multi_compare_bibliography` | Yes | Full bibliography + contrast + citations | None blocking |
| `graph_ego_methods` | No | **Empty `answer`**, no `final_answer` tool | Answer extraction + graph-only envelope |
| `multi_evidence_speed_accuracy` | No | Long text but **no `final_answer` tool** | Tool discipline + instruction adherence |

**Strict gate (E2E script):** 1/3 passed. **Conclusion:** the pipeline is **not yet consistently “no worse than before”** on graph-heavy and “finish with `final_answer`” constraints; one bibliographic multi-tool path is strong.

---

## 2. Artifacts (repo + traces)

### 2.1 Committed / repo-local outputs

Reproducible after re-running the same command from repo root:

```bash
AGENT_LIVE_BASE=http://127.0.0.1:18787 \
PHOENIX_UI_BASE_URL=http://127.0.0.1:16006 \
.venv/bin/python scripts/live_check/agent_od_workspace_e2e_audit.py \
  --suite heavy --trace-audit --timeout 600 \
  --markdown-report eval/results/live-heavy-trace-audit-20260428.md \
  --write-report eval/results/live-heavy-trace-audit.jsonl
```

| Artifact | Path |
|----------|------|
| Markdown summary (tables + `trace_audit` hints) | [`eval/results/live-heavy-trace-audit-20260428.md`](../../eval/results/live-heavy-trace-audit-20260428.md) |
| JSONL append (per-run summary line) | [`eval/results/live-heavy-trace-audit.jsonl`](../../eval/results/live-heavy-trace-audit.jsonl) |
| Full JSON + stderr (if captured) | `eval/results/live-heavy-trace-audit.log` (optional; may be gitignored—re-run produces JSON on stdout) |

**Harness:** [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) — `HEAVY_QUESTIONS`, Phoenix span cap via `AGENT_E2E_PHOENIX_SPAN_CAP`.

### 2.2 Phoenix deep links (run 2026-04-28, local)

These URLs assume Phoenix project slug **`science-graphrag`** (see `PHOENIX_PROJECT_NAME` / `eval.chat_agent.phoenix_export.phoenix_project_identifier`). Replace host if your UI is tunneled elsewhere.

| `case_id` | `phoenix_trace_id` (hex) | UI URL |
|-----------|--------------------------|--------|
| `multi_compare_bibliography` | `de9e9da60288e425fde65e57742479be` | `http://127.0.0.1:16006/projects/science-graphrag/traces/de9e9da60288e425fde65e57742479be` |
| `graph_ego_methods` | `c41d26341e6dc821078ccedbc866c2fd` | `http://127.0.0.1:16006/projects/science-graphrag/traces/c41d26341e6dc821078ccedbc866c2fd` |
| `multi_evidence_speed_accuracy` | `2ecd49312be3620206b48a885d05ae60` | `http://127.0.0.1:16006/projects/science-graphrag/traces/2ecd49312be3620206b48a885d05ae60` |

**Environment note:** stderr may show `PHOENIX_TRACE_SCOPE=extraction_llm` — agent spans were still present in this run; if traces are empty in another env, verify `PHOENIX_COLLECTOR_ENDPOINT` on the API container (see [`docker-compose.dev.yml`](../../docker-compose.dev.yml) `api.environment`).

---

## 3. Per-case analysis

### 3.1 `multi_compare_bibliography` — PASS

- **Tool sequence:** `coordinator_gate` → `find_works` ×2 → `paper_profile` ×2 → `format_bibliography_gost` → `final_answer`.
- **Metrics (approx.):** `duration_ms` ≈ 63 569; `answer_len` 632; `citations_count` 2; `cypher_query_error_count` 0.
- **Trace audit:** `heuristic_issues` empty; `phoenix_structure_audit.sequence_hints` flags **duplicate** `find_works` / `paper_profile` — **expected** for two detector families (not fan-out waste).
- **Phoenix:** `llm.agent.react_turn` and `tool.*` spans align with the catalog tool trace. **Caveat:** the flat span-name walk used by the E2E script also listed **unrelated** span names (ingest / VL / extra `cypher_query` / `exception`) inside the same payload slice — see §4.3.

### 3.2 `graph_ego_methods` — FAIL (empty answer)

- **Tool sequence:** `coordinator_gate` → `workspace_inspect` → `cypher_query` (stopped there).
- **API:** `answer_len` **0**, `final_answer_reached` **false**, `warnings`: **`graph_only`**, **`no_final_answer`**.
- **Root chain:**
  1. **Answer text:** [`extract_langgraph_answer`](../../science_graphrag/agent/runtime.py) prefers a completed **`final_answer`** tool (`ToolMessage` JSON). If the run ends on **`cypher_query`** without a following **`final_answer`** and without a terminal **bare `AIMessage`**, the extracted answer is **`""`**.
  2. **Warnings:** [`build_chat_envelope`](../../science_graphrag/agent/chat_envelope.py) adds **`graph_only`** when the trace has graph tools (`cypher_query` / `edge_search`) but no vector tools (`idea_search` / `paper_quote_search`) — intentional flag for evidence mix. It adds **`no_final_answer`** when the stripped answer is empty (same file, `answer_stripped` check).
- **Product gap:** the user receives **no narrative** even when Cypher returned rows the model could summarize — **unless** the model calls **`final_answer`** (or the API defines an explicit non–`final_answer` fallback for graph-only turns).

### 3.3 `multi_evidence_speed_accuracy` — FAIL (contract / instruction)

- **Tool sequence:** `workspace_inspect` → `idea_search` → `paper_profile` ×3 (with `idea_search` between) — **no `paper_quote_search`** despite the question requiring two paths among **`idea_search`**, **`paper_quote_search`**, **`workspace_inspect`**.
- **API:** `answer_len` **2273** but **`last_tool_not_final_answer`**; `warnings`: **`agent_finished_without_final_answer_tool`**.
- **Root chain:**
  1. **Answer text:** likely from **last `AIMessage` without tool calls** path in `extract_langgraph_answer` (fallback when no completed `final_answer` tool), so the user sees text but **`tool_trace` violates** the “catalog ends with `final_answer`” contract.
  2. **Envelope:** [`build_chat_envelope`](../../science_graphrag/agent/chat_envelope.py) emits **`agent_finished_without_final_answer_tool`** when `tool_policy == allow_tools`, answer is non-empty, last executed catalog tool ≠ `final_answer`, and path is tool-assisted.
- **Quality gap:** overuse of **`paper_profile`** vs **`paper_quote_search`** for “evidence” wording; duplicate `idea_search` / `paper_profile` flagged in `phoenix_structure_audit.sequence_hints`.

---

## 4. Cross-cutting technical findings

### 4.1 Contract: `final_answer` as single source of truth

The stack **already encodes** “prefer `final_answer` tool JSON” in [`science_graphrag/agent/runtime.py`](../../science_graphrag/agent/runtime.py) (`extract_langgraph_answer`). Failures are therefore **mostly policy/routing/model compliance**, not a missing line in the exporter.

**Implication:** remediation should prioritize **forcing or recovering** `final_answer` at the graph boundary (supervisor / max-turn handler / post-run repair), not only UI warnings.

### 4.2 `graph_only` vs empty answer

`graph_only` is a **marker** (evidence mix), not an error by itself. Combined with **no `final_answer`** and **no terminal assistant text**, it produces **`no_final_answer`** and an empty API `answer` — **bad UX** for graph-heavy questions.

**Tests already document envelope behavior:** [`tests/test_chat_envelope.py`](../../tests/test_chat_envelope.py) (`test_graph_only_trace`, `test_build_chat_envelope_warns_agent_finished_without_final_answer_tool`).

### 4.3 Phoenix span lists and E2E “flat walk”

[`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py) `_extract_span_names` recursively collects **every** JSON **`name`** field under the Phoenix payload. [`eval/chat_agent/phoenix_export.py`](../../eval/chat_agent/phoenix_export.py) `try_fetch_phoenix_spans` may return rich nested JSON.

**Observed risk:** span names from **other workflows** (e.g. ingest / `llm.vl_pdf` / unrelated `tool.cypher_query`) appeared in the same `span_names_full_cap200` slice as the chat trace for `multi_compare_bibliography`. Possible causes:

1. Phoenix REST returns **more than** the requested trace’s spans for the queried `trace_id` (backend / version behavior).
2. **Recursive walk** pulls `name` fields from nested metadata unrelated to span nodes.
3. **Project-wide noise** under the same project identifier (less likely if `trace_id` filter is strict).

**Implication:** use **structured span lists** (with `trace_id` per span) for audits, or filter names to a **known prefix allowlist** (`llm.agent.*`, `tool.*`, `retrieval.*`, `embedding.*` for agent subtree) and drop ingest-prefixed spans when parent trace does not match.

---

## 5. Remediation plan (ordered)

### P0 — User-visible correctness

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P0.1** | **Guarantee non-empty user answer** for `allow_tools` when the model stops after a catalog tool (especially `cypher_query` / `edge_search`) but there is a **last non-empty `AIMessage`**. Today `extract_langgraph_answer` may return `""` if the model never emitted a bare assistant message. Options: (a) **supervisor** injects a final “compose answer” turn; (b) **bounded repair** call that maps last tool JSON to a short summary + **`final_answer`**; (c) **reject** incomplete trace and auto-retry with a system nudge. | [`science_graphrag/agent/runtime.py`](../../science_graphrag/agent/runtime.py), graph supervisor / ReAct loop |
| **P0.2** | **Hard requirement:** last catalog tool **`final_answer`** before returning HTTP 200 for agent v2 (or explicit **4xx/structured incomplete** if product chooses “fail closed”). Aligns with E2E gate and removes **`agent_finished_without_final_answer_tool`** for successful HTTP paths. | [`science_graphrag/api/agent_v2.py`](../../science_graphrag/api/agent_v2.py), LangGraph edges |

### P1 — Instruction adherence and tool mix

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P1.1** | Strengthen **system / turn** instructions: if the user lists mandatory tool **categories**, the model must call them or **`final_answer`** stating **capability gap** with `empty_reason`-style honesty. | [`science_graphrag/agent/prompts/research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), tool docstrings |
| **P1.2** | Reduce **`paper_profile`** churn when the task is **quote/evidence**: promote **`paper_quote_search`** in the shortlist or add a **router hint** for “evidence / trade-off” questions. | [`science_graphrag/agent/tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py), supervisor routing |
| **P1.3** | Re-run **`--suite heavy`** after changes; optionally add a **CI nightly** with `AGENT_LIVE_BASE` (see [`scripts/live_check/README.md`](../../scripts/live_check/README.md)). | CI / runbook |

### P2 — Observability fidelity

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P2.1** | Replace flat `_extract_span_names` with **span-aware extraction**: only `name` fields on objects that include **matching `trace_id`** (when present), or walk only `data[].spans[]`. | [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py), optionally [`eval/chat_agent/phoenix_export.py`](../../eval/chat_agent/phoenix_export.py) |
| **P2.2** | Document **Phoenix scope** (`PHOENIX_TRACE_SCOPE`) and collector URL in [`docs/architecture/observability-phoenix.md`](../../docs/architecture/observability-phoenix.md) if not already aligned with agent+ingest coexistence. | Docs |

### P3 — Envelope semantics (optional product decision)

| ID | Action | Notes |
|----|--------|-------|
| **P3.1** | Decide whether **`graph_only`** should remain a **warning** only, or trigger a **product marker** / different `answer_class` for analytics. | [`science_graphrag/agent/chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) |

---

## 6. Acceptance criteria (next verification)

1. **`graph_ego_methods`:** HTTP 200, **`answer_len` ≥ 40**, last catalog tool **`final_answer`**, no `no_final_answer` unless product explicitly allows empty with a different status code.
2. **`multi_evidence_speed_accuracy`:** `tool_trace` includes **`paper_quote_search`** **or** `final_answer` text explicitly states that quotes are unavailable **and** last tool is **`final_answer`**; no `agent_finished_without_final_answer_tool` on success path.
3. **Phoenix audit:** span sample for chat traces does **not** include ingest-only roots (`ingest_document`, `llm.vl_pdf`, …) unless they are provably children of the same agent trace (verified by `trace_id` / parent id).

---

## 7. Related documents

- Agent tools architecture: [`docs/architecture/agent-chat-tools.md`](../../docs/architecture/agent-chat-tools.md)  
- Chat envelope / v2 spec: [`docs/specs/agent-chat-v1.md`](../../docs/specs/agent-chat-v1.md)  
- Live check entrypoints: [`scripts/live_check/README.md`](../../scripts/live_check/README.md)  
- Trace heuristics implementation: [`science_graphrag/agent/agent_trace_audit.py`](../../science_graphrag/agent/agent_trace_audit.py)

---

## 8. Changelog

| Date | Change |
|------|--------|
| 2026-04-28 | Initial document from live `--suite heavy` run, artifact paths, Phoenix trace IDs, and remediation plan. |
