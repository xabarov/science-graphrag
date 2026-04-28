# Work graph vs reader authorship: contract mismatch and remediation plan

**Date:** 2026-04-28  
**Scope:** `GET /v1/works/{work_id}/graph` (standalone work neighborhood), `collapse_authorship_for_reader_view`, UI entrypoints (`/graph?work_id=…`), parity with workspace graph semantics for **authors** and related reader fields.  
**Out of scope:** Neo4j ingestion correctness (verified separately: `Work → Authorship → OF_AUTHOR → Author` is populated when extraction succeeds).

**Implementation status:** **Phase 0 — Done** (2026-04-28): contract tests + `xfail(strict=True)` (since removed). **Phase 1 — Done** (2026-04-28): Option B in production; reader work graph no longer drops authorship when the payload has `HAS_AUTHORSHIP` only. **Phase 3 — Done** (2026-04-28): parity matrix + `include_authorship_debug` / `meta.authorship_projection` + HTTP expand smoke. Details and file pointers: §7.

---

## 1. Executive summary

> **Resolved (Phase 1):** standalone work graph `view=reader` again surfaces authors via `AUTHORED` + `Author` (real ids from `enrich_authorship_nodes.properties.author_entity_id` when Neo4j has `OF_AUTHOR`, else stable `va:…` surrogates). Historical failure mode below is kept for **root-cause context**.

Standalone **work graph** responses under `view=reader` **used to drop** all author-visible structure even when Neo4j contains full authorship. **Before Phase 1,** **`collapse_authorship_for_reader_view`** only built virtual `Work —[AUTHORED]→ Author` edges when **`OF_AUTHOR` edges were present** in the same payload, while the work-neighborhood builder **`_append_neighbor_edge` / `_work_neighbors_rows`** still never emits **`OF_AUTHOR`** in JSON (only `HAS_AUTHORSHIP` from `Work` to `Authorship`). The function then removed `Authorship` nodes without replacing them, so the UI showed **methods (and other neighbors) but no authors**.

**Workspace graph** path remains richer: incident `Authorship` nodes are included, and the UI’s **`projectAuthorSemanticGraph`** compensates when explicit `Author` / `OF_AUTHOR` are absent from the normalized payload.

**Recommendation:** treat this as a **single contract** problem: either (A) **extend the work-graph payload** to include `OF_AUTHOR` + `Author` nodes for included authorships (matches collapse’s assumptions), or (B) **harden `collapse_authorship_for_reader_view`** with a fallback that uses enriched `Authorship` properties (after `enrich_authorship_nodes`)—mirroring the UI fallback—so reader collapse never strips authorship without emitting `AUTHORED` edges. Prefer **(B) as minimal fix**, **(A) if** raw API consumers need explicit `Author` nodes without relying on UI projection.

---

## 2. Symptoms and user impact

| Symptom | Where |
|--------|--------|
| Graph shows center `Work` + semantic neighbors (e.g. `Method`) but **no author nodes** | `/graph?work_id=<uuid>` (no `workspace_id`), default `view=reader` |
| Extracted text / metadata show authors; Neo4j has `Author` nodes | Reader / document views vs graph |
| **Workspace** graph for the same work shows authorship-related structure | `/graph?workspace_id=…` (full workspace projection + client author projection) |

**Product expectation:** “Same meaning as workspace graph, scoped to one paper”—authors and other reader-relevant fields must remain **first-class** in the standalone work graph, subject only to **neighbor limits and prioritization**, not to a different logical model.

---

## 3. Current architecture (two surfaces)

### 3.1 Standalone work graph

**Entry:** `GET /v1/works/{work_id}/graph` — `science_graphrag/api/works/router.py` → `work_graph_neighborhood` → `_work_graph_neighborhood_payload` in `science_graphrag/api/works/graph_neighborhood.py`.

**Flow (simplified; order is contractual):**

