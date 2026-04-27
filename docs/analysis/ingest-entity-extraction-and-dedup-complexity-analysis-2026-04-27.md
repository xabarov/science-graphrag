# Ingest entity extraction and dedup complexity analysis (2026-04-27)

**Status:** code-path analysis of the current implementation.

**Primary question:** if a document produces `n` chunks, do current ingestion and dedup paths contain nonlinear operations of `O(n^2)` or higher, especially in LLM-dependent stages?

**Short answer:** not in the main chunk-driven ingestion path. The current pipeline is mostly linear in chunk count, with bounded batching for LLM calls. The main nonlinear behavior exists elsewhere:

- `O(m^2)` inside intra-document method consolidation, where `m` is the number of extracted methods in one paper;
- `O(E^2)` in generic full-scan entity dedup passes, where `E` is the number of entities being pairwise scanned;
- bounded cross-products such as `O(e_new * E_ws_trim)` during ingest-time entity conflict checks, where `e_new` is the number of entities on the newly ingested work and `E_ws_trim` is the workspace entity window.

So the current system does have quadratic logic, but the worst cases are tied to extracted entities and workspace-wide scans, not directly to chunk count.

---

## 1. Scope and notation

This note focuses on the current code paths in:

- `science_graphrag/ingestion/_pipeline_impl.py`
- `science_graphrag/ingestion/claims/extractor.py`
- `science_graphrag/ingestion/llm/orchestrator.py`
- `science_graphrag/ingestion/llm/semantic_extraction.py`
- `science_graphrag/ingestion/method_consolidation.py`
- `science_graphrag/dedup/ingest_conflict_check.py`
- `science_graphrag/dedup/entity_ingest_conflict_check.py`
- `science_graphrag/dedup/work_dedup_engine.py`
- `science_graphrag/dedup/author_dedup_engine.py`
- `science_graphrag/dedup/entity_pipeline_common.py`

Notation used below:

- `n`: number of document chunks after chunking;
- `r`: number of reference entries;
- `m`: number of methods extracted from one document;
- `c`: number of claims returned by claims extraction;
- `W`: number of works in a workspace;
- `A`: number of authors in a workspace;
- `E`: number of entities in a workspace for one entity type;
- `e_new`: number of newly ingested entities on the current work;
- `k`: top-k candidate count used in vector-search-based dedup;
- `E_ws_trim`: workspace entity subset considered during ingest-time entity checks.

When complexity depends on external systems such as Qdrant or Neo4j, this document describes the application-side cost first. Internal index complexity inside those systems is treated as implementation-dependent unless the Python code makes a stronger guarantee.

---

## 2. End-to-end ingestion complexity by stage

## 2.1 Parse, normalize, and chunk

The early ingest stages are linear in document length and chunk count:

- PDF/text extraction is document-linear from the Python side;
- normalization and boilerplate stripping are linear in document size;
- chunk dedup is linear in the number of produced chunks.

Important point: `dedupe_chunks_for_embedding()` does not compare all chunks against all chunks. It only keeps a `set` of seen fingerprints, so the dedup cost is `O(n)`.

Implication: there is no chunk-pairwise explosion at this stage.

## 2.2 Metadata, authorships, and references extraction

The layer-1 orchestrator in `science_graphrag/ingestion/llm/orchestrator.py` has three different shapes:

1. **Metadata extraction**: one LLM call per document, so `O(1)` in chunk count.
2. **Authorship extraction**: one LLM call per document, so `O(1)` in chunk count.
3. **Reference extraction**: batched over parsed reference entries, not over chunks.

Reference extraction uses `reference_chunk_groups(...)` to split references into batches of entries. That cost is approximately:

`O(r / batch_size)` LLM calls, plus linear merge/enrichment over extracted and heuristic references.

This is not `O(n^2)` in chunks unless someone assumes `r` itself grows quadratically with document size, which is not how the current code is structured.

## 2.3 Semantic extraction

`science_graphrag/ingestion/llm/semantic_extraction.py` runs a bounded sequence of retry prompts over the article body:

- primary;
- compact retry;
- micro retry;
- nano retry.

That means at most a small constant number of LLM calls per document. From a chunk-count perspective, semantic extraction is `O(1)`.

The expensive part is not retry count. The expensive part is what happens after semantic extraction, in intra-document method consolidation.

## 2.4 Claims extraction

Claims extraction is the most chunk-sensitive LLM stage, but it is still linear in chunk count.

In `science_graphrag/ingestion/claims/extractor.py`:

- small inputs run as one batch;
- when chunk count exceeds the threshold, the code splits into fixed-size batches;
- on failure, a batch may be recursively split into two smaller sub-batches.

Current batch constants in `science_graphrag/ingestion/llm/prompts/claims.py` are:

- `PRODUCTION_BATCH_TRIGGER_CHUNKS = 8`
- `PRODUCTION_BATCH_SIZE = 6`

So the normal production-case number of LLM calls is approximately:

`O(n / 6)`

