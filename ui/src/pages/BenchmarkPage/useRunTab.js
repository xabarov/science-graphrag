import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { listBenchmarkCases, getBenchmarkRun, runBenchmark } from "../../services/benchmarkApi.js";
import { useI18n } from "../../i18n/useI18n.js";
import {
  buildExecutionSummary,
  buildRunPayload,
  humanizeLauncherError,
  loadLauncherPrefs,
  mergeProfileDefaults,
  resolveNightlyScope,
  resolveScopeLabel,
  saveLauncherPrefs,
  validateLauncherConfig,
} from "./benchmarkLauncherConfig.js";
import {
  aggregateGroupStatus,
  buildApiPayloadForGroupJob,
  buildGroupJobs,
  createRunGroupId,
  humanizeGroupStartError,
  loadRecentCompareSetups,
  pushRecentCompareSetup,
  saveLastRunGroup,
} from "./benchmarkRunGroup.js";
import { toggleBenchmarkCaseSelection } from "./runTabCaseToggle.js";
import {
  getExperimentsForPack,
  getLauncherPresetForExperiment,
  getUiRunnableExperiments,
  parseRunLabQueryFromSearchParams,
  RUN_MODE_GROUPED,
} from "./experimentCatalog.js";

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

/**
 * @param {object} [opts]
 * @param {(runIds: string[]) => void} [opts.onOpenAnalysisWithGroup]
 */