1. Load center `Work` and **1-hop** rows: `MATCH (w:Work {id})-[r]-(n)` with optional `OPTIONAL MATCH (n)-[:OF_AUTHOR]->(auth:Author)` **only to enrich row fields** (`n_ash_author`), not to add `Author` nodes or `OF_AUTHOR` edges to the response.
2. Append nodes/edges via `_append_neighbor_edge` → edge type is `rec["rt"]` (e.g. `HAS_AUTHORSHIP` for `Authorship` neighbors).
3. Merge optional **claims** slice; `enrich_authorship_nodes(session, nodes)` — **Phase 1:** also writes `properties.author_entity_id` when `(Authorship)-[:OF_AUTHOR]->(Author)` exists in Neo4j (still no `OF_AUTHOR` *edges* in the JSON payload).
4. If `view=raw`: strip `author_entity_id` from `Authorship.properties` (`_strip_reader_only_authorship_properties`) so raw stays topology-oriented; **no** collapse.
5. If `view=reader`: **`collapse_authorship_for_reader_view`** — resolves each `HAS_AUTHORSHIP` to an `Author` target: native `OF_AUTHOR` edges in payload if present; else `author_entity_id`; else stable `va:…` + injected `Author` node with `distance: 1`.
6. `_enrich_edges_with_display(center_id, nodes, edges)`.
7. **~~If not raw: `_apply_aggregators`~~** — removed from the production pipeline (2026-04-28). **`meta.neighbor_aggregation`** is **`none`**; see [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md).

**Historical bug payload (pre–Phase 1, e.g. work with 7 authors):** edge types include `HAS_AUTHORSHIP`; **`OF_AUTHOR` count = 0** in `edges`. Old `collapse_authorship_for_reader_view` had **empty `author_by_ash`**, created **no** virtual `AUTHORED` edges, and **removed** all `Authorship` nodes from `nodes`.

### 3.2 Workspace graph + UI

**Entry:** `GET /v1/workspaces/{id}/graph` — `project_workspace_graph` uses depth-1 rows from internal `Work` endpoints; `Authorship` appears as a **one-hop** neighbor. Client **`projectAuthorSemanticGraph`** (`ui/src/components/graph/authorSemanticProjection.js`) synthesizes reader-facing `Author` / `AUTHORED` when `OF_AUTHOR` is missing from the normalized graph.

**UI routing:** `GraphPage` deliberately does **not** infer `workspace_id` from shell context when `work_id` is present, so links like `workGraphUrl(workId, null)` load **work graph only** (`ui/src/pages/GraphPage.jsx`, `ui/src/pages/WorkspacePage/WorkspacePaperRow.jsx`).

---

## 4. Root cause (technical)

> **After Phase 1:** collapse no longer depends solely on `OF_AUTHOR` *edges* in the payload; it also consumes `author_entity_id` from `enrich_authorship_nodes` and synthetic `va:…` ids. The table below documents the **original** contract gap.

| Component | Assumption | Reality in work graph |
|-----------|------------|------------------------|
| `collapse_authorship_for_reader_view` | `author_by_ash` populated from edges with `type == OF_AUTHOR` and `src` in `authorship_ids` | No `OF_AUTHOR` edges in `edges` |
| Same function | After collapse, `AUTHORED` edges connect `Work` to `Author` | `Author` nodes were never added by neighbor expansion (second hop from `Work`) |
| Neighbor query | Optional author name on row | Used for **display** on `Authorship`, not for graph topology in the payload |

**Conclusion:** This is not a data-layer bug; it is a **response-shape / pipeline contract** bug between neighbor materialization and reader normalization.

---

## 5. Why this is an architectural issue

> **After Phase 1:** work-graph reader collapse is closer to the UI fallback (enriched authorship → `Author` / `AUTHORED`), but workspace still uses **`projectAuthorSemanticGraph`** in addition; long-term, keep behavior and naming (`via`, synthetic metadata) aligned to avoid drift.

