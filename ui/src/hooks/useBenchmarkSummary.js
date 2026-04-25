import { useCallback, useEffect, useState } from "react";

import { fetchDecisionGateSummary } from "../services/benchmarkApi.js";

/**
 * Load ``GET /v1/benchmark/decision-gate-summary`` once on mount (Benchmark trust strip).
 * @returns {{ data: object | null, error: Error | null, loading: boolean, reload: () => Promise<void> }}
 */
export function useBenchmarkSummary() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await fetchDecisionGateSummary();
      setData(next);
    } catch (e) {
      setError(e instanceof Error ? e : new Error(String(e)));
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { data, error, loading, reload: load };
}
