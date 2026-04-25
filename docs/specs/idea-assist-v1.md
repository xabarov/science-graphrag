# Idea Assist v1 (Wave S, advisory)

## Scope

Idea-assist provides a rubric-evaluated advisory flow for:

1. generating up to 3 hypothesis candidates, and/or
2. surfacing claim contradiction candidates.

This is an advisory surface only; no production graph writes are allowed in Wave S.

## API contract

Endpoint: `POST /v1/agent/idea-assist`

Feature flag: `SCIENCE_GRAPHRAG_HYPOTHESIS_ENABLED` (default `false`)

Request:

```json
{
  "workspace_id": "ws_abc",
  "seed_topic": "contrastive pretraining for remote sensing",
  "mode": "both",
  "max_candidates": 3
}
```

Where:

- `workspace_id` is required.
- `seed_topic` is optional; when omitted, workflow uses workspace summary seed.
- `mode` is one of `hypotheses | contradictions | both`.
- `max_candidates` is clamped to `1..5` (default `3`).

Response:

```json
{
  "hypotheses": [
    {
      "text": "Hypothesis text",
      "supporting_claim_ids": ["claim_1", "claim_2"],
      "novelty_hint": "Partially overlaps with prior segmentation baseline claims.",
      "evidence_quotes": ["verbatim quote 1", "verbatim quote 2"]
    }
  ],
  "contradictions": [
    {
      "claim_a_id": "claim_a",
      "claim_b_id": "claim_b",
      "description": "Claims report opposite effects for the same setup."
    }
  ],
  "tool_trace": [],
  "duration_ms": 0,
  "run_metadata": {
    "advisory_only": true
  }
}
```

## Workflow

1. Retrieve candidate evidence via `idea_search` (workspace-scoped).
2. Fetch claims grouped by polarity via read-only `cypher_query`.
3. Probe optional contradiction edges with `edge_search` (read-only).
4. Ask LLM with frozen prompt to output structured JSON.
5. Return normalized candidates with tool trace and runtime metadata.

## Rubric (0..6)

Three dimensions, each scored `0..2`:

1. **novelty**: hypothesis is not near-copy of existing workspace claims.
2. **evidence_support**: candidate is grounded in valid claim IDs and verbatim quotes.
3. **no_plagiarism**: candidate does not reuse title/abstract text too closely.

Acceptance threshold for mini suite: `mean_rubric_score >= 4.0 / 6`.

## Bench family

- Fixtures: `tests/fixtures/benchmarks/idea_assist_v1/`
- Runner: `eval/idea_assist/runner.py`
- Judge: `eval/idea_assist/judge.py` + frozen `judge_prompt_v1.md`
- Artifacts:
  - `eval/results/current-idea-assist-mini.json`
  - `eval/results/current-idea-assist-judge-pilot.json`

## Risk controls

1. **Hallucinations:** each hypothesis must include at least one evidence quote.
2. **Plagiarism:** judge checks overlap against workspace titles/abstract snippets.
3. **Publication safety:** UI marks output as advisory and requires human review.
4. **Ontology safety:** Wave S does not persist hypothesis/contradiction graph edges.
