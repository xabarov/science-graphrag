import { useEffect, useState } from "react";

import { getSettingsSnapshot } from "../SettingsPage/settingsApi.js";

/**
 * Loads persisted benchmark defaults from the settings snapshot (Run Lab).
 */
export function useBenchmarkServerBenchmarkSnapshot() {
  const [serverBenchmarkSnapshot, setServerBenchmarkSnapshot] = useState(/** @type {object | null} */ (null));
  const [benchmarkSettingsLoadError, setBenchmarkSettingsLoadError] = useState(/** @type {string | null} */ (null));
  const [serverBenchmarkFetchDone, setServerBenchmarkFetchDone] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const snap = await getSettingsSnapshot();
        if (cancelled) return;
        setServerBenchmarkSnapshot(snap?.benchmark || null);
        setBenchmarkSettingsLoadError(null);
      } catch (e) {
        if (!cancelled) {
          setServerBenchmarkSnapshot(null);
          setBenchmarkSettingsLoadError(e?.message || "benchmark_settings_load_failed");
        }
      } finally {
        if (!cancelled) setServerBenchmarkFetchDone(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    serverBenchmarkSnapshot,
    benchmarkSettingsLoadError,
    serverBenchmarkFetchDone,
  };
}
