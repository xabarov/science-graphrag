# Retrieval / citation benchmark family (v1)

**Status:** implemented (Wave F) — complements [strategy-v1.md](strategy-v1.md) and roadmap Phase 4 *Retrieval / citation* row.

## Goal

Measure whether `POST /v1/query` returns **grounded** answers: correct work scope, non-empty retrieval trace, and (optional) overlap between returned `chunk_fingerprint` values and a frozen gold set per question.

## Fixture layout

```
tests/fixtures/benchmarks/retrieval/
  <case_id>/
    question.txt          # natural language question
    gold.json               # see schema below
```

### `gold.json` schema (v1)

| Field | Meaning |
|-------|---------|
| `work_id` | Optional filter passed to `answer_query`; `null` = corpus-wide. |
| `top_k` | Optional; default 5. |
| `min_hit_count` | Minimum `retrieval_trace.hit_count` (ignored when `contract_only` is true). |
| `required_chunk_fingerprints` | Each fingerprint must appear on at least one returned citation. |
| `contract_only` | If true, only assert trace + citations list shape (merge-safe smoke on empty Qdrant). |
| `skip_in_suite_cli` | If true, excluded from `--suite` discovery (e.g. unit-test-only stubs). |
| `benchmark_suite_tier` | Optional; when set to `strict_pilot`, the case is excluded from the default merge-safe suite unless `case_tiers.json` lists it (defensive if tiers file is missing). |

**Legacy chunks:** if Qdrant payload has no `chunk_fingerprint`, the API fills citations with the **stable Qdrant point id** (UUID) so strict gold can still freeze expectations until re-ingest writes explicit fingerprints.

## Suite tiers

[`tests/fixtures/benchmarks/retrieval/case_tiers.json`](../../tests/fixtures/benchmarks/retrieval/case_tiers.json) lists case ids per tier:

| Tier | Role |
|------|------|
| `merge_safe_contract` | `contract_only` smoke; default `--suite` tier; safe without live Qdrant when using `--mock-answer`. |
| `strict_pilot` | Non-contract gold with `required_chunk_fingerprints` (placeholders until captured on the signed-off pilot corpus); run with `--tier strict_pilot`; CI uses `--mock-answer` until real fingerprints are committed. |
| `live_corpus_mini` | **Live only:** five questions with frozen fingerprints against the pilot corpus (no `--mock-answer`). See [retrieval-live-tier-v1.md](retrieval-live-tier-v1.md). Advisory for the decision gate. |
| `all` | Every case under the root except `skip_in_suite_cli`. |

## Runner (implemented)

- CLI: `science-graphrag-retrieval-benchmark` (see [pyproject.toml](../../pyproject.toml) `project.scripts`).
- Single case: `science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval/cv_corpus_methods_overview`
- Suite (default tier `merge_safe_contract`): `science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --json-out eval/results/retrieval-suite.json`
- Strict pilot tier: add `--tier strict_pilot` (often with `--mock-answer` in CI until pilot capture).
- **Without live Qdrant/Neo4j:** add `--mock-answer` so each case uses a canned payload derived from its `gold.json`. Cases may set `"skip_in_suite_cli": true` in `gold.json` to exclude them from `--suite` discovery (e.g. fingerprint-only stubs for unit tests).
- Library: `eval.retrieval.runner.run_retrieval_case` accepts optional `answer_fn=` for tests.

## Automation in repo

- Contract scoring: `eval/retrieval/metrics.py` — `score_retrieval_answer`.
- Unit tests: `tests/test_retrieval_benchmark.py` (mocked `answer_query`).
- User journey trace examples: [user-journeys-retrieval-v1.md](../runbooks/user-journeys-retrieval-v1.md) appendix.

## Policy

- Merge-safe local runs may use **`contract_only`** cases when Qdrant is empty.
- Nightly / pilot: add real `required_chunk_fingerprints` after capturing citations from the signed-off corpus (`POST /v1/query`).
