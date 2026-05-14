# Agent v3 quality judge — cross-family agreement and promotion policy (2026-05-13)

**Status:** advisory lane follow-up after wave **R5** closeout  
**Related:** [`r5-benchmark-promotion-discipline-closeout-2026-05-13.md`](./r5-benchmark-promotion-discipline-closeout-2026-05-13.md), [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R5, [`eval/agent_v3_quality/README.md`](../../eval/agent_v3_quality/README.md)

## 1. Failure modes when cross-family agreement is low

When multiple judge model families disagree on the same pairwise outcome, treat the disagreement as **signal about the instrument**, not as a product verdict. Typical buckets:

1. **Near-tie cases** — rubric scores cluster; small wording or ordering differences flip `winner` between families.
2. **Rubric ambiguity** — criteria such as “more grounded” or “more complete” are interpreted differently by different backbones.
3. **Verbosity / style bias** — one family rewards longer structured answers; another penalizes redundancy vs the gold constraints.
4. **Evidence-grounding disagreements** — families differ on whether citations or tool trace satisfy `forbidden_fail_modes` vs “good enough” summaries.

**Operational response:** log per-case `(case_id, family_a_winner, family_b_winner, confidence, delta)` for a frozen pilot slice; only then consider a single coordinated change (prompt **or** judge model **or** calibration case set).

## 2. Adjudication policy (until strict calibration is green)

| Option | When to use | Risk |
|--------|-------------|------|
| **Advisory only (default)** | Current stance: Wave D strict calibration red; cross-family used for smell, not gates. | Lowest; no false authority. |
| **Tie-aware policy** | If near-ties dominate: treat `winner=tie` or low confidence as non-regressing in compare. | Requires explicit compare contract change + tests. |
| **Cross-family quorum** | e.g. require 2/3 families agree for promotion *review* (still not `decision_gate`). | High runtime cost; still not a substitute for human spot-check. |
| **Manual adjudication lane** | Holdout or pilot subset reviewed by operator for gold/rubric alignment. | Labor-intensive; best for calibration subset only. |

**Decision (2026-05-13):** keep **`agent_v3_quality_judge_v1` advisory**. Do not promote to `decision_gate` until horizon §7.3 conditions hold (two consecutive strict windows green, stable fingerprint, multiseed spread bound, cross-family or alternative policy documented).

## 3. Stop condition

After **one** coordinated remediation iteration (prompt **or** judge model **or** calibration window case set), if cross-family agreement remains below a useful threshold, **stop** spending live cycles on promotion experiments. Use the lane as **regression smell** only; see horizon §R5 stop condition.

## 4. Implementation maintenance

Runner orchestration split: [`eval/agent_v3_quality/runner_branches.py`](../../eval/agent_v3_quality/runner_branches.py), [`eval/agent_v3_quality/runner_report.py`](../../eval/agent_v3_quality/runner_report.py), thin [`eval/agent_v3_quality/runner.py`](../../eval/agent_v3_quality/runner.py) CLI — keeps cost axis (`cost_delta`) and multiseed plumbing maintainable without conflating promotion authority.
