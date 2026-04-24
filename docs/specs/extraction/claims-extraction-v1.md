# Claims extraction contract (v1, Wave O)

**Status:** implemented (ingestion + benchmark production lane).

## Scope

LLM extracts `Claim` rows with mandatory **verbatim** `Evidence.quote` substrings from retrieval chunks. See [ontology-claims-v1.md](../ontology-claims-v1.md) and [ADR 008](../../adr/008-ontology-claims-wave-h.md).

## Code

- `science_graphrag/ingestion/claims/extractor.py` — `extract_claims_llm`
- `science_graphrag/ingestion/claims/models.py` — `ClaimDraft`, `EvidenceDraft`
- Feature flag: `SCIENCE_GRAPHRAG_CLAIMS_EXTRACTION_ENABLED` (ingestion); benchmarks use `force_benchmark=True` in `eval/claims/runner.py`

## Output shape (logical)

- `claim_text`, `claim_type`, `polarity`, `confidence`
- `evidence[]`: `chunk_fingerprint`, `quote`, optional `section_path`

## Benchmarks

- Harness: `science-graphrag-claims-benchmark --extractor harness`
- Production: `--extractor production` → `eval/results/current-claims-production-pilot.json`
