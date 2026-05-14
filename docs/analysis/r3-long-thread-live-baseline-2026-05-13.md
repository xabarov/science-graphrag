# R3 — long-thread live acceptance baseline (operator checklist)

**Role:** executable checklist for **R3** in [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R3 — complements offline harness (`scripts/live_check/long_thread_compaction_eval.py`) with **live** trace-review evidence.

**Status:** operator evidence lane executed (2026-05-13 rerun) — code/docs side is shipped (`compaction_audit.l4_eligibility` + offline `memory_influence_audit_v1`), live pairwise artifacts are now present, but final rollout stance remains **provider-gated** until long-thread cache/compaction signal is observed in a representative acceptance lane.

## Preconditions

- Repo rules: [`../../.cursor/rules/long-running-ops.mdc`](../../.cursor/rules/long-running-ops.mdc) — `config-check`, explicit `AGENT_LIVE_BASE` URL for the target contour, docker healthy, API keys smoke.
- Same `workspace_id` and gate flags for baseline vs candidate paired compares (Wave H paired-rerun note).

## 1. Offline harness (already CI-gated)

```bash
cd /path/to/science-graphrag
.venv/bin/pytest tests/scripts/live_check/test_long_thread_compaction_eval.py -q
```

## 2. Live trace-review long-thread profile

Use [`../runbooks/agent-trace-review-sop.md`](../runbooks/agent-trace-review-sop.md) §9.3–9.5 (Wave H L4 + cache + paper sources).

Minimal pattern:

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:8787
export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
.venv/bin/science-graphrag config-check
# Baseline JSON/MD
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$AGENT_LIVE_BASE" \
  --workspace-id "$AGENT_LIVE_WORKSPACE_ID" \
  --profile heavy --suite heavy --timeout 90 --skip-e2e \
  --out-json eval/results/trace-review-r3-long-thread-heavy-baseline-YYYY-MM-DD.json \
  --out-md eval/results/trace-review-r3-long-thread-heavy-baseline-YYYY-MM-DD.md
# Candidate JSON/MD + compare
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --base-url "$AGENT_LIVE_BASE" \
  --workspace-id "$AGENT_LIVE_WORKSPACE_ID" \
  --profile heavy --suite heavy --timeout 90 --skip-e2e \
  --out-json eval/results/trace-review-r3-long-thread-heavy-candidate-YYYY-MM-DD.json \
  --out-md eval/results/trace-review-r3-long-thread-heavy-candidate-YYYY-MM-DD.md
.venv/bin/python scripts/live_check/trace_regression_compare.py \
  --baseline eval/results/trace-review-r3-long-thread-heavy-baseline-YYYY-MM-DD.json \
  --candidate eval/results/trace-review-r3-long-thread-heavy-candidate-YYYY-MM-DD.json \
  --min-side-llm-cache-read-ratio 0.4 \
  --paper-sources-restored-fail-on-loss \
  --out-json eval/results/trace-regression-r3-long-thread-heavy-YYYY-MM-DD.json \
  --out-md eval/results/trace-regression-r3-long-thread-heavy-YYYY-MM-DD.md
```

### 2b. Representative lane (W3 — stable API + acceptance-shaped load)

Use **stable** live-check API (`http://127.0.0.1:18787`) per project rules, then:

1. **Formal acceptance-shaped trace-review** (requires workspace):

```bash
export AGENT_LIVE_BASE=http://127.0.0.1:18787
export AGENT_LIVE_WORKSPACE_ID=ws-pilot-od
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --suite acceptance \
  --timeout 240 \
  --out-json eval/results/diagnostics/trace-review-r3-representative-$(date -I).json \
  --out-md eval/results/diagnostics/trace-review-r3-representative-$(date -I).md
```

2. **Compaction lane** merged into the same JSON (or standalone):

```bash
.venv/bin/python scripts/live_check/agent_trace_review.py \
  --suite acceptance \
  --with-compaction-turns 4 \
  --compaction-mode focused_long_thread \
  --compaction-max-retries-per-turn 1 \
  --timeout 240 \
  --out-json eval/results/diagnostics/trace-review-r3-representative-compaction-$(date -I).json \
  --out-md eval/results/diagnostics/trace-review-r3-representative-compaction-$(date -I).md
```

**Operator decision matrix (record in this doc):**

| Observation | Decision |
|---------------|----------|
| `side_llm_cache_read_ratio_avg >= 0.4` on acceptance lane + no trust regression | Eligible to revisit provider-gated → promote (per Wave H charter) |
| Cache weak **and** latency/cost up vs paired baseline | Keep **provider-gated** or **operator-off** L4 (`SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED`) |
| `compaction_turn_review.failure_reason` non-null | Fix infra/timeout first; do not interpret cache until lane is green |

**Record here after run:**

| Field | Value |
|-------|-------|
| Representative JSON (path) | `eval/results/diagnostics/...` |
| `side_llm_cache_read_ratio_avg` | |
| `post_compact_paper_sources_restored_total` | |
| `compaction_turn_review.failure_reason` | |
| Operator decision | provider-gated / promote / operator-off |

Representative acceptance lane (2026-05-13, rerun `r4`, bounded e2e + compaction):

| Field | Value |
|-------|-------|
| Baseline JSON | `eval/results/diagnostics/trace-review-r3-representative-2026-05-13-r4.json` |
| Candidate JSON | `eval/results/diagnostics/trace-review-r3-representative-candidate-2026-05-13-r4.json` |
| Compare JSON/MD | `eval/results/diagnostics/trace-regression-r3-representative-2026-05-13-r4.json` / `...md` |
| Compare status | `pass` |
| `side_llm_cache_read_ratio_avg` (baseline / candidate) | `null / null` |
| `post_compact_paper_sources_restored_total` (baseline / candidate) | `0 / 0` |
| `compaction_turn_review.failure_reason` | `null` |
| Additional failures in both lanes | `e2e_failed` (bounded timeout), `failed_check:agent_v2_malicious_deny` on candidate |
| Operator decision | `provider-gated` (insufficient cache/paper evidence for promotion) |

| Field | Value |
|-------|-------|
| Baseline JSON | `eval/results/trace-review-r3-long-thread-heavy-baseline-2026-05-13.json` |
| Candidate JSON | `eval/results/trace-review-r3-long-thread-heavy-candidate-2026-05-13.json` |
| Compare MD | `eval/results/trace-regression-r3-long-thread-heavy-2026-05-13.md` |
| `side_llm_cache_read_ratio_avg` (baseline / candidate) | `None / None` |
| Verdict | pass (compare), with insufficient long-thread cache/compaction signal |
| Operator decision | provider-gated |

Focused follow-up lane (stable API, deterministic compaction probe):

| Field | Value |
|-------|-------|
| Baseline JSON | `eval/results/trace-review-r3-focused-stable-baseline-2026-05-13-v5.json` |
| Candidate JSON | `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v5.json` |
| Compare MD | `eval/results/trace-regression-r3-focused-stable-2026-05-13-v5.md` |
| `compaction_event_count` (baseline / candidate) | `6 / 6` |
| `side_llm_cache_read_ratio_avg` (baseline / candidate) | `None / None` |
| `post_compact_paper_sources_restored_total` (baseline / candidate) | `0 / 0` |
| Verdict | pass (compare), compaction events are present but cache/paper restore signals are absent |
| Operator decision | provider-gated |

Focused follow-up lane v6 (R3 diagnostics hardening):

| Field | Value |
|-------|-------|
| Candidate JSON (normal) | `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6.json` |
| Candidate compaction JSON (normal) | `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6_compaction_review.json` |
| `compaction_event_count` | `4` |
| `compaction_turn_review.failure_reason` | `null` |
| Notes | focused lane completed with explicit per-turn diagnostics in compaction report |

Focused follow-up lane v6-timeout (forced timeout validation):

| Field | Value |
|-------|-------|
| Candidate JSON (timeout) | `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6-timeout.json` |
| Candidate compaction JSON (timeout) | `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6-timeout_compaction_review.json` |
| `compaction_turn_review.failure_reason` | `http_timeout_turn_1` |
| `compaction_turn_review.failed_turn` / `failure_kind` | `1 / http_timeout` |
| Notes | confirms deterministic timeout classification instead of ambiguous hang symptoms |

Targeted L4 + paper-restore probe (2026-05-13, operator attempt):

| Field | Value |
|-------|-------|
| Targeted JSON v2 | `eval/results/trace-review-r3-targeted-l4-paper-2026-05-13-v2.json` |
| Targeted JSON v3 | `eval/results/trace-review-r3-targeted-l4-paper-2026-05-13-v3.json` |
| v3 turn-1 tools | `idea_search`, `workspace_inspect`, `find_works` (plus routing/session tools) |
| v3 turn-1 L4 status | `l4_skip_reason=below_digest_cap`, `llm_full_history_compact=false` |
| v3 turn-2 outcome | `failure_reason=http_timeout_turn_2` |
| Operator decision | provider/infra-blocked for this lane; no promotable L4+paper evidence yet |

Model/provider A/B sanity check (same one-turn scenario, 2026-05-13):

| Field | Value |
|-------|-------|
| A/B artifact (planned) | `eval/results/trace-review-r3-model-ab-2026-05-13.json` |
| Compared models | `qwen/qwen3-235b-a22b-2507` vs `google/gemini-2.5-flash` |
| Execution status | blocked by contour instability (`/v1/settings` and `/v1/settings/llm` timed out during run) |
| Infra snapshot | `api: unhealthy`, `web: unhealthy` (`docker compose ps`) |
| Decision impact | provider/model hypothesis remains inconclusive until contour is healthy |

Post `make dev-up` targeted retry (2026-05-13):

| Field | Value |
|-------|-------|
| Targeted JSON | `eval/results/trace-review-r3-targeted-l4-paper-2026-05-13-v6-post-dev-up.json` |
| Run status | completed (`failure_reason=null`) |
| Observed model | `resolved_chat_llm_model=google/gemini-2.5-flash` |
| Turns completed | `4` |
| `digest_count` progression | `1 -> 2 -> 3 -> 4` |
| `l4_skip_reason` | `below_digest_cap` on all turns |
| `llm_full_history_compact` | `false` on all turns |
| `post_compact_paper_sources_restored_count` | `null` on all turns |
| Operator conclusion | contour stabilized, but this prompt path still does not trigger L4/paper restore evidence |

Acceptance lane rerun (heavy profile/suite, 2026-05-13, stable contour):

| Field | Value |
|-------|-------|
| Baseline JSON | `eval/results/trace-review-r3-forced-lane-baseline-2026-05-13.json` |
| Candidate JSON | `eval/results/trace-review-r3-forced-lane-candidate-2026-05-13.json` |
| Compare JSON/MD | `eval/results/trace-regression-r3-forced-lane-2026-05-13.{json,md}` |
| Compare status | `pass` |
| `side_llm_cache_read_ratio_avg` (baseline / candidate) | `None / None` |
| `post_compact_paper_sources_restored_total` (baseline / candidate) | `0 / 0` |
| Operator conclusion | formal acceptance lane is stable, but does not produce long-thread cache/paper signals by itself |

Targeted forced paper-restore probe v7 (2026-05-13):

| Field | Value |
|-------|-------|
| Targeted JSON | `eval/results/r3-targeted-paper-restore-v7.json` |
| Targeted MD | `eval/results/r3-targeted-paper-restore-v7.md` |
| Turns completed | `6/6` |
| `post_compact_paper_sources_restored_total` | `11` |
| `max_digest_count` | `6` |
| `l4_skip_reason` | `below_digest_cap` on all turns |
| `llm_full_history_compact` | `false` (`null` in audit payload) on all turns |
| Operator conclusion | paper-restore signal is now observed, but no L4 compaction signal yet |

Targeted forced long-thread probe v8 (14 turns, 2026-05-13):

| Field | Value |
|-------|-------|
| Targeted JSON | `eval/results/r3-targeted-paper-restore-v8-14turns.json` |
| Targeted MD | `eval/results/r3-targeted-paper-restore-v8-14turns.md` |
| Turns completed | `14/14` |
| `max_digest_count` | `10` |
| `l4_skip_reason` | `below_digest_cap` (turns 1-9) -> `cooldown_active` (turns 10-14) |
| `side_llm_cache_read_ratio_avg` | `0.0` |
| `post_compact_paper_sources_restored_total` | `0` |
| `llm_full_history_compact` | `false` (`null` in audit payload) on all turns |
| Operator conclusion | cache-read metric appears (zero-level), but L4 compact activation is still not observed |

### 2026-05-13 operator note

- Live contour is reachable in the rerun (`/health` and object-storage preflight passed).
- `agent_trace_review.py` accepts full URL base (`http://127.0.0.1:8787`), and baseline/candidate/compare artifacts were produced successfully.
- Acceptance `suite=acceptance` currently risks long hangs in `e2e_audit_subprocess`; for this closeout we used a bounded `suite=heavy --skip-e2e --timeout 90` lane to obtain deterministic artifacts.
- Compare status is `pass`; in the focused stable rerun we observe non-zero compaction events (`compaction_event_count=6`), but cache/paper long-thread signals remain absent (`side_llm_cache_read_ratio_avg=None`, `post_compact_paper_sources_restored_total=0`), so promotion evidence is still incomplete.
- Additional operator probe (`/v2/agent/query` single-thread diagnostic) hit `httpx.ReadTimeout` on the stable contour, so focused long-thread diagnostics still require hard-timeout + hang-classification follow-up (tracked in backend refactor backlog).
- Follow-up is partially closed: compaction probe now emits explicit per-turn progress and deterministic failure reasons (`http_timeout_turn_n`, `http_error_turn_n`) in JSON/MD; provider-gated stance remains because long-thread cache/paper restore signals are still absent in successful lanes.
- Targeted probe for explicit L4+paper restore evidence is attempted but blocked by contour instability (`api` unhealthy periods + repeated turn-level timeouts), so this turn does not provide promotable R3 evidence.
- A/B provider sanity run was also attempted, but timed out on settings/API surface under unhealthy contour; this does not disprove provider influence, but currently infra instability dominates the signal.
- After contour recovery (`make dev-up`), targeted run is stable but still shows `l4_skip_reason=below_digest_cap` despite digest growth; evidence for L4 compact/paper restore remains absent, so promotion is still blocked for product reasons (not only infra).
- Repeated formal acceptance lane (`heavy/heavy`) now passes deterministically on stable contour, but remains insufficient for R3 promotion because long-thread cache/paper metrics stay zero/absent in that lane.
- In forced probe v7 we now observe non-zero paper-restore signal (`post_compact_paper_sources_restored_total=11`) under stable contour, so this part is no longer blocked purely by infra.
- In extended forced probe v8 (`14` turns), digest reaches `10` and `l4_skip_reason` transitions to `cooldown_active`; `side_llm_cache_read_ratio_avg` appears as `0.0`, but `llm_full_history_compact` remains absent.
- Final R3 stance remains **provider-gated** until a stable acceptance lane emits real cache/compaction long-thread signals under the same gates.

## 3. R3 productization gates (post-implementation)

After `compaction_audit.l4_eligibility` ships (see `science_graphrag/agent/context/compaction_policy.py`):

- Confirm `compaction_audit` on SSE `context_compacted` and sync JSON includes `l4_eligibility` with `l4_skip_reason` or successful L4 audit from `llm_compact`.
- Confirm offline eval merge includes `memory_influence_audit_v1` under `long_thread_eval` in trace-review JSON (`eval/chat_agent/long_thread_eval.py`).

## 4. Decision template

Use exactly one of these after the compare completes:

- **promote** — live compare passes and no R3 stop condition is triggered.
- **provider-gated** — code stays shipped, but provider/model/cache behavior is not trusted enough for general rollout.
- **operator-off** — disable `SCIENCE_GRAPHRAG_AGENT_LLM_FULL_HISTORY_COMPACT_ENABLED=0` and keep only deterministic compact paths.

## Artifacts (placeholder)

Current artifact set (2026-05-13):

- `eval/results/trace-review-r3-long-thread-heavy-baseline-2026-05-13.{json,md}`
- `eval/results/trace-review-r3-long-thread-heavy-candidate-2026-05-13.{json,md}`
- `eval/results/trace-regression-r3-long-thread-heavy-2026-05-13.{json,md}`
- `eval/results/trace-review-r3-focused-stable-baseline-2026-05-13-v5.{json,md}`
- `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v5.{json,md}`
- `eval/results/trace-regression-r3-focused-stable-2026-05-13-v5.{json,md}`
- `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6.{json,md}`
- `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6_compaction_review.{json,md}`
- `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6-timeout.{json,md}`
- `eval/results/trace-review-r3-focused-stable-candidate-2026-05-13-v6-timeout_compaction_review.{json,md}`
- `eval/results/trace-review-r3-forced-lane-baseline-2026-05-13.{json,md}`
- `eval/results/trace-review-r3-forced-lane-candidate-2026-05-13.{json,md}`
- `eval/results/trace-regression-r3-forced-lane-2026-05-13.{json,md}`
- `eval/results/r3-targeted-paper-restore-v7.{json,md}`
- `eval/results/r3-targeted-paper-restore-v8-14turns.{json,md}`