with a larger constant factor when split-retry is triggered.

This remains linear rather than quadratic because:

- batches are fixed-size;
- there is no pairwise comparison between chunks;
- post-processing walks the returned claims/evidence rows once, plus hash/set-based dedup of final claims.

## 2.5 Embeddings and vector upserts

Chunk embedding cost is linear in chunk count:

- embedding input list size is `n`;
- Qdrant chunk upsert is also driven by those `n` vectors.

So the application-side complexity here is:

- `O(n)` for vectorization;
- `O(n)` for chunk upsert payload construction and submission.

Claim-vector upsert is similarly linear in number of claims `c`.

---

## 3. Direct answer for chunk-count `n`

If `n` means the number of chunks for one ingested document, the main ingest path is approximately:

`T_ingest(n, r, m, c) = O(n) + O(r / B_ref) + O(1) + O(m^2) + O(c)`

where:

- `O(n)` covers chunk construction, chunk dedup, claims batching, chunk embeddings, and chunk upserts;
- `O(r / B_ref)` covers batched reference extraction;
- `O(1)` covers metadata/authorship/semantic LLM call count;
- `O(m^2)` comes from method consolidation after semantic extraction;
- `O(c)` covers claim post-processing and persistence.

So:

- **No**, the main ingestion flow is not `O(n^2)` in chunk count.
- **Yes**, the overall ingest of one document can still hit quadratic behavior through `m^2` if semantic extraction produces many methods.

That distinction matters because the dominant nonlinear risk is tied to extraction cardinality, not chunk cardinality.

---

## 4. Where quadratic behavior actually exists

## 4.1 Intra-document method consolidation: `O(m^2)`

`science_graphrag/ingestion/method_consolidation.py` performs two all-pairs passes over extracted methods:

1. surface/alias overlap union;
2. embedding-cosine union.

This is explicit pairwise logic over the extracted methods of one paper.

Complexity:

- embedding build: `O(m)`
- pairwise surface pass: `O(m^2)`
- pairwise cosine pass: `O(m^2)`

Overall: `O(m^2)`.

This is the clearest nonlinear step currently reachable from normal ingest.

### Why it matters

Today this is probably acceptable if `m` stays small, which is the common case for one paper. But if prompts drift toward over-extraction of method mentions, the cost can rise sharply even though chunking itself remains linear.

## 4.2 Generic full entity scan: `O(E^2)`

`science_graphrag/dedup/entity_pipeline_common.py` contains a generic pairwise entity scan:

- embed each entity once;
- compare each entity against every later entity;
- auto-merge or queue conflicts based on similarity.

That is a true quadratic scan:

`O(E^2)`

This is not the normal chunk-driven ingest path, but it is part of the dedup subsystem and should be considered a real worst-case mode.

## 4.3 Full work dedup scan: approximately `O(W * k)` application-side

`science_graphrag/dedup/work_dedup_engine.py` does not compare every work against every other work in Python. Instead, it:

- retrieves the vector for each work;
- asks Qdrant for top-k similar works;
- deduplicates repeated pairs with a `seen` set;
- optionally runs an LLM judge for the similarity middle band.

From the application side this is closer to:

- `O(W * k)` candidate handling;
- up to `O(W * k)` LLM judgments in the worst middle-band case.

Current default `work_dedup_max_candidates` is `20`.

This is not quadratic in workspace size unless the search layer itself is replaced by brute-force all-pairs comparison.

## 4.4 Full author dedup scan: approximately `O(A * k)` application-side

`science_graphrag/dedup/author_dedup_engine.py` follows the same pattern:

- create/update one embedding per author;
- search top-k similar authors;
- optionally run LLM adjudication.

Application-side complexity is roughly:

- `O(A)` embedding generation;
- `O(A * k)` candidate handling;
- up to `O(A * k)` LLM calls in the worst middle-band case.

Current default `author_dedup_max_candidates` is `15`.

Again, this is not a workspace-wide all-pairs quadratic scan in Python.

---

## 5. Ingest-time dedup complexity

The ingest-time dedup path is important because it runs during normal document ingestion.

## 5.1 Work dedup during ingest

`enqueue_work_near_duplicate_conflicts_on_ingest(...)` in `science_graphrag/dedup/ingest_conflict_check.py`:

- builds one summary vector for the new work;
- searches top-k similar works in Qdrant;
- optionally runs an LLM same-work judgment on the middle band.

Application-side cost:

- one embedding call for the new work summary;
- `O(k)` candidate inspection;
- up to `O(k)` LLM calls in the worst middle-band case.

This is bounded and not `O(W^2)`.

## 5.2 Author dedup during ingest

`enqueue_author_near_duplicate_conflicts_on_ingest(...)`:

- loops over authors attached to the newly ingested work;
- builds/upserts a summary vector for each new author;
- searches top-k similar authors;
- may run LLM adjudication.

Application-side cost:

`O(a_new * k)`

where `a_new` is the number of authors on the current work.

This is not chunk-quadratic and not workspace-all-pairs.

