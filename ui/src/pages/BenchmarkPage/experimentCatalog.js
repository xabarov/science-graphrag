/**
 * Report-first benchmark experiment catalog (Phase 0).
 * Maps user-facing experiments to launcher/API surfaces and metric semantics.
 */

/** @typedef {"extraction"|"retrieval"|"graph_reasoning"|"claims"|"agent"|"composite"} BenchmarkType */

/** @typedef {"two_runs_same_family"|"matrix_later"|"cli_artifact"} RecommendedCompareMode */

/**
 * @typedef {object} ExperimentEntry
 * @property {string} id
 * @property {string} titleKey i18n key
 * @property {string} descriptionKey i18n key
 * @property {BenchmarkType} benchmarkType
 * @property {string[]} primaryMetricKeys i18n keys (short labels)
 * @property {string[]} secondaryMetricKeys
 * @property {string} defaultScopeKey i18n key
 * @property {RecommendedCompareMode} recommendedCompareMode
 * @property {"ui"|"cli_only"|"catalog"} runnableSurface
 * @property {"layer1"|"layer2"|"graph"|null} uiFamily When runnableSurface is ui, which family the Run Lab uses
 * @property {string | null} launcherScopePreset Hint for Run Lab: nightly, merge_safe, etc.
 * @property {boolean} reportCritical
 * @property {string[]} packIds
 */

