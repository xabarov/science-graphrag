# Documentation changelog (maintenance)

Short log of **navigation / indexing** changes under `docs/` (no functional code changes in this pass).

## 2026-05-15 — Full docs cleanup pass

### Indexes & policy

- **`docs/README.md`:** explicit **Active entrypoints**, **Reference**, **Historical / archive**; aligned wording with `.cursorignore` (incl. `eval/results/diagnostics`, `eval/results/multimodel`).
- **`docs/analysis/README.md`:** table maps roles to `Doc status`; **Archive & deletion policy** (stubs, backlinks, `_archive/`); LLM zones + `.cursorignore` eval paths.
- **`docs/analysis/ACTIVE.md`:** marked `Doc status: active`.
- **`docs/pilot/README.md`:** restored minimal stub so `docs/pilot/` links stay valid and policy matches ignore rules.

### Analysis headers

- Unified **`Doc status`** + **`Read hint`** (where missing) on long / canonical `docs/analysis/*.md` files, including the **active trio**: unified plan, next horizon, feature status; **`agent-engine-and-benchmarks-next-waves-2026-05-09.md`** as **`historical stub`**.

### Runbooks / specs / roadmap / backlog

- **`docs/runbooks/benchmark-program-status.md`**, **`agent-trace-review-sop.md`:** live planning pointers to `ACTIVE` / next-horizon / feature-status; historical wave log = stub only.
- **`docs/roadmap.md`:** Phase 3 Wave O — distinguish **reference** roadmap §7.4 vs **active** trust/extraction entrypoints.
- **`docs/specs/README.md`:** agent chat table links `ACTIVE`, unified plan, next horizon before deep runtime roadmap.
- **`docs/backlog/refactor-backend.md`:** sequencing sources use feature-status for E1/E2; next-waves stub marked historical.

### ADR / architecture

- **`docs/adr/README.md`**, **`docs/architecture/README.md`:** short “live planning” pointers so ADR index is not confused with weekly backlog.

### Link fixes (non-archive)

- **`docs/adr/025-llm-distributed-quota-redis.md`:** `science_graphrag/llm/concurrency.py` link depth (`../../`).
- **`docs/analysis/llm-concurrency-semaphore-and-timeout-hardening-plan-2026-04-27.md`:** `../../science_graphrag/`, `../../ui/` for repo-root paths.
- **`docs/analysis/phoenix-closeout-evidence-2026-04-27.md`:** `../../science_graphrag/`, `../../tests/`.
- **`docs/analysis/agent-v3-quality-judge-calibration-2026-05.md`:** fixtures path `../../tests/`.
- **`docs/specs/contradictions-article-grounded-v1.md`:** fixtures `../../tests/`.
- **`docs/specs/extraction/semantic-concept-topic-v1.md`:** ADR links `../../adr/`.

### Scripts

- **`scripts/pilot_measure_latency.py`:** docstring points at `docs/runbooks/pilot-checklist.md` (no removed pilot filenames); see Quality pass for pylint wrap-up.

### Known remaining debt

- **`docs/report/habr-article-2026-04-29.md`** embeds `assets/defense/*` images; if missing locally, restore assets or replace with public URLs for export.
- **`docs/analysis/_archive/**`** may still contain relative links written from older path assumptions; fix opportunistically when editing those files.

## 2026-05-15 — Quality pass (follow-up)

- **`scripts/pilot_measure_latency.py`:** docstring wrapped for pylint line length; plain path to pilot checklist (no fragile markdown URL in docstring).
- **`docs/analysis/README.md`:** archive policy step 2 points to **Closed / superseded** by name (removed fragile long fragment anchor).
- **`docs/README.md`:** note that the detailed product table extends the upper sections; pilot row wording matches stub-only `docs/pilot/`.
- **`docs/analysis/agent-engine-feature-status-2026-05-13.md`:** merged redundant Read hint / Role; fixed nested list indentation.
- **`docs/analysis/ontology-benchmarks-trust-audit-2026-04-25.md`:** removed stale claim that master roadmap §10 is the only live «what next»; normalized same-folder markdown links with `./`.
- **`docs/pilot/README.md`:** clarified `Doc status` vs ignore policy and when the folder is empty aside from this index.
