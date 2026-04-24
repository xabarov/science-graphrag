# Dedup v1 gold (Wave L)

`gold.json` stores an offline benchmark corpus for work-level dedup:

- `records[]`: compact bibliography cards (`work_id`, `title`, `year`, `first_author`, `abstract`)
- `clusters[]`: sets of `work_id` that represent the same underlying work

`eval/dedup_v1/runner.py` expands clusters into positive pair labels and computes
precision/recall/f1 for a deterministic baseline matcher. This keeps the benchmark
stable and runnable without external services.
