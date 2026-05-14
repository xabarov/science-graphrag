import { EXPERIMENTS } from "./experimentCatalogExperimentsBundle.js";

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

/** Experiments that can be started from Run Lab via benchmark API (UI-runnable). */
export function getUiRunnableExperiments() {
  return EXPERIMENTS.filter((e) => e.runnableSurface === "ui" && (e.uiFamily === "layer1" || e.uiFamily === "layer2"));
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
