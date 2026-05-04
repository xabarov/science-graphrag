# Habr window — tool_search / `agent_tools_mini` RCA (June 2026 live JSON)

**Source JSON (primary):** `eval/results/habr-window-2026-06-agent-tools-mini-band-1.35-live.json` — narrower `SCIENCE_GRAPHRAG_AGENT_TOOL_SEARCH_SCORE_BAND` (better suite `latency_p95_ms` vs band 1.5 in the paired run; see `habr-window-2026-06-tier-b-tool-search.txt`).

**Gold:** `tests/fixtures/benchmarks/agent_tools_v1/agent_case_*/gold.json` — each case declares `expected_tool_sequence` (first tool is the strict routing signal for this tier).

**How to regenerate the table:**

```bash
.venv/bin/python scripts/diag_agent_tools_mini.py \
  --live-json eval/results/habr-window-2026-06-agent-tools-mini-band-1.35-live.json
```

## Interpretation (no new LLM calls)

On this artifact, **9/10** cases fail formal gates even though answers are often grounded (`answer_grounded=1.0` everywhere here). The dominant pattern is **route mismatch vs gold**: the first non-`coordinator_gate` tool is frequently `find_works` or `workspace_inspect` when gold expects `idea_search`, or the trajectory adds long `paper_profile` chains before the benchmark-required tool order is satisfied. That collapses `tool_call_correctness` toward **0.0–0.33** and sometimes trips **`tool_budget_ok=false`** when the model burns steps on catalog-style navigation.

Band **1.5** does not “fix” pass rate in the paired June run (still **1/10**); it mainly shifts which wrong-first-tool branch appears and changes tail latency — compare by re-running the script with `--live-json eval/results/habr-window-2026-06-agent-tools-mini-band-1.5-live.json`.

## Markdown table (band 1.35)

| case_id | passed | tool_correctness | budget_ok | answer_grounded | duration_ms | expected_first | failure_class | observed_tools |
|---|---:|---:|---:|---:|---:|---|---|---|
| `agent_case_01` | false | 0.0 | false | 1.0 | 84621 | `idea_search` | `mixed` | find_works → paper_profile → paper_profile → paper_profile → paper_quote_search → final_answer |
| `agent_case_02` | false | 0.3333 | true | 1.0 | 21503 | `idea_search` | `mixed` | workspace_inspect → idea_search → paper_quote_search → paper_profile → final_answer |
| `agent_case_03` | false | 0.0 | true | 1.0 | 11509 | `idea_search` | `wrong_first_tool` | workspace_inspect → final_answer |
| `agent_case_04` | false | 0.0 | true | 1.0 | 5843 | `idea_search` | `wrong_first_tool` | find_works → final_answer |
| `agent_case_05` | false | 0.3333 | false | 1.0 | 24229 | `idea_search` | `mixed` | workspace_inspect → find_works → idea_search → paper_profile → paper_quote_search → final_answer |
| `agent_case_06` | false | 0.3333 | true | 1.0 | 10336 | `workspace_inspect` | `low_tool_correctness` | workspace_inspect → paper_profile → edge_search → final_answer |
| `agent_case_07` | true | 1.0 | true | 1.0 | 18660 | `idea_search` | `ok` | find_works → find_works → paper_profile → idea_search → paper_quote_search → final_answer |
| `agent_case_08` | false | 0.0 | true | 1.0 | 26122 | `idea_search` | `mixed` | workspace_inspect → edge_search → paper_profile → paper_profile → paper_profile → paper_profile → paper_profile → final_answer |
| `agent_case_09` | false | 0.0 | true | 1.0 | 6716 | `idea_search` | `wrong_first_tool` | find_works → final_answer |
| `agent_case_10` | false | 0.5 | true | 1.0 | 26728 | `idea_search` | `wrong_first_tool` | workspace_inspect → workspace_inspect → paper_profile → idea_search → paper_quote_search → paper_quote_search → final_answer |

**Failure class legend (deterministic rules in `scripts/diag_agent_tools_mini.py`):**

- `wrong_first_tool` — first non-coordinator tool ≠ first expected tool.
- `extra_tool_loops` — many extra tools vs expected length with low `tool_call_correctness`.
- `over_budget` — `tool_budget_ok=false` while `tool_call_correctness < 0.7`.
- `slow_no_error` — failed run, all tool steps `error=null`, `duration_ms > 60_000`.
- `answer_ungrounded` — `answer_grounded < 1.0`.
- `low_tool_correctness` — failed, no class above, but `tool_call_correctness < 0.7`.
- `mixed` — two or more of the above.

**Raised:** 2026-05-04
