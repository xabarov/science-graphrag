# R5 closeout — benchmark promotion discipline (2026-05-13)

## Executive summary

Wave **R5** goal: keep `agent_v3_quality_judge_v1` useful as **measurement** while blocking false authority for promotion.

**Outcome:** judge lane remains **`advisory_only`**. Wave D **strict calibration window** on the frozen 10-case subset is **red** (existing live artifact). **Release-train compare** of embedded frozen pilot baseline vs current `judge_pilot` snapshot **passes** (no regression on gate fields). **Cross-family** agreement on two live pilot judge runs is **0.3846** over 13 cases — useful signal, not a promotion gate without policy.

Canonical manifest (paths, commands, decision): `eval/results/r5-wave-2026-05-13-manifest.json`.

## Phase A — baseline freeze (reproducibility)

- **Mock, calibration-window case IDs** (10 cases from `calibration_window_case_ids.json`): per-case `science-graphrag-agent-v3-quality-benchmark … --case <id> --mock-agent`.
- **Combined artifact** (merged rows + `summarize_suite`): `eval/results/r5-phase-a-calibration-window-mock-combined-2026-05-13.json`, produced with `scripts/merge_agent_v3_quality_benchmark_reports.py --glob 'eval/results/r5-phase-a-part-*.json' …` (same `review_version`; case row order follows sorted glob).
- **Purpose:** CI-friendly contract + deterministic summary shape for the same case list as the strict window (no LLM judge).

## Phase B — strict calibration window (Wave D gate)

- **Artifact:** `eval/results/agent-v3-quality-judge-calibration-window-2026-05-13.{json,md}` (live subprocess, LLM rubric judge).
- **Results:** `strict_ok = False`; per-run `agreement_winner_rate` = 0.4, 0.6, 0.3 (threshold 0.7 each run); `mean_delta` spread = **0.835** (threshold ≤ 0.15).
- **Implication:** per R5 acceptance — **no promotion review** until strict calibration is green in **two consecutive** windows (see horizon §R5 / `benchmark-family-promotion-review.md`).

## Phase C — multiseed (variance discipline)

- **Smoke (mini tier):** `eval/results/r5-phase-c-multiseed-mock-mini-2026-05-13.{json,md}` (`judge_mini`, `--mock-agent --seeds 3`) — fast plumbing check; case set is **not** the frozen calibration window.
- **Calibration-aligned (same 10 ids as Wave D):** per-case loop over `calibration_window_case_ids.json` with `--tier judge_pilot --mock-agent --seeds 3` → `eval/results/r5-phase-c-multiseed-part-<case_id>-2026-05-13.{json,md}`; **do not** approximate this with `--max-cases N` on the full suite (directory order is lexicographic; the first N cases differ from the frozen window).
- **Combined calibration-window multiseed:** `eval/results/r5-phase-c-calibration-window-multiseed-mock-combined-2026-05-13.json` from `scripts/merge_agent_v3_quality_benchmark_reports.py --glob 'eval/results/r5-phase-c-multiseed-part-*-2026-05-13.json' …`.
- **Observation:** with `--mock-agent` / heuristic judge, `mean_delta_spread` stays **0** (expected); value is documenting F2 plumbing and `summary.multiseed` for operators, not judge variance.

## Phase D — cross-family aggregate

- **Inputs:** `current-agent-v3-quality-judge-pilot-wavef-live-deepseek-s3-full.json`, `current-agent-v3-quality-judge-pilot-wavef-live-anthropic-s1-full.json`.
- **Output:** `eval/results/r5-phase-d-cross-family-pilot-2026-05-13.{json,md}` — `inter_judge_agreement_rate ≈ 0.3846` (13 cases).
- **Policy note:** treat cross-family as **advisory** until rubric/calibration improves; tie-aware or manual adjudication remains an explicit follow-up (horizon R5 work item 4).

## Phase E — release-train compare (advisory gate)

- **Command:** `science-graphrag-agent-v3-quality-compare baseline-agent-v3-quality-judge-pilot-embedded.json current-agent-v3-quality-judge-pilot.json --release-train-gate`
- **Output:** `eval/results/r5-phase-e-release-train-compare-2026-05-13.{json,md}` — process **exit 0** (no advisory regression vs embedded baseline on gate fields).

## Phase F — guardrails and follow-ups

- **Fingerprint:** unchanged for this wave; any edit to `eval/agent_v3_quality/judge_prompt_v1.md` requires fingerprint bump + new stabilization window (`tests/scripts/test_judge_prompt_fingerprint_guard.py`).
- **Structural debt:** runner split remains tracked in `docs/backlog/refactor-backend.md` (`[OPEN] Split agent_v3_quality/runner.py …`).

## Rollback / next iteration

- **Rollback:** revert judge prompt / model only via explicit PR; never “silent” promotion without manifest + two-window policy.
- **Next single remediation iteration (if pursued):** one coordinated change (prompt **or** judge model **or** calibration case set), then re-run `--window --runs 3 --strict` and record new manifest.
