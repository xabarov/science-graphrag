# Agent engine next horizon — architecture, chat, ingestion, refactor (2026-05-13)

**Status:** new planning entry after
[`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md)
is effectively complete. That plan closed most of Waves D/E/F/G/H in code or evidence,
with important operator exceptions: Wave D promotion is still deferred; **E1/E2 ship
`True` defaults in `Settings` but remain under an operator rollout gate** (paired live
latency / cache-ratio evidence — see
[`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md));
Wave H L4 is default-on with **recommended** long-thread re-compare on provider changes.

**Purpose:** decide the next direction instead of adding another undifferentiated
feature list, then turn that decision into a wave roadmap. This document answers:

- whether the agent/chat architecture is going in the right direction;
- which openclaude practices are worth copying and which are not;
- what we forgot around ingestion;
- what refactor pass should happen before the next feature wave;
- which benchmarks are allowed to become gates;
- which waves should run first, what they produce, and when to stop.

**Short answer:** we did not go in the wrong direction, but we are close to the point
where adding more agent machinery has worse expected value than tightening interfaces,
operator gates, chat UX, and ingestion quality. The next horizon should be a
stabilization and depth pass, not a "more agents" pass.

**Roadmap summary:**

| Wave | Theme | Outcome | Start condition |
|------|-------|---------|-----------------|
| **R0** | Roadmap reconciliation | One source of truth for open gates / flags / artifacts. | **Done** (2026-05-13); matrix in companion doc. |
| **R1** | Observability refactor | Trace-review and compare gates become maintainable modules. | Before new agent runtime gates. |
| **R2** | Chat contract | SSE/product contract for progress, lifecycle, degraded mode. | After R1 interface sketch. |
| **R3** | Context memory | Long-thread compaction and `thread_insights` split into cost vs memory layers. | R1 metrics available. |
| **R4** | Real subagent runtime | One spawned child task with lifecycle, cancellation, merge provenance. | R2 contract agreed. |
| **R5** | Benchmark promotion discipline | Judge stays advisory until strict calibration and variance gates pass. | Can run in parallel after R1. |
| **R6** | Ingestion quality baseline | Corpus quality / claims / retrieval / dedup measured before headline updates. | Before publication metric refresh. |
| **R7** | Ingestion architecture | Structured executor, year/venue writeback, dedup parity slices. | R6 baseline exists. |
| **R8** | Artifact hygiene | Canonical vs diagnostics storage split, no noisy committed live dumps. | Before benchmark expansion scale-up. |
| **R9** | Product integration | Graph/retrieval/chat evidence reads as one user-facing workflow. | After R2 + R6. |

---

## 1. Current read of the system

### 1.1 What is solid now

| Area | Current state | Evidence |
|------|---------------|----------|
| Supervisor baseline | `langgraph_supervisor_v3` is the canonical dev runtime; `langgraph_research_v1` remains explicit fallback / comparison lane. | Orchestration closeout + trace-review acceptance. |
| Deterministic routing | `RoutePlan` + `QuestionFeatures` replaced scattered route latches and the separate LLM router layer. | `metadata.turn_policy.route_plan` is the single channel. |
| Runtime safety | `final_answer_missing_count=0`, `missing_span_count=0`, `tool_loop_repeat_max <= 3`, partial-state salvage exists. | Trace-review-v1 gates. |
| Writer | `writer_agent` is narrowed to terminal synthesis; `writer_oscillation_count_max=0` on recent acceptance artifacts. | Wave E3 / G3 closure. |
| Context compaction | L4 history compact runs through `run_side_llm_chat`; offline 50-turn harness shows `side_llm_cache_read_ratio_avg=0.844`. | `wave-h-rollout-decision-2026-05-12.md`. |
| Judge benchmark infrastructure | Pairwise judge runner, multiseed baseline, cost axis, cross-family research artifacts exist. | Wave D/F artifacts. |
| Trace-review discipline | Machine-readable warn allowlist, latency policies, writer oscillation policy, heartbeat diagnostics exist. | Wave G/H. |

### 1.2 What is not solid, and should not be hidden

| Area | Status | Meaning |
|------|--------|---------|
| Wave D promotion | Live calibration window failed strict thresholds: `agreement_winner_rate_min=0.3`, threshold `0.7`; variance spread `0.835`, threshold `0.15`. | `agent_v3_quality_judge_v1` stays advisory. Do not promote to `decision_gate`. |
| Cross-family judge | `inter_judge_agreement_rate=0.0769` on 13 pilot cases. | The judge lane is useful for visibility, not authority. |
| E1 subagents | Paired live showed p95 `43865 -> 69112 ms`. | **Operator rollout gate:** treat as risky for production until new compare; **Settings defaults** for fork legs are still `True` — override via env if needed (R0 matrix). |
| E2 `tool_use_summary` | Heavy live ratio `side_llm_cache_read_ratio_avg=0.1 < 0.4`. | **Operator rollout gate:** do not trust cost/cache story until ratio ≥ 0.4 or explicit policy; **`agent_tool_use_summary_enabled` default is `True`** in code — turn off via env for conservative stacks. |
| Ingestion | Robustness improved, but claims/gold realism, author/entity dedup, year/venue writeback, and full BT revalidation remain open. | Backlog OPEN/PARTIAL items. |
| Structural debt | Trace-review and benchmark runners became the new god-files. | Refactor pass needed before next benchmark expansion. |

### 1.3 What the first draft missed

The first version of this horizon doc was directionally right, but too coarse for
execution. It missed or under-specified:

