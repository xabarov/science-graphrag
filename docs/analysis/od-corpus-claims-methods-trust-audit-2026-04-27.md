# OD workspace audit — claims, methods, stores, trust (2026-04-27)

**Scope:** live DB snapshot on developer machine (docker `neo4j` / `postgres` / `qdrant` healthy). Workspace under investigation matches UI name **«Object Detection (clean ingested + claims)»**.

---

## 0. Workspace identification (plan §0)

| Field | Value |
|--------|--------|
| `workspace_id` | `2678c5f1-1b31-4aac-92c9-6bd0f4472b23` |
| `name` | Object Detection (clean ingested + claims) |
| `unbounded` | `false` |
| `(:Workspace)-[:CONTAINS]->(:Work)` | **31** works |

**Conclusion:** This is a **materialized** membership workspace (not `ws_full_corpus` unbounded). Empty claims on the graph are **not** explained by the «unbounded + no CONTAINS» API limitation from [`claims_projection.py`](../../science_graphrag/api/workspace_graph/claims_projection.py). The graph API can attach claims for any work that has `Claim→Evidence→Work` in Neo4j when `include_claims=true` and `Claim` is included in node types.

**Benchmark seed scripts (reference):** [`scripts/seed_benchmark_workspaces.py`](../../scripts/seed_benchmark_workspaces.py) + [`tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json`](../../tests/fixtures/benchmarks/retrieval/workspace_scoped_live/_workspaces.json). This UI workspace is a **user-scoped UUID workspace**, not one of the fixed `ws_*` ids from the fixture file.

---

## 1. Neo4j inventory (plan §1)

Per-work aggregation (same pattern as graph claims slice):

- **Claims:** `MATCH (c:Claim)-[:SUPPORTED_BY]->(:Evidence)-[:ANCHORED_IN]->(w)`
- **Methods:** `MATCH (w)-[:USES_METHOD]->(:Method)`
- **Citations out:** `MATCH (w)-[:CITES]->(:Work)`

### 1.1 Workspace-level totals

| Metric | Count |
|--------|------:|
| Works in workspace | 31 |
| Works with **0** claims | **28** |
| Works with **>0** claims | **3** |
| Distinct `Claim` nodes linked to these works | **147** (all on the 3 papers) |
| Works with **0** outgoing `CITES` | **2** (Histograms of Oriented Gradients…; Bridging the Gap…) |
| `HAS_AUTHorship` edges (row count before DISTINCT) | **0** works with zero authorship edges |

### 1.2 The three papers that carry all Neo4j claims

| Title (truncated) | `claim_n` (per-work) |
|-------------------|---------------------:|
| Cascade R-CNN: Delving into High Quality Object Detection | 29 |
| Bridging the Gap Between Anchor-based and Anchor-free Detection | 47 |
| CenterNet: Keypoint Triplets for Object Detection | 71 |

All other 28 works in the workspace have **no** `Claim`/`Evidence` chain in Neo4j under the canonical schema.

### 1.3 Methods

| `USES_METHOD` count (per work) | # works |
|-------------------------------|---------:|
| 1 | 17 |
| 3 | 3 |
| 4 | 10 |
| 6 | 1 |

**Every** of the 31 works has at least one `Method` edge. If the UI «does not show methods» for some papers, candidate causes are **UI/projection** (node-type filter, neighbor cap, mode `inner_only` vs semantic layer, aggregator) rather than **total absence** of `USES_METHOD` in Neo4j for this workspace.

---

## 2. Postgres + Qdrant (plan §2)

### 2.1 Postgres `documents`

- Rows joined by `work_id` in the 31-id set: **32** rows (one `work_id` appears twice — two documents).
- **`ingest_checkpoint_json`:** **all** sampled rows are `NULL` across the whole `documents` table in this environment (**58** documents, **0** non-null checkpoints).

So **stage-level audit** (`extract_claims`, `embed`, etc.) from SQL **is not available** on this DB snapshot. That is an environment/data-shape limitation, not proof that checkpoints are never written in production.

