# CONTRADICTS ontology: evidence gap, epistemic levels, and improvement paths (2026-04-27)

**Context:** The workspace graph UI shows a `CONTRADICTS` edge between two papers (example: EfficientDet vs RetinaNet / focal-loss line of work). The API payload only carries a **template summary** (`Source —[contradicts]→ Target`) and identifiers. Users reasonably ask: **what exactly contradicts what**, and **on what grounds**.

**Conclusion up front:** The gap is **not only “the LLM collects too little”**. Today the product stack **(1)** persists at most a **minimal** Work–Work edge in Neo4j, **(2)** drops **all relationship properties** when projecting edges to the UI, and **(3)** has **no single canonical place** where a human-verifiable *explanation* (quotes + scoped claims) must live. Rich human gold for benchmarks already encodes what we want; runtime graph and API **do not surface** that level of detail.

---

## 1. What users expect from “contradicts”

Scientific “contradiction” is rarely a Boolean between two titles. Useful interpretations include:

| Level | Example phrasing | Typical evidence |
|-------|-------------------|-------------------|
| **Logical** | Assertion P and assertion ¬P (same predicates, universe) | Same definitions; overlapping experimental setting |
| **Empirical** | Paper A reports higher AP than B on COCO under comparable training | Tables, metrics, training recipe alignment |
| **Methodological / paradigm** | “Anchors are necessary” vs “anchor-free is sufficient” | Architectural claims + ablations |
| **Scaling / efficiency** | “Depth scaling wins” vs “compound scaling wins under FLOP cap” | Scaling laws, compute-normalized curves |
| **Rhetorical / positioning** | “Prior work fails on X” (often cite-targeted) | Explicit citations, limitations sections |

Without **scope** (which metric, dataset, regime) and **anchors** (verbatim spans or normalized claim IDs), “Paper A contradicts Paper B” is **underspecified** and often **misleading**—especially in fast-moving CV lines where papers **supersede**, **refine**, or **offer alternatives under different budgets** rather than strict logical negation.

---

## 2. Current implementation (as of this audit)

### 2.1 Neo4j persistence (`:CONTRADICTS` between `:Work`)

`merge_work_contradicts` writes a directed edge with **only**:

- `subtype` (string, default `unspecified`, benchmark materialization uses gold `contradiction_type` values such as `scaling`, `design_paradigm`, …)
- `schema_version` (int, default 1)

There is **no** persisted field for rationale, quotes, claim IDs, severity, confidence, or detector provenance on the relationship itself.

Reference: `science_graphrag/storage/neo4j/writes/contradictions.py`.

### 2.2 Graph API → UI projection

`edge_dict_from_rel` builds `{id, source, target, type}` only. **No** `dict(rel)` merge into the payload.

`enrich_edges_workspace` then sets:

- `display_type` from relation type
- `summary` as `"{source_label} —[{display_type}]→ {target_label}"`

So the UI “summary” is **purely compositional** from node titles and edge type; it cannot express *why* the edge exists.

Reference: `science_graphrag/api/workspace_graph/projection.py` (`edge_dict_from_rel`, `enrich_edges_workspace`). The same enrichment pattern exists for work-level neighborhood graphs (`science_graphrag/api/works/graph_neighborhood.py`).

### 2.3 Claims ontology (parallel track)

`docs/specs/ontology-claims-v1.md` sketches **Claim–Claim** `:CONTRADICTS` (or an explicit `Contradiction` node) with evidence anchored in chunks. That is the **right epistemic layer** for explainable conflict, but it is **orthogonal** to the current **Work–Work** edge the user sees unless the UI resolves through claims.

### 2.4 Idea-assist / LLM (advisory)

`IdeaOrchestrator` can return `ContradictionPair(claim_a_id, claim_b_id, description)` with a `description` up to 600 characters, grounded on claim rows and optional `existing_contradictions` from `EdgeSearchTool`. This is **API output**, not automatically written onto `:CONTRADICTS` between works (see ADR 017 and backlog notes on ingest-time persistence).

Reference: `science_graphrag/agent/idea_workflow.py`.

### 2.5 Benchmark gold (what “good” looks like)

`tests/fixtures/benchmarks/contradictions_v1/*/gold.json` defines, per pair:

- `claim_a` / `claim_b` with `claim_text`, `evidence_quote`, `corpus_work_id`
- `contradiction_type`, `severity`, `rationale`
- `expected_neo4j_pattern` (Work–Work with `subtype`)

This is **human-authored** supervision, not what the live graph edge currently carries to the client.

---

## 3. Root-cause analysis (why it feels empty)

1. **Storage contract is minimal** — By design, BT12 materialization optimized for **existence** of an edge and a **taxonomy tag** (`subtype`), not for narrative explanation.
2. **Projection drops rel props** — Even `subtype` does not reach the UI today; the user JSON has no `subtype` field.
3. **Work–Work edge is the wrong granularity for explanation** — Titles are not propositions. Explanation belongs at **Claim (+ Evidence)** (or a dedicated reified node).
4. **“Contradicts” is overloaded** — Many corpus edges are **curatorial** (relations_v1 / domain knowledge) or **detector-inferred**; without provenance, the UI cannot distinguish **gold / human**, **LLM**, **heuristic**, or **legacy import**.
5. **Risk of spurious edges** — Paper-level “contradicts” between famous detection papers often reflects **competing recommendations** (scaling, anchors, two-stage vs one-stage) rather than classical contradiction; without rationale, users cannot **sanity-check** the edge.

---

## 4. Ontology directions (recommended semantics)

### 4.1 Keep `:CONTRADICTS` between works as a **summary index** (optional)

