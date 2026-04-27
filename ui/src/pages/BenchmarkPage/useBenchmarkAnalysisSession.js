import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { getBenchmarkRunSummary, listBenchmarkRuns } from "../../services/benchmarkApi.js";

import { loadLastRunGroup } from "./benchmarkRunGroup.js";
import { buildBenchmarkAnalysisSession, selectAnalysisSeed } from "./benchmarkAnalysisModel.js";

/**
 * @param {{ searchParams: URLSearchParams }} opts
 */
export function useBenchmarkAnalysisSession({ searchParams }) {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /** React Router may hand out a new URLSearchParams reference per render; key off serialized query. */
  const searchSignature = useMemo(() => searchParams.toString(), [searchParams]);

  const seed = useMemo(() => {
    const lastRunGroup = loadLastRunGroup();
    const params = new URLSearchParams(searchSignature);
    return selectAnalysisSeed({ searchParams: params, lastRunGroup });
  }, [searchSignature]);

  const fetchGenerationRef = useRef(0);

  const load = useCallback(async () => {
    const gen = ++fetchGenerationRef.current;
    if (!seed.runIds.length) {
      setSession(null);
      setError(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const listResp = await listBenchmarkRuns();
      if (gen !== fetchGenerationRef.current) return;
      const items = Array.isArray(listResp?.items) ? listResp.items : [];
      const byId = new Map(items.map((item) => [item.run_id, item]));
      const missingIds = seed.runIds.filter((runId) => !byId.has(runId));
      const fetched = await Promise.all(
        missingIds.map(async (runId) => {
          try {
            const summaryResp = await getBenchmarkRunSummary(runId);
            const payload = summaryResp?.data || summaryResp;
            return payload && payload.run_id ? payload : null;
          } catch {
            return null;
          }
        }),
      );
      if (gen !== fetchGenerationRef.current) return;
      const merged = [...items, ...fetched.filter(Boolean)];
      const nextSession = buildBenchmarkAnalysisSession({
        runIds: seed.runIds,
        runItems: merged,
        childByRunId: seed.childByRunId,
        modelProfileOrder: seed.modelProfileOrder,
        experimentOrder: seed.experimentOrder,
      });
      setSession({ ...nextSession, source: seed.source });
    } catch (e) {
      if (gen === fetchGenerationRef.current) {
        setError(e instanceof Error ? e : new Error(String(e)));
        setSession(null);
      }
    } finally {
      if (gen === fetchGenerationRef.current) setLoading(false);
    }
  }, [seed]);

  useEffect(() => {
    void load();
  }, [load]);

  return {
    seed,
    session,
    loading,
    error,
    reload: load,
  };
}