/** @type {ExperimentEntry[]} */
export const EXPERIMENTS = [
  {
    id: "layer1_nightly",
    titleKey: "benchmarkCatalog.experiment.layer1Nightly.title",
    descriptionKey: "benchmarkCatalog.experiment.layer1Nightly.description",
    benchmarkType: "extraction",
    primaryMetricKeys: ["benchmarkCatalog.metric.macroPRF1", "benchmarkCatalog.metric.rougeL"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.failedCount"],
    defaultScopeKey: "benchmarkCatalog.scope.nightlyTier",
    recommendedCompareMode: "two_runs_same_family",
    runnableSurface: "ui",
    uiFamily: "layer1",
    launcherScopePreset: "nightly",
    reportCritical: true,
    packIds: ["report_critical", "extraction"],
  },
  {
    id: "layer2_semantic",
    titleKey: "benchmarkCatalog.experiment.layer2Semantic.title",
    descriptionKey: "benchmarkCatalog.experiment.layer2Semantic.description",
    benchmarkType: "extraction",
    primaryMetricKeys: ["benchmarkCatalog.metric.macroPRF1", "benchmarkCatalog.metric.rougeL"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.failedCount"],
    defaultScopeKey: "benchmarkCatalog.scope.semanticGold",
    recommendedCompareMode: "two_runs_same_family",
    runnableSurface: "ui",
    uiFamily: "layer2",
    launcherScopePreset: "nightly",
    reportCritical: true,
    packIds: ["report_critical", "extraction"],
  },
  {
    id: "graph_cites",
    titleKey: "benchmarkCatalog.experiment.graphCites.title",
    descriptionKey: "benchmarkCatalog.experiment.graphCites.description",
    benchmarkType: "extraction",
    primaryMetricKeys: ["benchmarkCatalog.metric.graphExpectations"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.cliOrCatalog"],
    defaultScopeKey: "benchmarkCatalog.scope.graphCatalog",
    recommendedCompareMode: "two_runs_same_family",
    runnableSurface: "catalog",
    uiFamily: "graph",
    launcherScopePreset: null,
    reportCritical: false,
    packIds: ["extraction"],
  },
  {
    id: "workspace_scoped_live",
    titleKey: "benchmarkCatalog.experiment.workspaceScopedLive.title",
    descriptionKey: "benchmarkCatalog.experiment.workspaceScopedLive.description",
    benchmarkType: "retrieval",
    primaryMetricKeys: [
      "benchmarkCatalog.metric.hitCount",
      "benchmarkCatalog.metric.hitAtK",
      "benchmarkCatalog.metric.mrr",
    ],
    secondaryMetricKeys: ["benchmarkCatalog.metric.forbiddenViolations"],
    defaultScopeKey: "benchmarkCatalog.scope.liveWorkspace",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: true,
    packIds: ["report_critical", "reasoning"],
  },
  {
    id: "hybrid_ablation_live",
    titleKey: "benchmarkCatalog.experiment.hybridAblationLive.title",
    descriptionKey: "benchmarkCatalog.experiment.hybridAblationLive.description",
    benchmarkType: "retrieval",
    primaryMetricKeys: [
      "benchmarkCatalog.metric.hitCount",
      "benchmarkCatalog.metric.hitAtK",
      "benchmarkCatalog.metric.mrr",
    ],
    secondaryMetricKeys: ["benchmarkCatalog.metric.forbiddenViolations"],
    defaultScopeKey: "benchmarkCatalog.scope.hybridAblation",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: true,
    packIds: ["report_critical", "reasoning"],
  },
  {
    id: "multihop_v2",
    titleKey: "benchmarkCatalog.experiment.multihopV2.title",
    descriptionKey: "benchmarkCatalog.experiment.multihopV2.description",
    benchmarkType: "graph_reasoning",
    primaryMetricKeys: ["benchmarkCatalog.metric.recall", "benchmarkCatalog.metric.precision"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.diagnostics"],
    defaultScopeKey: "benchmarkCatalog.scope.multihopPack",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: true,
    packIds: ["report_critical", "reasoning"],
  },
  {
    id: "claims_production",
    titleKey: "benchmarkCatalog.experiment.claimsProduction.title",
    descriptionKey: "benchmarkCatalog.experiment.claimsProduction.description",
    benchmarkType: "claims",
    primaryMetricKeys: ["benchmarkCatalog.metric.precision", "benchmarkCatalog.metric.recall", "benchmarkCatalog.metric.f1"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.diagnostics"],
    defaultScopeKey: "benchmarkCatalog.scope.claimsProduction",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: false,
    packIds: ["claims"],
  },
  {
    id: "claims_paraphrase",
    titleKey: "benchmarkCatalog.experiment.claimsParaphrase.title",
    descriptionKey: "benchmarkCatalog.experiment.claimsParaphrase.description",
    benchmarkType: "claims",
    primaryMetricKeys: ["benchmarkCatalog.metric.precision", "benchmarkCatalog.metric.recall", "benchmarkCatalog.metric.f1"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.diagnostics"],
    defaultScopeKey: "benchmarkCatalog.scope.claimsParaphrase",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: true,
    packIds: ["report_critical", "claims"],
  },
  {
    id: "agent_tools_live",
    titleKey: "benchmarkCatalog.experiment.agentToolsLive.title",
    descriptionKey: "benchmarkCatalog.experiment.agentToolsLive.description",
    benchmarkType: "agent",
    primaryMetricKeys: ["benchmarkCatalog.metric.judgeScore", "benchmarkCatalog.metric.latency"],
    secondaryMetricKeys: ["benchmarkCatalog.metric.diagnostics"],
    defaultScopeKey: "benchmarkCatalog.scope.agentLive",
    recommendedCompareMode: "cli_artifact",
    runnableSurface: "cli_only",
    uiFamily: null,
    launcherScopePreset: null,
    reportCritical: true,
    packIds: ["report_critical", "reasoning"],
  },
];

/** @type {{ id: string, titleKey: string, descriptionKey: string, experimentIds: string[] }[]} */
export const EXPERIMENT_PACKS = [
  {
    id: "report_critical",
    titleKey: "benchmarkCatalog.pack.reportCritical.title",
    descriptionKey: "benchmarkCatalog.pack.reportCritical.description",
    experimentIds: [
      "layer1_nightly",
      "layer2_semantic",
      "workspace_scoped_live",
      "hybrid_ablation_live",
      "multihop_v2",
      "claims_paraphrase",
      "agent_tools_live",
    ],
  },
  {
    id: "extraction",
    titleKey: "benchmarkCatalog.pack.extraction.title",
    descriptionKey: "benchmarkCatalog.pack.extraction.description",
    experimentIds: ["layer1_nightly", "layer2_semantic", "graph_cites"],
  },
  {
    id: "reasoning",
    titleKey: "benchmarkCatalog.pack.reasoning.title",
    descriptionKey: "benchmarkCatalog.pack.reasoning.description",
    experimentIds: [
      "workspace_scoped_live",
      "hybrid_ablation_live",
      "multihop_v2",
      "agent_tools_live",
    ],
  },
  {
    id: "claims",
    titleKey: "benchmarkCatalog.pack.claims.title",
    descriptionKey: "benchmarkCatalog.pack.claims.description",
    experimentIds: ["claims_production", "claims_paraphrase"],
  },
];

export const TAB_CANONICAL = {
  overview: "overview",
  experiments: "experiments",
  runLab: "run-lab",
  analysis: "analysis",
  cases: "cases",
};

/** Canonical tab name -> main tab index (0..4) */
export const TAB_NAME_TO_INDEX = {
  [TAB_CANONICAL.overview]: 0,
  [TAB_CANONICAL.experiments]: 1,
  [TAB_CANONICAL.runLab]: 2,
  [TAB_CANONICAL.analysis]: 3,
  [TAB_CANONICAL.cases]: 4,
};

export const INDEX_TO_TAB_NAME = {
  0: TAB_CANONICAL.overview,
  1: TAB_CANONICAL.experiments,
  2: TAB_CANONICAL.runLab,
  3: TAB_CANONICAL.analysis,
  4: TAB_CANONICAL.cases,
};

/** @type {readonly ["results", "compare", "workbench"]} */
export const ANALYSIS_VIEWS = ["results", "compare", "workbench"];

const LEGACY_TAB_NAMES = {
  launch: { tabIndex: 2, analysisView: "results" },
  workbench: { tabIndex: 3, analysisView: "workbench" },
  results: { tabIndex: 3, analysisView: "results" },
  compare: { tabIndex: 3, analysisView: "compare" },
  cases: { tabIndex: 4, analysisView: "results" },
};

const LEGACY_NUMERIC = [
  { tabIndex: 2, analysisView: "results" },
  { tabIndex: 3, analysisView: "workbench" },
  { tabIndex: 3, analysisView: "results" },
  { tabIndex: 3, analysisView: "compare" },
  { tabIndex: 4, analysisView: "results" },
];

/**
 * Parse `tab` and `analysisView` search params into main tab index and analysis sub-view.
 * @param {string | null} tabParam
 * @param {string | null} analysisViewParam
 * @returns {{ tabIndex: number, analysisView: "results"|"compare"|"workbench" }}
 */
export function parseBenchmarkTabQuery(tabParam, analysisViewParam) {
  let tabIndex = 0;
  let analysisView = /** @type {"results"|"compare"|"workbench"} */ ("results");

  if (tabParam != null && tabParam !== "") {
    const asNum = Number(tabParam);
    if (!Number.isNaN(asNum) && asNum >= 0 && asNum <= 4) {
      const mapped = LEGACY_NUMERIC[asNum];
      tabIndex = mapped.tabIndex;
      analysisView = mapped.analysisView;
    } else if (TAB_NAME_TO_INDEX[tabParam] != null) {
      tabIndex = TAB_NAME_TO_INDEX[tabParam];
      if (tabIndex === 3) {
        analysisView = normalizeAnalysisView(analysisViewParam);
      }
    } else if (LEGACY_TAB_NAMES[tabParam]) {
      const mapped = LEGACY_TAB_NAMES[tabParam];
      tabIndex = mapped.tabIndex;
      analysisView = mapped.analysisView;
    }
  } else if (analysisViewParam && ANALYSIS_VIEWS.includes(analysisViewParam)) {
    tabIndex = 3;
    analysisView = /** @type {"results"|"compare"|"workbench"} */ (analysisViewParam);
  }

  return { tabIndex, analysisView };
}

/**
 * @param {string | null | undefined} v
 * @returns {"results"|"compare"|"workbench"}
 */
export function normalizeAnalysisView(v) {
  if (v && ANALYSIS_VIEWS.includes(v)) return /** @type {"results"|"compare"|"workbench"} */ (v);
  return "results";
}

/**
 * Build query entries for the benchmark page URL (canonical tab names).
 * @param {number} tabIndex
 * @param {"results"|"compare"|"workbench"} analysisView
 * @returns {Record<string, string>}
 */
export function benchmarkTabQueryEntries(tabIndex, analysisView) {
  const name = INDEX_TO_TAB_NAME[String(tabIndex)] || TAB_CANONICAL.overview;
  if (tabIndex === 3) {
    return { tab: name, analysisView };
  }
  return { tab: name };
}

/**
 * Merge tab query into existing URLSearchParams (drops analysisView when not on analysis).
 * @param {URLSearchParams} current
 * @param {number} tabIndex
 * @param {"results"|"compare"|"workbench"} analysisView
 * @returns {URLSearchParams}
 */
export function mergeBenchmarkTabIntoSearchParams(current, tabIndex, analysisView) {
  const next = new URLSearchParams(current.toString());
  const entries = benchmarkTabQueryEntries(tabIndex, analysisView);
  next.set("tab", entries.tab);
  if (entries.analysisView) {
    next.set("analysisView", entries.analysisView);
  } else {
    next.delete("analysisView");
  }
  return next;
}

export function getReportCriticalExperiments() {
  return EXPERIMENTS.filter((e) => e.reportCritical);
}

export function getExperimentsForPack(packId) {
  const pack = EXPERIMENT_PACKS.find((p) => p.id === packId);
  if (!pack) return [];
  const idSet = new Set(pack.experimentIds);
  return EXPERIMENTS.filter((e) => idSet.has(e.id));
}

export function getExperimentById(id) {
  return EXPERIMENTS.find((e) => e.id === id) ?? null;
}

/** Canonical `runMode` query values for Run Lab (Phase 2). */
export const RUN_MODE_SINGLE = "single";
export const RUN_MODE_GROUPED = "grouped";

const LAUNCHER_SCOPE_FROM_PRESET = {
  nightly: "nightly",
  merge_safe: "merge_safe",
  all: "all",
  selected: "selected",
};

/**
 * @param {string | null | undefined} v
 * @returns {"single"|"grouped"}
 */
export function normalizeRunMode(v) {
  if (v === RUN_MODE_GROUPED) return RUN_MODE_GROUPED;
  return RUN_MODE_SINGLE;
}

/** Experiments that can be started from Run Lab via benchmark API (UI-runnable). */
export function getUiRunnableExperiments() {
  return EXPERIMENTS.filter((e) => e.runnableSurface === "ui" && (e.uiFamily === "layer1" || e.uiFamily === "layer2"));
}

/**
 * Map catalog experiment id to launcher family + scope for Run Lab presets.
 * @param {string | null | undefined} experimentId
 * @returns {{ experimentId: string, uiFamily: "layer1"|"layer2", launcherScope: string } | null}
 */
export function getLauncherPresetForExperiment(experimentId) {
  const id = typeof experimentId === "string" ? experimentId.trim() : "";
  if (!id) return null;
  const exp = getExperimentById(id);
  if (!exp || exp.runnableSurface !== "ui") return null;
  const fam = exp.uiFamily;
  if (fam !== "layer1" && fam !== "layer2") return null;
  const preset = exp.launcherScopePreset;
  const launcherScope =
    preset && typeof preset === "string" && preset in LAUNCHER_SCOPE_FROM_PRESET
      ? LAUNCHER_SCOPE_FROM_PRESET[/** @type {keyof typeof LAUNCHER_SCOPE_FROM_PRESET} */ (preset)]
      : "nightly";
  return { experimentId: exp.id, uiFamily: fam, launcherScope };
}

/**
 * Merge Run Lab deep-link params into search params (preserves unrelated keys).
 * @param {URLSearchParams} current
 * @param {{ experimentId?: string | null, runMode?: "single"|"grouped" | null, packId?: string | null }} patch
 */
export function mergeRunLabQueryIntoSearchParams(current, patch) {
  const next = new URLSearchParams(current.toString());
  if (patch.experimentId !== undefined) {
    const v = typeof patch.experimentId === "string" ? patch.experimentId.trim() : "";
    if (v) next.set("experiment", v);
    else next.delete("experiment");
  }
  if (patch.runMode !== undefined && patch.runMode !== null) {
    if (patch.runMode === RUN_MODE_GROUPED) next.set("runMode", RUN_MODE_GROUPED);
    else next.delete("runMode");
  }
  if (patch.packId !== undefined) {
    const v = typeof patch.packId === "string" ? patch.packId.trim() : "";
    if (v) next.set("pack", v);
    else next.delete("pack");
  }
  return next;
}

/**
 * @param {URLSearchParams | { get: (k: string) => string | null }} params
 */
export function parseRunLabQueryFromSearchParams(params) {
  const experimentRaw = params.get("experiment");
  const packRaw = params.get("pack");
  return {
    experimentId: experimentRaw && experimentRaw.trim() ? experimentRaw.trim() : null,
    runMode: normalizeRunMode(params.get("runMode")),
    packId: packRaw && packRaw.trim() ? packRaw.trim() : null,
  };
}

export function compareModeLabelKey(mode) {
  switch (mode) {
    case "two_runs_same_family":
      return "benchmarkCatalog.compareMode.twoRuns";
    case "matrix_later":
      return "benchmarkCatalog.compareMode.matrixLater";
    case "cli_artifact":
      return "benchmarkCatalog.compareMode.cliArtifact";
    default:
      return "benchmarkCatalog.compareMode.unknown";
  }
}

export function benchmarkTypeLabelKey(type) {
  switch (type) {
    case "extraction":
      return "benchmarkCatalog.type.extraction";
    case "retrieval":
      return "benchmarkCatalog.type.retrieval";
    case "graph_reasoning":
      return "benchmarkCatalog.type.graphReasoning";
    case "claims":
      return "benchmarkCatalog.type.claims";
    case "agent":
      return "benchmarkCatalog.type.agent";
    case "composite":
      return "benchmarkCatalog.type.composite";
    default:
      return "benchmarkCatalog.type.unknown";
  }
}

export function runnableSurfaceLabelKey(surface) {
  switch (surface) {
    case "ui":
      return "benchmarkCatalog.surface.ui";
    case "cli_only":
      return "benchmarkCatalog.surface.cliOnly";
    case "catalog":
      return "benchmarkCatalog.surface.catalog";
    default:
      return "benchmarkCatalog.surface.unknown";
  }
}
