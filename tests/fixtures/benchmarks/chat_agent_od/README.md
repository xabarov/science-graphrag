# Chat agent — OD curated scenario specs (PR C Task 6)

This directory holds **product-reviewable** JSON specs for the first 12 OD chat scenarios from [`docs/analysis/chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](../../../docs/analysis/chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) §5.3.

They are **not** consumed by `science-graphrag-chat-agent-roadmap` today. That harness only understands [`tests/fixtures/benchmarks/chat_agent_roadmap/`](../chat_agent_roadmap) and the `expect` block in [`eval/chat_agent/roadmap_metrics.py`](../../../eval/chat_agent/roadmap_metrics.py). **Task 7** should add a runner that maps these specs onto live execution and enforces `requires_*` + lane gating.

## Canonical schema (per file)

Each `cases/*.json` is a single object with:

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `case_id` | string | yes | Stable id, e.g. `od_chat_01_inventory`. |
| `workspace_id` | string | yes | Rich OD UUID workspace (see post-restore closeout doc). |
| `baseline_workspace_id` | string | if `lane_compatibility` is `both` | Pilot workspace for baseline lane (`ws-pilot-od`). |
| `lane_compatibility` | string | yes | One of `baseline`, `rich_od`, `both` (see below). |
| `query` | string | one of `query` / `turns` | Primary user prompt for single-turn cases. |
| `turns` | array | one of `query` / `turns` | Multi-turn: `[{"question": "..."}, ...]`. |
| `answer_class_expected` | string | one of expected / allowed | Single class gate. |
| `answer_classes_allowed` | array | one of expected / allowed | Multi-class allowance. |
| `requires_chunks` | bool | yes | |
| `requires_neo4j_claims` | bool | yes | |
| `requires_qdrant_claim_vectors` | bool | yes | |
| `requires_methods` | bool | yes | |
| `requires_contradictions` | bool | yes | Graph-level tension / claims; not implied by vectors audit alone. |
| `tools_any_of` | array | yes | Tool names (agent tool_trace vocabulary). |
| `tools_must_not_use` | array | yes | May be empty `[]`. |
| `min_citation_count` | int | yes | Minimum structured citations in final output (0 allowed). |
| `typed_payload_expected` | array | yes | Hints: `inventory`, `bibliography`, `relation_trace`, `quote_candidates`, `idea_suggestions`, `citations`. |
| `trace_expectations` | object | yes | Subset of roadmap-style flags; extended in Task 7. |
| `manual_review_focus` | array | yes | Human reviewer prompts (strings). |
| `expect` | object | no | **Projection** for roadmap harness compatibility only; not authoritative for OD metadata. |

## Lane compatibility

- **`baseline`:** intended to run only against `ws-pilot-od` (small seeded workspace).
- **`rich_od`:** intended only against the restored 31-work OD UUID workspace. Do **not** set `baseline_workspace_id` (avoids implying a dual-lane mapping in rich-only specs).
- **`both`:** same scenario shape; Task 7 should pick `baseline_workspace_id` vs `workspace_id` per lane.

## Post-restore audit

Fill operational verdicts in [`docs/analysis/od-corpus-claims-methods-post-restore-closeout-2026-04-27.md`](../../../docs/analysis/od-corpus-claims-methods-post-restore-closeout-2026-04-27.md) after Task 3–4 artifacts exist under `eval/results/od-*-latest.*`.

## Validation

```bash
.venv/bin/pytest tests/eval/test_chat_agent_od_case_specs.py -q
```
