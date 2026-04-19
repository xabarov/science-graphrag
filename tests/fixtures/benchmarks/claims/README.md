# Claims benchmark fixtures (Wave H1)

Excerpts are **derived from** the public YOLOv1 layer-1 benchmark article ([`../layer1/yolov1/article.md`](../layer1/yolov1/article.md)) for traceability. `anchor_phrase` values support the deterministic v1 harness in `eval/claims/heuristic_extract.py` until real claims extraction is wired.

Additional **corpus-derived** packs (`corpus_*` cases) excerpt `article.md` from other `tests/fixtures/benchmarks/layer1/*_realpdf/` fixtures; they set `claim_match_mode` to `claim_id_or_normalized_text` so scoring tolerates text-first predictions.

**Holdout:** cases with `benchmark_holdout: true` in `gold.json` are excluded from the `claims_pilot_train` tier in [`case_tiers.json`](case_tiers.json).

See [`docs/benchmarks/ontology-claims-benchmark-v1.md`](../../../docs/benchmarks/ontology-claims-benchmark-v1.md).
