# Benchmark panel: research-first redesign plan (2026-04-27)

**Doc status:** `reference`

**Read hint:** benchmark UI product plan; not the agent engine backlog.

**Status:** proposed product/UX analysis and phased implementation plan. **Phase 0, Phase 1, Phase 2 (client slice), Phase 4 (benchmark-aware case inspector), Phase 3 (matrix / overview slice), and Phase 5 (legacy demotion)** are implemented in the UI (see **Implementation status (agent handoff)**). Optional backend **`run-group`** API still TBD.

**Primary goal:** redesign the benchmark panel so it supports the benchmark program that the final report actually argues for: **run one experiment or a batch, compare model/method variants, and read the resulting metrics without needing to mentally translate internal QA machinery**.

**Key alignment source:** [`docs/report/nlp-advanced-final-report-2026-04-26.md`](../report/nlp-advanced-final-report-2026-04-26.md)

**Current UI surface reviewed:**
- `ui/src/pages/BenchmarkPage/BenchmarkPage.jsx`
- `ui/src/pages/BenchmarkPage/RunTab.jsx`
- `ui/src/pages/BenchmarkPage/ResultsTab.jsx`
- `ui/src/pages/BenchmarkPage/CompareTab.jsx`
- `ui/src/pages/BenchmarkPage/CasesTab.jsx`
- `ui/src/pages/BenchmarkPage/workbench/BenchmarkWorkbenchRunPanel.jsx`
- `ui/src/pages/BenchmarkPage/caseInspector/` (Phase 4 — inspector shell + family panels)
- `ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx`

**Related prior spec:** [`docs/specs/benchmark-workbench-ui-plan.md`](../specs/benchmark-workbench-ui-plan.md)

---

## Implementation status (agent handoff)

**Last updated:** 2026-04-28 (Phase 5 legacy demotion: Analysis `overview` default, tools menu, Run Lab launcher advanced block, trust/Results copy).

### Done: Phase 0 + Phase 1 (UI)

The following matches **section 10** (`Phase 0`, `Phase 1`). See the next subsection for **Phase 2**.

| Area | Where in code / docs |
|------|------------------------|
| Experiment catalog + packs | [`ui/src/pages/BenchmarkPage/experimentCatalog.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.js) — `EXPERIMENTS`, `EXPERIMENT_PACKS`, report-critical set, `runnableSurface` (`ui` / `cli_only` / `catalog`), metric/scope/compare-mode i18n keys. |
| Tab routing + legacy deep links | Same file: `parseBenchmarkTabQuery`, `mergeBenchmarkTabIntoSearchParams`, `TAB_CANONICAL`. Legacy named tabs (`launch`, `workbench`, `results`, `compare`, `cases`) and **numeric tab 0–4 (old order)** still resolve. Canonical URLs use `overview`, `experiments`, `run-lab`, `analysis`, `cases` plus `analysisView` (`overview` default, `results`, `compare`, `workbench`) when on Analysis. |
| Page shell | [`ui/src/pages/BenchmarkPage/BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) — tabs Overview / Experiments / Run Lab / Analysis / Cases; URL sync for `run` / `case` when those query keys exist (avoids wiping `benchmark:lastRunId` on first paint without `run`). **Phase 4 addendum:** on Analysis (`tabIndex===3`), absence of `?case=` clears `selectedCaseId` (no stale case on Results/Compare/Workbench); fixture-first workbench keeps `run` empty when only `case` (+ `caseFamily`) is set. |
| Overview + diagnostics | [`ui/src/pages/BenchmarkPage/BenchmarkOverviewTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkOverviewTab.jsx) — report-critical cards, recent runs (`listBenchmarkRuns`), **TrustSignalPanel** in collapsed diagnostics block (not hero). |
| Experiments catalog tab | [`ui/src/pages/BenchmarkPage/BenchmarkExperimentsTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkExperimentsTab.jsx). |
| Analysis tab (shell) | [`BenchmarkAnalysisTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisTab.jsx) — overview + matrix; legacy tools via menu (see **Done: Phase 3 slice + Phase 5**). |
| i18n | [`ui/src/i18n/messages/en/partBenchmarkPage.js`](../../ui/src/i18n/messages/en/partBenchmarkPage.js), [`ui/src/i18n/messages/ru/partBenchmarkPage.js`](../../ui/src/i18n/messages/ru/partBenchmarkPage.js) — `benchmarkPage.pageTitle` (= Benchmark Lab), tab labels, `benchmarkCatalog.*`. |
| Entry links aligned | [`ui/src/pages/BenchmarkPage/caseDetail/CaseDetailArtifactsSection.jsx`](../../ui/src/pages/BenchmarkPage/caseDetail/CaseDetailArtifactsSection.jsx) (`tab=analysis&analysisView=workbench&run=…`), [`ui/src/pages/AdminEntryPage.jsx`](../../ui/src/pages/AdminEntryPage.jsx) (secondary benchmarks link). |
| Tests | [`ui/src/pages/BenchmarkPage/experimentCatalog.test.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.test.js); [`ui/src/routeCompatibility.test.js`](../../ui/src/routeCompatibility.test.js) extended for canonical benchmark query preservation. |

### Done: Phase 2 — client slice (UI, 2026-04-27)

Matches **section 10 — Phase 2** deliverables **except** a backend `run-group` API (still optional). Matrix read surface is covered by the **Phase 3 UI slice** (2026-04-28; see Implementation status). Grouped runs are **sequential child `runBenchmark` calls** in the browser, not a server-side batch job.

