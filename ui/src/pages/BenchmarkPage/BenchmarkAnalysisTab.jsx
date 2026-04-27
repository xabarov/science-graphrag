import React from "react";
import Box from "@mui/material/Box";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import { useTheme } from "@mui/material/styles";

import { useI18n } from "../../i18n/useI18n.js";

import BenchmarkWorkbenchTab from "./BenchmarkWorkbenchTab.jsx";
import CompareTab from "./CompareTab.jsx";
import ResultsTab from "./ResultsTab.jsx";

import { ANALYSIS_VIEWS, normalizeAnalysisView } from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {"results"|"compare"|"workbench"} props.analysisView
 * @param {(view: "results"|"compare"|"workbench") => void} props.onAnalysisViewChange
 * @param {(runId: string, caseId?: string | null) => void} props.onOpenWorkbench
 * @param {string | null} props.selectedRunId
 * @param {string | null} props.selectedCaseId
 * @param {(runId: string | null) => void} props.onSelectRun
 * @param {(caseId: string | null) => void} props.onSelectCase
 */
export default function BenchmarkAnalysisTab({
  analysisView,
  onAnalysisViewChange,
  onOpenWorkbench,
  selectedRunId,
  selectedCaseId,
  onSelectRun,
  onSelectCase,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const view = normalizeAnalysisView(analysisView);

  return (
    <Box>
      <Box sx={{ px: 2, pt: 1.5, borderBottom: `1px solid ${tk.border.default}` }}>
        <Tabs
          value={view}
          onChange={(e, v) => {
            if (ANALYSIS_VIEWS.includes(v)) onAnalysisViewChange(/** @type {"results"|"compare"|"workbench"} */ (v));
          }}
          aria-label={t("benchmarkPage.tab.analysis")}
          textColor="inherit"
          indicatorColor="secondary"
          variant="scrollable"
          sx={{
            "& .MuiTab-root:focus-visible": {
              outline: `2px solid ${tk.accent.fg}`,
              outlineOffset: 2,
            },
          }}
        >
          <Tab value="results" label={t("benchmarkPage.analysis.results")} />
          <Tab value="compare" label={t("benchmarkPage.analysis.compare")} />
          <Tab value="workbench" label={t("benchmarkPage.analysis.workbench")} />
        </Tabs>
      </Box>
      {view === "results" ? <ResultsTab onOpenWorkbench={onOpenWorkbench} /> : null}
      {view === "compare" ? <CompareTab onOpenWorkbench={onOpenWorkbench} /> : null}
      {view === "workbench" ? (
        <BenchmarkWorkbenchTab
          selectedRunId={selectedRunId}
          selectedCaseId={selectedCaseId}
          onSelectRun={onSelectRun}
          onSelectCase={onSelectCase}
        />
      ) : null}
    </Box>
  );
}
