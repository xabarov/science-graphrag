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

/** Legacy drill-down tools embedded under Analysis (not the matrix overview). */
/** @type {readonly ["results", "compare", "workbench"]} */
export const LEGACY_ANALYSIS_TOOL_VIEWS = ["results", "compare", "workbench"];

/** @deprecated Prefer LEGACY_ANALYSIS_TOOL_VIEWS; kept for external imports. */
export const ANALYSIS_VIEWS = LEGACY_ANALYSIS_TOOL_VIEWS;

/** Full Analysis sub-surface including matrix-first default. */
/** @type {readonly ["overview", "results", "compare", "workbench"]} */
export const ANALYSIS_SURFACE_VIEWS = ["overview", "results", "compare", "workbench"];

const LEGACY_TAB_NAMES = {
  launch: { tabIndex: 2, analysisView: "results" },
  workbench: { tabIndex: 3, analysisView: "workbench" },
  results: { tabIndex: 3, analysisView: "results" },
  compare: { tabIndex: 3, analysisView: "compare" },
  /** Align with canonical `cases` tab: no legacy Analysis sub-view. */
  cases: { tabIndex: 4, analysisView: "overview" },
};

const LEGACY_NUMERIC = [
  { tabIndex: 2, analysisView: "results" },
  { tabIndex: 3, analysisView: "workbench" },
  { tabIndex: 3, analysisView: "results" },
  { tabIndex: 3, analysisView: "compare" },
  { tabIndex: 4, analysisView: "overview" },
];

/**
 * Parse `tab` and `analysisView` search params into main tab index and analysis sub-view.
 * @param {string | null} tabParam
 * @param {string | null} analysisViewParam
 * @returns {{ tabIndex: number, analysisView: "overview"|"results"|"compare"|"workbench" }}
 */
export function parseBenchmarkTabQuery(tabParam, analysisViewParam) {
  let tabIndex = 0;
  let analysisView = /** @type {"overview"|"results"|"compare"|"workbench"} */ ("overview");

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
  } else if (
    analysisViewParam &&
    (analysisViewParam === "overview" || LEGACY_ANALYSIS_TOOL_VIEWS.includes(analysisViewParam))
  ) {
    tabIndex = 3;
    analysisView = normalizeAnalysisView(analysisViewParam);
  }

  return { tabIndex, analysisView };
}

/**
 * @param {string | null | undefined} v
 * @returns {"overview"|"results"|"compare"|"workbench"}
 */
export function normalizeAnalysisView(v) {
  if (v === "overview") return "overview";
  if (v && LEGACY_ANALYSIS_TOOL_VIEWS.includes(v)) return /** @type {"results"|"compare"|"workbench"} */ (v);
  return "overview";
}

/**
 * Build query entries for the benchmark page URL (canonical tab names).
 * @param {number} tabIndex
 * @param {"overview"|"results"|"compare"|"workbench"} analysisView
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
 * @param {"overview"|"results"|"compare"|"workbench"} analysisView
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
