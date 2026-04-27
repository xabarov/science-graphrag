# MinIO integration and artifact storage roadmap (2026-04-27)

**Status:** proposed architecture and operations roadmap.

**Primary goal:** reduce repository noise and local-host coupling by introducing an explicit object-storage seam for large runtime artifacts, while keeping small canonical benchmark artifacts reviewable in git and structured state in Postgres/Neo4j/Qdrant.

**Trigger:** repository audit on 2026-04-27 found that benchmark/live-debug outputs, OD restore snapshots, and other JSON/JSONL artifacts are currently split across git-tracked `eval/results/`, local `data/`, and process-local file stores. This creates search/navigation noise, machine-specific diffs, and weak durability for multi-worker or multi-host deployments.

---

## 1. Executive summary

MinIO is a good fit for this application, but **not** as a blanket replacement for all local files.

The strongest use case is to introduce a new seam:

1. **Canonical, reviewable artifacts stay in git**:
   - benchmark baselines,
   - small `current-*` inputs for the aggregate gate,
   - gold fixtures and curated specs.
2. **Large runtime artifacts move to object storage (MinIO / S3-compatible)**:
   - live benchmark traces,
   - repair/backfill progress JSONL,
   - heavy case-level benchmark outputs,
   - uploaded raw files and derived ingest artifacts,
   - durable benchmark-run snapshots,
   - optional exports and generated reports.
3. **Structured mutable state stays in databases**:
   - Postgres for job/session metadata and workflow state,
   - Neo4j for graph entities and relationships,
   - Qdrant for vectors.

This gives three benefits:

- cleaner repo and faster agent/code search;
- better multi-host durability than API-host-local disk;
- a deeper, more explicit artifact seam than the current filename-convention approach.

---

## 2. Current storage map

### 2.1 Git-tracked benchmark/results tree

Current benchmark and analysis artifacts are concentrated in:

- `eval/results/`
- `eval/dual_validate/`
- `tests/fixtures/benchmarks/`

Observed issues:

- `eval/results/` mixes canonical artifacts, local debug outputs, live traces, report-facing summaries, and repair JSONL progress.
- Some committed JSON includes absolute local paths and machine-specific context.
- Heavy `case_result.json` / `trace_audit.json` files increase repository noise and search cost.

Key modules/docs using this layout:

- `eval/README.md`
- `scripts/benchmark_aggregator/paths.py`
- `scripts/aggregate_benchmark_metrics.py`
- `science_graphrag/api/benchmark_decision_gate.py`

### 2.2 Local filesystem storage already in the app

The application already has several local-disk seams:

- raw blob storage via `science_graphrag/storage/blobs.py`
- queued ingest uploads under `blob_root/_ingest_queue/`
- derived ingest artifacts under `artifact_root`
- benchmark run history under `data/benchmark_runs`
- ask-session JSON files under `data/ask_sessions`
- runtime settings/secrets JSON under `data/settings`

Important config roots:

- `science_graphrag/config.py`
  - `blob_root = ./data/blobs`
  - `artifact_root = ./data/artifacts`
  - `openrouter_embedding_cache_root = ./data/embeddings_cache`

### 2.3 Databases and stores that should remain authoritative

- **Postgres**: `science_graphrag/storage/models_orm.py`
  - `DocumentRecord`
  - ingest jobs/events/stages
  - dedup queues
  - translations
  - persisted hypotheses
- **Neo4j**: graph truth
- **Qdrant**: vector truth

MinIO should complement these systems, not replace them.

---

## 3. Current problems driving the MinIO proposal

### 3.1 Repo hygiene and agent/search noise

The audit found that `eval/results/` currently combines multiple artifact classes:

- canonical gate inputs,
- historical reruns,
- heavy chat-agent traces,
- OD repair/restore snapshots,
- generated report summaries,
- local-only experiments.

That makes file naming (`current-*`, `latest`, `local-*`, `retest-*`, `*-for-report`) act as a shallow storage interface.

### 3.2 Machine-local coupling

Some JSON artifacts include absolute local paths, workspace ids, temporary file paths, and runtime details. This is especially visible in OD workspace audit/repair artifacts and some benchmark outputs.

That is acceptable for diagnostics, but weak as a git-tracked, cross-machine source of truth.

### 3.3 Weak multi-host durability

Several important runtime outputs are stored only on the API host filesystem:

- uploaded ingest source files,
- extracted markdown and diagnostics,
- benchmark run JSON snapshots,
- ask-session files,
- runtime settings/secrets JSON.

For single-host local development this is workable. For multi-worker or multi-host deployment it becomes fragile.

### 3.4 Misaligned artifact lifecycles

The application currently mixes artifacts with different lifecycles:

- long-lived curated benchmark inputs,
- short-lived queue files,
- operational diagnostics,
- reproducibility snapshots,
- per-run heavy traces.

