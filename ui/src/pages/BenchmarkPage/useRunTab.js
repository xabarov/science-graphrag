import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { useI18n } from "../../i18n/useI18n.js";
import { BENCHMARK_TERMINAL_RUN_STATUSES } from "./benchmarkRunGroup.js";
import {
  buildExecutionSummary,
  loadLauncherPrefs,
  mergeProfileDefaults,
  resolveNightlyScope,
  resolveScopeLabel,
  saveLauncherPrefs,
  validateLauncherConfig,
} from "./benchmarkLauncherConfig.js";
import { mergeLauncherPrefsWithServer } from "./mergeBenchmarkLauncherPrefs.js";
import { toggleBenchmarkCaseSelection } from "./runTabCaseToggle.js";
import { parseRunLabQueryFromSearchParams, RUN_MODE_GROUPED } from "./experimentCatalog.js";
import { tryStartBenchmarkSingleRun } from "./runTab/runTabSingleRunLaunch.js";
import { useBenchmarkRunGroup } from "./useBenchmarkRunGroup.js";
import { useBenchmarkRunLabCaseLists } from "./useBenchmarkRunLabCaseLists.js";
import { useBenchmarkRunPoll } from "./useBenchmarkRunPoll.js";
import { useBenchmarkServerBenchmarkSnapshot } from "./useBenchmarkServerBenchmarkSnapshot.js";
import { useRunLabExperimentPresetFromUrl } from "./useRunLabExperimentPresetFromUrl.js";

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
  const { serverBenchmarkSnapshot, benchmarkSettingsLoadError, serverBenchmarkFetchDone } =
    useBenchmarkServerBenchmarkSnapshot();
  const benchmarkFamily = launcherPrefs.activeFamily || "layer1";
  const [runId, setRunId] = useState(() => window.localStorage.getItem("benchmark:lastRunId") || null);
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [models, setModels] = useState([]);
  const [lastStartedSummary, setLastStartedSummary] = useState(null);

  useRunLabExperimentPresetFromUrl({ runLabQuery, setLauncherPrefs });

  const nightlyTierParam = resolveNightlyScope(benchmarkFamily);
  const nightlyLabel = nightlyTierParam;
  const isGraphCatalog = benchmarkFamily === "graph";

  const mergedLauncherPrefs = useMemo(
    () => mergeLauncherPrefsWithServer({ rawLocalPrefs: launcherPrefs, serverBenchmark: serverBenchmarkSnapshot }),
    [launcherPrefs, serverBenchmarkSnapshot],
  );

  const familyPrefs = useMemo(
    () => ({
      ...(mergedLauncherPrefs.byFamily?.[benchmarkFamily] || {}),
      selectedCaseIds: launcherPrefs.byFamily?.[benchmarkFamily]?.selectedCaseIds || [],
    }),
    [benchmarkFamily, mergedLauncherPrefs.byFamily, launcherPrefs.byFamily],
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
    launcherPrefs: mergedLauncherPrefs,
    activeFamilyModelProfile: familyPrefs.modelProfile || "env_default",
    models,
    onOpenAnalysisWithGroup,
    setRunId,
    setRun,
    setLastStartedSummary,
    t,
  });

  const { mergeSafeCases, nightlyCases, loadingCases } = useBenchmarkRunLabCaseLists({
    benchmarkFamily,
    nightlyTierParam,
    setError,
  });

  useBenchmarkRunPoll({
    runId,
    setRunId,
    setRun,
    setLastStartedSummary,
    setError,
  });

  useEffect(() => {
    saveLauncherPrefs(launcherPrefs);
  }, [launcherPrefs]);

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
    setError(null);
    const result = await tryStartBenchmarkSingleRun({
      executionMode,
      isGraphCatalog,
      benchmarkFamily,
      familyPrefs,
    });
    if (result.kind === "skipped") return;
    if (result.kind === "validation") {
      setError(result.error);
      return;
    }
    setRunId(result.newRunId);
    setLastStartedSummary(result.lastStartedSummary);
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
    benchmarkServerStatus: {
      loaded: serverBenchmarkFetchDone,
      error: benchmarkSettingsLoadError,
      hasSavedDefaults: Boolean(serverBenchmarkSnapshot?.status?.has_saved_defaults),
    },
    ...runGroup,
  };
}
