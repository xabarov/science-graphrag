import React from "react";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import Alert from "@mui/material/Alert";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../components/common/index.js";
import BenchmarkLauncherPanel from "./BenchmarkLauncherPanel.jsx";
import RunLabGroupedExecutionPanel from "./RunLabGroupedExecutionPanel.jsx";
import RunTabCurrentRunSection from "./RunTabCurrentRunSection.jsx";
import { useI18n } from "../../i18n/useI18n.js";
import { useRunTab } from "./useRunTab.js";
import { getExperimentById } from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {() => void} props.onSwitchToResults
 * @param {(runIds: string[]) => void} [props.onOpenAnalysisWithGroup]
 */
export default function RunTab({ onSwitchToResults, onOpenAnalysisWithGroup }) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const tab = useRunTab({ onOpenAnalysisWithGroup });

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
    executionMode,
    setExecutionModeInUrl,
    batchExperimentIds,
    batchModelProfileIds,
    profileOptionsForBatch,
    toggleBatchExperiment,
    toggleBatchModelProfile,
    groupChildren,
    groupMeta,
    groupAggregateStatus,
    groupIsStarting,
    groupError,
    setGroupError,
    startGroupBatch,
    groupHandoffRunIds,
    openAnalysisForCurrentGroup,
    selectRunFromGroup,
    recentCompareSetups,
    applyRecentCompareSetup,
    singleStartDisabled,
    RUN_MODE_GROUPED,
    linkedExperimentId,
    benchmarkServerStatus,
  } = tab;

  const experimentMeta = linkedExperimentId?.trim() ? getExperimentById(linkedExperimentId.trim()) : null;

  const familyLabelKey =
    benchmarkFamily === "layer2"
      ? "benchmarkPage.runLab.familyApi.layer2"
      : benchmarkFamily === "graph"
        ? "benchmarkPage.runLab.familyApi.graph"
        : "benchmarkPage.runLab.familyApi.layer1";

  const mainTitle = experimentMeta
    ? t(experimentMeta.titleKey)
    : isGraphCatalog
      ? t("benchmark.run.titleGraph")
      : benchmarkFamily === "layer2"
        ? t("benchmark.run.titleLayer2")
        : t("benchmark.run.titleLayer1");

  const showGroupProgress = executionMode === RUN_MODE_GROUPED && groupChildren.length > 0;

  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 0.5 }}>{mainTitle}</Typography>

      {experimentMeta ? (
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, mb: 1.5 }}>
          {t("benchmarkPage.runLab.catalogEntry", { id: experimentMeta.id })} ·{" "}
          {t("benchmarkPage.runLab.implementationLine", { label: t(familyLabelKey), apiId: benchmarkFamily })}
        </Typography>
      ) : null}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center", mb: 2 }}>
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted, mr: 0.5 }}>{t("benchmarkPage.runLab.mode.label")}</Typography>
        <CursorSmallButton
          size="small"
          onClick={() => setExecutionModeInUrl("single")}
          sx={
            executionMode !== RUN_MODE_GROUPED
              ? { borderColor: tk.accent.softBorder, backgroundColor: tk.accent.softBg, color: tk.accent.fg }
              : undefined
          }
        >
          {t("benchmarkPage.runLab.mode.single")}
        </CursorSmallButton>
        <CursorSmallButton
          size="small"
          onClick={() => setExecutionModeInUrl(RUN_MODE_GROUPED)}
          sx={
            executionMode === RUN_MODE_GROUPED
              ? { borderColor: tk.accent.softBorder, backgroundColor: tk.accent.softBg, color: tk.accent.fg }
              : undefined
          }
        >
          {t("benchmarkPage.runLab.mode.grouped")}
        </CursorSmallButton>
      </Box>

      {executionMode === RUN_MODE_GROUPED ? (
        <>
          <RunLabGroupedExecutionPanel
            selectedExperimentIds={batchExperimentIds}
            onToggleExperiment={toggleBatchExperiment}
            selectedModelProfileIds={batchModelProfileIds}
            onToggleModelProfile={toggleBatchModelProfile}
            profileOptions={profileOptionsForBatch}
            onStartBatch={() =>
              startGroupBatch().catch((e) => setGroupError(e?.message || t("benchmarkPage.runLab.grouped.errorBatchFailed")))
            }
            isStarting={groupIsStarting}
            batchError={groupError}
            onClearBatchError={() => setGroupError(null)}
            onOpenAnalysis={openAnalysisForCurrentGroup}
            canOpenAnalysis={groupHandoffRunIds.length > 0}
          />
          {recentCompareSetups.length ? (
            <Box sx={{ mb: 2, p: 1.25, border: `1px solid ${tk.border.default}`, borderRadius: "6px", backgroundColor: tk.surface.subtle }}>
              <Typography sx={{ fontWeight: 600, fontSize: "0.75rem", mb: 0.75 }}>{t("benchmarkPage.runLab.recentSetups.title")}</Typography>
              <Box sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                {recentCompareSetups.slice(0, 6).map((row, idx) => (
                  <Box key={`${row.savedAt}-${idx}`} sx={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: 0.75 }}>
                    <Typography sx={{ fontSize: "0.68rem", color: tk.text.secondary }}>
                      {new Date(row.savedAt || 0).toLocaleString()} · {(row.experimentIds || []).join(", ") || "—"}
                    </Typography>
                    <CursorSmallButton size="small" onClick={() => applyRecentCompareSetup(row)}>
                      {t("benchmarkPage.runLab.recentSetups.apply")}
                    </CursorSmallButton>
                  </Box>
                ))}
              </Box>
            </Box>
          ) : null}
        </>
      ) : null}

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
        benchmarkServerStatus={benchmarkServerStatus}
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
        startRunDisabled={singleStartDisabled}
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
        showSingleRun={!showGroupProgress}
        groupProgress={
          showGroupProgress
            ? {
                groupId: groupMeta?.groupId || null,
                aggregateStatus: groupAggregateStatus,
                children: groupChildren,
              }
            : null
        }
        onSelectGroupRun={selectRunFromGroup}
      />
    </Box>
  );
}
