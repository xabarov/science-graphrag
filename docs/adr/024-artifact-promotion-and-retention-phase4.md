# ADR 024 — Artifact promotion and retention (Phase 4)

## Status

Accepted (Phase 4 implementation).

## Context

Heavy runtime artifacts (diagnostics, benchmark full JSON) live in S3/MinIO with tags (`retention_class`, `written_at`, optional `retention_hint_days`). Git must keep only **small, sanitized, reviewable** payloads aligned with `ArtifactDescriptor.committable` and `scripts/benchmark_aggregator` / CI gate expectations (`docs/analysis/minio-integration-and-artifact-storage-roadmap-2026-04-27.md` §9.4).

## Decision

1. **Retention** — Operational classes use `RetentionClass` in code (`ephemeral_diagnostic`, `benchmark_full_run`, `promoted_review`). Objects uploaded via `diagnostic_object_sink` and `S3BenchmarkRunPersistence` carry S3 **tagging** and **user metadata** for lifecycle rules and `scripts/gc_object_storage.py`.

2. **Promotion** — Moving a runtime object toward git is **explicit** and **never implicit**:
   - Only `scripts/promote_object_for_review.py` (or future API with the same checks) writes under `eval/results/` or other tracked paths.
   - Requires `--commit-path` **and** `--i-confirm-git-write` when the destination is under the repository tree (safety interlock).
   - Output must pass **size cap** (default 512 KiB UTF-8) and **sanitization** (see `science_graphrag/artifacts/promotion.py`).

3. **Sanitization contract** — Promoted JSON:
   - Adds top-level `_promotion_meta` (`source`, `promoted_at` ISO UTC, optional `run_id` / `s3_key`). Any prior `_promotion_meta` on the input payload is removed before sanitization so re-promotion does not nest stale meta.
   - Redacts subtree keys using **whole-segment** rules on key names (split on non-alphanumerics plus explicit pairs such as `api` + `key`, `access` + `token`) so values like `secretary` / `tokenization` / `max_tokens` are not over-redacted.
   - Replaces string values that look like absolute POSIX paths (`/home/...`, `/Users/...`, `/tmp/...`) with the literal `"<redacted-absolute-path>"`.
   - Does **not** claim full safety for arbitrary nested structures; human review remains required before `git add`.

4. **Registry / gate** — Promoted OD-only diagnostics do **not** automatically register in `benchmark_registry` or affect `aggregate_benchmark_metrics` unless a maintainer intentionally places files where the gate reads them. Benchmark promotion is for **human review artifacts**; changing `current-*` baselines remains a separate curated change.

## Consequences

- Ops can expire `science-diagnostics/` and heavy benchmark prefixes via bucket lifecycle and/or GC script.
- Git noise and secret leaks are reduced by forcing a promote step with caps and redaction defaults.

## Related

- [ADR 025 — Mandatory S3-compatible object storage](025-mandatory-s3-object-storage.md)
