# Benchmark panel: research-first redesign plan (2026-04-27)

**Status:** proposed product/UX analysis and phased implementation plan. **Phase 0 + Phase 1 are implemented in the UI** (see section **Implementation status (agent handoff)** below the front matter).

**Primary goal:** redesign the benchmark panel so it supports the benchmark program that the final report actually argues for: **run one experiment or a batch, compare model/method variants, and read the resulting metrics without needing to mentally translate internal QA machinery**.

**Key alignment source:** [`docs/report/nlp-advanced-final-report-2026-04-26.md`](../report/nlp-advanced-final-report-2026-04-26.md)

**Current UI surface reviewed:**
- `ui/src/pages/BenchmarkPage/BenchmarkPage.jsx`
- `ui/src/pages/BenchmarkPage/RunTab.jsx`
- `ui/src/pages/BenchmarkPage/ResultsTab.jsx`
- `ui/src/pages/BenchmarkPage/CompareTab.jsx`
- `ui/src/pages/BenchmarkPage/CasesTab.jsx`
- `ui/src/pages/BenchmarkPage/workbench/BenchmarkWorkbenchRunPanel.jsx`
- `ui/src/pages/BenchmarkPage/TrustSignalPanel.jsx`

**Related prior spec:** [`docs/specs/benchmark-workbench-ui-plan.md`](../specs/benchmark-workbench-ui-plan.md)

---

## Implementation status (agent handoff)

**Last updated:** 2026-04-27.

### Done: Phase 0 + Phase 1 (UI)

The following matches **section 10** (`Phase 0`, `Phase 1`) in this document. Treat everything below **Phase 2** as not yet product-complete unless noted.

| Area | Where in code / docs |
|------|------------------------|
| Experiment catalog + packs | [`ui/src/pages/BenchmarkPage/experimentCatalog.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.js) — `EXPERIMENTS`, `EXPERIMENT_PACKS`, report-critical set, `runnableSurface` (`ui` / `cli_only` / `catalog`), metric/scope/compare-mode i18n keys. |
| Tab routing + legacy deep links | Same file: `parseBenchmarkTabQuery`, `mergeBenchmarkTabIntoSearchParams`, `TAB_CANONICAL`. Legacy named tabs (`launch`, `workbench`, `results`, `compare`, `cases`) and **numeric tab 0–4 (old order)** still resolve. Canonical URLs use `overview`, `experiments`, `run-lab`, `analysis`, `cases` plus `analysisView` (`results`, `compare`, `workbench`) when on Analysis. |
| Page shell | [`ui/src/pages/BenchmarkPage/BenchmarkPage.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkPage.jsx) — tabs Overview / Experiments / Run Lab / Analysis / Cases; URL sync for `run` / `case` only when those query keys exist (avoids wiping `benchmark:lastRunId` on first paint without `run`). |
| Overview + diagnostics | [`ui/src/pages/BenchmarkPage/BenchmarkOverviewTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkOverviewTab.jsx) — report-critical cards, recent runs (`listBenchmarkRuns`), **TrustSignalPanel** in collapsed diagnostics block (not hero). |
| Experiments catalog tab | [`ui/src/pages/BenchmarkPage/BenchmarkExperimentsTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkExperimentsTab.jsx). |
| Analysis tab (compose old surfaces) | [`ui/src/pages/BenchmarkPage/BenchmarkAnalysisTab.jsx`](../../ui/src/pages/BenchmarkPage/BenchmarkAnalysisTab.jsx) — wraps existing `ResultsTab`, `CompareTab`, `BenchmarkWorkbenchTab`. |
| i18n | [`ui/src/i18n/messages/en/partBenchmarkPage.js`](../../ui/src/i18n/messages/en/partBenchmarkPage.js), [`ui/src/i18n/messages/ru/partBenchmarkPage.js`](../../ui/src/i18n/messages/ru/partBenchmarkPage.js) — `benchmarkPage.pageTitle` (= Benchmark Lab), tab labels, `benchmarkCatalog.*`. |
| Entry links aligned | [`ui/src/pages/BenchmarkPage/caseDetail/CaseDetailArtifactsSection.jsx`](../../ui/src/pages/BenchmarkPage/caseDetail/CaseDetailArtifactsSection.jsx) (`tab=analysis&analysisView=workbench&run=…`), [`ui/src/pages/AdminEntryPage.jsx`](../../ui/src/pages/AdminEntryPage.jsx) (secondary benchmarks link). |
| Tests | [`ui/src/pages/BenchmarkPage/experimentCatalog.test.js`](../../ui/src/pages/BenchmarkPage/experimentCatalog.test.js); [`ui/src/routeCompatibility.test.js`](../../ui/src/routeCompatibility.test.js) extended for canonical benchmark query preservation. |

