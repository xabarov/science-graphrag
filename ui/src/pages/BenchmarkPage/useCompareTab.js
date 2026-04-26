import { useCallback, useEffect, useMemo, useState } from "react";

import { compareBenchmarkRuns, listBenchmarkRuns } from "../../services/benchmarkApi.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import {
  downloadBenchmarkCompareText,
  filterBenchmarkCompareDeltaRows,
} from "./benchmarkCompareModel.js";

export function useCompareTab() {
  const [runsPayload, setRunsPayload] = useState(null);
  const [baselineId, setBaselineId] = useState("");
  const [currentId, setCurrentId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [caseFilter, setCaseFilter] = useState("");
  const [metricFilter, setMetricFilter] = useState("");
  const [showUnchanged, setShowUnchanged] = useState(false);

  const refreshRuns = useCallback(async () => {
    const resp = await listBenchmarkRuns();
    setRunsPayload(resp);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await refreshRuns();
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_runs");
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [refreshRuns]);

  const items = runsPayload?.items || [];

  async function runCompare() {
    if (!baselineId || !currentId) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const resp = await compareBenchmarkRuns(baselineId, currentId);
      setResult(resp?.data || resp);
    } catch (e) {
      setError(formatResearchApiError(e) || "compare_failed");
    } finally {
      setLoading(false);
    }
  }

  const summary = result?.summary;
  const metaDelta = result?.run_metadata_delta;

  const regressionsFiltered = useMemo(
    () => filterBenchmarkCompareDeltaRows(result?.regressions, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );
  const improvementsFiltered = useMemo(
    () => filterBenchmarkCompareDeltaRows(result?.improvements, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );
  const unchangedFiltered = useMemo(
    () => filterBenchmarkCompareDeltaRows(result?.unchanged, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );

  function exportCompareJson() {
    if (!result) return;
    downloadBenchmarkCompareText(
      `benchmark-compare-${result.baseline_run_id?.slice(0, 8) || "base"}-${result.current_run_id?.slice(0, 8) || "cur"}.json`,
      JSON.stringify(result, null, 2),
      "application/json",
    );
  }

  function exportCompareMarkdown() {
    if (!result) return;
    const md = result.markdown || "";
    downloadBenchmarkCompareText(
      `benchmark-compare-${result.baseline_run_id?.slice(0, 8) || "base"}-${result.current_run_id?.slice(0, 8) || "cur"}.md`,
      md,
      "text/markdown;charset=utf-8",
    );
  }

  return {
    items,
    baselineId,
    setBaselineId,
    currentId,
    setCurrentId,
    result,
    error,
    loading,
    caseFilter,
    setCaseFilter,
    metricFilter,
    setMetricFilter,
    showUnchanged,
    setShowUnchanged,
    refreshRuns,
    runCompare,
    exportCompareJson,
    exportCompareMarkdown,
    summary,
    metaDelta,
    regressionsFiltered,
    improvementsFiltered,
    unchangedFiltered,
  };
}
