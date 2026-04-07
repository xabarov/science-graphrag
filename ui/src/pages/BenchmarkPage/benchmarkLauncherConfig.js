const STORAGE_KEY = "benchmark:launcherPrefs:v2";

export const LAUNCHER_SCOPE_PRESETS = ["selected", "merge_safe", "nightly", "all"];

export function defaultLauncherPrefs() {
  return {
    activeFamily: "layer1",
    byFamily: {
      layer1: buildDefaultFamilyPrefs("layer1"),
      layer2: buildDefaultFamilyPrefs("layer2"),
      graph: buildDefaultFamilyPrefs("graph"),
    },
  };
}

export function buildDefaultFamilyPrefs(family = "layer1") {
  if (family === "layer2") {
    return {
      modelProfile: "env_default",
      customModelId: "",
      goldSource: "semantic_gold",
      thresholdProfile: "from_gold",
      baseUrlOverride: "",
      apiKeyEnvName: "",
      launcherScope: "nightly",
      selectedCaseIds: [],
      userOverrides: {
        goldSource: false,
        thresholdProfile: false,
      },
    };
  }
  if (family === "graph") {
    return {
      modelProfile: "env_default",
      customModelId: "",
      goldSource: "curated_gold",
      thresholdProfile: "from_gold",
      baseUrlOverride: "",
      apiKeyEnvName: "",
      launcherScope: "selected",
      selectedCaseIds: [],
      userOverrides: {
        goldSource: false,
        thresholdProfile: false,
      },
    };
  }
  return {
    modelProfile: "env_default",
    customModelId: "",
    goldSource: "curated_gold",
    thresholdProfile: "from_gold",
    baseUrlOverride: "",
    apiKeyEnvName: "",
    launcherScope: "selected",
    selectedCaseIds: [],
    userOverrides: {
      goldSource: false,
      thresholdProfile: false,
    },
  };
}

export function loadLauncherPrefs(storage = window.localStorage) {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return defaultLauncherPrefs();
    const parsed = JSON.parse(raw);
    return normalizeLauncherPrefs(parsed);
  } catch (_error) {
    return defaultLauncherPrefs();
  }
}

export function saveLauncherPrefs(prefs, storage = window.localStorage) {
  storage.setItem(STORAGE_KEY, JSON.stringify(normalizeLauncherPrefs(prefs)));
}

export function normalizeLauncherPrefs(input) {
  const base = defaultLauncherPrefs();
  const parsed = input && typeof input === "object" ? input : {};
  const activeFamily = normalizeFamily(parsed.activeFamily || base.activeFamily);
  return {
    activeFamily,
    byFamily: {
      layer1: normalizeFamilyPrefs("layer1", parsed.byFamily?.layer1),
      layer2: normalizeFamilyPrefs("layer2", parsed.byFamily?.layer2),
      graph: normalizeFamilyPrefs("graph", parsed.byFamily?.graph),
    },
  };
}

export function normalizeFamilyPrefs(family, input) {
  const defaults = buildDefaultFamilyPrefs(family);
  const parsed = input && typeof input === "object" ? input : {};
  const goldSource =
    family === "layer2"
      ? "semantic_gold"
      : normalizeString(parsed.goldSource) || defaults.goldSource;
  const thresholdProfile =
    family === "layer2"
      ? "from_gold"
      : normalizeString(parsed.thresholdProfile) || defaults.thresholdProfile;
  return {
    modelProfile: normalizeString(parsed.modelProfile) || defaults.modelProfile,
    customModelId: normalizeString(parsed.customModelId),
    goldSource,
    thresholdProfile,
    baseUrlOverride: normalizeString(parsed.baseUrlOverride),
    apiKeyEnvName: normalizeString(parsed.apiKeyEnvName),
    launcherScope: LAUNCHER_SCOPE_PRESETS.includes(parsed.launcherScope)
      ? parsed.launcherScope
      : defaults.launcherScope,
    selectedCaseIds: Array.isArray(parsed.selectedCaseIds)
      ? parsed.selectedCaseIds.filter((item) => typeof item === "string")
      : defaults.selectedCaseIds,
    userOverrides: {
      goldSource: Boolean(parsed.userOverrides?.goldSource),
      thresholdProfile: Boolean(parsed.userOverrides?.thresholdProfile),
    },
  };
}

export function mergeProfileDefaults({
  family,
  prevPrefs,
  nextModelProfile,
  profile,
}) {
  const next = {
    ...normalizeFamilyPrefs(family, prevPrefs),
    modelProfile: nextModelProfile || "env_default",
  };
  if (!profile || family === "graph") {
    return next;
  }
  if (family === "layer1" && !next.userOverrides.goldSource && profile.default_gold_source) {
    next.goldSource = profile.default_gold_source;
  }
  if (family === "layer1" && !next.userOverrides.thresholdProfile) {
    next.thresholdProfile = profile.default_threshold_profile || "from_gold";
  }
  if (family === "layer2") {
    next.goldSource = "semantic_gold";
    next.thresholdProfile = "from_gold";
  }
  return next;
}

