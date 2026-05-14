# Eval / trace diagnostics (not canonical)

**R8 policy:** large `trace-review` JSON, chat-agent dumps, and multi-MB benchmark trees belong
here or under `data/diagnostics/`, **not** in committed `eval/results/*.json` summaries.

- Canonical small summaries stay in `eval/results/` (see
  [`docs/analysis/benchmark-artifact-hygiene-policy-2026-05-13.md`](../../docs/analysis/benchmark-artifact-hygiene-policy-2026-05-13.md)).
- Add this path to `.gitignore` if you store machine-local copies; the directory is a
  **convention anchor** for operators and scripts that accept `--out` overrides.
