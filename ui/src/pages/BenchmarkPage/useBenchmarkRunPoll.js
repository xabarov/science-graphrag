import { useEffect } from "react";

import { getBenchmarkRun } from "../../services/benchmarkApi.js";
import { BENCHMARK_TERMINAL_RUN_STATUSES } from "./benchmarkRunGroup.js";

/**
 * Polls benchmark run status while a run id is active.
 *
 * @param {{
 *   runId: string | null,
 *   setRunId: import("react").Dispatch<import("react").SetStateAction<string | null>>,
 *   setRun: import("react").Dispatch<import("react").SetStateAction<Record<string, unknown> | null>>,
 *   setLastStartedSummary: import("react").Dispatch<import("react").SetStateAction<Record<string, unknown> | null>>,
 *   setError: import("react").Dispatch<import("react").SetStateAction<string | null>>,
 * }} params
 */
export function useBenchmarkRunPoll({ runId, setRunId, setRun, setLastStartedSummary, setError }) {
  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    let intervalId = null;

    async function tick() {
      try {
        const resp = await getBenchmarkRun(runId);
        const payload = resp?.data || resp;
        if (cancelled) return;
        setRun(payload);

        const status = payload?.status;
        if (BENCHMARK_TERMINAL_RUN_STATUSES.includes(status)) {
          if (intervalId) clearInterval(intervalId);
        }
      } catch (e) {
        if (cancelled) return;
        const statusCode = e?.response?.status;
        if (statusCode === 404) {
          window.localStorage.removeItem("benchmark:lastRunId");
          setRunId(null);
          setRun(null);
          setLastStartedSummary(null);
          setError(null);
          if (intervalId) clearInterval(intervalId);
          return;
        }
        setError(e?.message || "failed_to_fetch_run");
      }
    }

    tick();
    intervalId = window.setInterval(tick, 2000);
    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [runId, setRunId, setRun, setLastStartedSummary, setError]);
}
