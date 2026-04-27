# Workspace graph: methods, external citations, «Untitled work» — root cause and action plan (2026-04-27)

**Context:** Graph tab with **methods display** enabled; user observes many internal papers **without green Method nodes**, few **purple citation** edges (~16 / 31 papers), and many targets labeled **«Untitled work»**.

**Conclusion up front:** This is **primarily a projection + depth contract mismatch between the UI and Neo4j**, compounded by **reference ingestion creating minimal `:Work` stubs** without a resolvable title. It is **not** «workspace was loaded wrong» (membership is fine) and **not** intentional benchmark fraud — nightly metrics use **different** artifacts (layer1 `gold.json`, graph fixtures) than this **interactive** workspace graph API.

**Update (2026-04-27, implemented):** The workspace graph contract is **fixed**: `GET /v1/workspaces/{id}/graph` always returns the **union of all incident edges** for every internal `Work` in the workspace (same shape as the former **`depth=1`** path, `build_from_depth1_rows`), with **no** server-side `depth`, `neighbor_limit`, or `node_types` query slicing for the main canvas. Neighbors/expand endpoints no longer apply hop/limit caps. **Node visibility** is **client-only** (`graphVisibilityFilter.js`, toolbar «Nodes»). Sections below that describe **`depth: 2`** and `build_from_depth2_rows` remain the **historical root-cause** explanation for the symptoms users saw before this change.

### Measured snapshot (Neo4j, workspace `2678c5f1-1b31-4aac-92c9-6bd0f4472b23`)

| Metric | Value |
|--------|------:|
| Internal works | 31 |
| Distinct `Method` nodes reachable via `USES_METHOD` from them | 62 |
| Internal works with **zero** `USES_METHOD` in Neo4j | **0** |
| `CITES` edges **internal → external** (1-hop, target not in workspace) | **280** |
| Of those external targets, edges where cited `Work` has **empty / null `title`** | **191** |

So the UI observation «~16 edges / mostly Untitled» was **inconsistent with Neo4j 1-hop reality** when the client used a **restricted graph slice** (historically: **`depth: 2`** projection — see §1–2). With the **full 1-hop** contract, citation and method counts in the UI should align with **1-hop** Neo4j counts modulo **UI rendering caps** (`GRAPH_UI_MAX_*`) and optional **client type hiding**.

---

## 1. Methods «missing» on the canvas

### 1.1 What Neo4j actually has

