# Work dedup review queue (v1 draft, Wave H3)

**Status:** draft — reporting only. **Smart dedup (embeddings + LLM + Postgres queue)** is specified in [work-dedup-pipeline-v2.md](work-dedup-pipeline-v2.md) (ADR [014](../adr/014-work-dedup-smart-wave-l.md)).

## Operator flow

1. Run `science-graphrag work-dedup-report` (add `--json` for machine-readable clusters).
2. For each cluster, decide `keep_id` / `drop_id` and run existing `science-graphrag merge-work`.
3. Log decision in pilot / release notes when closing a wave.

## Future automation (out of scope until gated)

- Persisted queue table + UI triage
- Auto-suggestions scored by DOI/OpenAlex agreement