- **Dual normalization paths:** server-side collapse (work graph) vs client `projectAuthorSemanticGraph` (workspace graph) encode similar intent with **different preconditions**.
- **Implicit contract:** `collapse_authorship_for_reader_view` documents “drop Authorship; add virtual AUTHORED” but **does not guarantee** its inputs; the neighbor layer does not advertise that contract.
- **User-visible inconsistency:** same `work_id` appears complete in workspace context and **incomplete** on standalone graph—violates the product rule “workspace semantics, scoped to one paper.”

---

## 6. Remediation options

### Option A — Materialize `OF_AUTHOR` + `Author` in work-graph build

**Idea:** When adding an `Authorship` neighbor, also append the linked `Author` node (from optional match or a follow-up query) and an `OF_AUTHOR` edge (`Authorship → Author` or direction consistent with Neo4j and collapse logic).

| Pros | Cons |
|------|------|
| Matches current collapse logic verbatim | More nodes/edges toward `neighbor_limit`; must align with caps and aggregators |
| Better for **raw** API consumers | Slightly larger payloads |

### Option B — Fallback inside `collapse_authorship_for_reader_view` (recommended first slice)

**Idea:** If `OF_AUTHOR` is missing but `Authorship` nodes exist and `enrich_authorship_nodes` has filled **author identity** (e.g. `full_name` / display fields in `properties` or node fields used by `compute_node_display`), synthesize:

- a stable **virtual `Author` id** (e.g. deterministic hash from `work_id + authorship_id` or reuse authorship id with explicit `synthesized_from` metadata—align with UI conventions if possible), and  
- virtual **`AUTHORED`** edges from `Work` to that author surrogate,

then remove `Authorship` as today.

| Pros | Cons |
|------|------|
| **Minimal** change; fixes reader path without duplicating Neo4j hop in all clients | Virtual ids must not collide with real `Author` ids; document semantics |
| Aligns behaviorally with **UI** fallback | Raw view users might still want explicit `Author` (optional follow-up) |

**Status:** Option B is **implemented** (Phase 1, 2026-04-28); see §7 Phase 1 for symbols (`via`, `va:…`, `author_entity_id`) and pipeline notes.

### Option C — Defer reader collapse to the client for work graph

**Idea:** Return the same shape as `view=raw` for authorship cluster and let `projectAuthorSemanticGraph` always run.

| Pros | Cons |
|------|------|
| Single place for “author semantics” | Changes API contract for existing `view=reader` clients; larger frontend responsibility |

**Suggested order:** implement **Option B** + tests → optionally **Option A** for raw/parity → reject **Option C** unless product explicitly wants API simplification.

---

## 7. Work plan (phased)

### Phase 0 — Lock the bug with tests (1–2 sessions) — **DONE**

- [x] **Backend unit/integration tests** — Implemented (no production code in this phase):
  - **Unit:** [`tests/test_works_graph_authorship_reader_collapse.py`](../../tests/test_works_graph_authorship_reader_collapse.py) — `_FakeSession` reproduces `_work_graph_neighborhood_payload` branches including `enrich_authorship_nodes` (`UNWIND $ids`). Reader tests originally used `xfail(strict=True)`; **Phase 1 removed `xfail`** — all four tests in that file are green (three reader + one raw).
  - **Integration:** [`tests/test_works_graph_authorship_integration.py`](../../tests/test_works_graph_authorship_integration.py) — `@pytest.mark.integration`, Neo4j skip when unavailable; seed with `HAS_AUTHORSHIP`/`OF_AUTHOR` in DB but work-graph payload still without `OF_AUTHOR` edges. Reader/parity tests were `xfail` until Phase 1; **now green** when Neo4j is up. Raw test additionally asserts **`author_entity_id` is absent** on `Authorship` in raw responses (Phase 1 hygiene).
  - **Sanity gate:** `tests/test_works_graph_priority_limit.py`, `tests/test_works_graph_display.py` — re-run after changes; keep green.
- [x] **Regression: raw view** — No synthetic `AUTHORED` in raw; `Authorship` + `HAS_AUTHORSHIP` preserved.

