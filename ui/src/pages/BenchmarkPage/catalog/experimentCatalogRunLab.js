import { getExperimentById } from "./experimentCatalogData.js";

/** Canonical `runMode` query values for Run Lab (Phase 2). */
export const RUN_MODE_SINGLE = "single";
export const RUN_MODE_GROUPED = "grouped";

const LAUNCHER_SCOPE_FROM_PRESET = {
  nightly: "nightly",
  merge_safe: "merge_safe",
  all: "all",
  selected: "selected",
};

/**
 * @param {string | null | undefined} v
 * @returns {"single"|"grouped"}
 */
export function normalizeRunMode(v) {
  if (v === RUN_MODE_GROUPED) return RUN_MODE_GROUPED;
  return RUN_MODE_SINGLE;
}

/**
 * Map catalog experiment id to launcher family + scope for Run Lab presets.
 * @param {string | null | undefined} experimentId
 * @returns {{ experimentId: string, uiFamily: "layer1"|"layer2", launcherScope: string } | null}
 */
export function getLauncherPresetForExperiment(experimentId) {
  const id = typeof experimentId === "string" ? experimentId.trim() : "";
  if (!id) return null;
  const exp = getExperimentById(id);
  if (!exp || exp.runnableSurface !== "ui") return null;
  const fam = exp.uiFamily;
  if (fam !== "layer1" && fam !== "layer2") return null;
  const preset = exp.launcherScopePreset;
  const launcherScope =
    preset && typeof preset === "string" && preset in LAUNCHER_SCOPE_FROM_PRESET
      ? LAUNCHER_SCOPE_FROM_PRESET[/** @type {keyof typeof LAUNCHER_SCOPE_FROM_PRESET} */ (preset)]
      : "nightly";
  return { experimentId: exp.id, uiFamily: fam, launcherScope };
}

/**
 * Merge Run Lab deep-link params into search params (preserves unrelated keys).
 * @param {URLSearchParams} current
 * @param {{ experimentId?: string | null, runMode?: "single"|"grouped" | null, packId?: string | null }} patch
 */
export function mergeRunLabQueryIntoSearchParams(current, patch) {
  const next = new URLSearchParams(current.toString());
  if (patch.experimentId !== undefined) {
    const v = typeof patch.experimentId === "string" ? patch.experimentId.trim() : "";
    if (v) next.set("experiment", v);
    else next.delete("experiment");
  }
  if (patch.runMode !== undefined && patch.runMode !== null) {
    if (patch.runMode === RUN_MODE_GROUPED) next.set("runMode", RUN_MODE_GROUPED);
    else next.delete("runMode");
  }
  if (patch.packId !== undefined) {
    const v = typeof patch.packId === "string" ? patch.packId.trim() : "";
    if (v) next.set("pack", v);
    else next.delete("pack");
  }
  return next;
}

/**
 * @param {URLSearchParams | { get: (k: string) => string | null }} params
 */
export function parseRunLabQueryFromSearchParams(params) {
  const experimentRaw = params.get("experiment");
  const packRaw = params.get("pack");
  return {
    experimentId: experimentRaw && experimentRaw.trim() ? experimentRaw.trim() : null,
    runMode: normalizeRunMode(params.get("runMode")),
    packId: packRaw && packRaw.trim() ? packRaw.trim() : null,
  };
}
