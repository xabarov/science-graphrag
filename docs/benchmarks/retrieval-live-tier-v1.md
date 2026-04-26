# Retrieval live mini-tier (`live_corpus_mini`) — v1

**Status:** implemented (fixtures + tier manifest). **Role:** advisory — same policy as other retrieval lanes until promoted in [`runbooks/benchmark-decision-gate.md`](../runbooks/benchmark-decision-gate.md) §8.

## Goal

Provide **5 reproducible questions** against the **signed-off pilot stack** (Neo4j + Qdrant populated from the pilot corpus, including the YOLOv1 work). Unlike `--mock-answer` CI smoke, this tier expects a **live** `answer_query` call. Work scoping uses portable gold: ``filter_work_layer1_slug`` (e.g. ``yolov1``) resolved to the current Neo4j ``Work.id`` at run time; chunk gates use ``min_hit_count`` (fingerprints are optional / may be empty after re-chunk).

## Preconditions

1. Docker stack up (`docker compose` per project docs) with Postgres, Neo4j, Qdrant, API.
2. Pilot corpus ingested so the YOLOv1 paper exists in Neo4j (title match for layer1 slug ``yolov1``).
3. Chunk vectors present in Qdrant for that work (and neighbors for corpus-wide cases).
4. **No** `--mock-answer``.

Re-ingests change chunk fingerprints; keep ``required_chunk_fingerprints`` empty for portable gates or re-capture from `POST /v1/query` in a dedicated PR.

## Tier manifest

[`tests/fixtures/benchmarks/retrieval/case_tiers.json`](../../tests/fixtures/benchmarks/retrieval/case_tiers.json) lists:

| Case id | Scope | Notes |
|---------|-------|--------|
| `live_yolov1_intro` | work-scoped | Single required chunk |
| `live_yolov1_architecture` | work-scoped | Single required chunk |
| `live_yolov1_training` | work-scoped | Loss / training question |
| `live_yolov1_methods_combo` | work-scoped | Two required chunks |
| `live_corpus_methods_wide` | corpus-wide | `work_id: null`, two hashes from pilot capture |

Work id and some fingerprints may align with `strict_pilot_*` captures when the **same** natural-language question is used. For **different** questions (e.g. intro vs methods overview), re-capture `required_chunk_fingerprints` from the top `citations` of `POST /v1/query` for that question — do not assume chunks match another case’s gold.

## Commands

```bash
# Single case (live)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval/live_yolov1_intro \
  --json-out eval/results/retrieval-live-one.json

# Full mini-tier (live; fails if stores empty or corpus mismatch)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite \
  --tier live_corpus_mini \
  --json-out eval/results/retrieval-live-corpus-mini.json
```

For **CI-safe** smoke only, keep using:

```bash
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite --mock-answer \
  --tier merge_safe_contract
```

## Re-capture procedure

When ingest or chunking changes invalidate fingerprints:

1. Run `POST /v1/query` with each `question.txt` and the same `work_id` / `top_k` as in `gold.json`.
2. From `citations`, copy `chunk_fingerprint` values that must be grounded for the question.
3. Update `required_chunk_fingerprints` and the `description` field with date + environment note.
4. Optionally refresh `strict_pilot_*` in the same PR if they share the same pilot work.

## Future

- Optional assertions on `graph_context.methods` / `datasets` once schema is stable.
- Optional promotion of this tier to **nightly advisory** with compose services in CI (secrets + seeded corpus).
