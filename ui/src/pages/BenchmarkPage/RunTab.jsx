import React from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";

import BenchmarkLauncherPanel from "./BenchmarkLauncherPanel.jsx";
import RunTabCurrentRunSection from "./RunTabCurrentRunSection.jsx";
import { useI18n } from "../../i18n/I18nContext.jsx";
import { useRunTab } from "./useRunTab.js";

export default function RunTab({ onSwitchToResults }) {
  const { t } = useI18n();
  const {
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
    handleFamilyChange,
    startRun,
    setModels,
    onToggleCase,
  } = useRunTab();

  const title = isGraphCatalog
    ? t("benchmark.run.titleGraph")
    : benchmarkFamily === "layer2"
      ? t("benchmark.run.titleLayer2")
      : t("benchmark.run.titleLayer1");

  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 2 }}>{title}</Typography>

      {isGraphCatalog ? (
        <Alert severity="info" sx={{ mb: 2, fontSize: "0.8125rem" }}>
          {t("benchmark.run.graphAlert")}
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
        onToggleCase={onToggleCase}
        onStartRun={() => startRun().catch((e) => setError(e?.message || "failed_to_start_run"))}
      />

      <Divider sx={{ my: 2 }} />

      <RunTabCurrentRunSection
        t={t}
        runId={runId}
        run={run}
        progressPercent={progressPercent}
        progressCompleted={progressCompleted}
        progressTotal={progressTotal}
        currentRunSummary={currentRunSummary}
        summary={summary}
        onSwitchToResults={onSwitchToResults}
        terminalStatuses={TERMINAL_STATUSES}
      />
    </Box>
  );
}
