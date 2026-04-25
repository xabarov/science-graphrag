# ADR 017: Hypothesis / idea-assist as rubric-only advisory layer (Wave S)

- **Status:** Accepted
- **Date:** 2026-04-25

## Context

Wave S needs a measurable "idea assist" capability for hypothesis generation and contradiction discovery.
The current stack already has:

1. Wave R read-only agent tools and traceable execution (`/v1/agent/query`).
2. Wave O claims extraction (`Claim`, `Evidence`, `polarity`) with provenance constraints.

However, hypothesis generation is high-risk (hallucinations, plagiarism, overclaiming) and does not have
enough product guardrails to be promoted to core or persisted as graph truth.

## Decision

1. Introduce a new **advisory-only** workflow: `idea_assist_v1`.
2. Keep the workflow read-only over existing sources (Qdrant retrieval + Neo4j claims lookups).
3. Return candidates and contradiction hints through API/UI, but do **not** write `:CONTRADICTS` or any
   new "hypothesis" nodes/edges to production graph in Wave S.
4. Add benchmark family `idea_assist_v1` with rubric scoring:
   - novelty,
   - evidence support,
   - no plagiarism.
5. Keep judge prompt frozen and run results as advisory artifacts only.
6. Require explicit user gate in UI before hypotheses are treated as publishable content.

## Consequences

- We can evaluate practical usefulness with measurable rubric scores without changing production ontology.
- Claims/evidence provenance from Wave O remains the mandatory grounding layer.
- Any future graph persistence for contradiction/hypothesis structures requires a separate ADR/review.
- This decision extends ADR 016 (tool registry) and aligns with `docs/specs/ontology-claims-v1.md`.
