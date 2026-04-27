/**
 * Client-side grouped benchmark execution: job building, persistence, recent setups.
 * Backend run-group API is optional; this module supports frontend-orchestrated batches.
 */

import {
  buildDefaultFamilyPrefs,
  buildRunPayload,
  humanizeLauncherError,
  normalizeFamilyPrefs,
  resolveScopeLabel,
  validateLauncherConfig,
} from "./benchmarkLauncherConfig.js";
import { getLauncherPresetForExperiment } from "./experimentCatalog.js";

// loadLauncherPrefs return type for group job payloads
/** @typedef {ReturnType<typeof import("./benchmarkLauncherConfig.js").loadLauncherPrefs>} LauncherPrefsV2 */

export const LS_LAST_RUN_GROUP = "benchmark:lastRunGroup";
export const LS_RECENT_COMPARE_SETUPS = "benchmark:recentCompareSetups";
const MAX_RECENT = 8;

/** Terminal statuses for benchmark runs (single + grouped polling). */
export const BENCHMARK_TERMINAL_RUN_STATUSES = Object.freeze(["completed", "failed", "cancelled"]);

/**
 * @typedef {object} GroupJob
 * @property {string} experimentId
 * @property {"layer1"|"layer2"} family
 * @property {string} launcherScope
 * @property {string} modelProfileId
 */

/**
 * @typedef {object} GroupChildRun
 * @property {string} key
 * @property {string} experimentId
 * @property {"layer1"|"layer2"} family
 * @property {string} modelProfileId
 * @property {string | null} runId
 * @property {string} status
 * @property {string | null} error
 * @property {Record<string, unknown> | null} run
 */

/**
 * Cartesian product of UI-runnable experiments and model profile ids.
 * @param {string[]} experimentIds
 * @param {string[]} modelProfileIds
 * @returns {GroupJob[]}
 */
export function buildGroupJobs(experimentIds, modelProfileIds) {
  const expIds = Array.isArray(experimentIds) ? [...new Set(experimentIds.filter(Boolean))] : [];
  const profiles = Array.isArray(modelProfileIds) ? [...new Set(modelProfileIds.filter(Boolean))] : [];
  /** @type {GroupJob[]} */
  const jobs = [];
  for (const eid of expIds) {
    const preset = getLauncherPresetForExperiment(eid);
    if (!preset) continue;
    for (const mp of profiles) {
      jobs.push({
        experimentId: eid,
        family: /** @type {"layer1"|"layer2"} */ (preset.uiFamily),
        launcherScope: preset.launcherScope,
        modelProfileId: mp,
      });
    }
  }
  return jobs;
}

/**
 * @param {GroupJob} job
 * @param {LauncherPrefsV2} launcherPrefs
 */
export function buildApiPayloadForGroupJob(job, launcherPrefs) {
  const base = launcherPrefs.byFamily?.[job.family] || buildDefaultFamilyPrefs(job.family);
  const fp = normalizeFamilyPrefs(job.family, {
    ...base,
    modelProfile: job.modelProfileId,
  });
  const errors = validateLauncherConfig({
    family: job.family,
    launcherScope: job.launcherScope,
    caseIds: fp.selectedCaseIds,
    modelProfile: fp.modelProfile,
    customModelId: fp.customModelId,
    baseUrlOverride: fp.baseUrlOverride,
    apiKeyEnvName: fp.apiKeyEnvName,
  });
  if (errors.length) {
    throw new Error(errors[0]);
  }
  const scopeLabel = resolveScopeLabel(job.family, job.launcherScope);
  const label = `${job.experimentId} · ${scopeLabel}`;
  return buildRunPayload({
    family: job.family,
    caseIds: fp.selectedCaseIds,
    launcherScope: job.launcherScope,
    label,
    modelProfile: fp.modelProfile,
    customModelId: fp.customModelId,
    goldSource: fp.goldSource,
    thresholdProfile: fp.thresholdProfile,
    baseUrlOverride: fp.baseUrlOverride,
    apiKeyEnvName: fp.apiKeyEnvName,
  });
}

/**
 * @param {GroupJob} job
 * @param {unknown} errorLike
 */
export function humanizeGroupStartError(job, errorLike) {
  const base = humanizeLauncherError(errorLike);
  return `${job.experimentId} (${job.family}): ${base}`;
}

/**
 * @param {object} session
 * @param {string} session.groupId
 * @param {GroupChildRun[]} session.children
 * @param {number} [session.startedAt]
 * @param {number} [session.completedAt]
 */
export function saveLastRunGroup(session, storage = window.localStorage) {
  try {
    storage.setItem(LS_LAST_RUN_GROUP, JSON.stringify(session));
  } catch (_e) {
    // ignore quota
  }
}

export function loadLastRunGroup(storage = window.localStorage) {
  try {
    const raw = storage.getItem(LS_LAST_RUN_GROUP);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || !Array.isArray(parsed.children)) return null;
    return parsed;
  } catch (_e) {
    return null;
  }
}

/**
 * @param {object} setup
 * @param {string[]} setup.experimentIds
 * @param {string[]} setup.modelProfileIds
 * @param {string[]} setup.runIds
 * @param {string} [setup.groupId]
 */
export function pushRecentCompareSetup(setup, storage = window.localStorage) {
  try {
    const prev = loadRecentCompareSetups(storage);
    const next = [
      {
        savedAt: Date.now(),
        groupId: setup.groupId || null,
        experimentIds: setup.experimentIds || [],
        modelProfileIds: setup.modelProfileIds || [],
        runIds: setup.runIds || [],
      },
      ...prev.filter((row) => JSON.stringify(row.runIds) !== JSON.stringify(setup.runIds)),
    ].slice(0, MAX_RECENT);
    storage.setItem(LS_RECENT_COMPARE_SETUPS, JSON.stringify(next));
  } catch (_e) {
    // ignore
  }
}

export function loadRecentCompareSetups(storage = window.localStorage) {
  try {
    const raw = storage.getItem(LS_RECENT_COMPARE_SETUPS);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (_e) {
    return [];
  }
}

export function createRunGroupId() {
  return globalThis.crypto?.randomUUID?.() ?? `rg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * @param {GroupChildRun[]} children
 * @param {readonly string[]} terminalStatuses
 */
export function aggregateGroupStatus(children, terminalStatuses = BENCHMARK_TERMINAL_RUN_STATUSES) {
  const term = new Set(terminalStatuses);
  if (!children.length) return "idle";
  const withId = children.filter((c) => c.runId);
  if (withId.length === 0) return children.some((c) => c.status === "failed") ? "failed" : "idle";
  const allTerminal = withId.every((c) => term.has(c.status));
  if (!allTerminal) return "running";
  const anyFailed = withId.some((c) => c.status === "failed");
  const anyOk = withId.some((c) => c.status === "completed");
  if (anyFailed && anyOk) return "partial";
  if (anyFailed) return "failed";
  return "completed";
}

