# Ingestion LLM architecture and Instructor standardization — 2026-04-27

**Doc status:** `reference`

**Read hint:** deep architecture/reference plan for ingestion seams. For active priorities use [`agent-engine-next-horizon-2026-05-13.md`](./agent-engine-next-horizon-2026-05-13.md), [`ontology-extraction-benchmarks-plan.md`](./ontology-extraction-benchmarks-plan.md), and [`ACTIVE.md`](./ACTIVE.md).

> **Done-index:** этот файл — план/архитектура без shipped-checklist; сводка по закрытым работам в других analysis-доках — [`completed-work-snapshot.md`](./completed-work-snapshot.md#ingestion-llm-and-instructor-standardization).

## TL;DR

Production ingestion already has a solid **structured extraction seam** based on `SyncInstructorExtractor` + Pydantic models, but it is applied unevenly.

- **Metadata / authorships / references / semantic extraction** already follow the intended pattern.
- **Claims extraction** reuses the same low-level extractor, but bypasses the shared executor and keeps its own local schemas, retry shape, and diagnostics contract.
- **VL PDF extraction** is intentionally a different kind of call (multimodal markdown generation, not schema extraction), but it still duplicates transport / timeout / observability policy instead of sharing a common seam.

The right target is **not** "use Instructor literally everywhere". The right target is:

1. every **text -> structured object** ingestion stage uses the same Instructor + Pydantic + executor contract;
2. every **non-structured LLM call** (for example VL PDF -> Markdown) uses a shared transport / tracing / error-policy seam even if Instructor is not the right tool.

## Why this analysis exists

The current ingestion stack grew in waves:

- ADR 003 introduced document slices and task-aware chunking;
- ADR 004 introduced the semantic ontology v1 extraction contract;
- later waves added `SyncInstructorExtractor`, semantic retries, claims extraction, method consolidation, and VL PDF support.

As a result, the system is no longer "raw LLM calls everywhere", but it is also not yet fully standardized around one deep module interface. The same production ingestion pipeline now contains:

- one mature path for structured extraction;
- one partially standardized path for claims;
- one separate multimodal path for VL extraction.

This document maps the current seams and proposes a work plan to make the architecture more consistent, testable, and easier to evolve.

## Scope

In scope:

- `science_graphrag/ingestion/_pipeline_impl.py`
- `science_graphrag/ingestion/llm/`
- `science_graphrag/ingestion/claims/extractor.py`
- `science_graphrag/ingestion/vl_pdf.py`

Out of scope:

- embeddings providers;
- dual_validate migration details beyond direct reuse lessons;
- adjudication / dedup LLM paths outside ingestion proper.

## Current architecture

### Pipeline view

`science_graphrag/ingestion/_pipeline_impl.py` orchestrates several distinct LLM-adjacent phases:

1. `PARSE_PDF`
   - PDF -> Markdown via `VLPDFProcessor` when VL mode is enabled.
   - This is a multimodal generation call returning markdown text, not a typed JSON object.

2. `EXTRACT_META`
   - `extract_stages_llm_first(...)` handles metadata, authorships, and references.
   - This is the most standardized structured extraction path today.

3. `WRITE_GRAPH` / semantic sub-step
   - `extract_semantic_method_dataset(...)` extracts methods / datasets / relations.
   - Also uses Instructor + Pydantic and then deterministic post-processing.

4. `EXTRACT_CLAIMS`
   - `extract_claims_llm(...)` extracts claim rows with evidence quotes.
   - Uses the same low-level Instructor client, but not the same executor seam.

### Current seam inventory

| Area | Main module | Return shape | Uses Instructor | Uses shared `run_extraction` | Notes |
| --- | --- | --- | --- | --- | --- |
| Metadata | `ingestion/llm/orchestrator.py` | Pydantic -> domain model | Yes | Yes | Canonical path |
| Authorships | `ingestion/llm/orchestrator.py` | Pydantic -> domain model | Yes | Yes | Canonical path |
| References | `ingestion/llm/orchestrator.py` | Pydantic -> domain model | Yes | Yes | Canonical path with chunk concurrency |
| Semantic methods/datasets | `ingestion/llm/semantic_extraction.py` | Pydantic -> domain model | Yes | Yes | Canonical path with staged prompt shrinking |
| Claims | `ingestion/claims/extractor.py` | Local Pydantic -> claim drafts | Yes | No | Partial adoption |
| VL PDF -> Markdown | `ingestion/vl_pdf.py` | raw markdown string | No | No | Different workload; should not be forced into Instructor |

## What is already good

### 1. There is already a real structured extraction module

`science_graphrag/ingestion/llm/extractor.py` is not a thin pass-through helper anymore. It centralizes:

- OpenAI-compatible client construction;
- Instructor mode selection;
- OpenRouter-specific quirks;
- bounded transport retries;
- token usage extraction;
- Phoenix span payload discipline.

That is a real seam with leverage, and it should remain the only low-level structured extraction adapter in production ingestion.

### 2. Metadata / references / semantic already use the right layered shape

The best current pattern is:

`prompt contract` -> `Pydantic schema` -> `SyncInstructorExtractor` -> `run_extraction(...)` -> `heuristics/domain mapping` -> `fallback policy`

This pattern appears in:

- `ingestion/llm/orchestrator.py`
- `ingestion/llm/semantic_extraction.py`
- `ingestion/llm/prompts/*`
- `ingestion/llm/schemas.py`
- `ingestion/llm/heuristics/*`

This is the architecture to copy.

### 3. Deterministic fallback is preserved as a separate concern

The code does **not** confuse "use Instructor" with "trust the LLM unconditionally". For metadata / authorships / references, the pipeline still keeps:

- heuristic extraction;
- merge policy;
- explicit fallback reasons;
- diagnostics.

That is a good practice and should be retained during standardization.

## Where the architecture is inconsistent

### 1. Claims extraction is only partially standardized

`science_graphrag/ingestion/claims/extractor.py` does use `SyncInstructorExtractor`, but it diverges from the canonical pattern in four ways:

1. it calls `extract_maybe(...)` directly instead of going through `run_extraction(...)`;
2. its Pydantic response models live locally instead of in shared schema modules;
3. it owns a separate fallback protocol (full schema -> compact schema) outside the shared executor seam;
4. it emits diagnostics through an ad-hoc mutable dict rather than a typed diagnostics contract.

This is the most important architectural inconsistency in ingestion today.

### 2. The shared executor is not yet the single orchestration surface

`science_graphrag/ingestion/llm/executor.py` exists, but it is still a narrow helper rather than the universal structured extraction entry point. As long as claims has its own direct flow, the system has at least two different standards for:

- retry accounting;
- span naming;
- error wording;
- fallback layering;
- test surface.

### 3. `SyncInstructorExtractor` config is duplicated at call sites

`orchestrator.py`, `semantic_extraction.py`, and `claims/extractor.py` each assemble `SyncInstructorExtractor(...)` from `Settings` manually. The parameters are close but not identical because the stages have different token budgets.

The stage-specific limits are legitimate. The duplication is not.

Best practice here is a small factory or preset builder:

- same adapter construction rules;
- stage-specific overrides for max tokens / temperature / timeout;
- one place for provider quirks and future model migrations.

### 4. VL PDF extraction is architecturally separate, but operationally too separate

`science_graphrag/ingestion/vl_pdf.py` should stay separate from Instructor because the job is:

- multimodal;
- markdown-generating;
- not naturally a Pydantic response object.

However, it still duplicates concerns that should be shared at a lower seam:

- raw HTTP client setup;
- timeout policy;
- error normalization;
- request metadata discipline.

So VL is a justified exception to Instructor, but not a justified exception to architecture hygiene.

### 5. Diagnostics shape is inconsistent across ingestion LLM stages

Today there are effectively three diagnostics styles:

- `ExtractionDiagnostics` for layer-1 metadata/authorships/references;
- semantic notes / fallback strings in the semantic result;
- ad-hoc `diagnostics: dict[str, Any]` for claims.

This makes cross-stage observability and regression testing harder than necessary.

## Best-practice target architecture

### Rule 1. Structured extraction stages

If a stage is conceptually:

`input text or chunk batch -> typed structured object`

then the default contract should be:

- prompt module in `ingestion/llm/prompts/`
- Pydantic schema in a shared schema module
- `SyncInstructorExtractor` as the only low-level adapter
- `run_extraction(...)` as the only structured execution entry point
- heuristic mapping / validation after the LLM call
- typed diagnostics and fallback reasons

Under this rule:

- metadata stays on the current pattern;
- authorships stays on the current pattern;
- references stays on the current pattern;
- semantic stays on the current pattern;
- claims should migrate to the same pattern.

### Rule 2. Non-structured LLM stages

If a stage is conceptually:

`input pages/images/text -> generated markdown/text`

then Instructor is optional or inappropriate. But the stage should still share:

- request factory / client construction;
- timeout and retry policy;
- telemetry shape;
- normalized provider error handling.

Under this rule:

- VL remains a separate adapter;
- VL should still reuse a lower-level transport / observability seam instead of being fully standalone.

## Recommended work plan

### Phase A. Unify claims with the structured extraction seam

Priority: highest

Changes:

1. Move claims response models into shared schema modules under `science_graphrag/ingestion/llm/`.
2. Introduce a claims-specific executor path built on `run_extraction(...)` rather than direct `extract_maybe(...)`.
3. Preserve the current compact fallback, but express it as executor policy rather than bespoke inline control flow.
4. Replace ad-hoc mutable diagnostics dict with a typed claims diagnostics object or a shared extraction diagnostics family.

Expected leverage:

- one execution contract for all text -> structured extraction stages;
- easier tracing and retry comparisons;
- simpler tests around claims fallback behavior;
- lower chance of drift when changing providers or Instructor modes.

### Phase B. Introduce an extractor factory from `Settings`

Priority: high

Changes:

1. Add a small factory, for example `build_ingestion_extractor(stage=...)`, or a preset object.
2. Keep stage-specific knobs like max tokens, but centralize:
   - base URL;
   - model;
   - mode selection;
   - timeout plumbing;
   - OpenRouter extra-body policy.
3. Make metadata / references / semantic / claims consume the same construction seam.

Expected leverage:

- one place to update provider quirks;
- less boilerplate in orchestrators;
- easier future migration of extraction models.

### Phase C. Standardize diagnostics across structured stages

Priority: medium

Changes:

1. Define a common diagnostics vocabulary:
   - stage name;
   - source (`llm`, `heuristic`, `hybrid`);
   - fallback reasons;
   - retry count;
   - compact fallback used;
   - extraction duration;
   - item counts.
2. Keep stage-specific detail fields where necessary, but nest them under a consistent typed envelope.
3. Align semantic extraction notes and claims diagnostics with the same reporting style.

Expected leverage:

- comparable benchmark evidence across stages;
- easier operator debugging;
- lower ambiguity in tests and runbooks.

### Phase D. Extract a lower-level transport seam for non-structured VL calls

Priority: medium

Changes:

1. Do **not** force VL into Instructor.
2. Instead, introduce a shared low-level client / request helper for OpenAI-compatible calls where the result is raw text.
3. Reuse common timeout, error normalization, usage extraction, and telemetry helpers.
4. Keep `VLPDFProcessor` focused on page batching and PDF-specific behavior.

Expected leverage:

- cleaner separation between "PDF/VL orchestration" and "provider transport";
- fewer provider-specific changes scattered across adapters;
- less operational drift between structured and non-structured ingestion calls.

### Phase E. Make the seam explicit in docs and tests

Priority: medium

Changes:

1. Add or update a short architecture note describing:
   - which ingestion stages are structured;
   - which are multimodal/raw;
   - which seam each stage must use.
2. Add focused tests for:
   - claims compact fallback through the shared executor;
   - extractor factory presets;
   - diagnostics contract stability.

Expected leverage:

- prevents future regressions back to ad-hoc call patterns;
- reduces ambiguity for new extraction stages.

## Proposed implementation order

1. **Claims -> shared executor**
   - highest leverage, lowest architectural ambiguity.
2. **Extractor factory**
   - removes call-site duplication after claims joins the shared seam.
3. **Diagnostics unification**
   - easier once the call path is standardized.
4. **VL transport seam**
   - important, but should not block claims standardization.

## Acceptance criteria for the standardization pass

The standardization pass can be considered successful when:

1. every production ingestion stage that returns a typed structured object uses:
   - shared Pydantic schema modules;
   - `SyncInstructorExtractor`;
   - `run_extraction(...)` or its direct standardized successor;
2. claims no longer owns a bespoke direct-call protocol over `extract_maybe(...)`;
3. extractor construction from `Settings` is centralized;
4. diagnostics vocabulary is aligned across metadata / semantic / claims;
5. VL still remains a separate multimodal path, but no longer duplicates low-level transport policy.

## Risks and non-goals

### Risks

- Over-standardizing too early can blur real differences between claims and semantic extraction.
- A too-generic executor can become shallow and push complexity back into callers.
- Diagnostics unification can become schema churn if done before execution seams are stabilized.

### Non-goals

- replacing deterministic fallback with pure LLM behavior;
- forcing VL markdown extraction into a Pydantic/Instructor contract;
- refactoring dual_validate in the same pass.

## Recommended decision

Adopt the following architectural rule for ingestion:

- **Instructor + shared executor is mandatory for structured extraction stages.**
- **A shared transport / telemetry seam is mandatory for non-structured LLM stages.**
- **Claims is the next module to align. VL is the next module to de-duplicate operational policy.**

This keeps the architecture deep where the problem is the same, and intentionally separate where the problem is different.

## References

- `science_graphrag/ingestion/_pipeline_impl.py`
- `science_graphrag/ingestion/llm/extractor.py`
- `science_graphrag/ingestion/llm/executor.py`
- `science_graphrag/ingestion/llm/orchestrator.py`
- `science_graphrag/ingestion/llm/semantic_extraction.py`
- `science_graphrag/ingestion/claims/extractor.py`
- `science_graphrag/ingestion/vl_pdf.py`
- `docs/adr/003-chunking-and-dedup-strategy.md`
- `docs/adr/004-ontology-v1-scope.md`
- `docs/analysis/instructor-adoption-dual-validate-2026-04-25.md`
- `docs/architecture/ingestion-llm-seams.md` (normative seam summary)
