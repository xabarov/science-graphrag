# Work graph vs workspace graph: architectural closure, parity, and DRY remediation plan

**Date:** 2026-04-28  
**Related:** [`work-graph-authorship-reader-contract-2026-04-28.md`](./work-graph-authorship-reader-contract-2026-04-28.md) (authorship reader contract — **Phases 0–3 done**), ADR-011 / ADR-012 (workspace vs work semantics), [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md).

**Scope:** End-to-end alignment of **semantic contracts** between `GET /v1/works/{work_id}/graph` and workspace graph APIs, **elimination of duplicated reader semantics** (server + UI), and **explicit product behavior** for membership, external citations, and multi-hop reader entities (institution, venue when data exists).

**Non-goals (this plan):** Ingest correctness for missing venue/year (see backlog `paper_profile year/venue`); full multihop graph product beyond documented 1-hop + expand.

---

## 1. Executive summary

We closed the **authorship** contract gap (reader work graph + `collapse_authorship_for_reader_view` + enrich + tests). Remaining pain is **structural**: two graph builders (`work` neighborhood vs `workspace` projection) implement overlapping **reader-facing** rules with different caps, different optional fields (`workspace_membership`, institution reachability), and a **client-side** `projectAuthorSemanticGraph` that partially mirrors server collapse. That violates **DRY** and keeps **“same paper, different graph”** surprises (e.g. external `CITES` neighbors without membership flags in standalone work graph; institution only visible when the hop is included in the chosen API slice).

**North star:** One **documented** product model with either (a) **one implementation seam** for “reader graph slice from Neo4j” reused by work and workspace paths, or (b) **two deliberately different modes** with **distinct UI labels and API names**, not two silent variants of “the graph.”

This document phases **contract clarification**, **shared projection module (DRY)**, **optional work-graph enrichment when workspace context is known**, **2-hop reader policy** (institution / venue), and **verification** (parity tests + UI migration checklist).

---

## 2. Problem inventory (current technical debt)

| Theme | Symptom | Risk |
|--------|---------|------|
| **Dual builders** | Work graph applies `neighbor_limit` / prioritization / aggregators; workspace inner graph is full 1-hop union (ADR-011). | Users and agents infer “same meaning,” hit truncation or missing nodes without knowing which mode they are in. |
| **Membership / “external”** | Standalone work graph neighbors may lack `workspace_membership` when the UI filter expects it (workspace-scoped notion on a non-workspace response). | “External works” filter appears broken on `/graph?work_id=…` even when data exists in Neo4j. |
| **DRY — authorship** | Server: `enrich_authorship_nodes` + `collapse_authorship_for_reader_view`. Client: `authorSemanticProjection.js` for workspace payloads. | Future contract changes require double edits; subtle divergence (already happened once). |
| **DRY — display / edges** | `_enrich_edges_with_display`, workspace edge helpers, and graph UI normalization may repeat label/display-type rules. | Inconsistent edge chips and legend across surfaces. |
| **2-hop reader entities** | Institution attached via `Authorship` may sit outside the strict 1-hop work neighborhood unless explicitly fetched. | “Authors + affiliations” product expectations not met on work graph. |
| **Venue** | Missing in graph when ingestion/OpenAlex merge did not populate (orthogonal data gap). | Confused with “graph bug”; needs clear empty-state + backlog link. |
| **Product link** | Opening full workspace graph from a paper row over-emphasized union semantics; reverted to `workGraphUrl(workId, null)` (see authorship doc §7). | Correct short-term; long-term still need a **named** entry to “workspace graph” vs “paper neighborhood.” |

---

## 3. Design principles (acceptance anchors)