### 2.2 Postgres `ingest_jobs`

- `ingest_jobs` for `workspace_id = 2678c5f1-…`: **no rows**.

Ingest for this workspace may have run through another entrypoint or jobs were pruned; this does not contradict Neo4j/Qdrant evidence below.

### 2.3 Qdrant `chunks`

- Sum of `count_chunks_for_work` over the 31 `work_id`s: **1096** points.
- **`count_chunks_for_workspace_work(workspace_id, work_id)`** vs total: **0** works had chunks globally but missing `workspace_id` in payload for this workspace (all scoped counts matched where chunks exist).

So retrieval/graph-adjacent chunk indexing for **this** workspace is **healthy** for workspace-scoped filters.

### 2.4 Qdrant `claims` collection

- **Collection point count (exact): 0** (entire collection empty).
- Per-sample `work_id` filters (including the three claim-rich Neo4j papers): **0** points each.

**Conclusion:** Neo4j holds 147 claim nodes for three works, but **no** claim vectors are stored in Qdrant on this snapshot. Any feature that relies on **vector search over the `claims` collection** will see an empty corpus regardless of Neo4j.

---

## 3. Hypothesis split (plan §3)

| Observation | Primary explanation (this DB) |
|-------------|--------------------------------|
| «No claims» for most papers | **Data gap:** 28/31 works have no `Claim`/`Evidence` subgraph in Neo4j. Not workspace shape (workspace is bounded + CONTAINS). |
| «No claims» at all in UI | If UI were on `ws_full_corpus` with `unbounded=true` and no CONTAINS, **API** would return empty graph; **not** the case here. Check `include_claims` + `Claim` in visible types. |
| Qdrant claims empty | **Pipeline / ops gap:** claims never embedded or collection wiped after graph write. |
| «Missing methods» in UI | **Unlikely** to be pure Neo4j absence (all 31 have `USES_METHOD`). Prefer **UI limits / filters / graph mode**. |
| Sparse citation graph (islands) | **Data / resolver gap:** only 2 works have zero outgoing `CITES`; others have citations — disconnected components still possible if targets are **outside** the 31-work set or edges not reciprocal. |

---

## 4. Benchmark trust mapping (plan §4)

Cross-reference: [`ontology-benchmarks-trust-audit-2026-04-25.md`](./ontology-benchmarks-trust-audit-2026-04-25.md), [`chat-agent-system-roadmap-2026-04-26.md`](./chat-agent-system-roadmap-2026-04-26.md).

| Area | Impact of this audit |
|------|----------------------|
| **Core nightly** (layer1/layer2/graph fixtures, e.g. yolov1) | **Low.** Those metrics are driven by committed fixtures, not this UUID workspace. |
| **BT2 `workspace_scoped_live`** | **Medium for interpretation:** This workspace has good **chunk + workspace_id** coverage; BT2 failures tied to `ws_full_corpus` / missing payloads are a **different** configuration. Missing claims do **not** invalidate BT2 hit-count logic unless cases explicitly require claim retrieval from Qdrant. |
| **BT4 hybrid / BT5 judge** | **Medium:** Depend on chunk corpus size and content; 31 papers + 1096 chunks is substantial; hybrid delta still corpus-dependent per trust doc. |
| **BT6 claims paraphrase** | **Orthogonal at oracle:** Green **synthetic_gold** runs do not assert Neo4j/Qdrant claim completeness for OD. **Production** BT6 + product «claims ready» narrative **are** weakened if Qdrant `claims` is empty and 28/31 works lack Neo4j claims. |
| **`decision_gate` JSONs** | **No mandatory re-run** solely from this workspace audit; **do** annotate product evaluations: «UI OD workspace ≠ benchmark `ws_*` seed unless explicitly aligned.» |

---

## 5. Agent tests & use cases (plan §5)

