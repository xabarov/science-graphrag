# Benchmark and eval artifact hygiene policy (2026-05-13)

**Role:** **R8** companion to horizon [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md) §R8 and backlog **[OPEN] Split benchmark artifact storage: canonical vs runtime diagnostics** in [`refactor-backend.md`](../backlog/refactor-backend.md).

## 1. Artifact classes

| Class | Purpose | Git | Typical root |
|-------|-----------|-----|----------------|
| **canonical_summary** | Small committed JSON/MD used by CI, trust rollup, Habr windows | Yes | `eval/results/current-*.json` |
| **publication_manifest** | Pinned window describing which canonical artifacts a public post uses | Yes | `eval/results/habr-window-*.json` |
| **live_diagnostic_trace** | Large trace-review / chat-agent dumps, `case_result.json` trees | No (ignored) | `data/diagnostics/` or operator path |
| **local_repair_progress** | JSONL checkpoints, backfill logs | No | `data/` or tmp |
| **ci_transient** | Ephemeral CI upload | No | CI artifact store |

## 2. Rules

1. New runners SHOULD accept explicit `--out` / `--out-json` and default **canonical** paths only for small summaries.
2. Do not commit absolute local paths, raw secrets, or full prompt dumps into **canonical_summary**.
3. Before expanding benchmark case counts or live suites, add or extend a **guard** (linter or `scripts/check_*`) so `eval/results/` does not grow new heavy diagnostics by default.
4. Prefer [`eval/results/diagnostics/README.md`](../../eval/results/diagnostics/README.md) for large trace-review outputs instead of defaulting to `eval/results/*.json`.

## 3. Minimal guard (implemented)

- [`scripts/check_canonical_eval_results.py`](../../scripts/check_canonical_eval_results.py) — default: secret-like patterns + JSON validity on `eval/results/*.json`; `--strict-paths` for home-style absolute paths (legacy artifacts may fail).
- **CI:** merge gate runs `python scripts/check_canonical_eval_results.py` after unit tests (see `.github/workflows/ci.yml`).
- **Local:** `make check-canonical-eval-results` (repo root).

## 4. Full split (backlog)

Moving live traces to ignored storage + manifest registry remains **[OPEN]** until a dedicated refactor pass; this policy doc is the **contract** that pass must implement.
