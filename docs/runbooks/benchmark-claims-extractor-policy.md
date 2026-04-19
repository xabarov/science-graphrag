# Claims benchmark: extractor policy and holdout

## Two extractors

| Mode | CLI | Code | Use |
|------|-----|------|-----|
| **Harness** (default) | `--extractor harness` (omit flag) | `eval.claims.heuristic_extract.extract_claims_anchor_harness` | Frozen regression on `tests/fixtures/benchmarks/claims/` |
| **Production path** | `--extractor production` | `science_graphrag.ingestion.claims.stub.extract_claims_stub` | Same callable as ingestion until ontology-claims-v1 ships |

`--use-stub` remains a shortcut for «harness slot filled with stub» (negative tests); do not combine with `--extractor production`.

## Holdout rules (anti-overfitting)

1. **`claims_pilot_train`** in `tests/fixtures/benchmarks/claims/case_tiers.json` — training-style pack; **do not** tune prompts or thresholds only on this tier and then report numbers on the same cases as final proof.
2. Prefer **separate** tiers for tuning vs reporting (`claims_mini`, `claims_corpus_v2_mini`, `claims_pilot` as holdout-style packs).
3. When promoting metrics into a stronger gate, follow [benchmark-family-promotion-review.md](benchmark-family-promotion-review.md).

## Regenerating advisory JSON (optional)

```bash
science-graphrag-claims-benchmark tests/fixtures/benchmarks/claims \
  --suite --tier claims_mini \
  --json-out eval/results/current-claims-mini-suite.json
```

Use `--extractor production` only when checking alignment with ingestion (expect empty predictions until the real extractor exists).
