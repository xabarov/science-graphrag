# Pilot / advisory benchmark runs (retrieval live + claims + references resolution)

Чеклист для локального или CI-like прогона **advisory** lanes после изменений в retrieval, чанкинге или claims harness. Не влияет на `decision` в [`benchmark-decision-gate.md`](benchmark-decision-gate.md).

## Предусловия

- Репозиторий: корень клона `science-graphrag`, активирован `.venv`.
- Для **live retrieval** (`live_corpus_mini`): подняты Postgres, Neo4j, Qdrant, API; пилотный корпус заингестирован (work id YOLOv1 совпадает с `strict_pilot_*` / `live_*` gold).
- Для **claims**: только файловые фикстуры, LLM не нужен (v1 anchor harness).
- Для **references_resolution**: только `gold.json` + deterministic `synthetic_predictions` (без Neo4j) до wiring graph resolver.

## Команды

```bash
# 1) Быстрый merge-safe retrieval (mock, CI-safe)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite \
  --tier merge_safe_contract --mock-answer \
  --json-out eval/results/current-retrieval-merge-safe-mock.json

# 2) Strict pilot fingerprints (mock)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite \
  --tier strict_pilot --mock-answer \
  --json-out eval/results/current-retrieval-strict-pilot-mock.json

# 3) Live mini-tier (без mock — нужен живой Qdrant + ingest)
science-graphrag-retrieval-benchmark tests/fixtures/benchmarks/retrieval --suite \
  --tier live_corpus_mini \
  --json-out eval/results/current-retrieval-live-corpus-mini.json

# 4) Claims: contract + mini-pack
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite \
  --tier claims_merge_contract \
  --json-out eval/results/current-claims-merge-contract.json
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite \
  --tier claims_mini \
  --json-out eval/results/current-claims-mini-suite.json

# 4b) Claims: corpus-derived v2 mini + pilot packs (claim_id_or_normalized_text)
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite \
  --tier claims_corpus_v2_mini \
  --json-out eval/results/current-claims-corpus-v2-mini.json
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims --suite \
  --tier claims_pilot \
  --json-out eval/results/current-claims-pilot-suite.json

# 4c) References resolution (synthetic harness)
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite \
  --tier refs_merge_contract \
  --json-out eval/results/current-references-resolution-contract.json
science-graphrag-references-resolution-benchmark tests/fixtures/benchmarks/references_resolution --suite \
  --tier refs_mini \
  --json-out eval/results/current-references-resolution-mini.json

# 5) Сводка метрик (включает advisory секции, если JSON на месте)
.venv/bin/python scripts/aggregate_benchmark_metrics.py

# 6) Agent v3 quality judge (Wave B, advisory — pairwise ReAct vs supervisor v3)
# Детерминированный mock (CI / без стека):
science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
  --tier judge_mini --mock-agent \
  --json-out eval/results/current-agent-v3-quality-judge-mini.json \
  --md-out eval/results/current-agent-v3-quality-judge-mini.md
# Live subprocess (нужны Neo4j/Qdrant/ключи; каждый runtime — отдельный процесс):
# science-graphrag-agent-v3-quality-benchmark tests/fixtures/benchmarks/agent_v3_quality --suite \
#   --tier judge_mini --transport subprocess \
#   --json-out eval/results/current-agent-v3-quality-judge-mini.json
# Сравнение двух снимков:
# science-graphrag-agent-v3-quality-compare \
#   eval/results/current-agent-v3-quality-judge-pilot-prev.json \
#   eval/results/current-agent-v3-quality-judge-pilot.json \
#   --json-out eval/results/current-agent-v3-quality-judge-compare.json \
#   --md-out eval/results/current-agent-v3-quality-judge-compare.md
```

## Если live tier красный

1. Убедиться, что вопрос и `work_id` в `gold.json` соответствуют ожидаемому прогону.
2. Вызвать `POST /v1/query` с текстом из `question.txt`, скопировать `chunk_fingerprint` из top `citations`.
3. Обновить `required_chunk_fingerprints` в кейсе и поле `description` (provenance). См. [retrieval-live-tier-v1.md](../benchmarks/retrieval-live-tier-v1.md).

## Связанные документы

- [benchmark-program-status.md](benchmark-program-status.md)
- [ontology-claims-benchmark-v1.md](../benchmarks/ontology-claims-benchmark-v1.md)
- [benchmark-family-references-resolution-v1.md](../specs/benchmark-family-references-resolution-v1.md)
- [eval/README.md](../../eval/README.md)
