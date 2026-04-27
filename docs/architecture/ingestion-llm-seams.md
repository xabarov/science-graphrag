# Ingestion LLM seams (structured vs raw)

This note is the normative counterpart to
`docs/analysis/ingestion-llm-architecture-and-instructor-standardization-2026-04-27.md`.

## Rule 1 — Structured extraction (`text → Pydantic`)

**Stages:** metadata, authorships, references, semantic methods/datasets, claims.

**Contract:**

1. Prompts live under `science_graphrag/ingestion/llm/prompts/`.
2. Response schemas live under `science_graphrag/ingestion/llm/` (e.g. `schemas.py`, `claims_schemas.py`).
3. Use `build_ingestion_extractor(settings, IngestionExtractorPreset.*)` from
   `science_graphrag/ingestion/llm/extractor_factory.py` for client construction.
4. Execute via `run_extraction(...)` from `science_graphrag/ingestion/llm/executor.py`.
5. Claims compact fallback uses `run_claims_extraction_with_compact_fallback(...)` (same executor
   discipline; second span `llm.claims_extraction_compact`).
6. Prefer typed diagnostics (`ClaimsExtractionDiagnostics`, semantic `llm_diagnostics` on
   `SemanticExtractionV1`) over ad-hoc dicts.

## Rule 2 — Raw / multimodal (`images → markdown`)

**Stages:** VL PDF → Markdown (`science_graphrag/ingestion/vl_pdf.py`).

**Contract:**

- Do **not** force these calls through Instructor / Pydantic response models.
- Use `post_chat_completions_json(...)` from `science_graphrag/ingestion/llm/raw_openai_transport.py`
  for OpenAI-compatible `POST /chat/completions` with shared transport retries.
- Keep PDF batching, image encoding, and VL-specific prompts in `VLPDFProcessor`.

## Adding a new ingestion LLM stage

1. Decide whether the output is **structured** (Rule 1) or **raw text** (Rule 2).
2. Reuse the matching seam only — do not duplicate `httpx` / OpenAI client wiring at call sites.
3. Add a focused unit test for schema limits and/or transport behavior.
