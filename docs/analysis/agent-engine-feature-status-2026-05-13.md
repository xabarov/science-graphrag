# Agent engine feature status — R0 reconciliation (2026-05-13)

**Role:** companion to [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R0. Single place for **flag / default / evidence / decision / next action** after Wave D–H.

**Status:** reconciled with `science_graphrag/config.py` as of repo state at R0 closeout.

---

## 1. Canonical sources (read order)

1. **`science_graphrag/config.py`** — authoritative **Pydantic `Settings` defaults** (what a fresh process gets unless env overrides).
2. **`agent-engine-and-benchmarks-next-waves-2026-05-09.md`** — live engineering queue narrative + artifact pointers (synced 2026-05-12).
3. **Wave closeouts** — evidence and operator checklists:
   - [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md)
   - [`wave-d-promotion-operator-closeout-2026-05-12.md`](./wave-d-promotion-operator-closeout-2026-05-12.md)
   - [`pre-f-closure-readiness-2026-05-12.md`](./pre-f-closure-readiness-2026-05-12.md)
   - E1/E2 detail: [`wave-e-e1-rollout-decision-2026-05-10.md`](./wave-e-e1-rollout-decision-2026-05-10.md) (linked from next-waves §3)
4. **Structural backlog** — implementation debt not resolved by doc edits: [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md).

**Terminology (do not conflate):**

| Term | Meaning |
|------|---------|
| **Settings default** | Value in `Settings` / `Field(default=…)` when env is unset. |
| **Operator rollout gate** | Product/ops policy: treat as off or compare-gated until fresh live evidence, **even if** Settings default is `True`. |
| **Effective runtime** | What actually runs given **all** dependent flags (e.g. microcompact requires `agent_tool_history_compact_enabled`). |
| **Advisory lane** | Benchmark / judge family used for visibility, not `decision_gate`. |

---

## 2. Reconciliation matrix (R0 acceptance set)

| Feature / knob | Settings default | Operator / rollout gate | Latest evidence (pointer) | Decision | Next action |
|----------------|------------------|-------------------------|---------------------------|----------|-------------|
| **E1** `corpus_explore` + `research_plan` (`agent_corpus_explore_enabled`, `agent_research_plan_subagent_enabled`, `agent_e1_retrieval_hop_evidence_gate_enabled`) | `True` / `True` / `True` | **Operator rollout gate:** paired live p95 regression; do not treat as “safe for production” until a new compare clears latency. | [`eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.json`](../../eval/results/agent-corpus-explore-research-plan-acceptance-2026-05-13-baseline.json) (+ candidate); [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) §3.1. | **promote** (Settings defaults + hop gate shipped); **rerun evidence** on material code changes. | Re-evaluate after R4 subagent runtime or new paired compare; latency-sensitive stacks: `SCIENCE_GRAPHRAG_AGENT_CORPUS_EXPLORE_ENABLED=0`, `SCIENCE_GRAPHRAG_AGENT_RESEARCH_PLAN_SUBAGENT_ENABLED=0` (and related knobs in `.env.example` R0 block). |
| **E2** `tool_use_summary` + cache hint (`agent_tool_use_summary_enabled`, `agent_side_llm_openrouter_cache_control_enabled`) | `True` / `True` | **Operator rollout gate:** heavy live `side_llm_cache_read_ratio_avg` below 0.4 target; PR3 open in next-waves. | [`eval/results/trace-regression-wave-e-2026-05-13-e2-v5.md`](../../eval/results/trace-regression-wave-e-2026-05-13-e2-v5.md); [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) §3.2. | **promote** (cache-prefix code + telemetry); **keep off** *product trust* for summarization rows until ratio ≥ 0.4 or explicit policy; OpenRouter cache hint remains independent of whether summaries fire. | Heavy live rerun after PR1+2 or set `SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED=false` until gate passes. |
| **Wave H L4** `agent_llm_full_history_compact_enabled` | `True` | **Promote** for code + offline harness; **operator compare** still recommended on provider/model change. | [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md); offline harness `side_llm_cache_read_ratio` cited in horizon §1.1. | **promote** (docs + defaults aligned). | Long-thread live acceptance when changing OpenRouter model / cache behavior. |
| **Wave H microcompact** `agent_tool_message_microcompact_time_trigger_enabled` | `True` | **Effective default off:** microcompact runs only when `agent_tool_history_compact_enabled` is `True` (Settings default **`False`**). | [`science_graphrag/agent/tool_message_compact.py`](../../science_graphrag/agent/tool_message_compact.py) guard; [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md) (when compact is on). | **promote** for *field* default; clarify **effective** behavior in runbooks. | If product wants microcompact in production, enable `agent_tool_history_compact_enabled` deliberately and re-run acceptance. |
| **`agent_note`** `agent_note_enabled` | `False` | None (already off by default). | [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §1.3; live 50-turn token pilot still open (operator). | **keep off** (default). | **Postponed (R2 2026-05-13):** optional only; not part of canonical minimal contract — see [`docs/specs/agent-chat-v1.md`](../specs/agent-chat-v1.md) §R2; run live pilot when product requests default-on. |
| **`thread_insights`** `agent_thread_insights_enabled` | `False` | Opt-in via `SCIENCE_GRAPHRAG_AGENT_THREAD_INSIGHTS_ENABLED=1`; Epic A backlog. | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN] Smart context summarization parity track (Epic A)`; Train T1 skeleton done. | **keep off** default; **promote** path via env when running A2/A3 work. | Continue A2/A3 per roadmap; no default flip without eval lane. |
| **`agent_v3_quality_judge_v1`** (logical family) | N/A (benchmark lane, not a single Settings bool) | **Advisory**; Wave D strict promotion not met. | [`wave-d-promotion-operator-closeout-2026-05-12.md`](./wave-d-promotion-operator-closeout-2026-05-12.md); [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §1.2. | **keep off** (from `decision_gate`); instrumentation **promote**. | Calibration windows + promotion review per runbooks; do not conflate with CI `--mock-agent`. |

*Roadmap narrative for each row is aligned with [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §1.2, §2.2, and §10 after R0 (no conflated “default-on” + “keep gated” without labels).*

---

## R3 operator verdict (2026-05-13)

| Track | Implementation | Operator verdict | Next action |
|-------|----------------|------------------|-------------|
| **L4 preflight telemetry** | **Shipped in code:** `compaction_audit.l4_eligibility` on SSE `context_compacted` + sync JSON (`compaction_policy.py`) | **provider-gated** as of 2026-05-13 rerun: baseline/candidate/compare artifacts are valid, but long-thread cache/compaction evidence is still absent in the bounded lane (`side_llm_cache_read_ratio_avg=None`, no compaction events) | Keep provider-gated; rerun stable acceptance lane with observable compaction/cache signal, then promote or operator-off based on real long-thread metrics |
| **Memory influence audit (offline)** | `memory_influence_audit_v1` under `long_thread_eval` in trace-review merge (`eval/chat_agent/long_thread_eval.py`) | **Shipped** (deterministic harness) | Keep `--with-long-thread-eval` on acceptance profiles; extend cases when new prompt-memory edges appear |

---

## 3. Gated-experiment classification (R0 work item 2)

| Bucket | Features here |
|--------|----------------|
| **retire** | — (no experiment marked for retirement in this slice; revisit in R8 artifact hygiene if a flag becomes dead weight). |
| **keep off** | `agent_note` (default); `thread_insights` (default); E2 **product** stance until cache ratio gate passes. |
| **rerun evidence** | E1 if supervisor/subagent or retrieval hop logic changes materially; E2 after provider/cache changes; Wave H long-thread when switching models. |
| **promote** | E1/E2 **code paths** and Settings defaults shipped; Wave H L4 default + docs; microcompact **knob** default (with **effective** behavior documented); judge **infra** (not gate authority). |

---

## 4. E1 / E2 ambiguity resolution (R0 work item 3)

Historical tension: next-waves and horizon narrative said “keep gated” while **`config.py` flipped defaults to `True`** for E1/E2 knobs (2026-05-12).

**Resolution (no code change in R0):**

- **Settings default `True`** = shipped **code path is on** in a clean env.
- **Operator rollout gate** = teams SHOULD run paired/trace compares before trusting latency/cost in production; historical live shows E1 p95 regression and E2 cache ratio failure — so **rollout policy** remains conservative even though defaults are `True`.
- Operators MUST use env overrides (see [`science_graphrag/config.py`](../../science_graphrag/config.py) field names → `SCIENCE_GRAPHRAG_*` via pydantic-settings) to force **off** on sensitive stacks without treating that as a “code bug”.

This removes the illegal pattern “same sentence says default-on and keep gated with no distinction”: we always split **Settings default** vs **operator rollout gate**.

---

## 5. Discoverability

- Env naming: all knobs above map through **`SCIENCE_GRAPHRAG_` + uppercase snake** of the `Settings` field (see pydantic-settings).
- Optional commented pointers were added in [`.env.example`](../../.env.example) under
  `--- Agent rollout knobs (R0 reconciliation, 2026-05-13) ---`.
- Navigation: [docs/analysis/README.md](./README.md) lists the horizon doc; this companion is linked from horizon §R0.

---

## 6. Product decision — E1/E2 defaults (2026-05-13)

**Recorded choice: (A)** — keep **`Settings` defaults `True`** for E1/E2-related fields in
[`science_graphrag/config.py`](../../science_graphrag/config.py) so a clean process reflects the
shipped code path.

**Operator rollout** remains conservative until **fresh live evidence** updates the matrix
rows (see §2 **operator gate** / **next action**). Sensitive stacks MUST use env overrides
(documented in `.env.example` under `--- Agent rollout knobs (R0 reconciliation, 2026-05-13) ---`)
rather than expecting implicit `False` defaults.

Alternative **(B)** (flip defaults to `False`) was deferred: would require a dedicated migration
note for stacks that assumed implicit `True` from unset env.

---

## 7. Evidence replication lane (operator; not CI)

Use this checklist when **material** agent / retrieval / cache-prefix code changes ship, or when
refreshing operator trust after a provider/model switch.

| Track | When to rerun | Primary commands / artifacts |
|-------|----------------|------------------------------|
| **E1** paired latency | After supervisor / subagent / retrieval hop logic changes | `scripts/live_check/agent_trace_review.py` + `trace_regression_compare.py` vs pinned baseline JSON under `eval/results/`; see [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) §3.1 and baseline row in §2 above. |
| **E2** cache ratio | After PRs touching tool-use summary / OpenRouter cache hint paths | Heavy live per [`README_trace_review.md`](../../scripts/live_check/README_trace_review.md) §4; compare artifact [`eval/results/trace-regression-wave-e-2026-05-13-e2-v5.md`](../../eval/results/trace-regression-wave-e-2026-05-13-e2-v5.md) pointer in §3.2 next-waves. |
| **Wave H long-thread** | After OpenRouter model / cache-behavior change | `long_thread_compaction_eval.py` + acceptance notes in [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md). |

Update **only** the `evidence / decision / next action` columns in §2 after a run completes —
do not rewrite terminology or Settings defaults unless `config.py` actually changes.

---

## 8. Wave H microcompact — effective runtime (operator note)

`agent_tool_message_microcompact_time_trigger_enabled` defaults **`True`** in `Settings`, but
**microcompact does not run** unless `agent_tool_history_compact_enabled` is **`True`**
(that knob defaults **`False`**). So **effective** microcompact is off until the operator
deliberately enables history compaction and re-runs acceptance.

See also [`README_trace_review.md`](../../scripts/live_check/README_trace_review.md) (Wave H
harness section) for compaction-focused review commands.


