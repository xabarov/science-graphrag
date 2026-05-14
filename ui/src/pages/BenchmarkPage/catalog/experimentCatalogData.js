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

export { EXPERIMENTS } from "./experimentCatalogExperimentsBundle.js";
export {
  EXPERIMENT_PACKS,
  benchmarkTypeLabelKey,
  compareModeLabelKey,
  getExperimentById,
  getExperimentsForPack,
  getReportCriticalExperiments,
  getUiRunnableExperiments,
  runnableSurfaceLabelKey,
} from "./experimentCatalogDataPacksAndQueries.js";
