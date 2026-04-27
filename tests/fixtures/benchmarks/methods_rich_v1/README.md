# Benchmark family `methods_rich_v1` (stub)

**Status:** scaffold only — extend with `gold.json` cases and a runner hook when the benchmark console should track rich-method metrics (ADR 023).

## Intended checks (future)

- `description_short` and `description_markdown` grounded in `evidence` quotes.
- Optional LaTeX fragments preserved end-to-end (Neo4j → workspace graph → UI).
- Ingest duplicate suppression counts (`method_ingest_auto_merged`, conflicts queued).

## Related

- Layer-2 semantic expectations: `eval/layer2/spec.py`
- Dedup methods pack: `tests/fixtures/benchmarks/dedup/methods_v1/`
