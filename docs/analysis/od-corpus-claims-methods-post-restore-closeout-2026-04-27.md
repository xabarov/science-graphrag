# OD workspace — post-restore closeout (claims, methods, scenario readiness)

**Purpose:** factual **after PR B** snapshot for the rich OD UUID workspace documented in the pre-repair audit. This document **does not** replace [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md); it **closes the loop** once operators have run Task 3–4 and verification.

**Related plan:** [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) (PR C — Task 5).

---

## 1. Source artifact registry (canonical inputs)

Use **live** outputs from the operator sequence in [`eval/README.md`](../../eval/README.md) § Rich OD PR A / PR B. Do not treat the pre-repair trust audit alone as proof of post-repair state.

| Role | Path (convention) | Produced by |
|------|-------------------|-------------|
| Frozen / live manifest | `eval/results/od-workspace-manifest-latest.json` | `scripts/chat_agent_od_workspace_manifest.py` |
| Gap classification | `eval/results/od-claims-gap-audit-latest.json` | `scripts/chat_agent_od_claims_gap_audit.py` |
| Claims backfill progress | `eval/results/od-claims-backfill-latest.jsonl` | `scripts/backfill_od_workspace_claims.py` |
| Claim vectors backfill | `eval/results/od-claim-vectors-backfill-latest.jsonl` | `scripts/backfill_od_workspace_claim_vectors.py` |
| Vectors + scenario-family gate | `eval/results/od-claim-vectors-audit-latest.json`, `.md` | `scripts/chat_agent_od_claim_vectors_audit.py` |

**Code reference for `scenario_families_*`:** [`eval/chat_agent/od_claim_vectors_audit.py`](../../eval/chat_agent/od_claim_vectors_audit.py) — heuristic only; it does **not** assert Neo4j contradiction edge completeness or per-claim pairing quality.

**Workspace under audit (same UUID as pre-repair doc):**

| Field | Value |
|--------|--------|
| `workspace_id` | `2678c5f1-1b31-4aac-92c9-6bd0f4472b23` |
| UI name (historical) | Object Detection (clean ingested + claims) |

---

## 2. Executive verdict (rich OD lane)

**Fill after Task 3–4 from `od-claim-vectors-audit-latest.json` + manifest.**

| Verdict | Meaning |
|---------|---------|
| `ready` | Claims backfill + vectors audit green for scenario families; remaining gaps documented as P2 or out-of-scope. |
| `partial` | Vectors / payload OK for most works but gap classes or methods/contradiction evidence still limit some OD scenarios. |
| `not_ready` | Material `missing_qdrant_claim_vectors`, unresolved `unknown` gap rows without opt-in, or empty `claims` collection. |

**Post-restore verdict (operator-filled):** _TBD — paste from audit summary after successful PR B run._

**One-line rationale:** _TBD._

---

## 3. Readiness dimensions (factual table)

Copy counts from **live manifest** (`work_reports`) and **vectors audit** JSON. Pre-repair baseline for comparison is in [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md) §1–2.

| Dimension | Pre-repair (trust audit) | Post-repair (fill) | Notes |
|-----------|-------------------------|--------------------|--------|
| Works in workspace | 31 | | From manifest `work_count` |
| Works with Neo4j claims | 3 | | `neo4j_claim_count > 0` |
| Works with 0 Neo4j claims | 28 | | Target ↓ after Task 3 |
| Qdrant `claims` collection | empty (0 points) | | Must be non-empty after Task 4 |
| `works_vector_ready` (neo + qdrant + payload) | 0 | | From vectors audit per-work flags |
| `works_missing_vectors_despite_neo4j_claims` | 3 | | Target 0 |
| `works_missing_workspace_scope_despite_vectors` | — | | Payload contract |
| Methods (`USES_METHOD` per work) | all 31 ≥ 1 | | Unchanged by claims-only path unless re-ingest |
| Contradiction / tension evidence | not audited as pass/fail in vectors audit | | **Separate** from claim-vector unblock; assess via graph + chunks for scenario `od_chat_08` |

---

## 4. Scenario families from vectors audit

From `od-claim-vectors-audit-latest.json`, copy:

- `scenario_families_unblocked`
- `scenario_families_still_blocked`

**Post-repair (operator-filled):**

- **Unblocked:** _TBD_
- **Still blocked:** _TBD_

**Caveat:** `claim_semantic_chat`, `quote_evidence_vector_lookup`, `contradiction_candidate_retrieval` are **retrieval-family** gates. They do **not** equal «full contradiction QA ready» for [`od_chat_08`](../../tests/fixtures/benchmarks/chat_agent_od/cases/od_chat_08_contradiction_explainer.json) without manual graph/chunk checks.

---

## 5. Scenario readiness after restore (12-case suite)

Maps to [`tests/fixtures/benchmarks/chat_agent_od/`](../../tests/fixtures/benchmarks/chat_agent_od). Mark each case **ready** / **partial** / **blocked** on the rich OD workspace after restore, with one reason string.

| `case_id` | Rich OD readiness | Blocker (if any) |
|-----------|-------------------|------------------|
| `od_chat_01_inventory` | | |
| `od_chat_02_authors` | | |
| `od_chat_03_method_profile` | | methods + chunks depth |
| `od_chat_04_quote_grounding` | | |
| `od_chat_05_relation_citation_path` | | |
| `od_chat_06_temporal_evolution` | | graph + chunks |
| `od_chat_07_method_family_compare` | | |
| `od_chat_08_contradiction_explainer` | | claims + contradiction evidence |
| `od_chat_09_gap_finder` | | corpus coverage |
| `od_chat_10_grounded_idea` | | |
| `od_chat_11_bibliography_export` | | |
| `od_chat_12_multi_turn_followup` | | session memory |

---

## 6. Remaining blockers (explicit list)

After PR B, list any:

1. **Per-work:** `work_id`, gap class from gap-audit, or vector audit `flags`.
2. **Systemic:** e.g. Postgres `ingest_checkpoint_json` still NULL (see PR B known gaps in restoration plan §12.2).
3. **Product:** UI vs Neo4j methods visibility (trust audit §6 follow-up).

**Operator-filled:** _TBD_

---

## 7. Operator / evaluator note

1. Always attach **paths + timestamps** of the `*-latest.json` / `.jsonl` files used for this closeout.
2. Re-run `chat_agent_od_claim_vectors_audit.py` after any Qdrant or Neo4j mutation affecting claims.
3. For benchmark lanes: baseline harness uses `ws-pilot-od`; rich lane uses this workspace UUID — see [`tests/fixtures/benchmarks/chat_agent_od/README.md`](../../tests/fixtures/benchmarks/chat_agent_od/README.md).

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial closeout template + artifact registry (PR C Task 5). |
