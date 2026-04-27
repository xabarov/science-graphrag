import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useI18n } from "../../i18n/useI18n.js";
import { listBenchmarkCases, getBenchmarkRun, runBenchmark } from "../../services/benchmarkApi.js";
import { BENCHMARK_TERMINAL_RUN_STATUSES } from "./benchmarkRunGroup.js";
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
import { toggleBenchmarkCaseSelection } from "./runTabCaseToggle.js";
import {
  getLauncherPresetForExperiment,
  parseRunLabQueryFromSearchParams,
  RUN_MODE_GROUPED,
} from "./experimentCatalog.js";
import { useBenchmarkRunGroup } from "./useBenchmarkRunGroup.js";

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

  const appliedExperimentKeyRef = useRef(/** @type {string | null} */ (null));

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

  const runGroup = useBenchmarkRunGroup({
    searchParams,
    setSearchParams,
    executionMode,
    runLabQuery,
    launcherPrefs,
    activeFamilyModelProfile: familyPrefs.modelProfile || "env_default",
    models,
    onOpenAnalysisWithGroup,
    setRunId,
    setRun,
    setLastStartedSummary,
    t,
  });

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
  }, [runId]);

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

  return {
    TERMINAL_STATUSES: BENCHMARK_TERMINAL_RUN_STATUSES,
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
    singleStartDisabled: executionMode === RUN_MODE_GROUPED,
    linkedExperimentId: runLabQuery.experimentId,
    ...runGroup,
  };
}
