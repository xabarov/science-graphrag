# Wave E — E1 rollout decision (`corpus_explore` / `research_plan`)

**Status:** live paired run **2026-05-13**. **Outcome: keep gated.**  
**Harness:** [`docs/runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §5.1.

## Preconditions

- Stack: `docker compose -f docker-compose.dev.yml` (api healthy on `http://127.0.0.1:18787`).
- Compose passes through `SCIENCE_GRAPHRAG_AGENT_CORPUS_EXPLORE_ENABLED`, `SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_SUBAGENT_ENABLED`, `SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED` (see `docker-compose.dev.yml`); recreate `api` between baseline and candidate so the **server** sees the intended flags.

## Live artifacts (2026-05-13)

| Role | JSON | MD |
|------|------|-----|
| Baseline (profile A: flags 0/0/0) | [`eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.json`](../../eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.json) | [`.md`](../../eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.md) |
| Candidate (profile B: flags 1/1/1) | [`eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-candidate.json`](../../eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-candidate.json) | [`.md`](../../eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-candidate.md) |
| Regression compare | [`eval/results/trace-regression-wave-e-2026-05-13-e1.json`](../../eval/results/trace-regression-wave-e-2026-05-13-e1.json) | [`.md`](../../eval/results/trace-regression-wave-e-2026-05-13-e1.md) |

Command used (warn-only on latency delta; hard fail on spans/tool_error/final_answer):

```bash
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.json \
  --candidate eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-candidate.json \
  --out-json eval/results/trace-regression-wave-e-2026-05-13-e1.json \
  --out-md eval/results/trace-regression-wave-e-2026-05-13-e1.md \
  --fail-on new_missing_spans,tool_error_increase,final_answer_missing_increase \
  --warn-on latency_p95_increase \
  --warn-is-pass
```

**Regression:** `pass` (hard deltas clean); **warn:** `latency_p95_increase: 43865 → 69112` ms (+25247 ms delta).

## Decision matrix (rollup metrics)

| Criterion | Baseline | Candidate | OK? |
|-----------|----------|-----------|-----|
| `tool_loop_repeat_max` | 2 | 2 | yes (≤ 3) |
| `latency_p95_ms` | 43865 | 69112 | **no** vs non-regression intent (large p95 increase) |
| `subagent_lifecycle_missing_count` | 0 | 0 | yes |
| `subagent_task_notification_count_avg` | 2.0 | 2.0 | no regression |
| `tool_use_summary_row_count_total` | 0 | 0 | default suite did not hit summary threshold; E2 not exercised here |

**Outcome:**

- [ ] **default-on** — rejected: latency p95 regression under candidate flags on this suite/workspace.
- [x] **keep gated** — ship subagent + summary opt-in via compose/env; do not flip repo defaults to forced-on for all dev stacks without a narrower routing story or cheaper subagent path.
- [ ] **needs narrower routing** — optional follow-up if we want corpus_explore only on specific answer classes (not decided in this run).

| optional OpenRouter `cache_control` hint | ✅ default-on via `agent_side_llm_openrouter_cache_control_enabled` (`Settings`) for `run_side_llm_chat` static system prefix |

## Supplement — 2026-05-12 programmatic default-on closure

After roadmap **Close Remaining Waves** execution:

- `Settings.agent_corpus_explore_enabled` / `agent_research_plan_subagent_enabled` default **True**.
- Latency guard: `agent_e1_retrieval_hop_evidence_gate_enabled` (default **True**) skips `corpus_explore` / `research_plan` when `len(retrieval_payloads) < agent_e1_retrieval_hop_min_payloads` (default **2**). See `science_graphrag/agent/graph/nodes/retrieval_fork_legs.py`.
- Historical **keep gated** evidence (2026-05-13 live) remains valid for the *un-gated* behavior; operators should treat the new gate as the mitigation path before disabling defaults repo-wide.

**Recorded by:** engineering closure batch **Date:** 2026-05-12