1. **Explicit modes:** Any response that applies caps or different hop rules must declare them in **`meta`** (already partially done: `is_truncated`, `neighbor_limit`, `prioritize`). Extend with **`graph_mode`** or equivalent enum: `work_capped` | `workspace_union` | `work_workspace_context` (name TBD) so clients do not guess. **Phase 0 (done):** `meta.graph_mode` + `meta.graph_contract_version` via [`science_graphrag/api/graph_reader_meta.py`](../../science_graphrag/api/graph_reader_meta.py) (`work_capped`, `workspace_union`, `workspace_v2`, `workspace_neighbors`, expand-only modes). **`work_workspace_context`:** **Phase 2 done (2026-04-28)** when work graph is requested with validated optional `workspace_id`.

2. **Single source of truth for reader authorship shape:** After refactor, **either** the server always emits reader-safe authorship for both surfaces **or** the UI projection is deleted in favor of server normalization — not both with overlapping logic.

3. **DRY boundary:** **`science_graphrag/api/graph_reader_projection/`** (Phase 1, 2026-04-28) owns:
   - pure functions: collapse / virtual author ids / `via` metadata (moved from ad-hoc `graph_neighborhood` + `graph_display` chunks);
   - optional **“annotate membership”** pass when `(work_id, workspace_id)` is known;
   - shared helpers consumed by **`graph_neighborhood`** and **`workspace_graph`** orchestrators (they keep Cypher assembly; projection owns JSON-level reader rules).

4. **Parity tests follow contracts:** Keep [`tests/fixtures/work_graph_workspace_authorship_parity.py`](../../tests/fixtures/work_graph_workspace_authorship_parity.py) style tests; add **membership** and **institution** fixtures when those fields become part of the declared contract.

5. **No silent breaking API:** Prefer **new query flag** or **minor version** for behavior that changes neighbor sets; document in [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md).

---

## 4. Current architecture snapshot (for implementers)

| Concern | Primary modules |
|----------|------------------|
| Work neighborhood + aggregators | `science_graphrag/api/works/graph_neighborhood.py` |
| Reader authorship collapse / meta / enrich seam | `science_graphrag/api/graph_reader_projection/` |
| Authorship batch enrich (implementation) | `science_graphrag/api/graph_display.py` (`enrich_authorship_nodes`; call sites use `graph_reader_projection.authorship_enrich`) |
| Workspace graph projection | `science_graphrag/api/workspace_graph/` (orchestration + normalization) |
| UI author semantics | `ui/src/components/graph/authorSemanticProjection.js` |
| ADR | `docs/adr/011-*.md`, `012-*.md` (workspace vs work semantics) |

**Asymmetry is documented** in ADR-011: workspace = union 1-hop; work = capped neighborhood. This plan does **not** mandate merging them into one HTTP resource; it mandates **honest labeling**, **shared projection code**, and **optional enrichment** when the product needs workspace-aware filters on a paper-centric view.

---

## 5. Phased remediation plan

### Phase 0 — Contract inventory and `meta` truthfulness (short) — **[DONE 2026-04-28]**

**Goal:** Stop silent confusion without large refactors.

**Tasks:**

