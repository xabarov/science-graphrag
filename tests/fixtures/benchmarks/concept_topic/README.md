# Concept / ResearchTopic benchmarks (Wave N)

Advisory-only family: harness matches `anchor_phrase` substrings in article text (see `eval/concept_topic/`).

- **Tiers:** `case_tiers.json` — `concept_topic_merge_contract` (shape), `concept_topic_mini` (5 papers).
- **Articles:** most cases use `article_path` in `gold.json` pointing at `tests/fixtures/benchmarks/layer1/*/article.md`.

Run:

```bash
science-graphrag-concept-topic-benchmark tests/fixtures/benchmarks/concept_topic \
  --suite --tier concept_topic_mini --json-out eval/results/current-concept-topic-mini.json
```