### Notes for the **next** agent (Phase 2+)

1. **Run Lab vs catalog:** `RunTab` + [`benchmarkLauncherConfig.js`](../../ui/src/pages/BenchmarkPage/benchmarkLauncherConfig.js) remain **family-first** (`layer1` / `layer2` / `graph`). Catalog rows describe experiments but **do not yet drive launcher presets** (no `?experiment=…` → family/scope). Phase 2 “run builder for one experiment + one variant” should wire optional query or launcher prefs from `experimentCatalog` ids.
2. **CLI-only rows:** Retrieval / claims / agent experiments are **documentation + navigation** in UI; runs still come from existing API/CLI workflows — no new `experiment_id` on runs until you add backend follow-up from section 10 optional notes.
3. **Backlog:** [`docs/backlog/refactor-frontend.md`](../../docs/backlog/refactor-frontend.md) item *Benchmark panel — separate experiment product from trust/admin console* is partially addressed by this slice; update or split when Phase 2 (batch/matrix) lands.
4. **Phase 3 wording:** Analysis tab already groups Results / Compare / Workbench — the remaining “no hopping” gap is **matrix / variant-first summaries**, not tab presence.
5. **Trust:** Still loaded via [`useBenchmarkSummary`](../../ui/src/hooks/useBenchmarkSummary.js) inside TrustSignalPanel; only **placement** changed. If product wants trust on other tabs, reuse the same panel in a small diagnostics slot rather than duplicating fetch logic.

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
5. graph expectations preview exists for graph artifacts.

This is important: the problem is not lack of infrastructure. The problem is mostly **information architecture and product framing**.

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

- a user can arrive at the page and immediately see what can be run and compared. **Met** at a landing level; deep compare/matrix is **Phase 2–3**.

## Phase 2 — Run Lab with batch/matrix execution

**Status: NOT STARTED (next vertical slice per section 11).**

Goal: support single-run and grouped-run workflows explicitly.

Deliverables:

1. run builder for one experiment + one variant;
2. batch builder for many experiments and/or many variants;
3. grouped progress model in the UI;
4. localStorage persistence for recent compare setups.

Backend follow-up:

- optional `run-group` API if the current child-run orchestration becomes too frontend-heavy.

Exit criteria:

- "run one benchmark" and "run a compare batch" both feel first-class.

## Phase 3 — Analysis-first comparison

Goal: make comparison the core analytical surface.

Deliverables:

1. variant matrix;
2. per-experiment delta summaries;
3. trade-off cards;
4. run-group detail page;
5. direct drill-down from matrix cell to worst cases.

Exit criteria:

- a user can compare models without manually hopping between Results, Compare, and Workbench tabs.

## Phase 4 — Benchmark-aware case inspector

Goal: turn case drill-down into an explanatory surface rather than a raw payload viewer.

Deliverables:

1. benchmark-type-specific case panels;
2. highlighted misses/extras/failures;
3. raw payload toggle instead of raw payload default;
4. stronger artifact links for report and trace review.

Exit criteria:

- the reason for a regression is understandable at case level without reading JSON first.

## Phase 5 — Cleanup and demotion of legacy surfaces

Goal: prevent the old QA-console architecture from continuing to shape the product.

Deliverables:

1. remove or minimize legacy launcher framing by family;
2. keep trust/deployment gates in diagnostics/admin mode;
3. de-duplicate result views between run report, compare, and workbench;
4. update docs/specs/screenshots.

Exit criteria:

- the benchmark panel has one clear product story instead of several competing ones.

---

## 11. Recommended implementation order

If only one vertical slice should happen first, do this:

1. **Phase 0 + Phase 1** — **done in UI (2026-04-27);** see **Implementation status (agent handoff)** at the top of this doc for paths and caveats.
2. **Phase 2** for grouped execution
3. **Phase 3** for model comparison
4. **Phase 4** for case clarity

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

---

## 14. Final recommendation

Do not continue evolving the current benchmark panel as a slightly nicer internal console.

Instead, treat this as a **product reframing**:

- from `family/run/trust` UI
- to `experiment/variant/analysis` UI

That shift is the one that matches the final report, the current project maturity, and the future goal of comparing both **models** and later **methods** for extraction, retrieval, and graph-based reasoning.
