# `references_resolution` benchmark fixtures (placeholder)

This directory reserves the layout for the next benchmark family after retrieval stabilization.

- Spec: [docs/specs/benchmark-family-references-resolution-v1.md](../../../docs/specs/benchmark-family-references-resolution-v1.md)
- Expansion order: [docs/benchmarks/benchmark-expansion-v1.md](../../../docs/benchmarks/benchmark-expansion-v1.md)

Planned layout per case:

```
<case_id>/
  gold.json       # schema in the spec doc
  context.json    # optional anchors / work_id for the runner (when implemented)
```

No runner consumes these files yet; add `case_tiers.json` here when the first tier is defined.