| Use-case class (roadmap §2.3) | Needs chunks | Needs Neo4j graph (cites, methods) | Needs Neo4j claims | Needs Qdrant `claims` |
|------------------------------|:--------------:|:------------------------------------:|:------------------:|:---------------------:|
| Inventory / catalog | helpful | optional | optional | no |
| Fact lookup | optional | yes for authoritative graph fields | no | no |
| Grounded explanation | **yes** | helpful | optional | optional |
| Relation tracing | optional | **yes** (`CITES`, paths) | no | no |
| Quote extraction | **yes** | optional | no | no |
| Synthesis / comparison | **yes** | yes | helpful | helpful |
| Contradictions / evidence-heavy | **yes** | yes | **yes** | helpful for semantic claim search |

**Recommendations for live / API tests:**

1. Tag scenarios with `requires_neo4j_claims`, `requires_qdrant_claim_vectors`, `requires_methods_visible` (or assert on Neo4j counts via admin path), so green runs are not **vacuous** when the graph omits claims.
2. Keep a **small golden workspace** (few papers, known non-zero claims + vectors + methods) for regression separate from the large OD UUID workspace.
3. For «Object Detection (clean ingested + claims)» specifically: either **backfill claims** for the 28 works or **rename** the workspace to avoid implying claims completeness.

---

## 6. Prioritized follow-ups (plan §6)

1. **P0 — Claims extraction completeness:** Determine why 28 works have no `Claim` subgraph (ingest logs, LLM extractor skip, failure before write, or batch import without claims stage). Re-run claims stage or full re-ingest for affected `document_id` / `work_id` pairs.
2. **P0 — Qdrant claims:** If product expects claim semantic search, run embed/upsert path so `claims` collection is non-empty for works that have Neo4j claims; investigate why collection is totally empty (cutover script, never run, or wipe).
3. **P1 — UI methods:** Reproduce on one `work_id` with known `USES_METHOD` count; verify `node_types`, `neighbor_limit`, and graph mode; compare with [`GET /v1/workspaces/.../graph`](../../science_graphrag/api/workspace_graph/router.py) response payload.
4. **P2 — Postgres checkpoints:** If checkpoints should be populated, fix persistence path so `ingest_checkpoint_json` is usable for future audits (optional for this read-only audit).

---

## Appendix — reproducible queries

**Neo4j — list workspaces (recent):**

```cypher
MATCH (ws:Workspace)
OPTIONAL MATCH (ws)-[:CONTAINS]->(w:Work)
WITH ws, collect(DISTINCT w.id) AS wids, count(DISTINCT w) AS n
RETURN ws.id, ws.name, coalesce(ws.unbounded,false) AS unbounded, n AS contains_n
ORDER BY ws.created_at DESC LIMIT 20;
```

**Neo4j — per-work claims/methods/cites for a workspace:**

```cypher
MATCH (ws:Workspace {id: $ws})-[:CONTAINS]->(w:Work)
OPTIONAL MATCH (w)-[:HAS_AUTHORSHIP]->(:Authorship)
WITH w, count(*) AS authorship_rows
OPTIONAL MATCH (w)-[:USES_METHOD]->(m:Method)
WITH w, authorship_rows, count(DISTINCT m) AS method_n
OPTIONAL MATCH (c:Claim)-[:SUPPORTED_BY]->(:Evidence)-[:ANCHORED_IN]->(w)
WITH w, authorship_rows, method_n, count(DISTINCT c) AS claim_n
OPTIONAL MATCH (w)-[:CITES]->(x:Work)
RETURN w.id, w.title, authorship_rows, method_n, claim_n, count(DISTINCT x) AS cites_out;
```

**Postgres — documents for a set of work ids:**

```sql
SELECT work_id, id, left(source_path, 120),
       ingest_checkpoint_json IS NOT NULL AS has_ck
FROM documents
WHERE work_id = ANY(:wids::text[]);
```

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial audit from live Neo4j/Postgres/Qdrant (see sections 0–2). |
