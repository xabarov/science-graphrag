import { getExperimentById, getUiRunnableExperiments } from "./experimentCatalog.js";
import { normalizeBenchmarkMetricsPayload } from "./benchmarkScorecardModel.js";

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

/**
 * @param {...unknown} candidates
 * @returns {number | null}
 */
function pickFiniteMetricNumber(...candidates) {
  for (const value of candidates) {
    if (typeof value === "number" && Number.isFinite(value)) return value;
    if (value != null && value !== "" && Number.isFinite(Number(value))) return Number(value);
  }
  return null;
}

/**
 * @param {Record<string, any> | null | undefined} run
 * @returns {{
 *   primary: Record<string, unknown>,
 *   secondary: Record<string, unknown>,
 *   diagnostic: Record<string, unknown>,
 *   definitions: Record<string, unknown> | null,
 *   hasStructuredBuckets: boolean,
 * }}
 */
function scorecardBucketTotal(norm) {
  if (!norm || typeof norm !== "object") return 0;
  return (
    Object.keys(norm.primary || {}).length +
    Object.keys(norm.secondary || {}).length +
    Object.keys(norm.diagnostic || {}).length
  );
}

export function extractNormalizedScorecardForRun(run) {
  const summaryRoot = run?.summary && typeof run.summary === "object" ? run.summary : {};
  const runMetrics = run?.metrics && typeof run.metrics === "object" ? run.metrics : {};
  let norm = normalizeBenchmarkMetricsPayload(summaryRoot);
  if (scorecardBucketTotal(norm) === 0 && Object.keys(runMetrics).length > 0) {
    const alt = normalizeBenchmarkMetricsPayload(runMetrics);
    if (scorecardBucketTotal(alt) > 0) norm = alt;
  }
  const hasStructuredBuckets = scorecardBucketTotal(norm) > 0;
  return {
    primary: norm.primary,
    secondary: norm.secondary,
    diagnostic: norm.diagnostic,
    definitions: norm.definitions,
    hasStructuredBuckets,
  };
}

/**
 * @param {Record<string, any> | null | undefined} run
 * @returns {{ caseCount: number, passCount: number, failCount: number, avgNamesF1: number | null, avgArxivF1: number | null, avgDoiF1: number | null, avgRecall: number | null }}
 */
export function summarizeRunForAnalysis(run) {
  const summaryRoot = run?.summary && typeof run.summary === "object" ? run.summary : {};
  const merged = { ...summaryRoot };
  if (summaryRoot.primary_metrics || summaryRoot.primaryMetrics) {
    const norm = normalizeBenchmarkMetricsPayload(summaryRoot);
    Object.assign(merged, norm.primary);
  }
  const runMetrics = run?.metrics;
  if (runMetrics && typeof runMetrics === "object" && (runMetrics.primary_metrics || runMetrics.primaryMetrics)) {
    const norm = normalizeBenchmarkMetricsPayload(runMetrics);
    Object.assign(merged, norm.primary);
  }
  return {
    caseCount: Number(merged.case_count ?? merged.caseCount ?? run?.progress?.total ?? 0) || 0,
    passCount: Number(merged.pass_count ?? merged.passCount ?? 0) || 0,
    failCount: Number(merged.fail_count ?? merged.failCount ?? 0) || 0,
    avgNamesF1: pickFiniteMetricNumber(merged.avg_names_f1, merged.avgNamesF1),
    avgArxivF1: pickFiniteMetricNumber(merged.avg_sample_arxiv_f1, merged.avgSampleArxivF1),
    avgDoiF1: pickFiniteMetricNumber(merged.avg_sample_doi_f1, merged.avgSampleDoiF1),
    avgRecall: pickFiniteMetricNumber(merged.avg_layer2_recall_ratio, merged.avgLayer2RecallRatio),
  };
}

/**
 * @param {object} args
 * @param {string[]} args.runIds
 * @param {Record<string, any>[]} args.runItems
 * @param {Map<string, any>} [args.childByRunId]
 * @param {string[]} [args.modelProfileOrder]
 * @param {string[]} [args.experimentOrder]
 */
export function buildBenchmarkAnalysisSession({
  runIds,
  runItems,
  childByRunId = new Map(),
  modelProfileOrder = [],
  experimentOrder = [],
}) {
  const runById = new Map((Array.isArray(runItems) ? runItems : []).map((item) => [item.run_id, item]));
  const orderedRuns = runIds.map((id) => runById.get(id)).filter(Boolean);
  const rowsByExperiment = new Map();
  const seenVariantIds = new Set();

  for (const run of orderedRuns) {
    const experimentId = inferExperimentIdForRun(run, childByRunId);
    if (!experimentId) continue;
    const experiment = getExperimentById(experimentId);
    if (!experiment) continue;
    const variantId = inferVariantIdForRun(run, childByRunId);
    const variantLabel = variantLabelForRun(run);
    seenVariantIds.add(variantId);
    if (!rowsByExperiment.has(experimentId)) {
      rowsByExperiment.set(experimentId, {
        experimentId,
        experiment,
        benchmarkType: experiment.benchmarkType,
        variants: [],
      });
    }
    const row = rowsByExperiment.get(experimentId);
    const existing = row.variants.find((item) => item.variantId === variantId);
    const nextCell = {
      variantId,
      variantLabel,
      runId: run.run_id,
      run,
      status: String(run.status || "unknown").toLowerCase(),
      summary: summarizeRunForAnalysis(run),
      scorecard: extractNormalizedScorecardForRun(run),
    };
    if (!existing) {
      row.variants.push(nextCell);
    } else if (statusRankForRun(run) >= statusRankForRun(existing.run)) {
      Object.assign(existing, nextCell);
    }
  }

  const experimentOrderResolved = experimentOrder.length
    ? experimentOrder.filter((id) => rowsByExperiment.has(id))
    : [...rowsByExperiment.keys()].sort((a, b) => a.localeCompare(b));

  const variantOrderResolved = modelProfileOrder.length
    ? [...new Set([...modelProfileOrder, ...[...seenVariantIds].sort((a, b) => a.localeCompare(b))])]
    : [...seenVariantIds].sort((a, b) => a.localeCompare(b));

  const rows = experimentOrderResolved.map((experimentId) => {
    const row = rowsByExperiment.get(experimentId);
    const baselineVariantId = chooseBaselineVariantId(experimentId, row.variants.map((item) => item.variantId), variantOrderResolved);
    const byVariantId = new Map(row.variants.map((item) => [item.variantId, item]));
    const variants = variantOrderResolved.map((variantId) => {
      const existing = byVariantId.get(variantId);
      if (existing) return { ...existing, isBaseline: variantId === baselineVariantId };
      return {
        variantId,
        variantLabel: variantId,
        runId: null,
        run: null,
        status: "missing",
        summary: null,
        scorecard: {
          primary: {},
          secondary: {},
          diagnostic: {},
          definitions: null,
          hasStructuredBuckets: false,
        },
        isBaseline: variantId === baselineVariantId,
      };
    });
    return {
      ...row,
      baselineVariantId,
      variants,
    };
  });

  return {
    runIds,
    rows,
    variantIds: variantOrderResolved,
    experimentIds: rows.map((row) => row.experimentId),
  };
}
