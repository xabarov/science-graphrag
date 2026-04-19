# Retrieval benchmark fixtures

Layout: `tests/fixtures/benchmarks/retrieval/<case_id>/question.txt` + `gold.json`.

- **Tiers:** [`case_tiers.json`](case_tiers.json) — `merge_safe_contract` (default suite) vs `strict_pilot` (fingerprint strict gold).
- **contract_only** cases are merge-safe smoke against a live API (they only assert trace shape).
- **strict_pilot** cases use `required_chunk_fingerprints` (replace with values captured from `POST /v1/query` on the signed-off pilot corpus); until then CI uses `--mock-answer`.

CLI: `science-graphrag-retrieval-benchmark` — see [docs/benchmarks/retrieval-eval-v1.md](../../../docs/benchmarks/retrieval-eval-v1.md). After changing `docker-compose.dev.yml` env for the API, run **`make dev-recreate-api`** so the container picks up new variables.

Examples:

```bash
# default tier = merge_safe_contract
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --mock-answer
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --tier strict_pilot --mock-answer
```
