import { useEffect, useRef } from "react";

import { getLauncherPresetForExperiment } from "./experimentCatalog.js";

/**
 * Applies Run Lab deep-link `experiment` / `pack` into launcher prefs (once per key).
 *
 * @param {{
 *   runLabQuery: { experimentId: string | null, packId: string | null },
 *   setLauncherPrefs: import("react").Dispatch<import("react").SetStateAction<Record<string, unknown>>>,
 * }} params
 */
export function useRunLabExperimentPresetFromUrl({ runLabQuery, setLauncherPrefs }) {
  const appliedExperimentKeyRef = useRef(/** @type {string | null} */ (null));

  useEffect(() => {
    if (!runLabQuery.experimentId) {
      appliedExperimentKeyRef.current = null;
      return;
    }
    const preset = getLauncherPresetForExperiment(runLabQuery.experimentId);
    if (!preset) return;
    const key = `${runLabQuery.experimentId}:${runLabQuery.packId || ""}`;
    if (appliedExperimentKeyRef.current === key) return;
    appliedExperimentKeyRef.current = key;
    setLauncherPrefs((prev) => ({
      ...prev,
      activeFamily: preset.uiFamily,
      byFamily: {
        ...prev.byFamily,
        [preset.uiFamily]: {
          ...(prev.byFamily?.[preset.uiFamily] || {}),
          selectedCaseIds: prev.byFamily?.[preset.uiFamily]?.selectedCaseIds || [],
          launcherScope: preset.launcherScope,
        },
      },
    }));
  }, [runLabQuery.experimentId, runLabQuery.packId, setLauncherPrefs]);
}