### Phase 1 — Fix reader collapse contract (core) — **DONE** (2026-04-28)

- [x] **Option B** — [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py): helpers `_reader_view_authored_target`, `_reader_synthetic_author_entity_id` (`va:` + SHA-256), `_author_label_from_authorship_node` (strip trailing `(#N)` like UI intent), `_authorship_props_for_authored_edge`; bidirectional parse of `HAS_AUTHORSHIP` / `OF_AUTHOR`; inject missing `Author` nodes with `distance: 1`; `via` is `["HAS_AUTHORSHIP","OF_AUTHOR"]` or `["HAS_AUTHORSHIP","enriched_authorship"]`. Collapse unit coverage: [`tests/api/test_collapse_authorship_reader_view.py`](../../tests/api/test_collapse_authorship_reader_view.py).
- [x] **Pipeline order** — `enrich_authorship_nodes` → (raw strip if `view=raw`) → `collapse_authorship_for_reader_view` (reader only) → `_enrich_edges_with_display`. **`_apply_aggregators` is not called** (aggregation disabled 2026-04-28).
- [x] **`enrich_authorship_nodes`** — [`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py): Cypher returns `author_entity_id` (`coalesce(au.id,'')`); merged into `Authorship.properties` for collapse; documented in function docstring.
- [x] **Manual / product check:** procedure captured in [`docs/runbooks/work-graph-authorship-qa.md`](../runbooks/work-graph-authorship-qa.md) — work with **many** citations + **≥7** authors, `neighbor_limit=200`, `include_claims=true` — expect authors visible as **concrete nodes** within the neighbor cap (no server-side **Aggregator** since 2026-04-28).

**Note:** `xfail` markers were removed in the same change set as the collapse fix (avoids `strict=True` XPASS failures).

### Phase 2 — Parity and API clarity (optional but valuable)

- [x] **Docs:** [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md) + cross-links from [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md) and [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) §4.
- [x] **Option A:** emit real `OF_AUTHOR` + `Author` in work graph neighbor expansion when Neo4j has `(Authorship)-[:OF_AUTHOR]->(Author)` (both views); see architecture note.
- [x] **Expand-aggregator (legacy):** `expand_work_aggregator` remains for API compatibility; main graph no longer emits `Aggregator` nodes (aggregation disabled 2026-04-28).
- [x] **Product link (revised 2026-04-28):** passing **`workspace_id` together with `work_id`** on `/graph` makes [`useGraphWorkspaceData`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) call **`getWorkspaceGraph`** (full workspace union) — there is **no** server-side “ego subgraph for one work inside workspace” today, so the paper-row graph icon would show the **entire workspace**, not a paper-scoped neighborhood. **Current behavior:** [`WorkspacePaperRow.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperRow.jsx) uses **`workGraphUrl(workId, null)`** so `/graph?work_id=…` loads **`GET /v1/works/{id}/graph`** (work neighborhood; authors fixed in Phase 1). Full workspace graph remains available from the workspace shell (e.g. [`WorkspaceContextStrip`](../../ui/src/pages/WorkspacePage/WorkspaceContextStrip.jsx) `workGraphUrl("", workspaceId)`). *Future optional backlog:* true “workspace + focus work” would need either a focused API slice or client-side filtering — do not re-enable `workspace_id` on the paper graph link until that exists.*
- [x] **HTTP expand smoke** (Phase 2 tail, closed with Phase 3): [`tests/api/test_work_graph_expand_http.py`](../../tests/api/test_work_graph_expand_http.py).

### Phase 3 — Hardening — **DONE** (2026-04-28)

