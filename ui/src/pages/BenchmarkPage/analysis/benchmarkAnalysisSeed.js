import { getUiRunnableExperiments } from "../experimentCatalog.js";

const UI_EXPERIMENT_IDS = new Set(getUiRunnableExperiments().map((item) => item.id));

/**
 * @param {URLSearchParams | { get: (key: string) => string | null }} params
 * @returns {string[]}
 */
export function parseAnalysisRunIdsFromSearchParams(params) {
  const ordered = [];
  const seen = new Set();
  const single = params.get("run");
  if (single && single.trim()) {
    const id = single.trim();
    ordered.push(id);
    seen.add(id);
  }
  const csv = params.get("runs");
  if (!csv) return ordered;
  for (const raw of csv.split(",")) {
    const id = raw.trim();
    if (!id || seen.has(id)) continue;
    ordered.push(id);
    seen.add(id);
  }
  return ordered;
}

/**
 * @param {unknown} lastRunGroup
 * @returns {{ runIds: string[], childByRunId: Map<string, any>, modelProfileOrder: string[], experimentOrder: string[] }}
 */
export function buildLastRunGroupLookup(lastRunGroup) {
  const childByRunId = new Map();
  const runIds = [];
  const experimentOrder = [];
  const modelProfileOrder = [];
  const seenRuns = new Set();
  const seenExperiments = new Set();
  const seenProfiles = new Set();
  const children = Array.isArray(lastRunGroup?.children) ? lastRunGroup.children : [];
  for (const child of children) {
    const runId = typeof child?.runId === "string" ? child.runId.trim() : "";
    if (!runId || seenRuns.has(runId)) continue;
    seenRuns.add(runId);
    runIds.push(runId);
    childByRunId.set(runId, child);
    const experimentId = typeof child?.experimentId === "string" ? child.experimentId.trim() : "";
    if (experimentId && !seenExperiments.has(experimentId)) {
      seenExperiments.add(experimentId);
      experimentOrder.push(experimentId);
    }
    const profileId = typeof child?.modelProfileId === "string" ? child.modelProfileId.trim() : "";
    if (profileId && !seenProfiles.has(profileId)) {
      seenProfiles.add(profileId);
      modelProfileOrder.push(profileId);
    }
  }
  return { runIds, childByRunId, modelProfileOrder, experimentOrder };
}

/**
 * @param {{ searchParams: URLSearchParams | { get: (key: string) => string | null }, lastRunGroup?: unknown }} args
 */
export function selectAnalysisSeed({ searchParams, lastRunGroup }) {
  const fromUrl = parseAnalysisRunIdsFromSearchParams(searchParams);
  if (fromUrl.length) {
    return {
      source: "url",
      runIds: fromUrl,
      ...buildLastRunGroupLookup(lastRunGroup),
    };
  }
  const fallback = buildLastRunGroupLookup(lastRunGroup);
  if (fallback.runIds.length) {
    return { source: "last_group", ...fallback };
  }
  return {
    source: "empty",
    runIds: [],
    childByRunId: new Map(),
    modelProfileOrder: [],
    experimentOrder: [],
  };
}

/**
 * @param {Record<string, any>} run
 * @param {Map<string, any>} childByRunId
 * @returns {string | null}
 */
export function inferExperimentIdForRun(run, childByRunId = new Map()) {
  const runId = typeof run?.run_id === "string" ? run.run_id : "";
  const child = runId ? childByRunId.get(runId) : null;
  const fromChild = typeof child?.experimentId === "string" ? child.experimentId.trim() : "";
  if (fromChild && UI_EXPERIMENT_IDS.has(fromChild)) return fromChild;

  const label = typeof run?.label === "string" ? run.label.trim() : "";
  const prefix = (label.split("·")[0] || "").trim();
  if (prefix && UI_EXPERIMENT_IDS.has(prefix)) return prefix;

  const family = String(run?.benchmark_family || "").trim().toLowerCase();
  if (family === "layer1") return "layer1_nightly";
  if (family === "layer2") return "layer2_semantic";
  return null;
}

/**
 * @param {Record<string, any>} run
 * @param {Map<string, any>} childByRunId
 * @returns {string}
 */
export function inferVariantIdForRun(run, childByRunId = new Map()) {
  const runId = typeof run?.run_id === "string" ? run.run_id : "";
  const child = runId ? childByRunId.get(runId) : null;
  const fromChild = typeof child?.modelProfileId === "string" ? child.modelProfileId.trim() : "";
  if (fromChild) return fromChild;
  const profileId = typeof run?.run_config?.model_profile === "string" ? run.run_config.model_profile.trim() : "";
  if (profileId) return profileId;
  const modelId = typeof run?.run_config?.model_id === "string" ? run.run_config.model_id.trim() : "";
  if (modelId) return modelId;
  return "default";
}

/**
 * @param {Record<string, any>} run
 * @returns {string}
 */
export function variantLabelForRun(run) {
  const profileId = typeof run?.run_config?.model_profile === "string" ? run.run_config.model_profile.trim() : "";
  if (profileId) return profileId;
  const modelId = typeof run?.run_config?.model_id === "string" ? run.run_config.model_id.trim() : "";
  if (modelId) return modelId;
  return "default";
}

/**
 * @param {Record<string, any>} run
 * @returns {number}
 */
export function statusRankForRun(run) {
  const status = String(run?.status || "").toLowerCase();
  if (status === "completed") return 3;
  if (status === "running") return 2;
  if (status === "queued") return 1;
  if (status === "failed") return -1;
  return 0;
}

/**
 * @param {string} experimentId
 * @param {string[]} variantIds
 * @param {string[]} preferredOrder
 * @returns {string | null}
 */
export function chooseBaselineVariantId(experimentId, variantIds, preferredOrder = []) {
  if (!variantIds.length) return null;
  const unique = [...new Set(variantIds)];
  for (const candidate of preferredOrder) {
    if (unique.includes(candidate)) return candidate;
  }
  if (unique.includes("env_default")) return "env_default";
  if (experimentId === "layer1_nightly" && unique.includes("teacher")) return "teacher";
  return [...unique].sort((a, b) => a.localeCompare(b))[0] || null;
}
