# OD workspace — post-restore closeout (claims, methods, scenario readiness)

**Purpose:** factual **after PR B** snapshot for the rich OD UUID workspace documented in the pre-repair audit. This document **does not** replace [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md); it **closes the loop** once operators have run Task 3–4 and verification.

**Related plan:** [`chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md`](./chat-agent-od-workspace-restoration-and-eval-plan-2026-04-27.md) (PR C — Task 5).

---

## 0. Evidence bundle (this capture)

Live scripts were run from repo root against Docker Neo4j/Qdrant/Postgres (`docker compose` healthy). A real **Task 3** attempt was launched with `--allow-unknown`, but it produced **no stdout progress**, created an **empty** `eval/results/od-claims-backfill-latest.log`, and had to be killed after ~157s when the Python subprocess showed `CLOSE_WAIT` on a local socket (`127.0.0.1:53186->127.0.0.1:16006`) while still holding Neo4j open. So there are still no usable `eval/results/od-claims-backfill-latest.jsonl` or `eval/results/od-claim-vectors-backfill-latest.jsonl` files; `task3_restored_work_ids` in the vectors audit remains empty.

| Artifact | Path | `generated_at` (from JSON) |
|----------|------|----------------------------|
| Workspace manifest | [`eval/results/od-workspace-manifest-latest.json`](../../eval/results/od-workspace-manifest-latest.json) | `2026-04-27T14:59:31.693279+00:00` |
| Manifest (human) | [`eval/results/od-workspace-manifest-latest.md`](../../eval/results/od-workspace-manifest-latest.md) | (same run) |
| Claims gap audit | [`eval/results/od-claims-gap-audit-latest.json`](../../eval/results/od-claims-gap-audit-latest.json) | `2026-04-27T14:59:39.356955+00:00` |
| Gap audit (human) | [`eval/results/od-claims-gap-audit-latest.md`](../../eval/results/od-claims-gap-audit-latest.md) | (same run) |
| Claim vectors audit | [`eval/results/od-claim-vectors-audit-latest.json`](../../eval/results/od-claim-vectors-audit-latest.json) | `2026-04-27T14:59:53.050870+00:00` |
| Vectors audit (human) | [`eval/results/od-claim-vectors-audit-latest.md`](../../eval/results/od-claim-vectors-audit-latest.md) | (same run) |

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

**Post-restore verdict:** `not_ready`

**One-line rationale:** Qdrant `claims` is still empty (`claims_collection_non_empty=false`); all three Neo4j claim–bearing works lack claim vectors; 28/31 works still have `neo4j_claim_count=0` with gap class `unknown` (no `ingest-progress` JSONL attached to the gap audit). A real Task 3 run was attempted in this environment but hung before first progress output, so Task 4 was not started.

---

## 3. Readiness dimensions (factual table)

