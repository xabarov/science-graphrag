/**
 * Benchmark launcher: local prefs persistence + run payload / validation.
 * Implementation lives under `./launch/`; this file is the stable import surface.
 */

export {
  LAUNCHER_SCOPE_PRESETS,
  buildDefaultFamilyPrefs,
  defaultLauncherPrefs,
  loadLauncherPrefs,
  mergeProfileDefaults,
  normalizeFamilyPrefs,
  normalizeLauncherPrefs,
  saveLauncherPrefs,
} from "./launch/benchmarkLauncherPrefs.js";

export {
  buildExecutionSummary,
  buildRunPayload,
  humanizeLauncherError,
  resolveNightlyScope,
  resolveScopeLabel,
  validateLauncherConfig,
} from "./launch/benchmarkLauncherRunPayload.js";