| Area | Where in code / docs |
|------|------------------------|
| Run Lab query model | `experimentCatalog.js`: `parseRunLabQueryFromSearchParams`, `RUN_MODE_GROUPED`, helpers for `experiment` / `runMode` / `pack` on **Run Lab** URL. |
| Catalog → Run Lab entry | `BenchmarkExperimentsTab.jsx`, `BenchmarkOverviewTab.jsx` — CTAs merge preset + `tab=run-lab` (+ optional `pack`, `runMode=grouped`). |
| Launcher preset from experiment | [`useRunTab.js`](../../ui/src/pages/BenchmarkPage/useRunTab.js) — effect applies `getLauncherPresetForExperiment(experimentId)` into `launcherPrefs` when `?experiment=` is present (with de-dupe ref by experiment+pack). **Phase 5:** Run Lab heading is experiment-first when `?experiment=`; API family lives under **Advanced** accordion in [`BenchmarkLauncherPanel.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkLauncherPanel.jsx). |
| Grouped batch UI + orchestration | [`RunLabGroupedExecutionPanel.jsx`](../../ui/src/pages/BenchmarkPage/RunLabGroupedExecutionPanel.jsx), [`useBenchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunGroup.js) (polling, finalize, handoff), [`benchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/benchmarkRunGroup.js) (jobs payload, `aggregateGroupStatus`, LS keys). |
| Single vs grouped wiring | [`RunTab.jsx`](../../ui/src/pages/BenchmarkPage/RunTab.jsx), [`RunTabCurrentRunSection.jsx`](../../ui/src/pages/BenchmarkPage/RunTabCurrentRunSection.jsx), [`BenchmarkLauncherPanel.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkLauncherPanel.jsx) (`startRunDisabled` when `runMode=grouped`). |
| Analysis handoff for a group | `BenchmarkPage.jsx` — `onOpenAnalysisWithGroup(runIds)` merges `run` + `runs` query params so Compare/Results can consume multiple IDs where supported. |
| Persistence | `benchmarkRunGroup.js`: `benchmark:lastRunGroup`, recent compare setups (`loadRecentCompareSetups` / `pushRecentCompareSetup`); on finalize, `benchmark:lastRunId` is set to the **first child `runId` in UI order** (job order) for continuity with single-run deep links. |
| Tests | [`benchmarkRunGroup.test.js`](../../ui/src/pages/BenchmarkPage/benchmarkRunGroup.test.js) alongside extended `experimentCatalog.test.js`. |

### Done: Phase 4 — Benchmark-aware case inspector (UI + API, 2026-04-27 / follow-ups 2026-04-28)

Matches **section 10 — Phase 4** (explanatory case surface; raw demoted; evidence links; compare-aware entry). **Not** merged: `CaseDetailDialog` remains for fixture “Preview”; Cases tab adds **Open inspector** into the same Workbench URL model (fixture-first when no `run`).

