# Heavy / operational outputs vs `eval/results/` (Phase 3 tail)

**Canonical gate inputs** (`current-*.json`, `benchmark-metrics-summary.*`, gold-adjacent paths) must stay under [`eval/results/`](../../eval/results/) per [`scripts/benchmark_aggregator/paths.py`](../../scripts/benchmark_aggregator/paths.py) and §10.4 of the MinIO roadmap — **do not** move those defaults to `data/diagnostics/` without an ADR and gate updates.

This table lists **operational** or **large** runners/scripts and where they write by default.

| Area | Path / default | Policy |
|------|------------------|--------|
| Chat-agent roadmap runner | `default_local_diagnostics_dir("chat_agent")/…` ([`eval/chat_agent/roadmap_runner.py`](../../eval/chat_agent/roadmap_runner.py)) | Already off `eval/results/`. |
| OD backfill / audits | `data/diagnostics/od/` via `default_result_path` / scripts ([`eval/chat_agent/od_claims_backfill.py`](../../eval/chat_agent/od_claims_backfill.py), `scripts/chat_agent_od_*.py`) | Heavy JSONL → S3 diagnostics prefix (or local defaults for paths only). |
| References smolagents suite | `data/diagnostics/eval/refs_agent_suite_<ts>.json` ([`scripts/experiment_references_smolagents_spike.py`](../../scripts/experiment_references_smolagents_spike.py)) | Default under `data/diagnostics/eval/` (not `eval/results/`). |
| References bench harness | `data/diagnostics/eval/refs_bench/` ([`scripts/run_references_benchmark.py`](../../scripts/run_references_benchmark.py)) | Default under `data/diagnostics/eval/`. |
| Most Typer eval runners | `--json-out` user-supplied; examples in [`eval/README.md`](../../eval/README.md) often use `eval/results/…` | Use explicit path; for **large** live runs prefer `data/diagnostics/eval/` or S3 via env. |
| Aggregate / reports | `eval/results/benchmark-metrics-summary.*`, `*-for-report.json` | **Canonical** — keep. |
| Per-case chat-agent S3 | `chat_agent_case_result_object_key` in [`science_graphrag/storage/benchmark_object_keys.py`](../../science_graphrag/storage/benchmark_object_keys.py) | Reserved for future writers; UI full runs already use `BenchmarkRunPersistencePort`. |

## Diagnostics uploads

`write_diagnostic_json` / `write_diagnostic_jsonl_line` always use the configured S3 bucket and `SCIENCE_GRAPHRAG_S3_DIAGNOSTICS_KEY_PREFIX`; see [`science_graphrag/artifacts/diagnostic_object_sink.py`](../../science_graphrag/artifacts/diagnostic_object_sink.py).

## Curation

See [`eval-results-curation.md`](eval-results-curation.md) and [`scripts/list_eval_results_large.py`](../../scripts/list_eval_results_large.py).