- Add **`meta.graph_contract_version`** (integer or semver string) to work graph + workspace reader responses; bump when neighbor or membership rules change.
  - **Done:** integer constant **`GRAPH_CONTRACT_VERSION`** in [`science_graphrag/api/graph_reader_meta.py`](../../science_graphrag/api/graph_reader_meta.py) (**`1`** at Phase 0 ship; **`2`** from Phase 2 when work-graph optional `workspace_id` membership shipped, 2026-04-28); written on work graph ([`graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py)), all workspace graph branches + [`workspace_graph_neighbors`](../../science_graphrag/api/workspace_graph/cypher.py), and expand endpoints (work [`expand_work_aggregator`](../../science_graphrag/api/works/graph_neighborhood.py), workspace [`router.py` expand](../../science_graphrag/api/workspace_graph/router.py)).
- Ensure **`meta`** always includes: `neighbor_limit`, `prioritize`, `is_truncated`, `view`, and explicit **`workspace_id`** when the handler received it (even if null).
  - **Done:** shared **`enrich_reader_graph_meta()`** adds `graph_contract_version`, `neighbor_limit` (requested int on work graph; **`null`** on workspace root — full 1-hop union per ADR-012), `prioritize`, `view`, `workspace_id` ( **`null`** on standalone work graph until Phase 2 query param; whitespace-only ids normalized to **`null`**), **`graph_mode`**, and **`neighbor_limit_applied`** when absent (**`null`** on workspace / neighbors / expand). Existing **`neighbor_limit_applied`** on work graph preserved. **`legacy_workspace_graph_union`** now receives `prioritize` / `view` for consistent meta after merge.
- Docs: one table in `frontend-ui-api-contracts-v1.md` — “When is `workspace_membership` present?”
  - **Done:** Phase 0 `meta` subsection, updated JSON example, workspace `meta` paragraph, and membership table in [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md).

**Acceptance:** UI can show a one-line subtitle (“Capped neighborhood · limit 40”) from `meta` alone; no new graph queries.

- **Done:** [`ui/src/components/graph/graphContractSubtitle.js`](../../ui/src/components/graph/graphContractSubtitle.js) + wiring in [`GraphDetailPanel.jsx`](../../ui/src/components/graph/GraphDetailPanel.jsx); i18n **`graph.contractSubtitle.*`** in `ui/src/i18n/messages/en|ru/partGraphUi.js`.

**Tests:** [`tests/api/test_graph_reader_meta.py`](../../tests/api/test_graph_reader_meta.py) (helper + normalize); [`tests/test_works_graph_priority_limit.py`](../../tests/test_works_graph_priority_limit.py) asserts Phase 0 keys on work graph meta.

---

### Phase 1 — DRY package: reader projection extraction (backend) — **[DONE 2026-04-28]**

**Goal:** Remove duplicated **stringly** logic between `graph_neighborhood.py` / `graph_display.py` / workspace normalization.

**Tasks:**

- Create package **`science_graphrag/api/graph_reader_projection/`** (exact name in implementation PR):
  - `authorship_collapse.py` — `collapse_authorship_for_reader_view` + unit tests moved next to it;
  - `authorship_enrich.py` — thin wrapper or re-export of `enrich_authorship_nodes` if it stays DB-backed in `graph_display`, but **call sites** go through one import path;
  - `meta_builders.py` — shared `authorship_projection` classification helpers used by HTTP layer.
- `graph_neighborhood.py` becomes orchestration: fetch rows → enrich → **call projection** → aggregators → meta.
- `workspace_graph` reader path: **stop duplicating** any collapse/enrich steps that belong in the shared module (if today it duplicates; if not, still **import shared constants** for `via`, `va:` prefix, salts).

**Acceptance:** `rg collapse_authorship_for_reader_view` shows a single definition; pylint/module boundaries clean; existing tests green.

**Done (implementation notes):**

- **Package:** [`science_graphrag/api/graph_reader_projection/`](../../science_graphrag/api/graph_reader_projection/) — `authorship_collapse.py` (single `def collapse_authorship_for_reader_view`), `authorship_meta.py` (planned `meta_builders.py` role: `compute_authorship_projection_meta`, `strip_reader_only_authorship_properties`), `authorship_enrich.py` (re-export of enrich), `stable_edge_id.py` (`stable_graph_edge_id` shared with work-graph aggregators / `_enrich_edges_with_display`), `constants.py` (`READER_SYNTHETIC_AUTHOR_ID_PREFIX`, hash salt marker for `va:` ids).
- **Orchestration:** [`graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) imports projection + enrich seam only; no second definition of collapse.
- **Workspace graph:** [`workspace_graph/cypher.py`](../../science_graphrag/api/workspace_graph/cypher.py) uses `authorship_enrich` for `enrich_authorship_nodes` (workspace still does not run server-side collapse — client `authorSemanticProjection.js` unchanged; **Phase 4**).
- **Tests:** imports updated in [`tests/api/test_collapse_authorship_reader_view.py`](../../tests/api/test_collapse_authorship_reader_view.py), [`tests/api/test_work_graph_authorship_projection_meta.py`](../../tests/api/test_work_graph_authorship_projection_meta.py), [`tests/test_workspace_graph_display.py`](../../tests/test_workspace_graph_display.py); behavior covered by existing integration tests.
- **Docs:** [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md) table + pipeline pointers updated.

---

### Phase 2 — Membership and “external” semantics on work graph (optional `workspace_id`) — **[DONE 2026-04-28]**

**Goal:** When the client knows **`workspace_id`**, the work graph response can annotate neighbor works with **`workspace_membership`** (or a documented subset) **without** switching to the full workspace union URL.

**Tasks:**

- API: `GET /v1/works/{work_id}/graph?workspace_id=…` (optional, validated membership) runs a **cheap annotation pass** after neighborhood build: for each neighbor `Work` id in payload, query membership in that workspace (batch Cypher or existing helper).
- Document: if `workspace_id` is absent, **`workspace_membership` must be omitted or null** — UI must not treat as “external=false.”
- UI: when opening from workspace context, pass **`workspace_id`** query param (if not already); keep `workGraphUrl` as default from paper list without workspace.

**Acceptance:** Integration test: seeded workspace + external work + `CITES`; with `workspace_id` param, neighbor shows expected membership flags; without param, filter disabled or labeled “N/A outside workspace context.”

**Done (implementation notes):**

- **API:** [`science_graphrag/api/works/router.py`](../../science_graphrag/api/works/router.py) — optional `workspace_id` on **`GET /{work_id}/graph`** and **`GET /{work_id}/graph/expand`**; validates workspace exists (**404** `workspace_not_found`) and center work ∈ workspace (**422** `work_not_in_workspace`); loads internal work ids once per request.
- **Annotation:** [`science_graphrag/api/works/graph_neighborhood.py`](../../science_graphrag/api/works/graph_neighborhood.py) — reuses **`annotate_membership_and_cites`** + **`apply_workspace_node_kind`** from [`workspace_graph/projection.py`](../../science_graphrag/api/workspace_graph/projection.py) after aggregators; **`meta.graph_mode`** = **`work_workspace_context`** when context active; **`GRAPH_CONTRACT_VERSION`** bumped to **2** in [`graph_reader_meta.py`](../../science_graphrag/api/graph_reader_meta.py).
- **Expand URLs:** Aggregator **`expand_endpoint`** appends **`workspace_id`** when the graph was loaded with workspace context so expand keeps membership.
- **UI:** [`useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) — if **`work_id`** is set, always **`getWorkGraph`** (passes `workspaceId` from URL/shell when present); workspace union only when work scope is empty. [`workspacePageUrls.js`](../../ui/src/pages/WorkspacePage/workspacePageUrls.js) unchanged API; [`WorkspacePaperRow.jsx`](../../ui/src/pages/WorkspacePage/WorkspacePaperRow.jsx) passes **`workspaceId`** into **`workGraphUrl`**. [`graph.js`](../../ui/src/services/research/graph.js) sends **`workspace_id`** query.
- **Tests:** [`tests/test_work_graph_workspace_membership_integration.py`](../../tests/test_work_graph_workspace_membership_integration.py), helper [`work_graph_workspace_membership_by_work_id`](../../tests/fixtures/work_graph_workspace_authorship_parity.py), [`test_graph_reader_meta.py`](../../tests/api/test_graph_reader_meta.py) enrich case for **`work_workspace_context`**; expand HTTP mock updated for Neo4j preflight session.
- **Docs:** [`frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md) — work graph / expand / membership table + **`/graph`** URL semantics (**work_id** → capped API always).

---

### Phase 3 — 2-hop reader policy (Institution; Venue when present)

**Goal:** Align **“authors + affiliations”** with a **declared** hop budget, not accidental 1-hop omission.

**Tasks:**

- Product pick one:
  - **3A (minimal):** optional `include_institutions=true` adds **Authorship → Institution** (or `Work → … → Institution` per schema) within a **small fixed cap** merged into the same response `meta.extra_hops`.
  - **3B:** institutions appear only inside **aggregator expand** (already partially true for authors — mirror pattern).
- Update ADR addendum: **institution is not implied by 1-hop work graph** unless flag on.

**Acceptance:** Fixture or integration test proves institution nodes/edges present under flag; default unchanged for API stability.

---

### Phase 4 — Frontend DRY: delete or narrow `authorSemanticProjection.js`

**Goal:** UI does not re-implement server reader semantics.

**Tasks:**

- After Phase 1–2, classify workspace graph payloads: if server always delivers **the same reader edge/node shapes** as work graph, **remove** redundant projection branches from `authorSemanticProjection.js`.
- If a thin client normalizer remains (ids, dedup), document it as **presentation-only**, not authorship contract.

**Acceptance:** `npm run lint` + graph smoke tests; fewer branches in projection file; no regression on workspace graph page.

---

### Phase 5 — Product copy and navigation (close the UX loop)

**Goal:** Match ADR truth to UI strings.

**Tasks:**

- Workspace graph entry: label as **“All papers in workspace (1-hop)”** or similar.
- Work graph: **“This paper’s neighborhood (capped)”** + show limit from `meta`.
- Link from paper row: remain **work-centric** unless user explicitly opens workspace graph (sidebar / menu).

**Acceptance:** i18n keys updated EN/RU; no user-facing claim of identity between the two modes.

---

## 6. Verification matrix (tests and manual QA)

| Layer | What to add / keep |
|-------|---------------------|
| Unit | Projection package tests (collapse, `va:` stability, `via` ordering). |
| Integration | Membership annotation with `workspace_id`; optional institution flag. |
| Parity | Extend parity helpers beyond authorship: **membership counts**, **institution presence** when contract says so. |
| Manual | Runbook row: “open same work in workspace vs work graph — read `meta.graph_mode` / limits.” |

---

## 7. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Larger payloads / slower work graph | Batch membership query; cache per request; strict caps on annotation pass. |
| Breaking mobile or external API clients | Versioned `meta` + conservative defaults; feature flags. |
| Venue still missing | Separate ingest/OpenAlex backlog; graph shows “venue unknown” with link to doc. |

---

## 8. Completion definition (“architecturally closed”)

- **DRY:** Reader authorship projection and related **`va:` / `via`** rules live in **one Python package** (`graph_reader_projection` — **Phase 1 done, 2026-04-28**); UI projection (`authorSemanticProjection.js`) still overlaps until **Phase 4**.
- **Honest asymmetry:** ADR, API spec, and UI strings agree; `meta` exposes mode and limits.
- **Workspace context:** Optional `workspace_id` on work graph enables **membership-aware** filters without misusing the workspace union endpoint.
- **2-hop policy:** Institution (and venue when data exists) governed by **explicit** flags / ADR, not accidental 1-hop shape.
- **Tests:** Parity + integration cover the above contracts.

---

## 9. References

- [`work-graph-authorship-reader-contract-2026-04-28.md`](./work-graph-authorship-reader-contract-2026-04-28.md)  
- [`docs/architecture/work-graph-reader-authorship.md`](../architecture/work-graph-reader-authorship.md)  
- [`docs/specs/frontend-ui-api-contracts-v1.md`](../specs/frontend-ui-api-contracts-v1.md)  
- ADR-011 / ADR-012 under `docs/adr/`  
- Backlog: `docs/backlog/refactor-backend.md` — **Graph work vs workspace — single projection seam + parity** (execution tracker for Phase 1–3).
