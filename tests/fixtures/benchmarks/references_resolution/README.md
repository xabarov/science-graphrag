# References resolution benchmark fixtures (v1 harness)

Each case is a directory with `gold.json` only (no `article.md` required for the synthetic harness).

- **Tiers:** [`case_tiers.json`](case_tiers.json) — `refs_merge_contract` (single contract case) vs `refs_mini` (three frozen resolution checks).
- **Harness:** the default runner loads `synthetic_predictions` from `gold.json` until a graph-backed resolver is wired; see [`docs/specs/benchmark-family-references-resolution-v1.md`](../../../docs/specs/benchmark-family-references-resolution-v1.md).

```bash
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite --tier refs_mini \
  --json-out eval/results/current-references-resolution-mini.json
```
