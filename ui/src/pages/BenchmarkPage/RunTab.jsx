import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import LinearProgress from "@mui/material/LinearProgress";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

import { listBenchmarkCases, getBenchmarkRun, runBenchmark } from "../../services/benchmarkApi.js";
import { CursorButton } from "../../components/common/index.js";
import BenchmarkLauncherPanel from "./BenchmarkLauncherPanel.jsx";
import BenchmarkRunConfigSummary from "./BenchmarkRunConfigSummary.jsx";
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

const TERMINAL_STATUSES = ["completed", "failed", "cancelled"];

function _toggleCase(prev, caseId) {
  if (prev.includes(caseId)) return prev.filter((x) => x !== caseId);
  return [...prev, caseId];
}

export default function RunTab({ onSwitchToResults }) {
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

  const progressPercent = run?.progress?.percent ?? 0;
  const progressCompleted = run?.progress?.completed ?? 0;
  const progressTotal = run?.progress?.total ?? 0;

  const summary = run?.summary || {};
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

  useEffect(() => {
    saveLauncherPrefs(launcherPrefs);
  }, [launcherPrefs]);

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

  const title = isGraphCatalog
    ? "Graph-v1 cases (catalog only)"
    : benchmarkFamily === "layer2"
      ? "Запуск Layer-2 (semantic) Benchmark"
      : "Запуск Layer-1 Benchmark";
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

  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 2 }}>{title}</Typography>

      {isGraphCatalog ? (
        <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          Graph-v1 runs ingest into Neo4j/Qdrant and are not started from this UI. Use:{" "}
          <code>science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/&lt;case_id&gt;</code> or CI{" "}
          <code>integration-nightly.yml</code>. Browse cases below; open <strong>Кейсы</strong> for{" "}
          <code>graph_expectations</code> preview.
        </Alert>
      ) : null}

      {error && (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      )}

      <BenchmarkLauncherPanel
        benchmarkFamily={benchmarkFamily}
        familyPrefs={familyPrefs}
        loadingCases={loadingCases}
        mergeSafeCases={mergeSafeCases}
        nightlyCases={nightlyCases}
        nightlyLabel={nightlyLabel}
        validationErrors={validationErrors}
        modelMeta={selectedModelMeta}
        pendingSummary={pendingSummary}
        onFamilyChange={handleFamilyChange}
        onFamilyPrefsChange={updateFamilyPrefs}
        onModelsLoaded={setModels}
        onToggleCase={(caseId) => updateSelectedCases((prev) => _toggleCase(prev, caseId))}
        onStartRun={() => startRun().catch((e) => setError(e?.message || "failed_to_start_run"))}
      />

      <Divider sx={{ my: 2 }} />

      <Typography sx={{ fontWeight: 600, mb: 1 }}>Текущий run</Typography>
      {!runId ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Запустите бенчмарк, чтобы увидеть прогресс.</Typography>
      ) : (
        <Box>
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
            run_id: <span style={{ color: "rgba(255,255,255,0.9)" }}>{runId}</span>
          </Typography>

          <LinearProgress variant="determinate" value={progressPercent} />
          <Typography sx={{ color: "rgba(255,255,255,0.6)", mt: 1 }}>
            {progressCompleted}/{progressTotal} ({progressPercent.toFixed(1)}%)
          </Typography>

          {currentRunSummary ? <BenchmarkRunConfigSummary summary={currentRunSummary} title="Current run config" /> : null}

          {run && (
            <Box sx={{ mt: 1, display: "flex", gap: 2, flexWrap: "wrap" }}>
              {(run.benchmark_family || "layer1") === "layer2" ? (
                <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                  avg layer2 recall ratio: {(summary.avg_layer2_recall_ratio ?? 0).toFixed(3)}
                </Typography>
              ) : (
                <>
                  <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                    avg names_f1: {(summary.avg_names_f1 ?? 0).toFixed(3)}
                  </Typography>
                  <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                    avg sample_arxiv_f1: {(summary.avg_sample_arxiv_f1 ?? 0).toFixed(3)}
                  </Typography>
                </>
              )}
            </Box>
          )}

          <Box sx={{ mt: 2 }}>
            <CursorButton
              disabled={!run || !TERMINAL_STATUSES.includes(run.status)}
              onClick={() => onSwitchToResults?.()}
            >
              Открыть результаты
            </CursorButton>
          </Box>
        </Box>
      )}
    </Box>
  );
}
