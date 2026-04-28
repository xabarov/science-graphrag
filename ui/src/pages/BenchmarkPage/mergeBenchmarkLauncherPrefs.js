import {
  buildDefaultFamilyPrefs,
  normalizeFamilyPrefs,
  normalizeLauncherPrefs,
} from "./benchmarkLauncherConfig.js";

const FAMILIES = ["layer1", "layer2", "graph"];

/**
 * @param {Record<string, unknown> | null | undefined} row
 * @returns {{ modelProfile: string, customModelId: string, goldSource: string, thresholdProfile: string, baseUrlOverride: string, apiKeyEnvName: string } | null}
 */
export function serverBenchmarkRowToCamel(row) {
  if (!row || typeof row !== "object") return null;
  return {
    modelProfile: typeof row.model_profile === "string" ? row.model_profile : "env_default",
    customModelId: typeof row.custom_model_id === "string" ? row.custom_model_id : "",
    goldSource: typeof row.gold_source === "string" ? row.gold_source : "curated_gold",
    thresholdProfile: typeof row.threshold_profile === "string" ? row.threshold_profile : "from_gold",
    baseUrlOverride: typeof row.base_url_override === "string" ? row.base_url_override : "",
    apiKeyEnvName: typeof row.api_key_env_name === "string" ? row.api_key_env_name : "",
  };
}

/**
 * True when the user likely customized model / API fields vs code defaults (keep local over server).
 * @param {string} family
 * @param {object} localFam
 */
export function hasLocalModelApiOverride(family, localFam) {
  const d = buildDefaultFamilyPrefs(family);
  const lp = localFam || {};
  return (
    (lp.modelProfile || d.modelProfile) !== d.modelProfile ||
    (typeof lp.customModelId === "string" ? lp.customModelId.trim() : "") !==
      (typeof d.customModelId === "string" ? d.customModelId.trim() : "") ||
    (typeof lp.baseUrlOverride === "string" ? lp.baseUrlOverride.trim() : "") !==
      (typeof d.baseUrlOverride === "string" ? d.baseUrlOverride.trim() : "") ||
    (typeof lp.apiKeyEnvName === "string" ? lp.apiKeyEnvName.trim() : "") !==
      (typeof d.apiKeyEnvName === "string" ? d.apiKeyEnvName.trim() : "")
  );
}

/**
 * Merge persisted browser launcher prefs with server benchmark defaults from GET /v1/settings.
 * Server does not receive scope / selectedCaseIds; those always stay local.
 *
 * @param {{ rawLocalPrefs: object, serverBenchmark: object | null | undefined }} args
 * @returns {ReturnType<typeof normalizeLauncherPrefs>}
 */
export function mergeLauncherPrefsWithServer({ rawLocalPrefs, serverBenchmark }) {
  const base = normalizeLauncherPrefs(rawLocalPrefs);
  const byServer = serverBenchmark?.by_family;
  if (!byServer || typeof byServer !== "object") {
    return base;
  }
  const nextBy = { ...base.byFamily };
  for (const family of FAMILIES) {
    const localFam = normalizeFamilyPrefs(family, base.byFamily[family]);
    const srvRow = byServer[family];
    const srvCam = serverBenchmarkRowToCamel(srvRow);
    if (!srvCam) {
      nextBy[family] = localFam;
      continue;
    }
    const modelBlockLocal = hasLocalModelApiOverride(family, localFam);
    let merged = { ...localFam };
    if (!localFam.userOverrides?.goldSource) {
      merged.goldSource = srvCam.goldSource;
    }
    if (!localFam.userOverrides?.thresholdProfile) {
      merged.thresholdProfile = srvCam.thresholdProfile;
    }
    if (!modelBlockLocal) {
      merged.modelProfile = srvCam.modelProfile;
      merged.customModelId = srvCam.customModelId;
      merged.baseUrlOverride = srvCam.baseUrlOverride;
      merged.apiKeyEnvName = srvCam.apiKeyEnvName;
    }
    nextBy[family] = normalizeFamilyPrefs(family, merged);
  }
  return { ...base, byFamily: nextBy };
}
