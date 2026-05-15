import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { runBenchmark } from "../../services/benchmarkApi.js";
import {
  aggregateGroupStatus,
  BENCHMARK_TERMINAL_RUN_STATUSES,
  buildApiPayloadForGroupJob,
  buildGroupJobs,
  createRunGroupId,
  humanizeGroupStartError,
  loadRecentCompareSetups,
} from "./benchmarkRunGroup.js";
import { RUN_MODE_GROUPED } from "./experimentCatalog.js";
import { useBenchmarkRunGroupBatchSeed } from "./useBenchmarkRunGroupBatchSeed.js";
import { useBenchmarkRunGroupPolling } from "./useBenchmarkRunGroupPolling.js";

/**
 * Grouped / batch benchmark execution: URL runMode, batch selection, start + poll + finalize, recent setups.
 * Single-run launcher state stays in `useRunTab`.
 *
 * @param {object} opts
 * @param {URLSearchParams} opts.searchParams
 * @param {import("react-router-dom").SetURLSearchParams} opts.setSearchParams
 * @param {"single"|"grouped"} opts.executionMode
 * @param {{ experimentId: string | null, runMode: "single"|"grouped", packId: string | null }} opts.runLabQuery
 * @param {ReturnType<typeof import("./benchmarkLauncherConfig.js").loadLauncherPrefs>} opts.launcherPrefs
 * @param {string} opts.activeFamilyModelProfile
 * @param {unknown[]} opts.models
 * @param {(runIds: string[]) => void} [opts.onOpenAnalysisWithGroup]
 * @param {import("react").Dispatch<import("react").SetStateAction<string | null>>} opts.setRunId
 * @param {import("react").Dispatch<import("react").SetStateAction<Record<string, unknown> | null>>} opts.setRun
 * @param {import("react").Dispatch<import("react").SetStateAction<Record<string, unknown> | null>>} opts.setLastStartedSummary
 * @param {(key: string, vars?: Record<string, string | number>) => string} opts.t
 */