- **artifact hygiene:** `eval/results/` now mixes canonical report artifacts and heavy
  diagnostics; this will get worse if R1/R5/R6 produce more live traces;
- **tool-search parity:** Epic C (`hybrid discovery-aware tool search`) is still open
  and should be treated as a later evidence-gated wave, not folded into subagents;
- **agent-note / progress UX:** `agent_note` remains default-off without the promised
  50-turn cost study; chat progress should not wait for real subagents;
- **settings / flags cleanup:** experiments under an **operator rollout gate** need an
  explicit policy: retire, keep off with runbook, or promote only after evidence;
- **API / UI integration:** chat, graph, reader, and benchmark panels are still separate
  product surfaces even when they explain one workflow;
- **security / artifact privacy:** more traces and summaries increase the chance of
  committing sensitive local paths, workspace ids, prompts, or corpus excerpts.

These are included in the wave roadmap below rather than left as loose follow-ups.

---

## 2. Did we go somewhere wrong?

### 2.1 Not wrong: killing the separate LLM router

The move away from "LLM router above specialists" was correct. It reduced a shallow
decision layer whose interface was almost as complex as its implementation. The current
`RoutePlan` / `QuestionFeatures` module is deeper: callers see typed route intent,
while the implementation hides substring/regex heuristics, completion rules, and
post-retrieval handoff policy.

**Decision:** do not reopen the separate LLM-router architecture unless a concrete
benchmark shows deterministic routing cannot handle a new class of questions.

### 2.2 At risk: treating subagents as automatic improvement

The E1 result is the warning sign: read-only subagents are architecturally cleaner,
but the paired live run shows a large p95 regression. The risk is not "subagents are
bad"; the risk is letting a nice diagram override latency and operator evidence.

**Decision:** keep E1 under **operator rollout gate** (not “code off”): the next
subagent work should focus on a real spawn / fanout / merge runtime with lifecycle
and provenance, not simply more specialist nodes inside the same graph. Until then,
stacks sensitive to latency should disable E1 legs via env (see R0 companion matrix).

### 2.3 At risk: over-trusting LLM-as-judge

The pairwise judge is now a good measurement instrument, but not a decision gate.
The multiseed range is useful; the cross-family agreement result is sobering.

**Decision:** keep `agent_v3_quality_judge_v1` advisory until both are true:

- strict calibration passes for at least two consecutive windows;
- cross-family agreement or a replacement adjudication method becomes acceptable
  for promotion decisions.

### 2.4 Missing perspective: chat UX as part of architecture

The engine now has traces, gates, and summaries. But chat quality is not only final
answer quality. It also includes:

- visible progress that matches actual work;
- fast partial feedback before long graph/retrieval phases finish;
- understandable "why this answer" provenance;
- cancellation and recovery that feel deliberate, not broken;
- thread memory that improves long sessions without surprising the user.

**Decision:** next agent architecture work must include chat contract / SSE evidence
as first-class acceptance, not only backend trace metrics.

---

## 3. Openclaude best practices: what to copy

This is based on local inspection of `/home/roman/pyprojects/ML/openclaude`, especially:

- `src/services/compact/autoCompact.ts`
- `src/services/toolUseSummary/toolUseSummaryGenerator.ts`
- `src/services/SessionMemory/sessionMemory.ts`
- `src/Task.ts`
- `src/coordinator/workerAgent.ts`

### 3.1 Copy: explicit context-window budgets and circuit breakers

Openclaude's auto-compact code reserves output tokens, computes an effective context
window, and has a consecutive failure circuit breaker. The useful lesson is not the
exact constants; it is that compaction is a policy module with headroom, warnings,
blocking thresholds, and failure backoff.

**Apply here:**

- promote our long-thread compaction policy into one explicit module with:
  - context window budget;
  - summary output reservation;
  - warning threshold;
  - blocking threshold;
  - consecutive failure circuit breaker;
  - telemetry for "why compact fired".
- add trace-review metrics for compact trigger reason, compact failure streak, and
  post-compact token estimate.

### 3.2 Copy carefully: session memory extraction at natural breaks

Openclaude session memory waits for token and tool-call thresholds, and prefers natural
breaks where the last assistant turn has no tool calls. That maps well to our
`thread_insights` backlog.

**Apply here:**

- finish `thread_insights` A2/A3 as a freshness-gated memory layer;
- inject it with deterministic precedence, not as another ad-hoc prompt chunk;
- require long-thread eval for recall / consistency, not just token reduction;
- do not update memory in the middle of tool-call bursts unless deadline salvage
  requires it.

### 3.3 Copy: tool summaries as UI labels, not reasoning substrate

Openclaude's `toolUseSummaryGenerator` creates a short progress label, around
30 characters. It does not try to become the agent's internal memory.

Our E2 `tool_use_summary` is heavier: it summarizes long `ToolMessage` batches for
runtime context. That can be useful, but the current cache ratio is not good enough.

**Apply here:**

- split two concepts:
  - `progress_tool_summary`: short UI label, cheap / non-critical / no gate;
  - `runtime_tool_summary`: context compression for the model, gated by cache ratio.
- keep `runtime_tool_summary` off until `side_llm_cache_read_ratio_avg >= 0.4` on
  heavy live or a documented provider policy says the cost is acceptable.

### 3.4 Copy: task lifecycle as a real interface

Openclaude `Task.ts` has explicit task types, statuses, terminal-state checks, output
files, offsets, notification state, and kill semantics. This is closer to a real
subagent runtime than our current specialist handoff telemetry.

**Apply here:**

