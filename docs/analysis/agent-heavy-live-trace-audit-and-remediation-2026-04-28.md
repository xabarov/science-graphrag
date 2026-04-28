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

**Historical (pre–P2.1):** the E2E script used a recursive walk that collected **every** JSON **`name`** field under the Phoenix payload while [`eval/chat_agent/phoenix_export.py`](../../eval/chat_agent/phoenix_export.py) `try_fetch_phoenix_spans` could return rich nested JSON.

**Observed risk:** span names from **other workflows** (e.g. ingest / `llm.vl_pdf` / unrelated `tool.cypher_query`) appeared in the same `span_names_full_cap200` slice as the chat trace for `multi_compare_bibliography`. Likely drivers: (1) REST shape / version, (2) **recursive walk** pulling `name` from nested metadata, (3) project-wide noise.

**Remediation (P2.1):** [`extract_span_names_for_trace`](../../eval/chat_agent/phoenix_export.py) reads only structured span lists and filters by **`trace_id`** (with conservative rules when spans omit `trace_id`); the live harness calls it from [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py). See §6.3 for acceptance.

---

## 5. Remediation plan (ordered)

### P0 — User-visible correctness (**shipped 2026-04-28**)

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P0.1** | **Guarantee non-empty user answer** when the graph ends after `cypher_query` / `edge_search` without a bare assistant message: **`extract_langgraph_answer`** third-phase **graph JSON salvage** (preview rows/items, warning `answer_salvaged_from_graph_tool`, span event `agent.graph_tool_answer_salvage`). | [`science_graphrag/agent/runtime.py`](../../science_graphrag/agent/runtime.py) |
| **P0.1b** | **One-shot `final_answer` nudge** in single-agent ReAct: if the model returns an `AIMessage` **without** `tool_calls` but the trace already has a catalog tool and the last one is **not** `final_answer`, route **`chat` → `final_answer_nudge` → `chat`** once (`metadata.final_answer_nudge_used`). | [`science_graphrag/agent/graph/react_edges.py`](../../science_graphrag/agent/graph/react_edges.py), [`science_graphrag/agent/graph/supervisor.py`](../../science_graphrag/agent/graph/supervisor.py), policy in [`science_graphrag/agent/final_answer_policy.py`](../../science_graphrag/agent/final_answer_policy.py) |
| **P0.2** | **Envelope:** `last_executed_catalog_tool_name` centralized in `final_answer_policy`; suppress **`agent_finished_without_final_answer_tool`** when `extra_warnings` contains **`answer_salvaged_from_graph_tool`**. Sync + SSE pass **`extra_warnings`** from salvage flag. | [`science_graphrag/agent/chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py), [`science_graphrag/api/agent_v2.py`](../../science_graphrag/api/agent_v2.py) |
| **P0.3** | **Import cycle fix:** `science_graphrag.agent.graph` package `__init__` no longer imports **`build_retrieval_graph`** (import **`build_retrieval_graph` from `…graph.supervisor`** explicitly). | [`science_graphrag/agent/graph/__init__.py`](../../science_graphrag/agent/graph/__init__.py) |

### P1 — Instruction adherence and tool mix (**[DONE] 2026-04-28**)

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P1.1** | ~~Strengthen **system / turn** instructions~~ — **Done:** mandatory enumerated tool paths + capability-gap rule in system prompt; docstrings for `paper_profile`, `paper_quote_search`, `idea_search`. | [`science_graphrag/agent/prompts/research_chat_system.py`](../../science_graphrag/agent/prompts/research_chat_system.py), [`science_graphrag/agent/tools/workspace_paper_tools.py`](../../science_graphrag/agent/tools/workspace_paper_tools.py), [`science_graphrag/agent/tools/idea_search.py`](../../science_graphrag/agent/tools/idea_search.py) |
| **P1.2** | ~~Reduce **`paper_profile`** churn~~ — **Done:** `paper_quote_search` in retrieval baseline merge; keyword scoring + manifest tags; `heuristic_answer_class` for evidence+trade-off → `quote_extraction`; single-agent shortlist uses `answer_class_hint or heuristic_answer_class(q, None)`; supervisor `ROUTING_PROMPT` mixed-evidence line; tests in `tests/test_tool_search.py`, `tests/test_chat_envelope.py`. | [`science_graphrag/agent/tool_search.py`](../../science_graphrag/agent/tool_search.py), [`science_graphrag/agent/tool_manifest.py`](../../science_graphrag/agent/tool_manifest.py), [`science_graphrag/agent/chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py), [`science_graphrag/agent/graph/supervisor.py`](../../science_graphrag/agent/graph/supervisor.py) |
| **P1.3** | ~~Re-run **`--suite heavy`**~~ — **Done:** local verify [`eval/results/live-heavy-p1-verify-20260428.md`](../../eval/results/live-heavy-p1-verify-20260428.md) + [`eval/results/live-heavy-p1-verify.jsonl`](../../eval/results/live-heavy-p1-verify.jsonl) (`--skip-phoenix`, `AGENT_LIVE_TIMEOUT_SEC=600`). `multi_evidence_speed_accuracy` **PASS** (`paper_quote_search` in trace); `graph_ego_methods` **deadline flake** (same class as §6 post-P0). **CI nightly:** deferred — runbook extended in [`scripts/live_check/README.md`](../../scripts/live_check/README.md) §Heavy suite. | Runbook |