export function useBenchmarkRunGroup({
  searchParams,
  setSearchParams,
  executionMode,
  runLabQuery,
  launcherPrefs,
  activeFamilyModelProfile,
  models,
  onOpenAnalysisWithGroup,
  setRunId,
  setRun,
  setLastStartedSummary,
  t,
}) {
  const [batchExperimentIds, setBatchExperimentIds] = useState(/** @type {string[]} */ ([]));
  const [batchModelProfileIds, setBatchModelProfileIds] = useState(/** @type {string[]} */ ([]));
  /** @type {import("./benchmarkRunGroup.js").GroupChildRun[]} */
  const [groupChildren, setGroupChildren] = useState([]);
  const [groupMeta, setGroupMeta] = useState(/** @type {{ groupId: string, startedAt: number } | null} */ (null));
  const [groupIsStarting, setGroupIsStarting] = useState(false);
  const [groupError, setGroupError] = useState(/** @type {string | null} */ (null));
  const [recentSetupsVersion, setRecentSetupsVersion] = useState(0);

  const groupChildrenRef = useRef(groupChildren);
  useEffect(() => {
    groupChildrenRef.current = groupChildren;
  }, [groupChildren]);

  const finalizedGroupRef = useRef(/** @type {string | null} */ (null));

  const profileOptionsForBatch = useMemo(() => {
    const seen = new Set();
    /** @type {Array<{ profile_id: string, label?: string }>} */
    const out = [];
    for (const item of models) {
      const fams = item.family_support || [];
      if (!fams.includes("layer1") && !fams.includes("layer2")) continue;
      if (seen.has(item.profile_id)) continue;
      seen.add(item.profile_id);
      out.push({ profile_id: item.profile_id, label: item.label });
    }
    return out;
  }, [models]);

  useBenchmarkRunGroupBatchSeed({
    executionMode,
    runLabQuery,
    activeFamilyModelProfile,
    setBatchExperimentIds,
    setBatchModelProfileIds,
  });

  useBenchmarkRunGroupPolling({
    groupChildrenRef,
    groupChildren,
    setGroupChildren,
    groupMeta,
    setRecentSetupsVersion,
    finalizedGroupRef,
  });

  const setExecutionModeInUrl = useCallback(
    (mode) => {
      const next = new URLSearchParams(searchParams.toString());
      if (mode === RUN_MODE_GROUPED) next.set("runMode", RUN_MODE_GROUPED);
      else next.delete("runMode");
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const toggleBatchExperiment = useCallback((id, checked) => {
    setBatchExperimentIds((prev) => {
      const set = new Set(prev);
      if (checked) set.add(id);
      else set.delete(id);
      return [...set];
    });
  }, []);

  const toggleBatchModelProfile = useCallback((profileId, checked) => {
    setBatchModelProfileIds((prev) => {
      const set = new Set(prev);
      if (checked) set.add(profileId);
      else set.delete(profileId);
      const next = [...set];
      if (next.length === 0 && profileId) return [profileId];
      return next;
    });
  }, []);

  const startGroupBatch = useCallback(async () => {
    setGroupError(null);
    const jobs = buildGroupJobs(batchExperimentIds, batchModelProfileIds);
    if (!jobs.length) {
      setGroupError(t("benchmarkPage.runLab.grouped.errorNoJobs"));
      return;
    }
    finalizedGroupRef.current = null;
    const groupId = createRunGroupId();
    const initialChildren = jobs.map((job, i) => ({
      key: `${job.experimentId}-${job.modelProfileId}-${i}`,
      experimentId: job.experimentId,
      family: job.family,
      modelProfileId: job.modelProfileId,
      runId: null,
      status: "queued",
      error: null,
      run: null,
    }));
    setGroupMeta({ groupId, startedAt: Date.now() });
    setGroupChildren(initialChildren);
    setGroupIsStarting(true);
    try {
      for (let i = 0; i < jobs.length; i += 1) {
        const job = jobs[i];
        const childKey = initialChildren[i].key;
        try {
          const payload = buildApiPayloadForGroupJob(job, launcherPrefs);
          const res = await runBenchmark(payload).catch((e) => {
            throw new Error(humanizeGroupStartError(job, e));
          });
          const newRunId = res?.run_id;
          if (!newRunId) throw new Error("run_id_missing");
          setGroupChildren((prev) =>
            prev.map((c) =>
              c.key === childKey ? { ...c, runId: newRunId, status: "running", error: null } : c,
            ),
          );
        } catch (e) {
          const msg = e?.message || "failed_to_start_run";
          setGroupChildren((prev) =>
            prev.map((c) => (c.key === childKey ? { ...c, status: "failed", error: msg, runId: null } : c)),
          );
        }
      }
    } finally {
      setGroupIsStarting(false);
    }
  }, [batchExperimentIds, batchModelProfileIds, launcherPrefs, t]);

  const groupHandoffRunIds = useMemo(() => groupChildren.map((c) => c.runId).filter(Boolean), [groupChildren]);

  const openAnalysisForCurrentGroup = useCallback(() => {
    if (groupHandoffRunIds.length) onOpenAnalysisWithGroup?.(groupHandoffRunIds);
  }, [groupHandoffRunIds, onOpenAnalysisWithGroup]);

  const selectRunFromGroup = useCallback(
    (rid) => {
      if (!rid) return;
      window.localStorage.setItem("benchmark:lastRunId", rid);
      setRunId(rid);
      setRun(null);
      setLastStartedSummary(null);
      const next = new URLSearchParams(searchParams.toString());
      next.set("run", rid);
      next.delete("runs");
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams, setRunId, setRun, setLastStartedSummary],
  );

  const recentCompareSetups = useMemo(() => loadRecentCompareSetups(), [recentSetupsVersion]); // eslint-disable-line react-hooks/exhaustive-deps -- storage invalidation tick

  const applyRecentCompareSetup = useCallback((setup) => {
    if (!setup || typeof setup !== "object") return;
    const eids = Array.isArray(setup.experimentIds) ? setup.experimentIds.filter(Boolean) : [];
    const mids = Array.isArray(setup.modelProfileIds) ? setup.modelProfileIds.filter(Boolean) : [];
    setBatchExperimentIds(eids);
    setBatchModelProfileIds(mids.length ? mids : ["env_default"]);
  }, []);

  return {
    batchExperimentIds,
    batchModelProfileIds,
    profileOptionsForBatch,
    toggleBatchExperiment,
    toggleBatchModelProfile,
    groupChildren,
    groupMeta,
    groupAggregateStatus: aggregateGroupStatus(groupChildren, BENCHMARK_TERMINAL_RUN_STATUSES),
    groupIsStarting,
    groupError,
    setGroupError,
    startGroupBatch,
    groupHandoffRunIds,
    openAnalysisForCurrentGroup,
    selectRunFromGroup,
    recentCompareSetups,
    applyRecentCompareSetup,
    setExecutionModeInUrl,
    RUN_MODE_GROUPED,
  };
}