| Area | Where in code / notes |
|------|------------------------|
| API: `highlights` + `evidence_links` on run case detail | [`science_graphrag/api/benchmark.py`](../../science_graphrag/api/benchmark.py) — `_build_inspector_highlights`, `_build_evidence_links`, wired into `get_benchmark_run_case_detail`; keeps `comparison` / `metrics` / `diagnostics` for compatibility. |
| Smoke test | [`tests/test_api_smoke.py`](../../tests/test_api_smoke.py) — `test_benchmark_run_case_detail_smoke` asserts `highlights` + `evidence_links`. |
| Inspector shell (highlights-first, raw accordion) | [`ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx) — compare banner, evidence rail, nested accordions for article/gold/prediction/metrics/diff/diagnostics; safe `formatComparisonCellValue`; default `onOpenRun`. |
| Family panels + registry | [`Layer1CaseInspectorPanel.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/Layer1CaseInspectorPanel.jsx), [`Layer2CaseInspectorPanel.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/Layer2CaseInspectorPanel.jsx), [`GraphCaseInspectorPanel.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/GraphCaseInspectorPanel.jsx) (reuses [`CaseGraphExpectationsPanel.jsx`](../../ui/src/pages/BenchmarkPage/caseDetail/CaseGraphExpectationsPanel.jsx)), [`caseInspectorRegistry.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/caseInspectorRegistry.jsx). |
| Data hook (run + fixture) | [`useBenchmarkCaseInspectorData.js`](../../ui/src/pages/BenchmarkPage/caseInspector/useBenchmarkCaseInspectorData.js), [`benchmarkCaseInspectorModel.js`](../../ui/src/pages/BenchmarkPage/caseInspector/benchmarkCaseInspectorModel.js) — fixture catalog shape + `buildEvidenceLinksFromArtifacts`; **`loadGenRef`** avoids stale async flipping `loading` / detail. |
| Workbench layout | [`BenchmarkWorkbenchRunPanel.jsx`](../../ui/src/pages/BenchmarkPage/workbench/BenchmarkWorkbenchRunPanel.jsx) — case list + inspector shell only (no default three-column JSON wall). [`BenchmarkWorkbenchTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkWorkbenchTab.jsx) — fixture-only path when URL has `case` but no `run`. |
| Navigation / URL contract | [`BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) — `openWorkbench(runId, caseId, opts)` with `caseFamily`, `cmpBaseline`, `cmpMetric` (encoded); `openCaseFromCatalog`; **Analysis tab (`tabIndex===3`): if `case` absent in query → `selectedCaseId=null`** (stale case cleared on Results/Compare/Workbench); **workbench fixture-first** still forces `run=null` when `case` present without `run`. |
| Analysis tab wiring | [`BenchmarkAnalysisTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisTab.jsx) — `caseFamily` + `compareContext` from search params → Workbench; forwards third arg on `onOpenWorkbench`. |
| Results / Compare entrypoints | [`BenchmarkRunCasesTable.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkRunCasesTable.jsx) — `onOpenWorkbench(runId, caseId)` (fixed signature). [`CompareDeltaTable.jsx`](../../ui/src/pages/BenchmarkPage/CompareDeltaTable.jsx) + [`CompareTab.jsx`](../../ui/src/pages/BenchmarkPage/CompareTab.jsx) — baseline + metric into Workbench open. |
| Cases tab | [`CasesTab.jsx`](../../ui/src/pages/BenchmarkPage/CasesTab.jsx) — `onOpenCaseInWorkbench` → Analysis Workbench fixture-first; i18n `benchmark.cases.*`. |
| i18n (inspector) | [`ui/src/i18n/messages/en/partBenchmarkTabs.js`](../../ui/src/i18n/messages/en/partBenchmarkTabs.js), [`ru/partBenchmarkTabs.js`](../../ui/src/i18n/messages/ru/partBenchmarkTabs.js) — `benchmark.inspector.*`. |
| **Explicitly deferred (per Phase 4 scope boundary)** | No new read API for committed `eval/results/*.json`; no Phoenix/trace explorer until runners serialize trace refs; `CaseDetailDialog` not removed (two entry points: Preview vs inspector). |

### Done: Phase 3 slice + Phase 5 — Analysis matrix default + legacy demotion (UI, 2026-04-28)

| Area | Where in code / notes |
|------|------------------------|
| Matrix + session | [`BenchmarkAnalysisOverview.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisOverview.jsx), [`BenchmarkVariantMatrix.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkVariantMatrix.jsx), [`useBenchmarkAnalysisSession.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkAnalysisSession.js), [`benchmarkAnalysisModel.js`](../../ui/src/pages/BenchmarkPage/benchmarkAnalysisModel.js). |
| `analysisView=overview` default | [`experimentCatalog.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.js) — `normalizeAnalysisView`, `LEGACY_ANALYSIS_TOOL_VIEWS`; [`BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) navigates to Analysis with overview unless a legacy tool is requested. |
| Legacy tools demoted | [`BenchmarkAnalysisTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisTab.jsx) — Menu **More tools** instead of equal MUI Tabs; **Back to matrix** when a tool is open. |
| Run Lab launcher | [`BenchmarkLauncherPanel.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkLauncherPanel.jsx) — family selector + env overrides under Accordion **Advanced**; i18n family labels; primary card title “Run configuration”. [`RunTab.jsx`](../../ui/src/pages/BenchmarkPage/RunTab.jsx) — experiment title when `?experiment=`. |
| Trust + Results copy | [`TrustSignalPanel.jsx`](../../ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx) — `decisionChipSxDemoted` + operational caption; [`ResultsTab.jsx`](../../ui/src/pages/BenchmarkPage/ResultsTab.jsx) — i18n empty state (Run Lab). |
| Cases | [`CasesTab.jsx`](../../ui/src/pages/BenchmarkPage/CasesTab.jsx) — fixture dialog vs workbench hint + button labels (`benchmark.cases.*`). |

### Notes for the **next** agent (remaining gaps)

1. **Phase 4 polish:** optional gold-source toggle in fixture-only inspector (parity with `CaseDetailDialog` teacher/curated), or fold Preview into inspector only if product wants one surface.
2. **Phase 3 backend / product:** optional normalized `primary_metrics` / scorecards from API (section 9.4); richer drill from matrix cell to worst cases without opening legacy Compare manually.
3. **CLI-only catalog rows** are unchanged: UI documents and deep-links; no `experiment_id` persisted on run records until backend chooses to add it (section 9.2 / Phase 2 backend follow-up).
4. **Optional backend `run-group`:** if sequential browser starts become fragile (rate limits, tab closed mid-batch, audit), implement server-side batch + idempotent group id per section 10 Phase 2 “Backend follow-up”; then thin the frontend loop in `useBenchmarkRunGroup`.
5. **Backlog:** [`docs/backlog/refactor-frontend.md`](../../docs/backlog/refactor-frontend.md) — *Benchmark panel* item updated for Phase 5; next meaningful update is normalized metrics API or `run-group`.
6. **Trust:** still [`useBenchmarkSummary`](../../ui/src/hooks/useBenchmarkSummary.js) + `TrustSignalPanel`; diagnostics-only presentation on Overview.

---

## 1. Why this document exists

The benchmark UI has improved a lot as an internal console, but it is still shaped around a **developer/QA workflow**:

- launch a `layer1` or `layer2` run;
- inspect trust signal / decision gate status;
- open raw-ish run details;
- compare two runs within one family;
- browse fixtures.

That is no longer the main product question.

From the final report, the benchmark program is now presented as a **research and evaluation surface** with a small set of meaningful experiment families:

1. extraction quality for GraphRAG (`Layer-1`, `Layer-2`, graph `CITES`);
2. retrieval quality (`workspace_scoped_live`, `hybrid_ablation_live`);
3. graph reasoning quality (`multihop_v2`);
4. claims quality (`claims production`, `claims_paraphrase`);
5. end-to-end agent quality (`agent_tools_live`);
6. model comparison and later method comparison across those experiments.

So the benchmark panel should stop behaving primarily like a gate dashboard and start behaving like an **experiment lab + analysis workbench**.

---

## 2. Product direction from the final report

The report implies four strong product requirements.

### 2.1 The primary unit is not "family", but "experiment"

The report is written in terms of experiments such as:

- `Layer-1 nightly`
- `Layer-2 semantic`
- `workspace_scoped_live`
- `hybrid_ablation_live`
- `multihop_v2`
- `claims_paraphrase`
- `agent_tools_live`

These are the units a human wants to reason about.

`layer1` / `layer2` / `graph` are implementation families, useful internally, but too low-level for the top-level UX.

### 2.2 The primary question is not "go / no-go", but "what changed and why?"

The report explicitly keeps weaker results visible because they are informative. That means the benchmark panel should optimize for:

- comparing variants;
- understanding trade-offs;
- seeing where a model is stronger or weaker;
- drilling down from aggregate metrics to worst cases;
- reading metric definitions in context.

Nightly `GO / NO-GO` and trust-gate decisions still matter operationally, but they are **secondary** for this surface.

### 2.3 Batch execution must include both "one run" and "matrix runs"

The user goal is not only "run one benchmark", but:

- run one experiment on one model;
- run one experiment on multiple models;
- run a group of experiments on one model;
- later run multiple methods/approaches on the same experiment pack.

This is closer to an experiment matrix than to a single-run launcher.

### 2.4 Metrics must be interpretable by benchmark type

The report already defines the metric semantics:

- extraction: macro P/R/F1, ROUGE-L, `failed_count` as engineering regression signal;
- retrieval: `hit_count`, `hit@K`, `MRR`, forbidden-violation checks;
- graph reasoning: `recall`, `precision`;
- claims: `precision`, `recall`, `F1`, plus diagnostics;
- agent: judge score and latency.

The UI should therefore present metrics grouped by **evaluation purpose**, not by whatever JSON fields happen to exist in a run payload.

---

## 3. Current-state diagnosis

## 3.1 What is already good

The current panel already has several strong foundations:

1. benchmark runs are persistent and queryable;
2. the backend already supports model-aware run configuration;
3. run summary, paginated cases, case detail, and compare endpoints exist;
4. workbench drill-down exists for case-level inspection;
5. graph expectations preview exists for graph artifacts;
6. **(2026-04-27+)** run case detail API exposes `highlights` / `evidence_links`; Workbench uses a **benchmark-aware inspector** (explanation-first, raw payloads nested) with unified entry from Results, Compare, and Cases.

This is important: the problem is not lack of infrastructure. The problem was mostly **information architecture and product framing**; **Phase 3 (matrix slice) and Phase 5 (legacy demotion) are now addressed in the UI** (2026-04-28), with backend scorecards and optional `run-group` API still ahead.

## 3.2 Main mismatches

### A. The page mixes too many products at once

`BenchmarkPage` currently combines:

- launch control panel;
- trust / decision gate dashboard;
- run history;
- run comparison;
- fixture catalog;
- case workbench.

These are different jobs with different mental models.

Result: the page feels capable, but not coherent.

### B. The top navigation is implementation-first, not researcher-first

Current tabs:

- Launch
- Workbench
- Results
- Compare
- Cases

This organization assumes the user already understands the system internals. It does not answer:

- what experiments exist?
- which ones matter for the report?
- what should I run to compare models?
- which metrics should I read for this experiment?

### C. Trust signal is overexposed for this use case

`TrustSignalPanel` sits at the top of the page and frames the experience around decision status and phantom detection. That is useful for benchmark governance, but it biases the whole page toward a gate-review console.

For the report-aligned workflow, the first question should instead be:

> Which experiment do I want to run or compare?

### D. Run launch is still family-centric

The launcher still begins with:

- `layer1`
- `layer2`
- `graph`

But the report and the intended future usage are closer to:

- extraction pack
- retrieval pack
- graph reasoning pack
- claims pack
- agent pack
- custom comparison pack

### E. Results are still too summary-light for research comparison

`ResultsTab` shows a generic table with compact metrics, but it does not provide:

- experiment-aware KPI cards;
- latest-best-per-experiment snapshot;
- model-vs-experiment matrix;
- "what regressed / improved" across multiple experiments;
- a report-friendly overview of the benchmark program.

### F. Compare is run-to-run, not experiment-analysis-first

The existing compare tab is useful, but it is still framed as:

- choose baseline run;
- choose current run;
- inspect metric deltas.

The more useful framing for this panel is:

- choose an experiment or experiment pack;
- compare variants (models / methods);
- see winners, losers, and trade-offs;
- drill down to the cases that explain the delta.

### G. Case workbench is better than before, but still raw for explanation-heavy workflows

The workbench still leans heavily on:

- raw markdown;
- raw JSON payloads;
- generic diff tables.

That is fine for development, but for model/method analysis we need stronger semantic structure:

- benchmark-specific drill-down cards;
- metric explanations;
- highlighted misses/extras;
- case-level rationale for the aggregate score.

### 3.3 Research chat vs Benchmark Lab (shared explainability path)

**Benchmark Lab** and **research chat** are different surfaces, but the same product story is: **answer → evidence → inspect run → trace review**. Without a shared correlation model, users see visually similar “runs” (benchmark cases, chat turns, tool traces) that do not stitch together.

Shared observability fields (conceptual contract):

- **`thread_id`**: stable conversation key for chat turns and session memory.
- **`phoenix_trace_id`**: OTel trace hex for one agent turn (must remain populated under `PHOENIX_TRACE_SCOPE=extraction_llm` for agent allowlisted spans — see `science_graphrag/observability/spans/decorators.py`).
- **Run artifacts / benchmark evidence**: persisted benchmark `run_id`, case ids, and judge payloads on the Lab side.
- **Evidence links**: citations and `tool_trace` in chat; benchmark workbench panels on the Lab side.

**Risk:** two polished UIs with no explicit link between a chat turn’s `tool_trace`, a benchmark case’s artifacts, and the Phoenix trace for the same underlying retrieval stack. Phase 4+ analysis work should treat **chat trace review** as a first-class sibling to benchmark case drill-down (same mental model: prove *why* the system answered the way it did).

---

## 4. Product requirements for the redesigned panel

The redesigned benchmark panel should support the following user jobs.

## 4.1 Job A — Run a single experiment quickly

Examples:

- "Run `claims_paraphrase` on Mistral"
- "Run `agent_tools_live` on the default extraction model"
- "Run `workspace_scoped_live` only on a selected subset"

Required UX:

- one-click entry from the experiment card;
- visible model/variant selector;
- clear case scope selector;
- obvious output destination in run history.

## 4.2 Job B — Run a comparison batch

Examples:

- "Run the extraction pack on 2 models"
- "Run retrieval + multihop on one model"
- "Compare model A vs model B on the report-critical experiments"

Required UX:

- matrix/batch builder;
- named run group or experiment session;
- progress at both group level and child-run level;
- aggregated compare view after completion.

## 4.3 Job C — Understand metrics without opening raw JSON

Required UX:

- benchmark-aware KPI cards;
- small metric glossary inline;
- "why this metric matters" description per experiment;
- case table sorted by the most informative failure metric.

## 4.4 Job D — Compare variants and interpret trade-offs

Required UX:

- model/method comparison matrix;
- deltas by experiment;
- deltas by metric family;
- best/worst cases that explain the aggregate movement.

## 4.5 Job E — Drill down to evidence

Required UX:

- open one case directly from a compare cell or a run report;
- view article excerpt, gold expectation, prediction, and benchmark-specific diff;
- preserve access to raw JSON as secondary detail, not primary presentation.

## 4.6 Job F — Correlate chat turns with external audit (shared observability)

Required product behavior (cross-surface, not only Benchmark Lab):

- chat responses expose **inspectable** tool traces and, when configured, a **Phoenix deep link** or an honest **trace id hint** (UI requires `VITE_PHOENIX_PROJECT_ID` for a stable `/projects/{id}/traces/...` URL);
- benchmark Analysis / case drill-down and chat “Inspect run” follow the **same** high-level path: grounded answer, evidence payload, optional Phoenix trace;
- documentation and runbooks state explicitly when `phoenix_trace_id` is expected to be empty (misconfiguration) vs intentionally suppressed.

---

## 5. Proposed information architecture

## 5.1 Replace the current tabs with a research-first structure

Recommended top-level surfaces:

1. **Overview**
2. **Experiments**
3. **Run Lab**
4. **Analysis**
5. **Cases**

### 1. Overview

Purpose: answer "what is the state of the benchmark program?" without forcing the user into dev-only trust details.

Should show:

- report-critical experiment cards;
- latest result for each experiment;
- latest compare session;
- shortcuts to rerun and compare;
- optional secondary diagnostics banner for trust / runtime warnings.

### 2. Experiments

Purpose: browse experiment definitions, not just fixture families.

Each experiment card should include:

- experiment id and human title;
- what it measures;
- main metrics;
- current latest result;
- recommended scope (`single`, `suite`, `report-critical`, etc.);
- actions: `Run`, `Compare`, `Open latest`.

### 3. Run Lab

Purpose: create one run or a matrix run.

Modes:

- single run;
- batch by multiple experiments;
- batch by multiple variants;
- matrix: experiments × variants.

### 4. Analysis

Purpose: compare variants and interpret results.

Core elements:

- experiment × variant score matrix;
- per-experiment delta panels;
- metric-family filters;
- links to case-level drill-down.

### 5. Cases

Purpose: keep the fixture and artifact browser, but as a secondary surface.

This tab remains useful for fixture maintenance, but it should no longer define the benchmark product mentally.

---

## 6. Proposed domain model for the UI

The redesign becomes much simpler if the frontend stops treating benchmark data as only `family + run`.

Recommended UI concepts:

### 6.1 Experiment definition

An experiment definition should expose:

- `experiment_id`
- title
- family
- benchmark type (`extraction`, `retrieval`, `graph_reasoning`, `claims`, `agent`)
- default case selector / tier
- primary metrics
- secondary metrics
- report relevance
- metric interpretation copy

Examples:

| Experiment ID | Family | Benchmark type | Primary metrics |
| --- | --- | --- | --- |
| `layer1_nightly` | `layer1` | extraction | macro slot metrics, `failed_count` |
| `layer2_semantic` | `layer2` | extraction | methods/datasets P/R/F1, `failed_count` |
| `workspace_scoped_live` | retrieval | retrieval | `forbidden_violation_count`, answer quality |
| `hybrid_ablation_live` | retrieval | retrieval | `hit_count`, MRR |
| `multihop_v2` | graph | graph_reasoning | recall, precision |
| `claims_paraphrase` | claims | claims | precision, recall, F1 |
| `agent_tools_live` | agent | agent | judge score, latency |

### 6.2 Variant

A variant is the thing being compared:

- model profile
- explicit model id
- method / strategy id (future)
- optional runtime knobs

The important shift is this:

> today the UI is model-aware, but not truly variant-aware.

It should become variant-aware now so that later "different extraction or IR methods" fit naturally.

### 6.3 Run group / experiment session

A run group should represent a user intention such as:

- "April extraction compare"
- "Report refresh"
- "Mistral vs DeepSeek retrieval pack"

It contains multiple child runs and gives the analysis page a natural aggregation unit.

---

## 7. Proposed UX behavior

## 7.1 Overview page

Recommended layout:

- top summary strip:
  - latest report-critical results
  - latest compare session
  - runs in progress
- experiment grid:
  - Extraction
  - Retrieval
  - Graph reasoning
  - Claims
  - Agent
- secondary diagnostics drawer:
  - trust signal
  - phantom / mock warnings
  - decision-gate details

This keeps governance visible without letting it dominate the page.

## 7.2 Experiments page

Each experiment card should answer five questions immediately:

1. What does it test?
2. Why does it matter?
3. Which metrics matter?
4. What are the latest numbers?
5. What can I run next?

Recommended actions:

- `Run now`
- `Compare variants`
- `Open latest report`
- `Inspect worst cases`

## 7.3 Run Lab

The run builder should have two explicit modes.

### Mode A. Single run

Form:

- experiment
- variant
- scope
- optional label

### Mode B. Compare batch

Form:

- experiment pack or selected experiments
- one or more variants
- scope
- session label

Output:

- one parent session row;
- child runs listed underneath;
- progress bar for session and per-run states.

## 7.4 Analysis page

This should become the real home of comparison.

Recommended sections:

### A. Variant matrix

Rows: experiments  
Columns: variants  
Cells: primary metric summary + delta vs baseline

### B. Trade-off summary

Example prompts answered visually:

- best extraction model
- best retrieval model
- best overall report pack
- fastest acceptable agent model

### C. Explainers

For a selected cell:

- aggregate metrics;
- top improved cases;
- top regressed cases;
- links into case workbench.

## 7.5 Case workbench

Keep the current three-pane spirit, but make the center and right panes benchmark-aware.

Per-benchmark-type adaptations:

- **Extraction:** field groups, authorship matching, references coverage, failed contract checks.
- **Retrieval:** expected hits, returned hits, top-K quality, violations.
- **Claims:** gold statements, predicted statements, misses/extras, paraphrase diagnostics.
- **Agent:** prompt, answer, citations, judge feedback, latency, trace link.
- **Research chat (parallel requirement):** same “evidence + trace” affordances as agent benchmark cases — tool trace normalization, `phoenix_trace_id`, and Inspect run must not diverge in naming or empty-trace behavior from Lab expectations.

Raw JSON should remain available behind a `Raw payload` toggle.

---

## 8. What should be removed, demoted, or reframed

## 8.1 Demote trust/decision gate from the top hero

Recommendation:

- remove `TrustSignalPanel` from the top of the default landing view;
- move it into:
  - `Overview -> Diagnostics`, or
  - a collapsible side panel / drawer.

Reason:

- the benchmark panel is no longer primarily a release gate dashboard;
- the user explicitly does not want nightly `Go / No go` to dominate this surface.

## 8.2 Demote raw family selection

`layer1` / `layer2` / `graph` should remain available, but mostly as metadata or advanced filtering.

Primary selectors should be:

- experiment
- experiment pack
- variant
- scope

## 8.3 Demote raw fixture browsing

The `Cases` view still matters, but it should not be the user’s first conceptual step when the real job is experiment comparison.

---

## 9. Backend/API gaps for the redesign

The redesign is mostly frontend/product work, but several backend additions would make it much stronger.

## 9.1 Add experiment catalog endpoints

Recommended new endpoint family:

- `GET /v1/benchmark/experiments`
- `GET /v1/benchmark/experiments/{experiment_id}`

Each entry should define:

- title and description;
- family and benchmark type;
- default selectors;
- primary/secondary metrics;
- report-critical flag;
- whether batch compare is supported.

## 9.2 Add run group / batch execution support

Recommended addition:

- `POST /v1/benchmark/run-groups`

Request shape:

- selected experiments
- selected variants
- scope / case selector
- label

Response shape:

- group id
- child run ids
- group status

This is the natural backend surface for "one benchmark or groups".

## 9.3 Add experiment-oriented compare summaries

Existing run-to-run compare is useful but not sufficient.

Recommended additions:

- compare by run group;
- compare by experiment across variants;
- compare latest results for one experiment.

## 9.4 Normalize metric schemas for UI consumption

The UI should not infer meaning from arbitrary metric key names where possible.

Recommended normalization:

- `primary_metrics`
- `secondary_metrics`
- `diagnostic_metrics`
- `metric_definitions`
- `scorecards`

This would allow reusable cards across benchmark types.

## 9.5 Optional: correlation hooks for chat × benchmark

If product needs explicit linking later, consider lightweight API fields or admin-only views:

- optional `benchmark_run_id` / `case_id` echoed on eval harness responses;
- server-provided Phoenix URL template when UI project id discovery is unreliable.

Until then, the **minimum** is consistent identifiers in JSON (`thread_id`, `phoenix_trace_id`, `tool_trace[].tool`) and documented verification order (see `docs/architecture/observability-phoenix.md`).

---

## 10. Phased implementation plan

## Phase 0 — Taxonomy and experiment mapping

**Status: DONE (2026-04-27, UI).** Catalog is front-end static data; no new benchmark API fields yet.

Goal: shift the product language from internal families to user-facing experiments.

Deliverables:

1. define experiment catalog for the report-critical set; **Done:** [`experimentCatalog.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.js) (`EXPERIMENTS`, `EXPERIMENT_PACKS`, helpers `getReportCriticalExperiments`, etc.).
2. assign each experiment:
   - benchmark type,
   - primary metrics,
   - default scope,
   - recommended compare mode; **Done:** encoded as fields + i18n keys (`benchmarkCatalog.*` in `partBenchmarkPage` EN/RU).
3. mark trust/deployment-only surfaces as secondary diagnostics. **Done:** copy + IA (trust lives under Overview diagnostics; decision gate still secondary to “what to run”).

Exit criteria:

- the team can name benchmark UI actions in terms of experiments, not only `layer1/layer2`. **Met** in UI copy and Experiments/Overview; launcher internals remain visible inside Run Lab where needed.

## Phase 1 — New information architecture

**Status: DONE (2026-04-27, UI).** Reuses existing Run/Results/Compare/Workbench/Cases components under new tabs.

Goal: make the panel understandable before any large rendering refactor.

Deliverables:

1. replace current tab structure with Overview, Experiments, Run Lab, Analysis, Cases. **Done:** [`BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) plus `BenchmarkOverviewTab`, `BenchmarkExperimentsTab`, `BenchmarkAnalysisTab`; legacy `?tab=` values still parse (see handoff table).
2. move `TrustSignalPanel` into a secondary diagnostics area; **Done:** only on Overview, `defaultExpanded={false}` in [`BenchmarkOverviewTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkOverviewTab.jsx).
3. add report-critical experiment cards on the landing surface. **Done:** Overview grid from `getReportCriticalExperiments()` plus quick actions and recent runs list.

Exit criteria:

- a user can arrive at the page and immediately see what can be run and compared. **Met** at a landing level; **grouped batch run** is first-class in Run Lab (2026-04-27); **aggregate matrix / variant-first Analysis** has a **UI slice** (2026-04-28; see Phase 3 + Phase 5 in Implementation status).

## Phase 2 — Run Lab with batch/matrix execution

**Status: DONE — client/UI slice (2026-04-27).** Not done: server-side run group API. Matrix read surface: **partially done** in UI (2026-04-28); see **Implementation status → Phase 3 slice + Phase 5**.

Goal: support single-run and grouped-run workflows explicitly.

Deliverables:

1. run builder for one experiment + one variant; **Done (2026-04-28):** `?experiment=` + catalog CTAs apply launcher preset via `useRunTab`; family/API target demoted under **Advanced** accordion in Run Lab (`BenchmarkLauncherPanel`).
2. batch builder for many experiments and/or many variants; **Done:** grouped mode — multi-select experiments × model profiles, `buildGroupJobs` / `startGroupBatch` in [`useBenchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/useBenchmarkRunGroup.js).
3. grouped progress model in the UI; **Done:** child rows, aggregate status, sequential start with per-child errors, polling until terminal states (`BENCHMARK_TERMINAL_RUN_STATUSES`).
4. localStorage persistence for recent compare setups. **Done:** recent setups + `benchmark:lastRunGroup` in [`benchmarkRunGroup.js`](../../ui/src/pages/BenchmarkPage/benchmarkRunGroup.js).

Backend follow-up:

- optional `run-group` API if the current child-run orchestration becomes too frontend-heavy — **still open**; frontend currently chains `runBenchmark` per child.

Exit criteria:

- "run one benchmark" and "run a compare batch" both feel first-class. **Met** for batch; single-run is first-class with experiment-first Run Lab copy and Advanced API target block.

## Phase 3 — Analysis-first comparison

**Status: UI slice DONE (2026-04-28)** for matrix + deltas + trade-off cards + grouped detail in [`BenchmarkAnalysisOverview.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisOverview.jsx). **Open:** dedicated run-group detail *page* (vs panel), API-normalized scorecards (§9.4), one-click worst-case drill without opening legacy Compare.

Goal: make comparison the core analytical surface.

Deliverables:

1. variant matrix; **Done** (`BenchmarkVariantMatrix`).
2. per-experiment delta summaries; **Done** (compare API + `CompareDeltaTable` / summary in overview).
3. trade-off cards; **Done** (`benchmarkTradeoffModel.js` in overview).
4. run-group detail page; **Partially done** (group detail panel in overview, not separate route).
5. direct drill-down from matrix cell to worst cases. **Partially done** (matrix → selection → regressions table; full auto-open of Compare optional).

Exit criteria:

- a user can compare models without manually hopping between Results, Compare, and Workbench tabs. **Mostly met:** matrix-first default (`analysisView=overview`); legacy tools are secondary (More tools menu), not three equal tabs.

## Phase 4 — Benchmark-aware case inspector

**Status: DONE (2026-04-27 UI + API; URL/loading follow-ups 2026-04-28).** See **Implementation status → Done: Phase 4** for file-level map and deferred scope (CI JSON artifacts, Phoenix explorer, full merge of `CaseDetailDialog`).

Goal: turn case drill-down into an explanatory surface rather than a raw payload viewer.

Deliverables:

1. benchmark-type-specific case panels; **Done:** `ui/src/pages/BenchmarkPage/caseInspector/` — `Layer1CaseInspectorPanel`, `Layer2CaseInspectorPanel`, `GraphCaseInspectorPanel` (+ reuse `CaseGraphExpectationsPanel`), `caseInspectorRegistry.jsx`.
2. highlighted misses/extras/failures; **Done:** backend `highlights` (`headline`, `issues`, `failed_checks`) in [`benchmark.py`](../../science_graphrag/api/benchmark.py) `_build_inspector_highlights`; UI lists issues + headline before raw block.
3. raw payload toggle instead of raw payload default; **Done:** [`BenchmarkCaseInspectorShell.jsx`](../../ui/src/pages/BenchmarkPage/caseInspector/BenchmarkCaseInspectorShell.jsx) — single collapsed accordion “Raw payloads…” with nested sections.
4. stronger artifact links for report and trace review; **Done:** `evidence_links` from API + `buildEvidenceLinksFromArtifacts` in fixture mode; evidence rail + “last completed run” CTA; **trace/report URLs** still only when backend adds them (explicitly out of scope until runners expose refs).

Exit criteria:

- the reason for a regression is understandable at case level without reading JSON first. **Met** for run-scoped detail (highlights + family panels + compare-entry banner from `cmpBaseline`/`cmpMetric`); fixture-only shows catalog headline + evidence until a run is opened.

## Phase 5 — Cleanup and demotion of legacy surfaces

**Status: DONE in UI (2026-04-28).** See **Implementation status → Done: Phase 3 slice + Phase 5**.

Goal: prevent the old QA-console architecture from continuing to shape the product.

Deliverables:

1. remove or minimize legacy launcher framing by family; **Done** — Advanced accordion + i18n labels; experiment-first Run Lab title when `?experiment=`.
2. keep trust/deployment gates in diagnostics/admin mode; **Done** — demoted chip + caption on Overview (`TrustSignalPanel`).
3. de-duplicate result views between run report, compare, and workbench; **Done** — matrix overview default; Results/Compare/Workbench behind **More tools** + **Back to matrix**.
4. update docs/specs/screenshots. **Done** for docs/specs (this file + `benchmark-workbench-ui-plan.md`); screenshots not in repo.

Exit criteria:

- the benchmark panel has one clear product story instead of several competing ones. **Met** at Analysis + Run Lab level; optional further merge of `CaseDetailDialog` deferred.

---

## 11. Recommended implementation order

If only one vertical slice should happen first, do this:

1. **Phase 0 + Phase 1** — **done in UI (2026-04-27);** see **Implementation status (agent handoff)** at the top of this doc for paths and caveats.
2. **Phase 2 (grouped/batch Run Lab)** — **done in UI (2026-04-27)** as client orchestration; see Phase 2 table + “Notes for the next agent” at the top. Optional backend `run-group` still TBD.
3. **Phase 3** — UI matrix slice **done** (2026-04-28); follow-ups: API scorecards, run-group route, sharper drill-down.
4. **Phase 4** for case clarity — **done** (see §10 Phase 4 and handoff table).
5. **Phase 5** legacy demotion — **done** (2026-04-28).

Why this order:

- the biggest current problem is not lack of raw capabilities;
- it is that the page tells the wrong story;
- fixing IA first makes later implementation decisions much easier.

---

## 12. Concrete UI recommendations

Recommended naming:

- rename page title from generic "Benchmark" to **"Benchmark Lab"** or **"Evaluation Lab"**
- use `Experiments`, not `Families`, in top-level copy
- use `Variant`, not only `Model`, so future method comparisons fit naturally
- use `Analysis`, not only `Compare`, because the target task is interpretive, not just diff generation

Recommended status labeling:

- `Completed`, `Running`, `Failed` remain as run states
- `Go / No-go` should not be a first-class hero state on this page
- trust warnings should appear as contextual warnings, not as the main page identity

Recommended packs to predefine:

1. **Report-critical pack**
   - `layer1_nightly`
   - `layer2_semantic`
   - `workspace_scoped_live`
   - `hybrid_ablation_live`
   - `multihop_v2`
   - `claims_paraphrase`
   - `agent_tools_live`

2. **Extraction pack**
   - `layer1_nightly`
   - `layer2_semantic`
   - graph `CITES`

3. **Reasoning pack**
   - `workspace_scoped_live`
   - `hybrid_ablation_live`
   - `multihop_v2`
   - `agent_tools_live`

4. **Claims pack**
   - `claims production`
   - `claims_paraphrase`

---

## 13. Risks and mitigations

### Risk 1. The UI becomes "prettier" but still reflects backend internals

Mitigation:

- define experiment catalog first;
- make experiments the first-class UI object.

### Risk 2. Batch compare becomes fragile if represented only as many independent runs

Mitigation:

- add a run-group abstraction early if usage grows beyond simple local orchestration.

### Risk 3. Trust diagnostics disappear too much

Mitigation:

- keep them in `Overview -> Diagnostics` and in admin-oriented secondary views;
- do not delete the logic, only demote it from the primary narrative.

### Risk 4. Compare remains model-only and blocks future method comparisons

Mitigation:

- adopt `variant` terminology and payload shape now.

### Risk 5. Chat and Benchmark Lab look equally “trustworthy” but use different correlation keys

Mitigation:

- keep `thread_id` / `phoenix_trace_id` / `tool_trace` semantics aligned with Lab run artifacts;
- avoid hard-coded Phoenix UI project slugs; require explicit UI env for deep links or show trace hints only;
- extend Analysis phase work to chat trace review when chat becomes a primary research surface.

---

## 14. Final recommendation

Do not continue evolving the current benchmark panel as a slightly nicer internal console.

Instead, treat this as a **product reframing**:

- from `family/run/trust` UI
- to `experiment/variant/analysis` UI

That shift is the one that matches the final report, the current project maturity, and the future goal of comparing both **models** and later **methods** for extraction, retrieval, and graph-based reasoning.