## 5.3 Entity dedup during ingest

`enqueue_entity_near_duplicate_conflicts_on_ingest(...)` in `science_graphrag/dedup/entity_ingest_conflict_check.py` is the main remaining nonlinear ingest-time component.

For institutions, venues, methods, and datasets it compares entities from the new work against a trimmed workspace entity set:

`O(e_new * E_ws_trim)`

with:

- `e_new`: number of new entities on the just-ingested work;
- `E_ws_trim <= workspace_entity_limit`.

The default `workspace_entity_limit` is `500`.

This means:

- it is nonlinear;
- it can be expensive when one work has many entities and the workspace is large;
- but it is not an unbounded `O(E^2)` full scan in the ingest path.

### Method-specific note

Methods are special here. For method pairs with similarity in the middle band, the code may call `adjudicate_method_pair_llm(...)`.

That means the LLM cost for method ingest-dedup is approximately:

`O(p_mid)`

where `p_mid` is the number of method pairs that survive similarity thresholding and fall into the LLM-adjudication band.

By default `method_ingest_llm_adjudicate` is currently `False`, so this expensive path is opt-in rather than always-on.

---

## 6. LLM cost model by stage

This section answers the "especially everything tied to LLM" part more explicitly.

## 6.1 LLM calls per ingested document

Ignoring retries from transient transport errors, one document can trigger:

1. metadata extraction: `1`
2. authorship extraction: `1`
3. semantic extraction: up to `4`
4. references extraction: about `ceil(r / B_ref)`
5. claims extraction: about `ceil(n / 6)` in the current batch regime
6. work dedup LLM checks on ingest: up to `k`
7. author dedup LLM checks on ingest: up to `a_new * k`
8. method dedup LLM checks on ingest: up to `p_mid`, only when enabled

So the current LLM-heavy part is not driven by chunk-pair comparisons. It is mostly:

- linear batching over chunks for claims;
- linear batching over references for reference extraction;
- candidate-limited judgment calls for dedup.

## 6.2 Where LLM usage can still feel nonlinear in practice

Even when asymptotics are not quadratic in `n`, latency and spend can still rise sharply because several linear terms stack:

- claims extraction grows with chunk count;
- author dedup can multiply by number of authors on the paper;
- reference extraction grows with bibliography size;
- candidate-based LLM dedup can spike if thresholds are too permissive.

So the operational pain may look "nonlinear" to an operator even when the code path is formally linear in chunks.

---

## 7. What is not currently `O(n^2)` in chunk count

The following paths do **not** currently perform chunk-all-pairs work:

- chunk dedup for embedding;
- claims extraction batching;
- chunk embedding generation;
- chunk upsert into Qdrant;
- metadata extraction;
- authorship extraction;
- reference extraction batching;
- work dedup on ingest;
- author dedup on ingest.

This is the core reason the answer to the original question is "mostly no" if the independent variable is chunk count.

---

## 8. Practical risk ranking

From a runtime and scale-risk perspective, the most important current hotspots are:

1. **Intra-document method consolidation (`O(m^2)`)**
   - clear quadratic logic in a normal ingest path;
   - likely safe today if method counts stay small;
   - vulnerable to prompt drift or over-extraction.

2. **Workspace entity ingest checks (`O(e_new * E_ws_trim)`)**
   - not full quadratic in total workspace size, but still a cross-product;
   - can grow if a workspace accumulates many methods/datasets/institutions and the trim limit increases.

3. **Generic full entity scan (`O(E^2)`)**
   - explicit quadratic behavior;
   - dangerous if invoked on large workspaces without stronger pruning or ANN candidate generation.

4. **LLM candidate adjudication in dedup**
   - formally candidate-bounded rather than quadratic in chunks;
   - can still dominate wall-clock and cost if threshold bands are broad.

---

## 9. Recommended follow-up checks

If we want to validate whether this stays safe under real corpus growth, the highest-value next measurements are:

1. Record empirical distributions for:
   - chunks per document,
   - extracted methods per document,
   - authors per work,
   - reference count per work,
   - newly created entities per work.

2. Add per-stage counters and timing histograms for:
   - claims batches per document,
   - reference batches per document,
   - method consolidation input size,
   - ingest-time author dedup candidate count,
   - ingest-time method dedup candidate count.

3. Treat `method_consolidation.py` as the first candidate for algorithmic hardening if method extraction volume rises.

4. Treat `entity_pipeline_common.py` as the first candidate for architectural replacement if full-scan entity dedup must run on larger workspaces.

---

## 10. Final conclusion

For the current implementation, the answer is:

- **Main ingestion path by chunk count `n`: no obvious `O(n^2)` or worse behavior.**
- **Overall ingest + dedup system: yes, it contains real quadratic components, but they are tied to extracted entities or workspace-wide pair scans rather than chunk count itself.**

The most important nuance is this:

> The system is mostly linear in chunks, but not uniformly linear in extracted semantic objects.

That is the real scaling boundary in the current design.
