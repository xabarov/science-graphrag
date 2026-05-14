import { normalizeFamily, normalizeString } from "./benchmarkLauncherInternals.js";

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