Copy counts from **live manifest** (`work_reports`) and **vectors audit** JSON. Pre-repair baseline for comparison is in [`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md) §1–2.

| Dimension | Pre-repair (trust audit) | Post-repair (this capture) | Notes |
|-----------|-------------------------|----------------------------|--------|
| Works in workspace | 31 | **31** | `work_count_total` |
| Works with Neo4j claims | 3 | **3** | `works_with_neo4j_claims` |
| Works with 0 Neo4j claims | 28 | **28** | No Task 3 movement in this snapshot |
| Qdrant `claims` collection | empty (0 points) | **empty** (`claims_collection_non_empty=false`) | Task 4 not reflected |
| Sum of workspace-scoped chunk points | 1096 | **1096** | Sum of `qdrant_chunk_points_workspace_scoped` in manifest |
| `works_vector_ready` (neo + qdrant + payload) | 0 | **0** | Vectors audit |
| `works_missing_vectors_despite_neo4j_claims` | 3 | **3** | Same three claim-rich papers |
| `works_missing_workspace_scope_despite_vectors` | — | **0** | `works_missing_workspace_scope_despite_vectors` |
| Manifest `workspace_audit_status` | (not in trust doc) | **`degraded`** | Some works flagged `no_authors` / `no_outgoing_cites` per [`workspace_audit.py`](../../eval/chat_agent/workspace_audit.py) |
| Methods (`USES_METHOD` per work) | all 31 ≥ 1 | **unchanged pattern** (per-work `neo4j_method_count` in manifest) | Claims-only repair does not remove methods |
| Contradiction / tension evidence | not audited as pass/fail in vectors audit | **not audited** | **Separate** from claim-vector unblock; scenario `od_chat_08` remains **blocked** until claims + vectors + graph evidence exist |

---

## 4. Scenario families from vectors audit

From `od-claim-vectors-audit-latest.json`, copy:

- `scenario_families_unblocked`
- `scenario_families_still_blocked`

**Post-restore (this capture):**

- **Unblocked:** *(none)* — `[]`
- **Still blocked:** `claim_semantic_chat`, `quote_evidence_vector_lookup`, `contradiction_candidate_retrieval`

**Caveat:** `claim_semantic_chat`, `quote_evidence_vector_lookup`, `contradiction_candidate_retrieval` are **retrieval-family** gates. They do **not** equal «full contradiction QA ready» for [`od_chat_08`](../../tests/fixtures/benchmarks/chat_agent_od/cases/od_chat_08_contradiction_explainer.json) without manual graph/chunk checks.

---

## 5. Scenario readiness after restore (12-case suite)

Maps to [`tests/fixtures/benchmarks/chat_agent_od/`](../../tests/fixtures/benchmarks/chat_agent_od). **Rich OD lane** after this DB snapshot (chunks/graph usable; claims path not):

| `case_id` | Rich OD readiness | Blocker (if any) |
|-----------|-------------------|------------------|
| `od_chat_01_inventory` | **partial** | Manifest `workspace_audit_status=degraded` (subset of works missing authors or cites); listing still feasible |
| `od_chat_02_authors` | **partial** | Same degradation; verify per-work `author_rows` before strict gates |
| `od_chat_03_method_profile` | **partial** | Methods exist; FPN may be absent by name — spec asks for fallback; chunk quality varies |
| `od_chat_04_quote_grounding` | **partial** | Chunks present; no Qdrant claim-quote path |
| `od_chat_05_relation_citation_path` | **partial** | Graph cites exist on many works; some works `no_outgoing_cites` |
| `od_chat_06_temporal_evolution` | **partial** | Synthesis + chunks + graph; no claim-semantic retrieval |
| `od_chat_07_method_family_compare` | **partial** | Same as 06/03 |
| `od_chat_08_contradiction_explainer` | **blocked** | No Qdrant claim vectors; only 3 works with Neo4j claims; contradiction evidence not established by audit |
| `od_chat_09_gap_finder` | **partial** | Ideation grounded in corpus; not blocked on claim vectors |
| `od_chat_10_grounded_idea` | **partial** | Same |
| `od_chat_11_bibliography_export` | **partial** | Bibliography tool path; metadata may be thin — spec allows empty bib with reason |
| `od_chat_12_multi_turn_followup` | **partial** | Session + chunks; same global degradation caveats |

---

## 6. Remaining blockers (explicit list)

After PR B, list any:

1. **Per-work:** 28 works remain `claims_gap_classification=unknown` with `neo4j_claim_count=0` (gap audit). Optional: attach `eval/results/ingest-progress-*.jsonl` to gap audit to sharpen classes.
2. **Vectors:** three works with `neo4j_claim_count>0` still have `qdrant_claim_vector_count=0` and `vector_ready=false` (`missing_qdrant_claim_vectors` in per-work flags where applicable).
3. **Collection:** Qdrant `claims` collection globally empty for this workspace snapshot.
4. **Task 3 runtime blocker:** `scripts/backfill_od_workspace_claims.py --allow-unknown` was launched against the current manifest/gap-audit but hung before first work-level output; terminal capture ended after ~157s with no stdout and an empty `eval/results/od-claims-backfill-latest.log`. Inspection showed the Python subprocess in `CLOSE_WAIT` on a local socket while still connected to Neo4j. Until that hang is root-caused, Task 4 should not be treated as runnable for the remaining 28 works.
5. **Operator outputs missing:** `od-claims-backfill-latest.jsonl` and `od-claim-vectors-backfill-latest.jsonl` were not written under `eval/results/` in this capture — if Task 3–4 were run elsewhere, copy or symlink to `*-latest.*` and re-run [`scripts/chat_agent_od_claim_vectors_audit.py`](../../scripts/chat_agent_od_claim_vectors_audit.py).
6. **Systemic:** Postgres `ingest_checkpoint_json` still null on sampled documents (manifest); see restoration plan §12.2 known gaps.
7. **Product:** UI vs Neo4j methods visibility (trust audit §6 follow-up) — orthogonal to numbers above.

---

## 7. Operator / evaluator note

1. This revision used **paths** in §0; re-run scripts after any DB mutation and update `generated_at` rows.
2. Re-run `chat_agent_od_claim_vectors_audit.py` after any Qdrant or Neo4j mutation affecting claims.
3. For benchmark lanes: baseline harness uses `ws-pilot-od`; rich lane uses this workspace UUID — see [`tests/fixtures/benchmarks/chat_agent_od/README.md`](../../tests/fixtures/benchmarks/chat_agent_od/README.md).

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial closeout template + artifact registry (PR C Task 5). |
| 2026-04-27 | Filled §0–§6 from live `eval/results/od-*-latest.*` (manifest + gap + vectors audit); noted Task 3/4 JSONL absent. |
| 2026-04-27 | Updated §0/§2/§6 after a real Task 3 attempt hung before first progress output (`CLOSE_WAIT`, no JSONL emitted). |