Prior audit ([`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md)): for workspace **Object Detection (clean ingested + claims)** every internal `Work` had **at least one** `[:USES_METHOD]->(:Method)` edge. So the graph **database layer** is not empty for methods.

### 1.2 What the frontend requested (before the contract fix)

[`useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) **used to** load the workspace graph with:

- `mode: "full"`
- **`depth: 2`** (removed from the API contract; the client no longer sends depth)
- `includeExternal: true`
- `includeClaims: true`

### 1.3 What the backend did for `depth >= 2` (historical)

[`cypher.py`](../../science_graphrag/api/workspace_graph/cypher.py) **previously** set `depth_eff = 2` when `depth >= 2`. For 31 internal works, GDS fast-path was often **not** used (`len(internal_ids) > 50` is false — see [`_cypher_gds.py`](../../science_graphrag/api/workspace_graph/_cypher_gds.py)), so the payload was built with **`build_from_depth2_rows`** (this path has been **removed** for the main workspace graph; projection is always **depth‑1 union** now).

That query is structurally:

```140:148:science_graphrag/api/workspace_graph/_cypher_projection.py
    query = (
        "MATCH (ws:Workspace {id: $wid})-[:CONTAINS]->(iw:Work) WITH collect(DISTINCT iw.id) AS I "
        "MATCH (a:Work)-[r1]-(m)-[r2]-(b) WHERE a.id IN I "
        "AND (NOT m:Work OR m.id IN I OR $includeExternal) AND (NOT b:Work OR b.id IN I OR $includeExternal) "
        "AND ($typesEmpty OR any(l IN labels(b) WHERE l IN $nodeTypes)) "
        ...
        f"{sem_clause}RETURN DISTINCT a, r1, m, r2, b"
    )
```

So every returned row must contain **two** relationship steps `r1` and `r2` from internal anchor `a` through `m` to `b`.

**Direct** `(:Work)-[:USES_METHOD]->(:Method)` is **one** hop. It only appears in this result set if there exists a **second** hop `(Method)-[r2]-(b)` to some `b` that still passes filters (e.g. another `Work` that also `USES_METHOD` the same node, a `Dataset` via `TRAINED_OR_TESTED_ON`, etc.). If a `Method` is only linked to **one** paper in the graph and has **no** further typed neighbors, it **never appears** in the depth‑2 payload — **even though `USES_METHOD` exists in Neo4j**.

That matches the screenshots:

- **Dense left/center:** shared methods (FPN, RPN, YOLO, …) sit on multi-work or multi-rel paths → satisfy 2-hop pattern.
- **Right column «without methods»:** papers whose ontology methods are **unique** or **leaf** in the induced subgraph under this query → **0 Method nodes** in the API response despite Neo4j edges.

### 1.4 Verdict (methods)

| Question | Answer |
|----------|--------|
| Broken ontology for those papers? | **Unlikely** as sole explanation; Neo4j had `USES_METHOD` for all audited internal works. |
| Wrong workspace membership? | **No.** |
| UI bug? | **Was partially:** UI forced **`depth: 2`**, which was **incompatible** with «show every direct semantic neighbor» for Methods. |
| Fix surface | **Shipped:** full **1-hop union** on the server + **client-only** type visibility; see ADR 011 addendum and `graph-ui-plan.md` workspace section. |

---

## 2. External citations sparse; «Untitled work»

### 2.1 Where «Untitled work» comes from

[`science_graphrag/api/graph_display.py`](../../science_graphrag/api/graph_display.py):

```142:145:science_graphrag/api/graph_display.py
    if node_type == "Work":
        year = p.get("publication_year")
        display_label = display_label or "Untitled work"
        subtitle = f"Work · {int(year)}" if year is not None else "Work"
```

So **any** `Work` node reaching the client **without a usable `title`/`label` in props** is shown as **«Untitled work»**. That is **display logic**, not a separate node type.

### 2.2 How cited works are created (ingestion)

[`science_graphrag/ingestion/_pipeline_impl.py`](../../science_graphrag/ingestion/_pipeline_impl.py) `_persist_reference_citation` merges `(:Work)` via [`upsert_minimal_work`](../../science_graphrag/storage/neo4j/writes/works.py). Titles come from OpenAlex, or from `ref.title`, or may be **weak / empty** when PDF reference parsing is poor.

Additionally, **many references never become edges**: the loop only persists citations when the draft has **doi**, or **arxiv id**, or **(non-empty normalized title + year)**:

```1004:1013:science_graphrag/ingestion/_pipeline_impl.py
                for ref in references:
                    if not (
                        normalize_doi(ref.doi)
                        or _normalize_arxiv_id(ref.arxiv_id)
                        or (
                            _normalized_title_for_fingerprint(ref.title) is not None
                            and ref.year is not None
                        )
                    ):
                        continue
                    _retry_call(_persist_reference_citation, neo, work_id, ref, settings)
```

So the **PDF bibliography** can be «100% extensive» while **`references_linked` in the pipeline** counts only **linkable** rows — the rest are skipped with no `CITES` edge.

### 2.3 Why the **graph** shows even fewer citation arrows than Neo4j might have

Same **depth‑2** issue as for methods:

- A **one-hop** internal → external `CITES` edge `(internal)-[:CITES]->(external_stub)` does **not** match `(a)-[r1]-(m)-[r2]-(b)` **unless** the external `Work` has **another** incident relationship `r2` to some `b` passing filters.
- Stub cited works (only incoming `CITES`, no title, no other rels) fail both **human readability** (Untitled) and often **2-hop inclusion** (invisible on depth‑2 graph).

### 2.4 Verdict (citations / Untitled)

| Question | Answer |
|----------|--------|
| Workspace load error? | **No** — `CONTAINS` and chunk payloads were healthy in the OD audit. |
| Ingestion incomplete vs PDF? | **Yes** — many refs never linked (gate above); linked stubs may lack title → **Untitled**. |
| Metrics «lying»? | **Different measurement object:** layer1 / graph benchmarks use **fixture `gold.json`** and/or **separate** expectations, not this interactive subgraph. Pipeline metrics expose `references_total` vs `references_linked` — that is **honest partial linking**, not the same as «all bibliography rows». |
| UI-only artifact? | **Was partly** — depth‑2 projection **suppressed** many valid `CITES` edges that exist as **single** hops (resolved by full 1-hop contract). |

---

## 3. Interaction matrix (symptoms → causes)

| Symptom | Main cause | Secondary |
|---------|------------|-------------|
| Many papers without green Method nodes | **Was:** depth‑2 projection omitted 1‑hop `USES_METHOD` leaves | Aggregator; now also check **client** type filter |
| ~16 citation-like edges for 31 papers | **Was:** depth‑2 + stub cited works without 2nd hop | Fewer `CITES` in DB than PDF refs (reference gate) |
| «Untitled work» | **`w.title` missing** on merged cited `Work` | UUID / empty string label cleanup → fallback string |

---

## 4. Action plan (prioritized)

### P0 — Make the graph truthful for «methods mode» and citations — **[DONE]**

1. **Implemented:** Workspace graph is always the **full union of 1-hop** rows (`build_from_depth1_rows`); query params **`depth`**, **`neighbor_limit`**, **`node_types`** removed from `GET .../graph` (no server-side slice for canvas). Neighbors/expand: **uncapped** 1-hop. UI: **no** workspace depth toggle; visibility via **`graphVisibilityFilter`** only.
2. **Docs:** `graph-ui-plan.md` (Workspace graph v2), ADR **011** addendum (workspace), ADR **012** addendum (projection).

### P1 — Reduce «Untitled work»

1. When merging minimal cited works, set **`title`** from best available: OpenAlex → parsed ref → «Unknown reference (DOI …)» instead of leaving property absent.
2. Optional backfill: OpenAlex lookup by stub `doi` / `fingerprint` for existing `Work` nodes with empty title.

### P2 — Increase `CITES` coverage (ingestion)

1. Second-pass linker for refs missing doi/year (e.g. **raw string** match against OpenAlex search, or Crossref title query) — behind feature flag.
2. Log **skipped** reference counts per document (not only `references_linked`) in UI ingest summary for transparency.

### P3 — Benchmarks / trust

1. Add a sentence to trust / eval docs: **workspace graph API ≠** citation recall benchmark surface.
2. If a future benchmark claims «graph citations visible in UI», pin **`include_external`**, **`mode`**, and **client visibility defaults** in the spec (workspace graph no longer exposes server **`depth`** / **`node_types`**).

---

## 5. Quick validation queries (Neo4j)

**Count direct methods from internal workspace works (should be ≥ 31 for OD audit):**

```cypher
MATCH (ws:Workspace {id: $ws})-[:CONTAINS]->(w:Work)
OPTIONAL MATCH (w)-[:USES_METHOD]->(m:Method)
RETURN count(DISTINCT w) AS works, count(DISTINCT m) AS method_nodes, sum(CASE WHEN m IS NULL THEN 1 ELSE 0 END) AS works_with_zero_methods;
```

**Count `CITES` from internal works to works outside workspace (1-hop):**

```cypher
MATCH (ws:Workspace {id: $ws})-[:CONTAINS]->(iw:Work)
WITH collect(DISTINCT iw.id) AS I
MATCH (a:Work)-[:CITES]->(b:Work)
WHERE a.id IN I AND NOT b.id IN I
RETURN count(*) AS cites_to_external;
```

If `cites_to_external` is large but the UI shows almost nothing **after** the 2026-04-27 contract fix, check **client caps** (`GRAPH_UI_MAX_*`), **hidden node types**, and ingestion/linking — not server depth (removed).

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial root-cause analysis from code paths + prior OD DB audit. |
| 2026-04-27 | Contract fix: full 1-hop workspace graph; P0 marked done; sections 1.2–1.3 labeled historical. |
