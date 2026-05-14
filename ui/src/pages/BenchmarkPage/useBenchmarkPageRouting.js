import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import {
  mergeBenchmarkTabIntoSearchParams,
  mergeRunLabQueryIntoSearchParams,
  normalizeAnalysisView,
  parseBenchmarkTabQuery,
} from "./experimentCatalog.js";

/**
 * URL-driven shell state for Benchmark page (tabs, analysis sub-view, run/case selection).
 */
export function useBenchmarkPageRouting() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [tabIdx, setTabIdx] = useState(0);
  const [analysisView, setAnalysisView] = useState(/** @type {"overview"|"results"|"compare"|"workbench"} */ ("overview"));
  const [selectedRunId, setSelectedRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [selectedCaseId, setSelectedCaseId] = useState(null);

  const canonicalAdminPath = useMemo(() => {
    const query = searchParams.toString();
    return `/admin/benchmarks${query ? `?${query}` : ""}`;
  }, [searchParams]);

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect -- sync shell from URL (external nav / back) */
    const tabParam = searchParams.get("tab");
    const avParam = searchParams.get("analysisView");
    const runParam = searchParams.get("run");
    const caseParam = searchParams.get("case");
    const { tabIndex, analysisView: av } = parseBenchmarkTabQuery(tabParam, avParam);
    setTabIdx(tabIndex);
    setAnalysisView(av);
    if (searchParams.has("run")) {
      if (runParam) {
        setSelectedRunId(runParam);
        window.localStorage.setItem("benchmark:lastRunId", runParam);
      } else {
        setSelectedRunId(null);
      }
    }
    if (searchParams.has("case")) {
      setSelectedCaseId(caseParam || null);
    }
    const workbenchFixtureFirst =
      tabIndex === 3 && av === "workbench" && Boolean(caseParam) && !runParam;
    if (workbenchFixtureFirst) {
      setSelectedRunId(null);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [searchParams]);

  const onNavigate = useCallback(
    (opts) => {
      const nextIdx = opts.tabIndex;
      let nextAv = /** @type {"overview"|"results"|"compare"|"workbench"} */ ("overview");
      if (nextIdx === 3) {
        nextAv = opts.analysisView != null ? normalizeAnalysisView(opts.analysisView) : "overview";
        setAnalysisView(nextAv);
      }
      setTabIdx(nextIdx);
      let merged = mergeBenchmarkTabIntoSearchParams(
        searchParams,
        nextIdx,
        nextIdx === 3 ? nextAv : "overview",
      );
      if ("experimentId" in opts || "runMode" in opts || "packId" in opts) {
        merged = mergeRunLabQueryIntoSearchParams(merged, {
          experimentId: "experimentId" in opts ? opts.experimentId : undefined,
          runMode: "runMode" in opts ? opts.runMode : undefined,
          packId: "packId" in opts ? opts.packId : undefined,
        });
      }
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleOpenAnalysisWithGroup = useCallback(
    (runIds) => {
      if (!runIds?.length) return;
      const first = runIds[0];
      setSelectedRunId(first);
      window.localStorage.setItem("benchmark:lastRunId", first);
      setTabIdx(3);
      setAnalysisView(runIds.length > 1 ? "compare" : "results");
      let merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, runIds.length > 1 ? "compare" : "results");
      merged.set("run", first);
      if (runIds.length > 1) merged.set("runs", runIds.join(","));
      else merged.delete("runs");
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  /**
   * @param {string | null} runId
   * @param {string | null} [caseId]
   * @param {{ caseFamily?: string | null, compareBaselineRunId?: string | null, compareMetric?: string | null }} [opts]
   */
  const openWorkbench = useCallback(
    (runId, caseId = null, opts = {}) => {
      if (runId) {
        setSelectedRunId(runId);
        window.localStorage.setItem("benchmark:lastRunId", runId);
      } else {
        setSelectedRunId(null);
      }
      setSelectedCaseId(caseId);
      setTabIdx(3);
      setAnalysisView("workbench");
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, "workbench");
      if (runId) merged.set("run", runId);
      else merged.delete("run");
      if (caseId) merged.set("case", caseId);
      else merged.delete("case");

      if (runId) {
        merged.delete("caseFamily");
      } else if (caseId && opts.caseFamily) {
        merged.set("caseFamily", opts.caseFamily);
      } else if (!caseId) {
        merged.delete("caseFamily");
      }

      if (opts.compareBaselineRunId && opts.compareMetric) {
        merged.set("cmpBaseline", opts.compareBaselineRunId);
        merged.set("cmpMetric", encodeURIComponent(String(opts.compareMetric)));
      } else {
        merged.delete("cmpBaseline");
        merged.delete("cmpMetric");
      }
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const openCaseFromCatalog = useCallback(
    (catalogCaseId, family) => {
      if (!catalogCaseId) return;
      setSelectedRunId(null);
      setSelectedCaseId(catalogCaseId);
      setTabIdx(3);
      setAnalysisView("workbench");
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, "workbench");
      merged.delete("run");
      merged.set("case", catalogCaseId);
      merged.set("caseFamily", family || "layer1");
      merged.delete("cmpBaseline");
      merged.delete("cmpMetric");
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const setAnalysisViewInUrl = useCallback(
    (view) => {
      const v = normalizeAnalysisView(view);
      setAnalysisView(v);
      const merged = mergeBenchmarkTabIntoSearchParams(searchParams, 3, v);
      setSearchParams(merged, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleSelectRun = useCallback(
    (runId) => {
      setSelectedRunId(runId);
      if (runId) window.localStorage.setItem("benchmark:lastRunId", runId);
      const next = new URLSearchParams(searchParams.toString());
      if (runId) next.set("run", runId);
      else next.delete("run");
      next.delete("cmpBaseline");
      next.delete("cmpMetric");
      if (!runId) {
        next.delete("case");
        setSelectedCaseId(null);
      }
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const handleSelectCase = useCallback(
    (caseId) => {
      setSelectedCaseId(caseId);
      const next = new URLSearchParams(searchParams.toString());
      if (caseId) next.set("case", caseId);
      else next.delete("case");
      next.delete("cmpBaseline");
      next.delete("cmpMetric");
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  return {
    searchParams,
    tabIdx,
    analysisView,
    selectedRunId,
    selectedCaseId,
    canonicalAdminPath,
    onNavigate,
    handleOpenAnalysisWithGroup,
    openWorkbench,
    openCaseFromCatalog,
    setAnalysisViewInUrl,
    handleSelectRun,
    handleSelectCase,
  };
}
