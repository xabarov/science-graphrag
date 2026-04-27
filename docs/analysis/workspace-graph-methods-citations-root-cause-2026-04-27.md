# Workspace graph: methods, external citations, «Untitled work» — root cause and action plan (2026-04-27)

**Context:** Graph tab with **methods display** enabled; user observes many internal papers **without green Method nodes**, few **purple citation** edges (~16 / 31 papers), and many targets labeled **«Untitled work»**.

**Conclusion up front:** This is **primarily a projection + depth contract mismatch between the UI and Neo4j**, compounded by **reference ingestion creating minimal `:Work` stubs** without a resolvable title. It is **not** «workspace was loaded wrong» (membership is fine) and **not** intentional benchmark fraud — nightly metrics use **different** artifacts (layer1 `gold.json`, graph fixtures) than this **interactive** workspace graph API.

### Measured snapshot (Neo4j, workspace `2678c5f1-1b31-4aac-92c9-6bd0f4472b23`)

| Metric | Value |
|--------|------:|
| Internal works | 31 |
| Distinct `Method` nodes reachable via `USES_METHOD` from them | 62 |
| Internal works with **zero** `USES_METHOD` in Neo4j | **0** |
| `CITES` edges **internal → external** (1-hop, target not in workspace) | **280** |
| Of those external targets, edges where cited `Work` has **empty / null `title`** | **191** |

So the UI observation «~16 edges / mostly Untitled» is **inconsistent with Neo4j 1-hop reality** unless the client uses a **restricted graph slice** (here: **`depth: 2`** projection — see §1–2).

---

## 1. Methods «missing» on the canvas

### 1.1 What Neo4j actually has

Prior audit ([`od-corpus-claims-methods-trust-audit-2026-04-27.md`](./od-corpus-claims-methods-trust-audit-2026-04-27.md)): for workspace **Object Detection (clean ingested + claims)** every internal `Work` had **at least one** `[:USES_METHOD]->(:Method)` edge. So the graph **database layer** is not empty for methods.

### 1.2 What the frontend requests

[`ui/src/components/graph/hooks/useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) loads the workspace graph with:

- `mode: "full"`
- **`depth: 2`**
- `includeExternal: true`
- `includeClaims: true`

### 1.3 What the backend does for `depth >= 2`

[`science_graphrag/api/workspace_graph/cypher.py`](../../science_graphrag/api/workspace_graph/cypher.py) sets `depth_eff = 2` when `depth >= 2`. For 31 internal works, GDS fast-path is **not** used (`len(internal_ids) > 50` is false — see [`_cypher_gds.py`](../../science_graphrag/api/workspace_graph/_cypher_gds.py)), so the payload is built with **`build_from_depth2_rows`**.

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
| UI bug? | **Partially:** UI forces **`depth: 2`**, which is **incompatible** with «show every direct semantic neighbor» for Methods. |
| Fix surface | **Frontend** (`depth: 1` or configurable), and/or **backend** (union of depth‑1 semantic edges with depth‑2 skeleton), and/or **document** that «methods mode» is «methods reachable in 2-hop reader graph». |

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
| UI-only artifact? | **Partly** — depth‑2 projection **suppresses** many valid `CITES` edges that exist as **single** hops. |

---

## 3. Interaction matrix (symptoms → causes)

| Symptom | Main cause | Secondary |
|---------|------------|-------------|
| Many papers without green Method nodes | **Depth‑2 projection** omits 1‑hop `USES_METHOD` leaves | Aggregator / caps (lower priority here) |
| ~16 citation-like edges for 31 papers | **Depth‑2** + **stub cited works** without 2nd hop | Fewer `CITES` in DB than PDF refs (reference gate) |
| «Untitled work» | **`w.title` missing** on merged cited `Work` | UUID / empty string label cleanup → fallback string |

---

## 4. Action plan (prioritized)

### P0 — Make the graph truthful for «methods mode» and citations

1. **Either** change workspace graph fetch to **`depth: 1`** in [`useGraphWorkspaceData.js`](../../ui/src/components/graph/hooks/useGraphWorkspaceData.js) (simplest), **or** add a dedicated query flag e.g. `semantic_1hop=1` that **unions**:
   - current depth‑2 skeleton (for context), **with**
   - explicit `MATCH (w:Work)-[r:USES_METHOD|CITES]->(x) WHERE w.id IN $internal` (subject to caps and visibility).
2. Document in UI copy that **«reader graph» depth** is not «full Neo4j degree‑1 neighborhood».

### P1 — Reduce «Untitled work»

1. When merging minimal cited works, set **`title`** from best available: OpenAlex → parsed ref → «Unknown reference (DOI …)» instead of leaving property absent.
2. Optional backfill: OpenAlex lookup by stub `doi` / `fingerprint` for existing `Work` nodes with empty title.

### P2 — Increase `CITES` coverage (ingestion)

1. Second-pass linker for refs missing doi/year (e.g. **raw string** match against OpenAlex search, or Crossref title query) — behind feature flag.
2. Log **skipped** reference counts per document (not only `references_linked`) in UI ingest summary for transparency.

### P3 — Benchmarks / trust

1. Add a sentence to trust / eval docs: **workspace graph API ≠** citation recall benchmark surface.
2. If a future benchmark claims «graph citations visible in UI», pin **`depth`**, **`include_external`**, and **node_types** in the spec.

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

If `cites_to_external` is large but the UI shows almost nothing, **depth‑2 projection** is confirmed in practice.

---

## Document history

| Date | Action |
|------|--------|
| 2026-04-27 | Initial root-cause analysis from code paths + prior OD DB audit. |