- design `AgentTask` / `SubagentRun` as a first-class module:
  - `pending | running | completed | failed | killed`;
  - `parent_turn_id`, `child_turn_id`, `task_type`, `description`;
  - output artifact pointer and offset;
  - cancellation / timeout semantics;
  - terminal-state invariant;
  - merge provenance.
- SSE should expose lifecycle without leaking internal tool logs.
- Trace-review should gate missing lifecycle events before we trust fanout.

### 3.5 Do not copy blindly

| Openclaude pattern | Why not direct copy |
|--------------------|---------------------|
| UI/client-heavy task model | SciGraph agent runs in backend API + SSE, not only local CLI UI. Need persistence and API contracts. |
| Haiku-specific summaries | We run through OpenRouter and model mix; provider cache behavior differs. |
| General-purpose worker agents | SciGraph needs domain-aware evidence/provenance, not generic autonomous workers by default. |
| GrowthBook-style flags | We already have `Settings` + persisted settings; avoid introducing a second flag system. |

---

## 4. Architecture decisions for the next horizon

### 4.1 Keep supervisor v3, but stop deepening it by default

**Decision:** `langgraph_supervisor_v3` remains the canonical backbone.

**Do next:**

- reduce latency and improve observability before adding new roles;
- keep `langgraph_research_v1` as comparison / fallback, not product default;
- remove or quarantine flags that are "experiment complete" but still need an explicit
  **operator rollout** policy (`keep off`, `rerun evidence`, or `promote`).

**Do not do next:**

- add another LLM-based coordinator above supervisor;
- enable E1 subagents for production **without** latency evidence and env escape hatches;
- make pairwise judge a merge blocker.

### 4.2 Create a real subagent runtime only if it buys lifecycle depth

The current subagent language is overloaded:

- fixed graph specialists are not the same as spawned child tasks;
- sidechain traces are not the same as independently cancellable subagents;
- a child ReAct graph without lifecycle and merge provenance is mostly added cost.

**Proposal:** build one thin vertical slice of real spawned subagent runtime:

1. `SubagentRun` state model and persistence adapter.
2. One read-only child task type: `corpus_explore`.
3. Fanout cap = 1 first; no parallel fanout until lifecycle is stable.
4. Merge node with source provenance.
5. SSE lifecycle events and trace-review gates.

**Acceptance:**

- live trace shows parent -> child -> merge with terminal child status;
- cancellation kills child task and records `killed`;
- no missing lifecycle events;
- p95 latency does not exceed current supervisor baseline by >25%;
- user-visible progress is clearer than current fixed-specialist progress.

### 4.3 Split chat contract from engine internals

The chat API should not mirror every graph implementation detail. It should expose a
stable product contract:

- intent / plan headline;
- progress step labels;
- evidence gathered;
- partial answer readiness;
- final answer with citations;
- explicit degraded-mode reason when salvage was used.

**Next doc / implementation:** update `docs/specs/agent-chat-v1.md` after the
subagent runtime design, before changing SSE payloads.

### 4.4 Treat context as a product feature

Context compaction is not just a token-saving optimization. It changes what the user
expects the agent to remember.

**Next:**

- finish `thread_insights` as a product-visible memory layer;
- separate compact-for-cost from memory-for-quality;
- add long-thread eval cases where the correct answer depends on earlier turns;
- show in trace artifacts which memory layer influenced the answer.

---

## 5. Ingestion phase: what we forgot

The article currently tells the CLOSE-WAIT story and mentions async ingest. That is
true, but incomplete. The next product bottleneck is likely not runtime routing; it
is corpus quality and ingestion drift.

### 5.1 Open ingestion issues that matter for answer quality

| Backlog item | Why it matters |
|--------------|----------------|
| `paper_profile year/venue — OD null-rate closure` | Agent answers and UI cards lose bibliographic trust when year/venue are missing. Read-path overlay is not enough; writeback should happen at ingest/merge time. |
| `Ingest dedup — parity with osint-gr` | Work dedup exists; author/entity conflicts during ingest are still weaker than scan dedup and weaker than osint-gr's conflict resolution model. |
| `BT6 gold realism + optional embedding-soft quote fallback` | Claims F1 is the headline weakness; gold semantics and quote fallback are still the critical path. |
| `Standardize ingestion LLM seams around structured executor` | Different LLM call patterns across stages mean different retry/error/diagnostic contracts. |
| `Switch Qdrant production embeddings to bge-m3` | Phase 0 was done, but full BT2/BT4/BT5 revalidation remains open for acceptance. |
| `reuse_cached_markdown cache-collision` | Cache ambiguity can silently affect reproducibility. |

### 5.2 Next ingestion wave should be quality-first, not pipeline-first

**Wave I1 — corpus quality baseline**

- Pick one stable CV workspace and one non-CV pilot workspace.
- Run:
  - claims paraphrase BT6 pilot/holdout;
  - citation edge benchmark;
  - retrieval BT2/BT4/BT5;
  - paper_profile null-rate snapshot;
  - work/author/entity dedup report.
- Publish one markdown note: "corpus quality baseline after agent stabilization".

**Acceptance:**

- no headline metric update without a manifest;
- pilot and holdout remain separate;
- CV vs non-CV are not averaged;
- `trust_signal.runtime_mode == live` for headline artifacts.

**Wave I2 — ingestion structured executor standardization**

- Move claims onto the same structured executor/factory contract as metadata /
  semantic stages, where reasonable.
- Keep VL as non-Instructor transport, but use the shared low-level transport /
  diagnostics vocabulary.
- Align retry, timeout, span, and diagnostics keys across ingest stages.

**Acceptance:**