export function buildRunPayload({
  family,
  caseIds,
  launcherScope,
  label,
  modelProfile,
  customModelId,
  goldSource,
  thresholdProfile,
  baseUrlOverride,
  apiKeyEnvName,
}) {
  const resolvedFamily = normalizeFamily(family);
  const payload = {
    family: resolvedFamily,
    case_ids: resolveCaseSelector({ family: resolvedFamily, launcherScope, caseIds }),
    label,
    model_profile: modelProfile || "env_default",
  };

  if (payload.model_profile === "custom" && normalizeString(customModelId)) {
    payload.model_id = normalizeString(customModelId);
  }
  if (resolvedFamily === "layer1") {
    payload.gold_source = normalizeString(goldSource) || "curated_gold";
    const tp = normalizeString(thresholdProfile);
    if (tp && tp !== "from_gold" && tp !== "none") {
      payload.threshold_profile = tp;
    }
  } else if (resolvedFamily === "layer2") {
    payload.gold_source = "semantic_gold";
  }

  if (normalizeString(baseUrlOverride)) {
    payload.base_url_override = normalizeString(baseUrlOverride);
  }
  if (normalizeString(apiKeyEnvName)) {
    payload.api_key_env_name = normalizeString(apiKeyEnvName);
  }
  return payload;
}

export function validateLauncherConfig({
  family,
  launcherScope,
  caseIds,
  modelProfile,
  customModelId,
  baseUrlOverride,
  apiKeyEnvName,
}) {
  const errors = [];
  const resolvedFamily = normalizeFamily(family);

  if (resolvedFamily === "graph") {
    errors.push("Graph benchmarks are catalog-only in the UI. Use the CLI for execution.");
  }
  if (launcherScope === "selected" && (!Array.isArray(caseIds) || caseIds.length === 0)) {
    errors.push("Select at least one case before starting a selected-cases run.");
  }
  if ((modelProfile || "env_default") === "custom" && !normalizeString(customModelId)) {
    errors.push("Custom model id is required when the custom profile is selected.");
  }
  if (normalizeString(baseUrlOverride) && !isValidHttpUrl(baseUrlOverride)) {
    errors.push("Base URL override must be a valid http(s) URL.");
  }
  if (normalizeString(apiKeyEnvName) && !/^[A-Z_][A-Z0-9_]*$/i.test(apiKeyEnvName.trim())) {
    errors.push("API key env var should look like a single environment variable name.");
  }
  return errors;
}

export function humanizeLauncherError(errorLike) {
  const detail =
    errorLike?.response?.data?.detail ||
    errorLike?.detail ||
    errorLike?.message ||
    String(errorLike || "");
  if (detail === "custom_model_id_required") {
    return "Custom profile requires a custom model id.";
  }
  if (detail === "graph_benchmark_use_cli") {
    return "Graph benchmark runs are not started from the UI. Use the CLI.";
  }
  if (detail === "invalid_family") {
    return "The selected benchmark family is not supported by the API.";
  }
  if (detail.startsWith("unknown_model_profile:")) {
    return `Unknown model profile: ${detail.split(":")[1] || "unknown"}.`;
  }
  if (detail.startsWith("model_profile_not_supported_for_family:")) {
    const [, profileId, family] = detail.split(":");
    return `Model profile ${profileId || "unknown"} is not supported for ${family || "this family"}.`;
  }
  if (detail.startsWith("gold_source_not_supported_for_family:")) {
    const [, goldSource, family] = detail.split(":");
    return `Gold source ${goldSource || "unknown"} is not supported for ${family || "this family"}.`;
  }
  if (detail.startsWith("api_key_env_missing:")) {
    return `Backend environment variable ${detail.split(":")[1] || ""} is missing.`;
  }
  if (detail.startsWith("unknown_case_ids:")) {
    return "Some selected cases are no longer available.";
  }
  if (detail === "unknown_case_selector") {
    return "Unknown run scope selector.";
  }
  return detail || "Failed to start benchmark run.";
}

export function buildExecutionSummary(run, { fallbackPayload, fallbackScopeLabel } = {}) {
  const config = run?.run_config || fallbackPayload || {};
  const family = run?.benchmark_family || fallbackPayload?.family || "layer1";
  return {
    runId: run?.run_id || null,
    status: run?.status || "queued",
    family,
    scopeLabel: fallbackScopeLabel || "custom",
    label: run?.label || fallbackPayload?.label || null,
    modelProfile: config.model_profile || fallbackPayload?.model_profile || "env_default",
    effectiveModelId: config.resolved_model_id || config.model_id || fallbackPayload?.model_id || "from environment",
    goldSource: config.gold_source || fallbackPayload?.gold_source || (family === "layer2" ? "semantic_gold" : "curated_gold"),
    thresholdProfile: config.threshold_profile || fallbackPayload?.threshold_profile || "from_gold",
    baseUrlOverride: config.base_url_override || fallbackPayload?.base_url_override || "",
    apiKeyEnvName: config.api_key_env_name || fallbackPayload?.api_key_env_name || "",
  };
}

export function resolveNightlyScope(family) {
  return normalizeFamily(family) === "layer2" ? "nightly_semantic" : "nightly_heavy";
}

export function resolveScopeLabel(family, launcherScope) {
  if (launcherScope === "nightly") return resolveNightlyScope(family);
  if (launcherScope === "all") return "all";
  if (launcherScope === "merge_safe") return "merge_safe";
  return "selected";
}

function resolveCaseSelector({ family, launcherScope, caseIds }) {
  if (launcherScope === "all") return "all";
  if (launcherScope === "merge_safe") return "merge_safe";
  if (launcherScope === "nightly") return resolveNightlyScope(family);
  return Array.isArray(caseIds) ? caseIds : [];
}

function normalizeFamily(value) {
  const normalized = normalizeString(value) || "layer1";
  if (["layer1", "layer2", "graph"].includes(normalized)) return normalized;
  return "layer1";
}

function normalizeString(value) {
  return typeof value === "string" ? value.trim() : "";
}

function isValidHttpUrl(value) {
  try {
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch (_error) {
    return false;
  }
}