### P2 — Observability fidelity (**[DONE] 2026-04-28**)

| ID | Action | Owner files / notes |
|----|--------|---------------------|
| **P2.1** | ~~Replace flat `_extract_span_names` with **span-aware extraction**~~ — **Done:** `extract_span_names_for_trace` in [`eval/chat_agent/phoenix_export.py`](../../eval/chat_agent/phoenix_export.py); E2E uses it from [`scripts/live_check/agent_od_workspace_e2e_audit.py`](../../scripts/live_check/agent_od_workspace_e2e_audit.py); tests in [`tests/eval/test_phoenix_export.py`](../../tests/eval/test_phoenix_export.py). | |
| **P2.2** | ~~Document **Phoenix scope** / collector / E2E sampling~~ — **Done:** subsection *Agent vs ingest in one Phoenix project* in [`docs/architecture/observability-phoenix.md`](../../docs/architecture/observability-phoenix.md); trace-scoped span note in [`scripts/live_check/README.md`](../../scripts/live_check/README.md). | |

### P3 — Envelope semantics (**[DONE] 2026-04-28**)

| ID | Action | Notes |
|----|--------|-------|
| **P3.1** | ~~**`graph_only`** product shape~~ — **Done (variant A):** remains **warnings-only**; documented in [`docs/specs/agent-chat-v1.md`](../../docs/specs/agent-chat-v1.md) (*Evidence-mix warnings*); contract assertion in [`tests/test_chat_envelope.py`](../../tests/test_chat_envelope.py) (`graph_only` ∉ `product_markers`). | [`science_graphrag/agent/chat_envelope.py`](../../science_graphrag/agent/chat_envelope.py) unchanged for markers |

---

## 6. Acceptance criteria (verification)

1. **`graph_ego_methods`:** HTTP 200, **`answer_len` ≥ 40**, last catalog tool **`final_answer`**, no `no_final_answer` unless product explicitly allows empty with a different status code.
2. **`multi_evidence_speed_accuracy`:** `tool_trace` includes **`paper_quote_search`** **or** `final_answer` text explicitly states that quotes are unavailable **and** last tool is **`final_answer`**; no `agent_finished_without_final_answer_tool` on success path.
3. **Phoenix audit:** span sample for chat traces does **not** include ingest-only roots (`ingest_document`, `llm.vl_pdf`, …) unless they are provably children of the same agent trace (verified by `trace_id` / parent id).

### Post–P0 live heavy run (2026-04-28)

Command (same as §2.1) with artifacts:

- [`eval/results/live-heavy-p0-verify-20260428.md`](../../eval/results/live-heavy-p0-verify-20260428.md)
- [`eval/results/live-heavy-p0-verify.jsonl`](../../eval/results/live-heavy-p0-verify.jsonl)

| Case | Result | Notes |
|------|--------|--------|
| `multi_compare_bibliography` | **PASS** | Unchanged quality path. |
| `multi_evidence_speed_accuracy` | **PASS** | Ends with **`paper_quote_search` → `final_answer`**; `no_quote_found` warning only (corpus/thin quote merge). |
| `graph_ego_methods` | **FAIL (flake)** | **`agent_turn_deadline_exceeded`**, empty `tool_trace` in response, `missing_phoenix_trace_id` — run hit wall-clock limit before tools completed; **not** a regression of the P0 nudge/salvage path. Re-run with higher `SCIENCE_GRAPHRAG_AGENT_STEP_TIMEOUT_SECONDS` / `AGENT_LIVE_TIMEOUT_SEC` to validate graph-ego under load. |

### Post–P1 live heavy run (2026-04-28)

Artifacts: [`eval/results/live-heavy-p1-verify-20260428.md`](../../eval/results/live-heavy-p1-verify-20260428.md), [`eval/results/live-heavy-p1-verify.jsonl`](../../eval/results/live-heavy-p1-verify.jsonl). Flags: `--skip-phoenix`, `AGENT_LIVE_TIMEOUT_SEC=600`.

| Case | Result | Notes |
|------|--------|-------|
| `multi_compare_bibliography` | **PASS** | |
| `multi_evidence_speed_accuracy` | **PASS** | `idea_search` → `paper_quote_search` → `final_answer`; `no_quote_found` only. |
| `graph_ego_methods` | **FAIL (flake)** | `agent_turn_deadline_exceeded`, empty `tool_trace` in JSON — same timeout class as post-P0; not attributed to P1 prompt/shortlist changes. |

### Post–closure full verify (`--suite full`, Phoenix on) — 2026-04-28

After P0–P3 and doc closure, re-ran **all six** OD scenarios (default + heavy) with **`--trace-audit`**, `AGENT_LIVE_TIMEOUT_SEC=600`, API `http://127.0.0.1:18787`, Phoenix `http://127.0.0.1:16006`. Runtime ≈ **77 s** total.