- one documented `stage -> seam` matrix;
- no bespoke direct-call protocol in claims for production path;
- diagnostics keys are stable enough for report aggregation.

**Wave I3 — dedup and bibliography trust**

- Add ingest-time year/venue writeback where OpenAlex/PDF front matter is reliable.
- Extend ingest conflict queue for authors/entities or explicitly decide post-hoc only.
- Add domain-specific dedup policy for author/entity matching.

**Acceptance:**

- OD/null-rate snapshot improves or has documented "thin corpus" rationale;
- author/entity conflict count is visible after ingest;
- no hidden merge without operator decision if gated path is enabled.

---

## 6. Refactoring: first pass should be observability infrastructure

The next refactor pass should not start with agent graph code. That code has just been
stabilized and has strong tests. The immediate risk is the tooling that tells us
whether agent changes are safe.

### 6.1 Priority 1: split trace-review monoliths

**Source backlog:** `[OPEN] Split trace-review CLI monoliths`.

**Why first:** every future agent/context/subagent decision depends on trace-review.
If `trace_review_schema.py` and `trace_regression_compare.py` keep accumulating gates,
the gate itself becomes unreviewable.

**Target module shape:**

- `trace_review/serde.py`
- `trace_review/timeline.py`
- `trace_review/metrics_aggregation.py`
- `trace_review/acceptance_gates.py`
- `trace_review/gates/latency.py`
- `trace_review/gates/cache_telemetry.py`
- `trace_review/gates/writer_oscillation.py`
- `trace_review/gates/compaction.py`
- `trace_compare/policies/*`
- thin CLI wrappers preserving current flags.

**Acceptance:**

- no file in `scripts/live_check/` over ~600 LoC for this subsystem;
- each gate has unit tests independent of full JSON fixture;
- CLI output and JSON schema remain backward compatible;
- existing `tests/scripts/live_check/*` pass.

### 6.2 Priority 2: split `agent_v3_quality/runner.py`

The runner now owns transport execution, heartbeat, row assembly, summary merge, and
rendering. Since pairwise judge remains advisory, this is not as urgent as trace-review,
but it is the next benchmark-maintenance bottleneck.

**Acceptance:**

- branch execution adapter separate from reporting;
- JSON/markdown rendering separate from suite control;
- golden tests for summary keys and compare output.

### 6.3 Priority 3: API chat seams

`api/agent_v2.py` is still around ~1000 LoC even after partial module extraction.
Do not refactor it while changing SSE semantics. First freeze chat contract, then split.

**Acceptance:**

- router / streaming / payload / orchestration are separate modules;
- SSE protocol changes happen in one module;
- smoke and trace-audit tests cover compatibility.

### 6.4 Priority 4: ingestion pipeline seams

`ingestion/_pipeline_impl.py` and ingestion LLM seams remain partial. Do this after
the corpus quality baseline, so refactor decisions follow observed quality gaps.

---

## 7. Benchmark and promotion policy

### 7.1 What can be a gate now

- `final_answer_missing_count == 0`
- `missing_span_count == 0`
- `tool_loop_repeat_max <= 3`
- `writer_oscillation_count_max <= 1`
- unacceptable warn reasons outside allowlist == 0
- latency hard drift policy from trace-review compare
- paper-source restore after compact, once live long-thread acceptance is green

### 7.2 What must stay advisory

- `agent_v3_quality_judge_v1` pairwise winner;
- cross-family judge agreement;
- `mean_delta` without multiseed range;
- token cost ratio when provider does not emit token totals;
- E1 subagent improvement claims without paired latency evidence;
- E2 runtime summary improvement claims while cache ratio is below 0.4.

### 7.3 Next promotion review condition

Open a promotion review only when:

- Wave D strict calibration passes in two consecutive windows;
- `judge_prompt_fingerprint` is stable for at least two weeks;
- multiseed spread stays <= 0.15 on the frozen pilot;
- cross-family agreement improves materially or an alternative adjudication policy is documented;
- promotion PR includes rollback criteria.

---

## 8. Detailed roadmap waves

### R0 — roadmap reconciliation and flag policy

