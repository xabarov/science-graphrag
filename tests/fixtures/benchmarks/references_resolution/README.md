# References resolution benchmark fixtures (v1 harness)

Each case is a directory with `gold.json` only (no `article.md` required for the synthetic harness).

- **Tiers:** [`case_tiers.json`](case_tiers.json) — `refs_merge_contract` (single contract case) vs `refs_mini` (three frozen resolution checks).
- **Harness:** the default runner loads `synthetic_predictions` from `gold.json`; Neo4j lane uses `--resolver graph` (Wave M).
- **Spec:** [`docs/specs/benchmark-family-references-resolution-v1.md`](../../../docs/specs/benchmark-family-references-resolution-v1.md).

```bash
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite --tier refs_mini \
  --json-out eval/results/current-references-resolution-mini.json
```

Graph-backed lane (requires Neo4j with matching `:Work` rows for DOI/arXiv/`work_id` keys in `expected_resolutions`):

```bash
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite --tier refs_mini \
  --resolver graph \
  --json-out eval/results/current-references-resolution-graph.json
```