- [x] **Contract test matrix** — [`tests/test_works_graph_authorship_integration.py`](../../tests/test_works_graph_authorship_integration.py): workspace 1-hop slice vs reader work graph (non-truncated parity), no-`OF_AUTHOR` / `va:` parity, truncation invariant on center `authors_count`, five-author aggregator + `expand_work_aggregator` round-trip. Comparison rules: [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md) § «Parity tests»; helpers: [`tests/fixtures/work_graph_workspace_authorship_parity.py`](../../tests/fixtures/work_graph_workspace_authorship_parity.py).
- [x] **Observability** — `GET /v1/works/{work_id}/graph?include_authorship_debug=true` → `meta.authorship_projection` ∈ {`native`,`synthesized`,`mixed`,`none`} (post-collapse, pre-aggregator). Implementation: [`science_graphrag/api/graph_reader_projection/authorship_meta.py`](../../science_graphrag/api/graph_reader_projection/authorship_meta.py) (`compute_authorship_projection_meta`), called from [`graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py); router query param in [`science_graphrag/api/works/router.py`](../../science_graphrag/api/works/router.py).
- [x] **Phase 2 tail (HTTP expand)** — smoke: [`tests/api/test_work_graph_expand_http.py`](../../tests/api/test_work_graph_expand_http.py).

---

## 8. Acceptance criteria

*(Items 1–3 are met by Phase 1 implementation + tests in §7; item 4 remains a documentation backlog choice.)*

1. For any `Work` with `HAS_AUTHORSHIP → Authorship` in Neo4j, **`GET /v1/works/{id}/graph?view=reader`** includes reader-visible authorship: **either** explicit `Author` nodes connected by `AUTHORED` **or** documented virtual author nodes with the same UX contract as workspace graph (checkbox “Author”, legend, etc.).
2. **No regression:** `authors_count` on center `Work` properties remains correct; aggregators for dense kinds unchanged except where explicitly reviewed.
3. **Automated tests** — Multi-author unit fake + Neo4j integration + raw regression; **Phase 1:** all former `xfail` reader/parity tests pass without markers (see §7).
4. **Documentation:** [x] Linked from [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) §4 and [`docs/specs/graph-ui-plan.md`](../specs/graph-ui-plan.md); canonical maintainer summary in [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md).

---

## 9. Key file references

| Area | Path |
|------|------|
| Work graph payload | `science_graphrag/api/works/graph_neighborhood.py` (`_work_graph_neighbors_rows`, `_append_neighbor_edge`, `_work_graph_neighborhood_payload`; calls projection package for collapse / strip / meta) |
| Reader authorship collapse + strip + projection meta | `science_graphrag/api/graph_reader_projection/` (`authorship_collapse`, `authorship_meta`, `stable_edge_id`) |
| Authorship enrich (Phase 1) | `science_graphrag/api/graph_display.py` (`enrich_authorship_nodes`, `compute_node_display`); **call sites** `graph_reader_projection.authorship_enrich` + `graph_neighborhood` |
| HTTP surface | `science_graphrag/api/works/router.py` (`get_work_graph`) |
| Workspace projection | `science_graphrag/api/workspace_graph/cypher.py`, `_cypher_projection.py` |
| Client author projection | `ui/src/components/graph/authorSemanticProjection.js` |
| Graph routing | `ui/src/pages/GraphPage.jsx`, `ui/src/pages/WorkspacePage/workspacePageUrls.js`, `WorkspacePaperRow.jsx` |

---

## 10. Open questions

- Should virtual author ids be **stable across requests** (hash-based) so deep links / selection survive refresh? *(Phase 1: yes for `va:…` — hash of `center_work_id`, `authorship_id`, and a fixed salt; stable across requests for the same work + authorship row.)*
- Should **expand-aggregator** for authorship on work graph reuse the same projection rules after the fix?
- Do we want **explicit** `OF_AUTHOR` in `view=raw` for external API users in addition to reader synthesis?

---

## 11. References (internal)

- Prior investigation (Neo4j verification, payload shapes): discussion 2026-04-28 — work id `4c381718-6fc0-48fb-b2c8-8ad550d5c765`, workspace `2678c5f1-1b31-4aac-92c9-6bd0f4472b23` (example; IDs are environment-specific).
