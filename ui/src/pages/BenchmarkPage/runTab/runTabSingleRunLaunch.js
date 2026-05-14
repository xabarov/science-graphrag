import { runBenchmark } from "../../services/benchmarkApi.js";
import {
  buildExecutionSummary,
  buildRunPayload,
  humanizeLauncherError,
  resolveScopeLabel,
  validateLauncherConfig,
} from "../benchmarkLauncherConfig.js";
import { RUN_MODE_GROUPED } from "../catalog/experimentCatalogRunLab.js";

/**
 * Start a single benchmark run (Run tab) after validation.
 *
 * @param {{
 *   executionMode: string,
 *   isGraphCatalog: boolean,
 *   benchmarkFamily: string,
 *   familyPrefs: Record<string, unknown>,
 * }} args
 * @returns {Promise<{ kind: "skipped" } | { kind: "validation", error: unknown } | { kind: "started", newRunId: string, lastStartedSummary: object }>}
 */
export async function tryStartBenchmarkSingleRun(args) {
  const { executionMode, isGraphCatalog, benchmarkFamily, familyPrefs } = args;
  if (executionMode === RUN_MODE_GROUPED) return { kind: "skipped" };
  if (isGraphCatalog) return { kind: "skipped" };

  const validationErrors = validateLauncherConfig({
    family: benchmarkFamily,
    launcherScope: familyPrefs.launcherScope,
    caseIds: familyPrefs.selectedCaseIds,
    modelProfile: familyPrefs.modelProfile,
    customModelId: familyPrefs.customModelId,
    baseUrlOverride: familyPrefs.baseUrlOverride,
    apiKeyEnvName: familyPrefs.apiKeyEnvName,
  });
  if (validationErrors.length) {
    return { kind: "validation", error: validationErrors[0] };
  }

  const scopeLabel = resolveScopeLabel(benchmarkFamily, familyPrefs.launcherScope);
  const payload = buildRunPayload({
    family: benchmarkFamily,
    caseIds: familyPrefs.selectedCaseIds,
    launcherScope: familyPrefs.launcherScope,
    label: scopeLabel,
    modelProfile: familyPrefs.modelProfile,
    customModelId: familyPrefs.customModelId,
    goldSource: familyPrefs.goldSource,
    thresholdProfile: familyPrefs.thresholdProfile,
    baseUrlOverride: familyPrefs.baseUrlOverride,
    apiKeyEnvName: familyPrefs.apiKeyEnvName,
  });

  const res = await runBenchmark(payload).catch((e) => {
    throw new Error(humanizeLauncherError(e));
  });
  const newRunId = res?.run_id;
  if (!newRunId) throw new Error("run_id_missing");
  window.localStorage.setItem("benchmark:lastRunId", newRunId);
  const lastStartedSummary = buildExecutionSummary(res, {
    fallbackPayload: payload,
    fallbackScopeLabel: scopeLabel,
  });
  return { kind: "started", newRunId, lastStartedSummary };
}
