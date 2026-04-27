# Curating `eval/results/` (repo hygiene)

`eval/results/` mixes **canonical** artifacts (gate, trust baselines, `current-*` suites referenced from [`benchmark_registry.py`](../../science_graphrag/artifacts/benchmark_registry.py)) with **historical** or **local** JSON. The MinIO roadmap does **not** auto-delete anything here.

## Principles

1. **Do not delete or move** files that [`scripts/aggregate_benchmark_metrics.py`](../../scripts/aggregate_benchmark_metrics.py) or CI expect unless you update paths and regenerate summaries.
2. **Large non-canonical** files (live traces, one-off pilots) should not be committed; prefer `data/diagnostics/` or S3 (see [eval-heavy-artifacts-inventory.md](eval-heavy-artifacts-inventory.md)).
3. **Archival:** if you must keep a large JSON for ops, upload to object storage (`scripts/export_evidence_bundle.py` / `scripts/sync_benchmark_runs_to_s3.py` patterns) and store only a pointer or a small summary in git.

## Operator utilities

- **Find large files:** from repo root  
  `.venv/bin/python scripts/list_eval_results_large.py --min-mb 0.5`  
  (adjust `--min-mb`; add `--json` for machine-readable output.)
- **Inventory:** [eval-heavy-artifacts-inventory.md](eval-heavy-artifacts-inventory.md)
- **GC object storage** (diagnostics / benchmark keys): [`minio-object-lifecycle-phase4.md`](minio-object-lifecycle-phase4.md) and `scripts/gc_object_storage.py`

## Optional manual clean-up

1. Run `list_eval_results_large.py` and review paths.
2. Move obvious stale files to `eval/results/historic/` (if your team uses that convention) or delete locally only after confirming nothing references them in docs or scripts.
3. Re-run `scripts/aggregate_benchmark_metrics.py` if you removed a lane file that was still listed in the registry (expect gate changes).