MinIO helps only if these lifecycles become explicit.

---

## 4. Where MinIO is the best fit

This section is ordered by implementation value, not by theoretical neatness.

### 4.1 Ingest raw uploads and queue payloads

**Current code:**

- `science_graphrag/storage/blobs.py`
- `science_graphrag/api/workspaces.py`
- `science_graphrag/api/ingest/dispatcher.py`
- `science_graphrag/worker/actor.py`

**Current behavior:**

- uploaded files are persisted under local `blob_root`
- queued ingest jobs read from `blob_root/_ingest_queue/{job_id}.{ext}`

**Why MinIO helps:**

- makes ingest queue durable across API restarts and host replacement;
- enables clean producer/worker separation when workers do not share a filesystem;
- fits raw binary object storage very naturally;
- existing blob layout is already close to an object-key model.

**Recommended target:**

- move raw uploads and queued ingest source files to MinIO;
- keep metadata (`document_id`, `sha256`, status, workspace/job ids) in Postgres;
- persist only object keys/ETags/checksums in DB/job rows.

### 4.2 Derived ingest artifacts (`artifact_root`)

**Current code:**

- `science_graphrag/ingestion/_pipeline_impl.py`
- `science_graphrag/ingestion/artifact_layout.py`
- `science_graphrag/api/works/detail.py`
- `docs/adr/022-reader-extracted-body-vs-qdrant-chunks.md`

**Current behavior:**

- canonical `article.md`, `normalized.md`, and diagnostics are written under local `artifact_root`
- read paths assume files exist on the API host

**Why MinIO helps:**

- extracted markdown and diagnostics are durable document artifacts, not ephemeral temp files;
- they can be fetched on demand by any API instance;
- large corpora and re-index operations become less tied to one host filesystem;
- backup/restore becomes cleaner.

**Recommended target:**

- keep canonical relative paths and document-scoped naming;
- replace the local-disk implementation with an object-storage-backed artifact store;
- keep the API contract stable (`artifact_root` becomes a logical root, not necessarily a local path).

### 4.3 Benchmark run snapshots and heavy runtime diagnostics

**Current code:**

- `science_graphrag/api/task_store.py`
- `science_graphrag/api/benchmark.py`
- `scripts/aggregate_benchmark_metrics.py`
- benchmark/chat-agent runners under `eval/` and `scripts/`

**Current behavior:**

- benchmark runs persist JSON snapshots under `data/benchmark_runs`
- many heavy outputs also land in `eval/results/`

**Why MinIO helps:**

- full run JSON and trace-heavy outputs are large and mostly operational;
- object storage is a better fit than git or API-host-local disk;
- makes it easy to separate compact summaries from full payloads.

**Recommended target:**

- persist compact run summaries in Postgres or local cache if needed for fast UI listing;
- store full run payloads, case-level blobs, and trace-heavy artifacts in MinIO;
- add manifest pointers in DB or lightweight summary JSON.

### 4.4 Chat-agent live traces and OD repair/backfill artifacts

**Current examples:**

- `eval/results/chat-agent-live-*`
- `eval/results/chat-agent-roadmap-live-*`
- `eval/results/od-workspace-manifest-latest.json`
- `eval/results/od-claims-gap-audit-latest.json`
- `eval/results/od-claims-backfill-*.jsonl`

**Why MinIO helps:**

- these are high-volume, runtime, machine-specific artifacts;
- they are useful for audit/debugging, but poor git citizens;
- retention/expiration policies make sense here.

**Recommended target:**

- store raw manifests/audits/progress/traces in MinIO;
- optionally keep a small sanitized summary in git or in `docs/analysis` when it must support a review.

### 4.5 Generated report exports and Phoenix evidence snapshots

**Current examples:**

- report-facing JSON/MD in `eval/results/*-for-report.*`
- Phoenix closeout/evidence workflows in `docs/analysis/phoenix-*.md`

**Why MinIO helps:**

- generated raw evidence packages, exported trace snapshots, and large supporting JSON are classic object-storage artifacts;
- docs should summarize them, not necessarily embed/store all raw evidence in git.

**Recommended target:**

- keep small human-readable summaries in git/docs;
- store raw evidence bundles in MinIO with a stable key referenced from the summary.

---

## 5. Where MinIO is useful, but not first priority

### 5.1 Teacher gold and large generated evaluation byproducts

Possible candidates:

- `eval/teacher_gold/`
- large generated compare artifacts
- archived multimodel outputs

These can stay local/git for now, but object storage becomes attractive if:

- regeneration is expensive,
- artifacts are large,
- multiple hosts need access,
- or archival history matters more than line-by-line git review.

### 5.2 Workspace export/import bundles

Not a strong current codepath, but a natural future use:

- workspace ZIP exports,
- graph snapshot export bundles,
- curated evidence packages for review.

These are object-storage-native artifacts and should prefer MinIO over local host paths.

### 5.3 Large temporary benchmark comparisons

If future benchmark UX introduces experiment matrices, bulk compare exports, or downloadable evidence packs, MinIO is a better target than `eval/results/` or local temp files.

---

## 6. Where MinIO should probably NOT be used

### 6.1 Runtime settings and secrets

**Current code:**

- `science_graphrag/settings/repository.py`
- `science_graphrag/settings/secrets.py`

Do **not** move `runtime_settings.json` or `runtime_secrets.json` to MinIO as a primary store.

Reasons:

- secrets do not belong in generic object storage without a stronger secret-management story;
- mutable configuration requires stronger consistency and access control than “write object / read object”;
- a proper DB/secret manager is a better target than MinIO.

### 6.2 Ask sessions

**Current code:**

- `science_graphrag/api/ask_sessions_store.py`

Ask sessions are small, mutable, low-latency user state.

MinIO is a poor primary store for:

- frequent patch/save operations,
- active-session switching,
- conversational state updates.

Better targets:

- Postgres,
- Redis,
- or a dedicated lightweight DB-backed session store.

### 6.3 Embedding caches

**Current code:**

- `science_graphrag/embeddings/openrouter_provider.py`
- `science_graphrag/ingestion/embeddings.py`

Object storage can hold embedding-cache objects, but it is **not** the first optimization target.

Reasons:

- cache hit latency matters;
- embedding cache behavior should first be unified logically across ingest/eval;
- local disk remains a good L1 cache even if MinIO later becomes a shared L2 cache.

### 6.4 Canonical benchmark fixtures and curated gold

Do **not** move these out of git:

- `tests/fixtures/benchmarks/**`
- curated `gold.json`
- small canonical `current-*` / baseline artifacts needed for review and CI reproducibility

They are part of the code-and-fixture contract, not operational object payloads.

---

## 7. Recommended target architecture

### 7.1 Storage classes

Introduce explicit artifact classes:

1. **Canonical**
   - small, curated, reviewable
   - git-tracked
2. **Runtime durable**
   - raw uploads, extracted markdown, benchmark full runs
   - MinIO-backed
3. **Operational diagnostics**
   - traces, repair manifests, JSONL progress, evidence bundles
   - MinIO-backed with retention policy
4. **Structured mutable state**
   - job/session/config metadata
   - Postgres / Redis / Neo4j / Qdrant

### 7.2 Suggested MinIO key layout

Example logical buckets/prefixes:

- `science-raw/ingest-queue/<job_id>/<filename>`
- `science-raw/blobs/raw/<sha256-prefix>/<sha256>`
- `science-artifacts/ingestion/<document_id>/article.md`
- `science-artifacts/ingestion/<document_id>/normalized.md`
- `science-artifacts/ingestion/<document_id>/extraction_diagnostics.json`
- `science-benchmarks/runs/<run_id>/full.json`
- `science-benchmarks/runs/<run_id>/summary.json`
- `science-benchmarks/chat-agent/<run_id>/cases/<case_id>/case_result.json`
- `science-benchmarks/chat-agent/<run_id>/cases/<case_id>/trace_audit.json`
- `science-diagnostics/od/<timestamp>/workspace_manifest.json`
- `science-diagnostics/od/<timestamp>/claims_gap_audit.json`
- `science-diagnostics/od/<timestamp>/claims_backfill.jsonl`
- `science-reports/<report_id>/raw/<artifact>`

Exact bucket naming is less important than the artifact-class split.

### 7.3 Metadata ownership

Keep metadata in the systems already suited for it:

- Postgres stores:
  - object key,
  - checksum,
  - content type,
  - size,
  - lifecycle class,
  - owning run/job/document id.
- MinIO stores:
  - the opaque payload itself.

This avoids trying to query object storage like a database.

---

## 8. Integration roadmap

### Phase 0 — artifact taxonomy and registry seam

**Goal:** stop using filename conventions as the only artifact interface.

Work:

- define artifact classes (`canonical`, `runtime`, `diagnostic`, `report`);
- add a small storage abstraction (`ArtifactStore` / `ObjectStore`) behind current local path usage;
- document which classes are git-tracked vs object-backed;
- sanitize exported JSON that should remain committable.

Acceptance:

- new code writes through a storage seam, not directly through ad-hoc path strings;
- docs and runners use the same class vocabulary.

### Phase 1 — raw blob and ingest queue cutover

**Goal:** make upload/worker flow multi-host safe.

Work:

- replace local `_ingest_queue` file dependency with object storage;
- keep job metadata and claim/terminal state in Postgres;
- update worker to fetch queued source object by key.

Files involved:

- `science_graphrag/storage/blobs.py`
- `science_graphrag/api/workspaces.py`
- `science_graphrag/api/ingest/dispatcher.py`
- `science_graphrag/worker/actor.py`

Acceptance:

- API and worker can run on separate hosts without a shared filesystem;
- job recovery after API restart does not depend on host-local queue files.

### Phase 2 — ingest artifact cutover

**Goal:** move canonical document artifacts to object storage without changing reader semantics.

Work:

- back `artifact_root` with object storage;
- preserve document-scoped paths from `artifact_layout.py`;
- adapt readers/endpoints to fetch through storage abstraction.

Files involved:

- `science_graphrag/ingestion/_pipeline_impl.py`
- `science_graphrag/ingestion/artifact_layout.py`
- `science_graphrag/api/works/detail.py`

Acceptance:

- extracted-body API works across hosts;
- resume/re-embed flows still resolve `normalized.md` correctly.

### Phase 3 — benchmark runtime artifact cutover

**Goal:** remove heavy runtime artifacts from git/local-only storage.

Work:

- store full benchmark run payloads in MinIO;
- keep small run summaries locally or in DB;
- move chat-agent heavy traces and OD repair artifacts out of `eval/results/`;
- keep only compact canonical artifacts in git.

Files involved:

- `science_graphrag/api/task_store.py`
- `scripts/aggregate_benchmark_metrics.py`
- `scripts/benchmark_aggregator/paths.py`
- relevant `eval/*/runner.py` and `scripts/*`

Acceptance:

- `eval/results/` contains only canonical/report-facing artifacts;
- large live artifacts are referenced via manifest/object key.

### Phase 4 — retention, lifecycle, and exports

**Goal:** make storage operationally manageable.

Work:

- add TTL/retention classes for diagnostic artifacts;
- define promotion path from runtime object -> review summary -> canonical artifact if needed;
- add export helpers for evidence packages.

Acceptance:

- stale diagnostic runs expire cleanly;
- promoted artifacts are explicit and reviewable.

---

## 9. Proposed application-specific decisions

### 9.1 Keep in git

- benchmark fixtures and curated gold
- compact baseline/current benchmark artifacts used by CI and gate logic
- docs and sanitized summaries

### 9.2 Move to MinIO early

- raw uploaded documents and queue payloads
- extracted markdown and diagnostics
- benchmark full-run payloads
- chat-agent trace-heavy results
- OD restore/backfill JSON/JSONL

### 9.3 Keep in DB / not in MinIO

- job state
- sessions
- runtime editable settings
- secrets
- graph/vector state

---

## 10. Risks and caveats

### 10.1 Do not create “MinIO everywhere”

The main failure mode is cargo-culting object storage into every file-like concern. The app still needs:

- fast local/process caches,
- structured state in DB,
- reviewable artifacts in git.

### 10.2 Reader/resume code currently assumes local paths

Several codepaths directly build `Path(settings.artifact_root) / ...`.

That means the first MinIO step should be an abstraction seam, not direct string substitution.

### 10.3 Settings/secrets need a different modernization path

Moving runtime settings/secrets to MinIO would conflate object storage with secret/config management. This should be a separate decision, likely toward DB + secret manager instead.

### 10.4 Benchmark aggregator still relies on canonical file paths

`scripts/benchmark_aggregator/paths.py` and `scripts/aggregate_benchmark_metrics.py` currently depend on committed path conventions. MinIO integration should preserve a compact canonical layer rather than forcing the aggregator to query object storage for everything.

---

## 11. Recommended next steps

### Immediate

1. Approve the storage split:
   - git canonical,
   - MinIO runtime/diagnostic,
   - DB structured state.
2. Implement a minimal object-storage abstraction behind:
   - `BlobStore`,
   - ingest queue paths,
   - artifact-root reads/writes.
3. Stop committing new OD repair/live trace artifacts to `eval/results/`.

### Short-term

1. Convert ingest queue and raw uploads first.
2. Convert `artifact_root` second.
3. Convert benchmark full-run and heavy trace artifacts third.

### Explicit non-goal for the first wave

Do not move:

- ask sessions,
- runtime settings,
- runtime secrets,
- benchmark fixtures/gold,
- Qdrant/Neo4j/Postgres data.

---

## 12. Final recommendation

MinIO should be adopted as the application's **durable object store for large runtime artifacts and document payloads**, not as a universal persistence layer.

The highest-value rollout order is:

1. ingest queue + raw blobs,
2. ingest artifacts,
3. benchmark full runs and heavy diagnostics,
4. optional report/export bundles.

If implemented this way, MinIO will materially improve:

- durability,
- deployment flexibility,
- artifact hygiene,
- benchmark operability,
- and codebase navigability.

If implemented as “replace files with S3 calls everywhere,” it will add infrastructure cost without solving the real seam problem.