**Status:** reconciled **2026-05-13**. Full matrix and terminology live in
[`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md)
(companion — keeps this file as the entrypoint without inventory bloat).

**Goal:** before coding, make the current state unambiguous. The old D/E/F/G/H plan
contains a mix of done, default-on, gated, and "operator recommended" statements.
This wave prevents the next plan from inheriting contradictory status.

**Canonical precedence:** (1) `science_graphrag/config.py` field defaults;
(2) `agent-engine-and-benchmarks-next-waves-2026-05-09.md` queue + artifact pointers;
(3) wave closeouts below; (4) [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md)
for structural follow-ups. When narrative and defaults disagree, split **Settings
default** vs **operator rollout gate** (never both in one vague sentence).

**Inputs:**

- `agent-engine-and-benchmarks-next-waves-2026-05-09.md`
- `wave-h-rollout-decision-2026-05-12.md`
- `wave-d-promotion-operator-closeout-2026-05-12.md`
- `pre-f-closure-readiness-2026-05-12.md`
- current `config.py` defaults and `.env.example`
- `docs/backlog/refactor-backend.md`

**Completed outputs (was work items):**

1. **Status table** — one matrix lists E1, E2, Wave H L4 compact, microcompact,
   `agent_note`, `thread_insights`, and `agent_v3_quality_judge_v1` with columns
   `feature / Settings default / operator gate / evidence / decision / next action`
   in the companion doc.
2. **Gated-experiment classification** — `retire` | `keep off` | `rerun evidence` |
   `promote` applied per feature in companion §3.
3. **E1/E2 language** — resolved: defaults in code are `True`; rollout policy stays
   conservative until new live evidence; operators use env overrides (see
   `.env.example` block `--- Agent rollout knobs (R0 reconciliation, 2026-05-13) ---`.
4. **Backlog** — product follow-up for optional **defaults flip** (A vs B) tracked in
   [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) `[OPEN] E1/E2
   Settings defaults vs operator rollout gate (product choice)`.

**Acceptance:**

- One table lists E1, E2, Wave H L4 compact, microcompact, `agent_note`,
  `thread_insights`, and `agent_v3_quality_judge_v1` — **in companion** (linked above).
- No roadmap sentence says "default-on" and "keep gated" for the same feature without
  an explicit environment / operator distinction (use **Settings default** vs
  **operator rollout gate** vocabulary).
- [`docs/analysis/README.md`](./README.md) continues to point to this doc as the
  next-horizon entrypoint (and lists the R0 companion).

**Stop condition:** if defaults and evidence disagree and we cannot verify current code
quickly, freeze the feature as "operator-gated" until a live compare is run.

**Artifacts:**

- Updated `agent-engine-next-horizon-2026-05-13.md` (this file).
- [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md) — reconciliation matrix + E1/E2 resolution.
- `.env.example` — commented `SCIENCE_GRAPHRAG_AGENT_*` pointers under `--- Agent rollout knobs (R0 reconciliation, 2026-05-13) ---`.

### R1 — trace-review and compare refactor

**Goal:** make the safety gate maintainable before it absorbs subagent lifecycle,
thread memory, and ingestion-quality signals.

**Why first:** every later wave depends on trace-review. A gate that is hard to change
will either block good work or silently accept bad work.

**Scope:**

- `scripts/live_check/trace_review_schema.py` (facade) and `scripts/live_check/trace_review/`
  (`types`, `serde`, `aggregation`, `gates`, `timeline_*`, `CONTRACT.md`)
- `scripts/live_check/trace_regression_compare.py` (CLI entry) and `scripts/live_check/trace_compare/`
- existing tests under `tests/scripts/live_check/`

**Work items:**

1. Split schema/serde from metric aggregation.
2. Split acceptance gates by concern:
   - final answer / missing spans;
   - tool loops;
   - writer oscillation;
   - latency drift;
   - cache telemetry;
   - compaction restore;
   - future lifecycle gates.
3. Split compare CLI into parser, delta computation, policies, and rendering.
4. Preserve existing CLI flags and JSON output shape.
5. Add table-driven tests per gate with minimal fixtures.

**Acceptance:**

- No file in the trace-review subsystem exceeds ~600 LoC.
- No single function trips `R0915` without an explicit suppression note.
- Existing trace-review tests pass.
- Existing acceptance artifacts still parse.
- A new gate can be added by adding a gate module + test, not editing a giant function.

**Quality gates:**

- `.venv/bin/pytest tests/scripts/live_check/test_trace_review_schema.py tests/scripts/live_check/test_trace_regression_compare.py`
- `black --check` / `isort --check-only` on touched Python files.
- `ReadLints` on touched files.

**Stop condition:** if behavior changes are needed to make the split possible, stop and
write a smaller "behavior-preserving split" checklist first.

**Artifacts:**

- Refactor PR / commit.
- Short closeout note appended here or to `docs/backlog/refactor-backend.md`.

### R2 — chat contract and progress UX

**Goal:** define what the user sees during long agent work before implementing real
spawned subagents. Chat contract should be stable enough that runtime internals can
change without UI churn.

**Scope:**

- `docs/specs/agent-chat-v1.md`
- `science_graphrag/api/agent_v2_modules/stream_lifecycle.py`
- product step mapping / i18n keys
- optional `agent_note` cost study

**Work items:**

1. Define product-level event groups:
   - `intent_detected`;
   - `plan_ready`;
   - `tool_progress`;
   - `evidence_ready`;
   - `subtask_started` / `subtask_completed` (contract-first, even before R4);
   - `degraded_mode`;
   - `final_answer`.
2. Define degraded-mode reasons:
   - deadline salvage;
   - tool timeout;
   - partial evidence;
   - compact restored sources;
   - child task failed / killed (reserved for R4).
3. Audit `_product_step_code_for_tool` production traces for generic `using_tool`.
4. Decide `agent_note`: run the 50-turn cost study or explicitly keep it off until
   the next UX cycle.
5. Add snapshot tests for SSE event contract where possible.

**Acceptance:**

- `agent-chat-v1.md` documents stable user-facing event semantics.
- New progress labels can be added without exposing graph node names.
- Generic `using_tool` is either absent in representative traces or explicitly allowed.
- `agent_note` has a decision: pilot / postpone / drop.

**Quality gates:**

- Relevant API smoke tests.
- Product-step coverage tests.
- Trace-review still green on quick/default suite after contract changes.

**Stop condition:** if the UI cannot represent lifecycle/degraded-mode without major
frontend work, split a frontend roadmap item before changing SSE semantics.

**Artifacts:**

- Updated `docs/specs/agent-chat-v1.md`.
- Optional updated `docs/analysis/agent-note-cost-eval-2026-05-06.md`.

### R3 — context memory and compaction productization

**Goal:** separate context cost control from user-visible memory quality.

**Scope:**

- L4 `llm_history_compact`
- microcompact triggers
- `thread_insights`
- long-thread eval
- cache telemetry

**Work items:**

1. Run live long-thread Wave H acceptance with current provider settings:
   `--min-side-llm-cache-read-ratio 0.4` and paper-source restore gate.
2. Promote compaction policy into an explicit module:
   - context budget;
   - summary output reservation;
   - warning threshold;
   - blocking threshold;
   - consecutive failure circuit breaker;
   - trigger reason telemetry.
3. Finish `thread_insights` A2:
   - prompt injection with deterministic precedence;
   - freshness policy;
   - audit in run metadata.
4. Add A3 eval lane:
   - long-thread recall / consistency;
   - compaction churn;
   - latency/cost;
   - memory influence audit.
5. Keep `runtime_tool_summary` separate from `progress_tool_summary`.

**Acceptance:**

- Live long-thread acceptance passes or feature remains provider-gated.
- Trace-review includes compact trigger reason and failure streak.
- `thread_insight` appears only when freshness policy says it should.
- Long-thread eval shows no regression in trust/verdict and a measurable gain in
  recall/consistency on memory-dependent cases.

**Quality gates:**

- `tests/agent/test_llm_history_compact.py`
- `tests/agent/test_message_sanitizers.py`
- `tests/agent/test_paper_sources_restore_regression.py`
- `tests/scripts/live_check/test_long_thread_compaction_eval.py`
- trace-review compare with cache and paper-source gates.

**Stop condition:** if live cache ratio falls below 0.4 on current provider and
latency/cost rises, treat L4 full-history compact as **operator-off** (disable via
`SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED`) and focus on deterministic
microcompact only.

**Artifacts:**

- Live long-thread trace-review artifacts.
- Updated Wave H decision section or companion closeout.

### R4 — real subagent runtime vertical slice

**Goal:** test whether spawned child runtimes buy lifecycle depth and better UX, not
just a more complicated graph.

**Scope:**

- new `SubagentRun` / `AgentTask` model;
- one read-only child task (`corpus_explore`);
- fanout cap 1;
- lifecycle SSE;
- merge provenance;
- trace-review gates.

**Work items:**

1. Write ADR: fixed specialists vs spawned child runtimes.
2. Define `SubagentRun` state:
   - ids: `parent_turn_id`, `child_turn_id`, `task_id`;
   - type / description;
   - status: `pending | running | completed | failed | killed`;
   - timestamps;
   - output pointer;
   - merge provenance;
   - error class.
3. Implement in-process child execution first; no parallel fanout until terminal
   state and cancellation semantics are stable.
4. Add cancellation / timeout propagation.
5. Add merge node with provenance and no hidden overwrite of parent state.
6. Add SSE events using R2 contract.
7. Add trace-review metrics:
   - `subagent_lifecycle_missing_count`;
   - `subagent_terminal_state_missing_count`;
   - `subagent_merge_provenance_missing_count`;
   - child latency and timeout count.
8. Compare against current supervisor baseline.

**Acceptance:**

- Live trace shows parent -> child -> merge with terminal child status.
- Cancellation records `killed` and does not emit a fake success.
- Merge provenance appears in final run metadata.
- p95 latency does not regress >25% unless explicitly waived.
- User-visible progress is clearer than current fixed specialist progress.

**Quality gates:**

- Unit tests for terminal state transitions.
- SSE contract tests.
- Trace-review acceptance + compare.
- Pairwise judge remains advisory only; not used to promote R4.

**Stop condition:** if lifecycle is incomplete or p95 regression exceeds 25% without a
clear fix, stop R4 and keep fixed specialists. Do not add fanout >1.

**Artifacts:**

- ADR under `docs/adr/`.
- `eval/results/trace-review-subagent-runtime-r4-*.{json,md}`.
- Closeout note linked from this doc.

### R5 — benchmark promotion discipline

**Goal:** keep LLM-as-judge useful without letting it become a false authority.

**Scope:**

- `agent_v3_quality_judge_v1`;
- calibration window;
- multiseed baseline;
- cross-family research;
- runner/report split.

**Work items:**

1. Keep current pilot/holdout frozen until a judge-prompt revision is explicitly
   started.
2. If revising judge prompt, reset stabilization window and update fingerprint guard.
3. Add failure analysis for low cross-family agreement:
   - near-tie cases;
   - rubric ambiguity;
   - verbosity bias;
   - evidence-grounding disagreements.
4. Decide whether promotion requires cross-family agreement, a tie-aware policy, or a
   third "manual adjudication" lane.
5. Split `eval/agent_v3_quality/runner.py` after R1 or in parallel if conflicts are low.
6. Keep cost axis (`cost_delta`) next to quality axis in all summaries.

**Acceptance:**

- No promotion review while strict calibration is red.
- Prompt changes reset the stabilization window.
- Multiseed range is always shown with headline `mean_delta`.
- Runner/report split preserves artifact schema.

**Quality gates:**

- judge prompt fingerprint tests;
- agent-v3-quality runner tests;
- compare tests;
- mock-agent CI remains separate from live promotion evidence.

**Stop condition:** if cross-family agreement remains below a useful threshold after
one prompt/rubric revision, keep the lane advisory and stop spending runtime cycles
on promotion. Use it as regression smell, not release gate.

**Artifacts:**

- Updated calibration note.
- Optional `agent-v3-quality-judge-rubric-revision-2026-05.md`.
- Runner split closeout.

### R6 — corpus and ingestion quality baseline

**Goal:** measure whether the corpus can support better answers before spending more
cycles on runtime architecture.

**Scope:**

- one stable CV workspace;
- one non-CV pilot workspace if available;
- claims / citations / retrieval / dedup / paper_profile null-rate.

**Work items:**

1. Run `config-check` and infra preflight before any long benchmark.
2. For each workspace, run:
   - claims paraphrase BT6 pilot/holdout;
   - citation edge benchmark;
   - retrieval BT2/BT4/BT5;
   - paper_profile null-rate snapshot;
   - work dedup report;
   - author/entity dedup report if available.
3. Create a manifest that separates:
   - CV vs non-CV;
   - pilot vs holdout;
   - live vs mock/synthetic;
   - pre/post dedup or gold changes.
4. Decide whether Habr/public headline metrics should remain pinned or receive a new
   update window.

**Acceptance:**

- All headline-eligible artifacts have `trust_signal.runtime_mode == live`.
- Pilot and holdout are not averaged.
- CV and non-CV are not averaged.
- Any metric update names exactly one changed axis.
- Baseline note identifies whether ingestion quality or runtime quality is the larger
  bottleneck.

**Quality gates:**

- Long-running ops checklist.
- Benchmark trust aggregate.
- `decision_gate` review.

**Stop condition:** if non-CV quality collapses, stop agent architecture expansion and
prioritize ingestion/gold realism for domain transfer.

**Artifacts:**

- `docs/analysis/corpus-quality-baseline-after-agent-stabilization-2026-05.md`
- pinned `eval/results/habr-window-*` if publication metrics change.

### R7 — ingestion architecture and quality repairs

**Goal:** address the ingestion issues that directly affect answer quality and
benchmark trust.

**Depends on:** R6 baseline.

**Work items:**

1. Claims structured executor standardization:
   - shared schema modules;
   - shared factory/preset;
   - aligned retry/timeout/span/diagnostics.
2. Year/venue writeback:
   - use OpenAlex/PDF front matter where reliable;
   - persist to graph, not only read-path overlay;
   - re-run null-rate snapshot.
3. Dedup parity:
   - matrix `work / author / entity × scan / ingest`;
   - decide post-hoc vs gated ingest pause;
   - add visible conflict counts.
4. Cache cleanup:
   - migrate old markdown artifacts to document-scoped keys;
   - reduce ambiguous fallback roots.
5. BGE-M3 acceptance closure:
   - re-run live BT2/BT4/BT5 after corpus/model changes;
   - close ADR-021 only when retrieval gates are stable.

**Acceptance:**

- `stage -> seam` matrix documented.
- Claims production path no longer uses bespoke direct-call protocol where structured
  executor is appropriate.
- Year/venue null-rate improves or has documented corpus rationale.
- Dedup conflicts are visible after ingest.
- Retrieval gates are stable after BGE-M3 cutover acceptance.

**Stop condition:** if claims gold realism remains the limiting factor, do not tune
extractor prompts further until gold tiers are clarified (`production_realistic` vs
`aspirational_v2`).

**Artifacts:**

- Updates to ingestion standardization doc.
- Dedup parity matrix update.
- Null-rate and retrieval benchmark artifacts.

### R8 — artifact hygiene and storage seam

**Goal:** keep benchmark artifacts reviewable and prevent diagnostics from polluting
canonical results.

**Scope:**

- `eval/results/`;
- live trace outputs;
- local repair progress JSONL;
- benchmark aggregator inputs;
- future MinIO/S3 seam, if needed.

**Work items:**

1. Define artifact classes:
   - canonical committed summary;
   - publication window manifest;
   - live diagnostic trace;
   - local repair/progress;
   - CI transient artifact.
2. Add default output roots per artifact class.
3. Update runners to make `--out` class explicit.
4. Add sanitizer/check for local paths, workspace ids, secrets, and large prompt dumps
   in committed canonical artifacts.
5. Update aggregator to read canonical inputs through a registry/manifest seam.

**Acceptance:**

- `eval/results/` contains small canonical/report-facing artifacts by default.
- Heavy live diagnostics default to ignored storage.
- Publication manifests point to checksummed canonical artifacts.
- No new absolute local paths in committed canonical JSON.

**Stop condition:** if storage migration is too large, first add a linter/check that
prevents new diagnostic dumps in `eval/results/`.

**Artifacts:**

- Artifact-class policy doc.
- Runner default output changes.
- Optional backlog item for MinIO/S3 if multi-host storage becomes real.

### R9 — product integration: answer as report

**Goal:** connect chat, graph, reader, and retrieval evidence into one workflow that
users can understand.

**Why this is last:** R9 should consume stable chat contract (R2), quality baseline
(R6), and graph/retrieval evidence. Doing it earlier risks polishing the wrong
runtime behavior.

**Work items:**

1. Define an "answer report" structure:
   - final answer;
   - cited snippets;
   - graph paths / relations used;
   - works inspected;
   - confidence / degraded-mode note;
   - follow-up questions.
2. Map agent evidence payloads to graph/reader UI affordances.
3. Decide which graph readability backlog items are required for report UX:
   - reader view virtual `AUTHORED` edges;
   - cap-aware aggregation;
   - display keys for i18n;
   - denormalized Work counters.
4. Add product eval cases that judge not only final text but evidence usability.

**Acceptance:**

- A user can move from answer -> citation -> paper context -> graph relation without
  switching mental models.
- Product eval includes evidence usability checks.
- Graph payload changes are backward compatible.

**Stop condition:** if graph readability backlog is still too open, do a graph UX
wave before answer-report integration.

**Artifacts:**

- `docs/analysis/agent-answer-report-roadmap-2026-05.md` or update to existing UI plans.
- Product eval fixtures.

---

## 9. Execution cadence and dependency graph

```text
R0 status reconciliation
  ├─ R1 trace-review split
  │   ├─ R3 context memory productization
  │   ├─ R5 benchmark promotion discipline
  │   └─ R4 real subagent runtime (after R2)
  ├─ R2 chat contract
  │   └─ R4 real subagent runtime
  ├─ R6 corpus / ingestion baseline
  │   ├─ R7 ingestion repairs
  │   └─ R9 answer-as-report
  └─ R8 artifact hygiene (can start after R0; should finish before scale-up)
```

Recommended order:

1. **R0 + R1** first: remove ambiguity and protect the gate.
2. **R2 + R3** next: product contract and context memory before new runtime machinery.
3. **R6** in parallel if operator time is available: it may change priorities.
4. **R4** only after R2 and enough R1 gate modularity.
5. **R5** as a calibration lane, not a blocker for R1/R2/R3.
6. **R7/R8/R9** after the baseline tells us where product quality is bottlenecked.

---

## 10. Cross-wave decision matrix

| Question | Default decision | Reopen only if |
|----------|------------------|----------------|
| Return separate LLM router? | No. Keep deterministic `RoutePlan`. | Deterministic routing fails a new frozen suite and a non-LLM rule cannot cover it. |
| Default-on E1 fixed subagents? | No for **operator rollout** until new evidence; **Settings** defaults are `True` (override via env). | Paired live shows no >25% p95 regression and clearer progress. |
| Promote pairwise judge to gate? | No. Advisory. | Two strict calibration windows pass and promotion review is explicit. |
| Use `tool_use_summary` as runtime memory? | No for **operator trust** until ratio gate; **Settings** default is `True` (set `SCIENCE_GRAPHRAG_AGENT_TOOL_USE_SUMMARY_ENABLED=false` if needed). | Heavy live `side_llm_cache_read_ratio_avg >= 0.4` or accepted provider policy. |
| Use tool summaries as UI progress labels? | Yes, but cheap and non-critical. | Cost study shows visible latency/cost regression. |
| Update Habr/public headline metrics? | Only via pinned window manifest. | One changed axis is isolated and `trust_signal.runtime_mode == live`. |
| Start graph/chat product integration? | After R2 + R6. | A user-facing demo is needed earlier; then keep it prototype-only. |
| Add more benchmark cases? | Only after artifact hygiene and baseline discipline. | Case fixes a known blind spot and does not change promotion thresholds. |

## 11. Stop conditions

Stop adding agent complexity if any of these happens:

- subagent vertical slice fails latency by >25% without a clear fix;
- trace-review split is not done and new gates require touching giant functions again;
- pairwise judge calibration remains red after one prompt/rubric revision;
- ingestion quality baseline shows claims/retrieval regressions larger than runtime gains;
- chat UX cannot explain progress/degraded-mode clearly to a user.

In that case, the next best work is not another agent architecture wave. It is:

1. corpus quality and ingestion repair;
2. trace-review/benchmark maintainability;
3. chat UX contract;
4. only then new runtime machinery.

---

### R1 closeout — trace-review package split (2026-05-13)

- **Code layout:** `scripts/live_check/trace_review/` (`types`, `serde`, `serde_helpers`, `aggregation`, `timeline_helpers`, `timeline_case`, `gates/*`); `scripts/live_check/trace_compare/` (`parser`, `delta`, `policies`, `rendering`, `runner`); `trace_review_schema.py` and `trace_regression_compare.py` remain **import-stable facades**.
- **Contract:** [`scripts/live_check/trace_review/CONTRACT.md`](../../scripts/live_check/trace_review/CONTRACT.md) documents behavior-preserving JSON/CLI invariants.
- **Tests:** `tests/scripts/live_check/test_trace_review_schema.py`, `test_trace_regression_compare.py` (includes table-driven `verdict_from_signals` + delta symmetry checks).

---

## 12. Reference links

| Topic | Doc / artifact |
|-------|----------------|
| Prior plan | [`agent-engine-and-benchmarks-next-waves-2026-05-09.md`](./agent-engine-and-benchmarks-next-waves-2026-05-09.md) |
| Agent master plan | [`agent-unified-plan-doing-and-benchmarks-2026-05-08.md`](./agent-unified-plan-doing-and-benchmarks-2026-05-08.md) |
| Runtime/tools/context roadmap | [`agent-runtime-tools-context-roadmap-2026-05-04.md`](./agent-runtime-tools-context-roadmap-2026-05-04.md) |
| Wave H decision + R0 feature matrix | [`wave-h-rollout-decision-2026-05-12.md`](./wave-h-rollout-decision-2026-05-12.md); [`agent-engine-feature-status-2026-05-13.md`](./agent-engine-feature-status-2026-05-13.md) |
| Wave F slice1 closure | [`wave-f-f3-slice1-closure-2026-05-12.md`](./wave-f-f3-slice1-closure-2026-05-12.md) |
| Wave F slice2 expansion | [`wave-f-f3-slice2-expansion-2026-05-12.md`](./wave-f-f3-slice2-expansion-2026-05-12.md) |
| Wave D operator closeout | [`wave-d-promotion-operator-closeout-2026-05-12.md`](./wave-d-promotion-operator-closeout-2026-05-12.md) |
| Trace-review SOP | [`../runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) |
| Promotion review | [`../runbooks/benchmark-family-promotion-review.md`](../runbooks/benchmark-family-promotion-review.md) |
| Structural backlog | [`../backlog/refactor-backend.md`](../backlog/refactor-backend.md) |
| Ingestion LLM standardization | [`ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`](./ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md) |
| Ingest dedup complexity | [`ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md`](./ingest-entity-extraction-and-dedup-complexity-analysis-2026-04-27.md) |