export function useRunTab(opts = {}) {
  const { onOpenAnalysisWithGroup } = opts;
  const { t } = useI18n();
  const [searchParams, setSearchParams] = useSearchParams();
  const runLabQuery = useMemo(() => parseRunLabQueryFromSearchParams(searchParams), [searchParams]);
  const executionMode = runLabQuery.runMode;

  const [launcherPrefs, setLauncherPrefs] = useState(() => loadLauncherPrefs());
  const benchmarkFamily = launcherPrefs.activeFamily || "layer1";
  const [mergeSafeCases, setMergeSafeCases] = useState([]);
  const [nightlyCases, setNightlyCases] = useState([]);
  const [runId, setRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [loadingCases, setLoadingCases] = useState(false);
  const [models, setModels] = useState([]);
  const [lastStartedSummary, setLastStartedSummary] = useState(null);

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

  const appliedExperimentKeyRef = useRef(/** @type {string | null} */ (null));
  const seededPackRef = useRef(/** @type {string | null} */ (null));
  const finalizedGroupRef = useRef(/** @type {string | null} */ (null));
  const defaultBatchExperimentsSeededRef = useRef(false);
  const batchModelsSeededRef = useRef(false);

  const nightlyTierParam = resolveNightlyScope(benchmarkFamily);
  const nightlyLabel = nightlyTierParam;
  const isGraphCatalog = benchmarkFamily === "graph";
  const familyPrefs = useMemo(
    () => ({
      ...(launcherPrefs.byFamily?.[benchmarkFamily] || {}),
      selectedCaseIds: launcherPrefs.byFamily?.[benchmarkFamily]?.selectedCaseIds || [],
    }),
    [benchmarkFamily, launcherPrefs.byFamily],
  );
  const selectedModelMeta = useMemo(
    () => models.find((item) => item.profile_id === familyPrefs.modelProfile) || null,
    [familyPrefs.modelProfile, models],
  );

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

  useEffect(() => {
    saveLauncherPrefs(launcherPrefs);
  }, [launcherPrefs]);

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
  }, [runLabQuery.experimentId, runLabQuery.packId]);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED || !runLabQuery.packId) return;
    if (seededPackRef.current === runLabQuery.packId) return;
    seededPackRef.current = runLabQuery.packId;
    defaultBatchExperimentsSeededRef.current = true;
    const fromPack = getExperimentsForPack(runLabQuery.packId)
      .map((e) => e.id)
      .filter((id) => Boolean(getLauncherPresetForExperiment(id)));
    setBatchExperimentIds(fromPack);
  }, [executionMode, runLabQuery.packId]);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED) {
      defaultBatchExperimentsSeededRef.current = false;
      return;
    }
    if (runLabQuery.packId) return;
    if (defaultBatchExperimentsSeededRef.current) return;
    defaultBatchExperimentsSeededRef.current = true;
    setBatchExperimentIds(getUiRunnableExperiments().map((e) => e.id));
  }, [executionMode, runLabQuery.packId]);

  useEffect(() => {
    if (executionMode !== RUN_MODE_GROUPED) {
      batchModelsSeededRef.current = false;
      return;
    }
    if (batchModelsSeededRef.current) return;
    batchModelsSeededRef.current = true;
    const mp = familyPrefs.modelProfile || "env_default";
    setBatchModelProfileIds([mp]);
  }, [executionMode, familyPrefs.modelProfile]);

  useEffect(() => {
    let cancelled = false;
    async function loadCases() {
      setLoadingCases(true);
      try {
        const fam = benchmarkFamily === "graph" ? "graph" : benchmarkFamily;
        const [merge, nightly] = await Promise.all([
          listBenchmarkCases({ family: fam, tier: "merge_safe" }),
          listBenchmarkCases({ family: fam, tier: nightlyTierParam }),
        ]);
        if (cancelled) return;
        setMergeSafeCases(merge?.items || []);
        setNightlyCases(nightly?.items || []);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_cases");
      } finally {
        if (!cancelled) setLoadingCases(false);
      }
    }
    loadCases();
    return () => {
      cancelled = true;
    };
  }, [benchmarkFamily, nightlyTierParam]);

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
        if (TERMINAL_STATUSES.includes(status)) {
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
  }, [runId]);

  const needsGroupPoll = useMemo(
    () => groupChildren.some((c) => c.runId && !TERMINAL_STATUSES.includes(c.status)),
    [groupChildren],
  );

  useEffect(() => {
    if (!needsGroupPoll) return;
    let cancelled = false;
    async function tick() {
      const current = groupChildrenRef.current;
      const updates = await Promise.all(
        current.map(async (c) => {
          if (!c.runId || TERMINAL_STATUSES.includes(c.status)) return c;
          try {
            const resp = await getBenchmarkRun(c.runId);
            const payload = resp?.data || resp;
            return { ...c, status: payload?.status || c.status, run: payload };
          } catch {
            return c;
          }
        }),
      );
      if (!cancelled) setGroupChildren(updates);
    }
    void tick();
    const intervalId = window.setInterval(() => void tick(), 2000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [needsGroupPoll]);

  useEffect(() => {
    if (needsGroupPoll) return;
    if (!groupMeta?.groupId) return;
    if (!groupChildren.length) return;
    if (finalizedGroupRef.current === groupMeta.groupId) return;
    // Do not finalize while orchestration still has rows in "queued" (prevents firing before startGroupBatch finishes).
    if (groupChildren.some((c) => c.status === "queued")) return;
    const allResolved = groupChildren.every((c) => !c.runId || TERMINAL_STATUSES.includes(c.status));
    if (!allResolved) return;
    finalizedGroupRef.current = groupMeta.groupId;
    const runIds = groupChildren.map((c) => c.runId).filter(Boolean);
    pushRecentCompareSetup({
      groupId: groupMeta.groupId,
      experimentIds: [...new Set(groupChildren.map((c) => c.experimentId))],
      modelProfileIds: [...new Set(groupChildren.map((c) => c.modelProfileId))],
      runIds,
    });
    saveLastRunGroup({
      groupId: groupMeta.groupId,
      startedAt: groupMeta.startedAt,
      completedAt: Date.now(),
      aggregateStatus: aggregateGroupStatus(groupChildren, TERMINAL_STATUSES),
      children: groupChildren,
    });
    if (runIds[0]) {
      window.localStorage.setItem("benchmark:lastRunId", runIds[0]);
    }
    setRecentSetupsVersion((v) => v + 1);
  }, [needsGroupPoll, groupMeta, groupChildren]);

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

  function updateFamilyPrefs(field, value, options = {}) {
    setLauncherPrefs((prev) => {
      const current = {
        ...(prev.byFamily?.[benchmarkFamily] || {}),
        selectedCaseIds: prev.byFamily?.[benchmarkFamily]?.selectedCaseIds || [],
      };
      let nextFamilyPrefs = {
        ...current,
        [field]: value,
      };
      if (options.markOverride) {
        nextFamilyPrefs = {
          ...nextFamilyPrefs,
          userOverrides: {
            ...current.userOverrides,
            [field]: true,
          },
        };
      }
      if (field === "modelProfile") {
        nextFamilyPrefs = mergeProfileDefaults({
          family: benchmarkFamily,
          prevPrefs: nextFamilyPrefs,
          nextModelProfile: value,
          profile: options.profile,
        });
      }
      return {
        ...prev,
        byFamily: {
          ...prev.byFamily,
          [benchmarkFamily]: nextFamilyPrefs,
        },
      };
    });
  }

  function updateSelectedCases(updater) {
    setLauncherPrefs((prev) => {
      const current = prev.byFamily?.[benchmarkFamily] || {};
      const currentSelected = current.selectedCaseIds || [];
      const nextSelected = typeof updater === "function" ? updater(currentSelected) : updater;
      return {
        ...prev,
        byFamily: {
          ...prev.byFamily,
          [benchmarkFamily]: {
            ...current,
            selectedCaseIds: nextSelected,
          },
        },
      };
    });
  }

  function handleFamilyChange(nextFamily) {
    setError(null);
    setLauncherPrefs((prev) => ({
      ...prev,
      activeFamily: nextFamily,
    }));
  }

  async function startRun() {
    if (executionMode === RUN_MODE_GROUPED) return;
    if (isGraphCatalog) return;
    setError(null);
    const validationErrors = validateLauncherConfig({
      family: benchmarkFamily,
      launcherScope: familyPrefs.launcherScope,
      caseIds: familyPrefs.selectedCaseIds,
      modelProfile: familyPrefs.modelProfile,
      customModelId: familyPrefs.customModelId,
      baseUrlOverride: familyPrefs.baseUrlOverride,
      apiKeyEnvName: familyPrefs.apiKeyEnvName,
    });
    if (validationErrors.length) {
      setError(validationErrors[0]);
      return;
    }

    const scopeLabel = resolveScopeLabel(benchmarkFamily, familyPrefs.launcherScope);
    const payload = buildRunPayload({
      family: benchmarkFamily,
      caseIds: familyPrefs.selectedCaseIds,
      launcherScope: familyPrefs.launcherScope,
      label: scopeLabel,
      modelProfile: familyPrefs.modelProfile,
      customModelId: familyPrefs.customModelId,
      goldSource: familyPrefs.goldSource,
      thresholdProfile: familyPrefs.thresholdProfile,
      baseUrlOverride: familyPrefs.baseUrlOverride,
      apiKeyEnvName: familyPrefs.apiKeyEnvName,
    });

    const res = await runBenchmark(payload).catch((e) => {
      throw new Error(humanizeLauncherError(e));
    });
    const newRunId = res?.run_id;
    if (!newRunId) throw new Error("run_id_missing");
    window.localStorage.setItem("benchmark:lastRunId", newRunId);
    setRunId(newRunId);
    setLastStartedSummary(
      buildExecutionSummary(res, {
        fallbackPayload: payload,
        fallbackScopeLabel: scopeLabel,
      }),
    );
  }

  const summary = run?.summary || {};
  const validationErrors = validateLauncherConfig({
    family: benchmarkFamily,
    launcherScope: familyPrefs.launcherScope,
    caseIds: familyPrefs.selectedCaseIds,
    modelProfile: familyPrefs.modelProfile,
    customModelId: familyPrefs.customModelId,
    baseUrlOverride: familyPrefs.baseUrlOverride,
    apiKeyEnvName: familyPrefs.apiKeyEnvName,
  });
  const pendingSummary = buildExecutionSummary(
    {
      benchmark_family: benchmarkFamily,
      run_config: {
        model_profile: familyPrefs.modelProfile,
        model_id: familyPrefs.customModelId,
        gold_source: benchmarkFamily === "layer2" ? "semantic_gold" : familyPrefs.goldSource,
        threshold_profile: benchmarkFamily === "layer2" ? null : familyPrefs.thresholdProfile,
        base_url_override: familyPrefs.baseUrlOverride,
        api_key_env_name: familyPrefs.apiKeyEnvName,
      },
    },
    {
      fallbackScopeLabel: resolveScopeLabel(benchmarkFamily, familyPrefs.launcherScope),
    },
  );
  const currentRunSummary = run
    ? buildExecutionSummary(run, {
        fallbackScopeLabel: lastStartedSummary?.scopeLabel || resolveScopeLabel(benchmarkFamily, familyPrefs.launcherScope),
      })
    : lastStartedSummary;

  const progressPercent = run?.progress?.percent ?? 0;
  const progressCompleted = run?.progress?.completed ?? 0;
  const progressTotal = run?.progress?.total ?? 0;

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
    [searchParams, setSearchParams],
  );

  // recentSetupsVersion intentionally forces re-read from localStorage after a group finalizes
  const recentCompareSetups = useMemo(() => loadRecentCompareSetups(), [recentSetupsVersion]); // eslint-disable-line react-hooks/exhaustive-deps -- storage invalidation tick

  const applyRecentCompareSetup = useCallback((setup) => {
    if (!setup || typeof setup !== "object") return;
    const eids = Array.isArray(setup.experimentIds) ? setup.experimentIds.filter(Boolean) : [];
    const mids = Array.isArray(setup.modelProfileIds) ? setup.modelProfileIds.filter(Boolean) : [];
    setBatchExperimentIds(eids);
    setBatchModelProfileIds(mids.length ? mids : ["env_default"]);
  }, []);

  return {
    TERMINAL_STATUSES,
    benchmarkFamily,
    mergeSafeCases,
    nightlyCases,
    runId,
    run,
    error,
    setError,
    loadingCases,
    nightlyLabel,
    isGraphCatalog,
    familyPrefs,
    selectedModelMeta,
    validationErrors,
    pendingSummary,
    currentRunSummary,
    summary,
    progressPercent,
    progressCompleted,
    progressTotal,
    updateFamilyPrefs,
    updateSelectedCases,
    handleFamilyChange,
    startRun,
    setModels,
    onToggleCase: (caseId) => updateSelectedCases((prev) => toggleBenchmarkCaseSelection(prev, caseId)),
    executionMode,
    setExecutionModeInUrl,
    batchExperimentIds,
    batchModelProfileIds,
    profileOptionsForBatch,
    toggleBatchExperiment,
    toggleBatchModelProfile,
    groupChildren,
    groupMeta,
    groupAggregateStatus: aggregateGroupStatus(groupChildren, TERMINAL_STATUSES),
    groupIsStarting,
    groupError,
    setGroupError,
    startGroupBatch,
    groupHandoffRunIds,
    openAnalysisForCurrentGroup,
    selectRunFromGroup,
    recentCompareSetups,
    applyRecentCompareSetup,
    singleStartDisabled: executionMode === RUN_MODE_GROUPED,
    RUN_MODE_GROUPED,
    linkedExperimentId: runLabQuery.experimentId,
  };
}
