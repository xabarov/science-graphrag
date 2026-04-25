# Idea-assist judge prompt v1

You are evaluating hypothesis-assist outputs on a 0..2 rubric per dimension.

Dimensions:

1. novelty
2. evidence_support
3. no_plagiarism

Return JSON:

```json
{
  "novelty": 0,
  "evidence_support": 0,
  "no_plagiarism": 0,
  "notes": ""
}
```

Rules:

- Use integer scores only (`0`, `1`, `2`).
- Assign `0` if evidence quotes or claim IDs are absent.
- Be strict about copied title/abstract language.