Use Work–Work edges for **navigation** (“these works are in tension”) but treat them as **non-self-explanatory** unless properties or linked objects are present.

**Suggested optional rel properties (v2 sketch):**

| Property | Purpose |
|----------|---------|
| `subtype` | Already exists; align enum with gold: `era_shift`, `design_paradigm`, `post_processing`, `architectural`, `classical_vs_deep`, `scaling`, `unspecified`, … |
| `severity` | `direct` vs `nuanced` (from gold schema) |
| `confidence` | Float 0–1 or discrete `low/medium/high` |
| `detector` | `human_corpus` \| `llm` \| `benchmark_materialize` \| … |
| `source_refs` | Optional list of chunk fingerprints / offsets (if detector emits them) |
| `rationale_short` | One paragraph, **non-PII**, for UI (max length cap) |
| `claim_pair_fingerprint` | Stable join key to a `Contradiction` pattern or claim IDs |

Version with `rel_schema_version` / migration strategy when extending.

### 4.2 Prefer **reified contradiction** at claim level (strongest UX + QA)

Introduce (or standardize on) one of:

- `(Claim)-[:CONTRADICTS]->(Claim)` plus each claim’s `SUPPORTED_BY` → `Evidence` → `ANCHORED_IN` → `Work`, or  
- `(:Contradiction)` node with edges to two claims and optional links to works.

**UI behavior:** Clicking Work–Work `CONTRADICTS` fetches **claim neighborhood** or a small **“evidence card”** subgraph (two quotes + short merged rationale). The Work–Work edge becomes a **shortcut** to that structure.

### 4.3 Vocabulary split (future, if product needs precision)

Consider replacing a single `CONTRADICTS` label with or adding subtypes as **edge types or enums**:

- `REFUTES_CLAIM`, `INCONSISTENT_RESULTS_UNDER`, `ALTERNATIVE_TO_ASSUMPTION`, `SUPERSEDES_METHOD_CLAIM`, …

This reduces false “contradiction” readings and improves retrieval and trust rollups.

---

## 5. Improvement paths (ordered by leverage vs effort)

### Path A — **Surface what Neo4j already has** (small, high ROI)

- Extend `edge_dict_from_rel` (and any alternate edge builders) to attach **sanitized** `properties` from `dict(rel)` for selected types (`CONTRADICTS`, …).
- Extend `enrich_edges_workspace` to prefer `rationale_short` or `subtype` in `summary` when present, e.g. `"{sl} —[contradicts: {subtype}]→ {tl}"` plus optional subtitle field `edge["detail"]`.
- **Acceptance:** UI raw JSON shows `subtype` (and any new fields) for materialized edges; no PII leakage; size caps enforced.

### Path B — **Persist rationale + quotes on materialization / ingest** (medium)

- When writing `:CONTRADICTS`, populate `rationale_short` and optional `quote_a` / `quote_b` (truncated, verbatim from corpus) from the same contract as `contradictions_v1` gold.
- For LLM-detected edges, require **quote gate** (substring of stored chunks) before MERGE, mirroring claims extraction rules.
- **Acceptance:** New edges carry verifiable anchors; benchmark runner can check optional new fields.

### Path C — **Claim-level graph as source of truth** (larger, architecturally clean)

- Promote contradictions to **Claim–Claim** (or `Contradiction` node) with mandatory evidence; Work–Work edge derived by projection query or lazy “rollup” for the graph tab.
- **Acceptance:** Idea-assist and graph tab share one schema; trust metrics can move from “edge exists” to “evidence-backed contradiction”.

### Path D — **Product copy + warnings** (small, immediate)

- In the edge inspector, if no `subtype` / rationale / linked claims: show **“Underspecified relation — see papers or enable claims view”** and link to both works. Sets expectations until A–C land.

---

## 6. Risks and guardrails

- **Hallucinated conflicts** if LLM writes Work–Work edges without quotes.
- **Citation graph ≠ contradiction graph** — Do not infer `CONTRADICTS` from `CITES` alone.
- **Directionality** — Current MERGE uses canonical UUID order for `(x)-[:CONTRADICTS]->(y)`; the UI shows `source`/`target` from that projection. Epistemic “A refutes B” may be **asymmetric**; document whether the edge is **undirected tension** vs **directed refutation** if the product requires it.
- **EfficientDet vs focal-loss family** — Benchmark rationale for the related gold pair is about **scaling strategies** (depth vs compound scaling under resource constraints), not “Focal Loss is false.” Product language should avoid implying **logical negation** when the edge means **design tension**.

---

## 7. Suggested next steps (engineering backlog)

1. Implement **Path A** so `subtype` and future rel props reach the UI (quick win; aligns projection with persistence).
2. Decide product owner for **Path B vs C**: short-term text on Work–Work vs medium-term claim reification.
3. If ingest-time LLM contradiction detection is added, reuse **claims quote gate** and `contradictions_v1` **taxonomy** for consistency with BT12.

---

## 8. References in-repo

| Artifact | Role |
|----------|------|
| `science_graphrag/storage/neo4j/writes/contradictions.py` | Work–Work MERGE + `subtype` |
| `science_graphrag/api/workspace_graph/projection.py` | Edge payload + `summary` template |
| `docs/specs/ontology-claims-v1.md` | Claim-level epistemic model |
| `science_graphrag/agent/idea_workflow.py` | LLM `description` on claim pairs (advisory) |
| `tests/fixtures/benchmarks/contradictions_v1/` | Rich gold schema (target state for evidence) |
| `docs/analysis/ontology-benchmarks-trust-audit-2026-04-25.md` | BT12 / persistence status |
| `docs/adr/017-hypothesis-idea-assist-advisory.md` | Advisory vs graph write policy |
