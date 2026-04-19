# Teacher-gold fixtures — audit procedure (v1)

Supports backlog item in [refactor-backend.md](../backlog/refactor-backend.md).

## Scope

- `eval/teacher_gold/layer1/` and `eval/teacher_gold/layer2/`
- Generation scripts under `scripts/`
- Persisted UI run payloads under `data/benchmark_runs/*.json` (`result.gold` vs fixture `gold.json`)

## Steps

1. **Inventory** — list case ids; for each, record which `gold.json` fields are empty or default placeholders (`authors_preview`, `abstract_prefix`, semantic arrays).
2. **Compare to last UI run** — for the same `case_id` and `benchmark_family`, diff fixture `gold.json` vs `result.gold` from the newest completed run in `data/benchmark_runs/` (or exported JSON from `/v1/benchmark/runs/{id}`).
3. **Author / identifier hygiene** — flag truncated author strings, missing DOI/arXiv when `article.md` clearly contains them, and suspicious duplicate `work_id` references.
4. **Triage** — classify each delta as: (a) fixture refresh needed, (b) extractor regression, (c) acceptable alias / scoring tolerance — link to [benchmark-stabilization-triage.md](../runbooks/benchmark-stabilization-triage.md).
5. **Remediation** — prefer regenerating teacher gold from the same model profile as documented in the run metadata; avoid hand-editing without recording provenance in git commit message.

## Exit

- Checklist table attached to the pilot or Phase 4 notes with **OPEN / CLOSED** rows per suspect case.
- Agreed rule for refreshing teacher gold vs. adjusting metric thresholds.
- **`publication_year` policy** for arXiv-heavy fixtures: see checklist section *Policy: publication_year* in [teacher-gold-audit-checklist.md](teacher-gold-audit-checklist.md).

**Living checklist (repo):** [teacher-gold-audit-checklist.md](teacher-gold-audit-checklist.md) — phase tables for layer-1 `gold_teacher.json`; layer-2 inventory below in that file. Update phase status when a batch closes.