**Artifacts:** [`eval/results/live-full-verify-2026-04-28.md`](../../eval/results/live-full-verify-2026-04-28.md), [`eval/results/live-full-verify-2026-04-28.jsonl`](../../eval/results/live-full-verify-2026-04-28.jsonl), [`eval/results/live-full-verify-2026-04-28.log`](../../eval/results/live-full-verify-2026-04-28.log).

| `case_id` | Strict gate | `final_answer` last? | Notable warnings / trace_audit |
|-----------|-------------|----------------------|----------------------------------|
| `catalog_resolution` | PASS | Yes | `phoenix_structure_audit`: duplicate `find_works` hint (expected: title + refine). |
| `workspace_stats` | PASS | Yes | Clean. |
| `grounded_quote` | PASS | Yes | `no_quote_found` (envelope / quote merge — corpus or merge path). |
| `multi_compare_bibliography` | PASS | Yes | Duplicate `find_works`/`paper_profile` hint (expected for two families). |
| `graph_ego_methods` | PASS | Yes | **`graph_only`** (graph tools without vector retrieval — informational). Sequence: `workspace_inspect` → `cypher_query` → **`final_answer`** (P0 nudge/contract satisfied). |
| `multi_evidence_speed_accuracy` | PASS | Yes | **`paper_quote_search`** present; `no_quote_found`; duplicate `paper_profile` hint (acceptable churn vs prior run without `paper_quote_search`). |

**Phoenix deep links (this run):**

| `case_id` | Trace id (hex) |
|-----------|----------------|
| `catalog_resolution` | `9c8df5163f4309bee1da019ac4b9b06f` |
| `workspace_stats` | `75f72d87b1fd74c9a714474ff5e3025e` |
| `grounded_quote` | `068a0402c1879f49b4c4269b9fa696aa` |
| `multi_compare_bibliography` | `b62708c752aeb15bed41d274449f268c` |
| `graph_ego_methods` | `4e1e18a47dde9c44a6ae0e4f2f6aaff2` |
| `multi_evidence_speed_accuracy` | `e73fa3b18a65bd7c25114a722aa8e89a` |

UI: `http://127.0.0.1:16006/projects/science-graphrag/traces/<trace_id>`.

**Conclusion vs “не хуже / лучше”:** on this run the agent is **strictly not worse** (6/6 E2E gate) and **better** on the two previously failing heavy paths: **`graph_ego_methods`** now completes with **`final_answer`** and long grounded text; **`multi_evidence_speed_accuracy`** uses **`paper_quote_search`** and ends with **`final_answer`**. Remaining signals are **warnings** (`no_quote_found`, `graph_only`) and **heuristic** duplicate-tool hints — not gate failures.

**Sequence / tooling / prompts (audit):**

- **Optimality:** Heavy paths are lean (4–7 catalog steps). `multi_evidence` order `workspace_inspect` → `idea_search` → `paper_quote_search` → `paper_profile` ×2 → `final_answer` is reasonable (inventory → semantic → quotes → metadata → close).
- **Tools:** No `cypher_query_error_count` / edge zero-row streaks in summary; no Phoenix `phoenix_structure_audit.issues` on this sample.
- **Prompts / product:** `no_quote_found` still appears where quote extraction is thin — correlate with `paper_quote_search` `empty_reason` in tool payloads when debugging corpus. `graph_only` is expected for pure-graph ego tasks until product policy changes (see §4.2 / P3).

## 6b. `langgraph_supervisor_v1` (deferred)

The **`final_answer_nudge`** edge and salvage logic apply to **`langgraph_research_v1`** (single-agent ReAct) only. **`langgraph_supervisor_v1`** ends the user turn from **`writer_agent`** without this ReAct router; if the same contract issues appear there, add an analogous **writer-side completion** check or route back to a tool-capable specialist (separate small plan).

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
| 2026-04-28 | P0 implemented: `final_answer_policy`, ReAct `final_answer_nudge`, graph-tool salvage in `extract_langgraph_answer`, envelope + SSE sync; post-P0 heavy verify artifacts (`live-heavy-p0-verify-*`); §6b supervisor v1 deferred. |
| 2026-04-28 | **P1 done:** mandatory-tool-path system prompt + tool docstrings; `tool_search` baseline/scoring + `heuristic_answer_class` evidence/trade-off + single-agent `effective_ac` shortlist; supervisor routing hint; post-P1 heavy verify (`live-heavy-p1-verify-*`, `--skip-phoenix`); §5 P1 table marked done; README heavy-suite runbook. |
| 2026-04-28 | **P2 done:** `extract_span_names_for_trace` (trace-scoped Phoenix span names for live E2E); observability-phoenix *Agent vs ingest* + README trace-scoped note. **P3 done:** `graph_only` / `text_only` spec (warnings-only, no `product_markers`); envelope test extended. §5 P2/P3 marked done. |
| 2026-04-28 | **Post-closure verify:** `--suite full` + Phoenix, 6/6 PASS; artifacts `eval/results/live-full-verify-2026-04-28.*`; §6c narrative + trace id table. |
