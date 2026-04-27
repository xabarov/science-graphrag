import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import { compareBenchmarkRuns } from "../../services/benchmarkApi.js";
import { formatResearchApiError } from "../../services/researchApi.js";

import BenchmarkAnalysisOverview from "./BenchmarkAnalysisOverview.jsx";
import BenchmarkWorkbenchTab from "./BenchmarkWorkbenchTab.jsx";
import CompareTab from "./CompareTab.jsx";
import ResultsTab from "./ResultsTab.jsx";
import { useBenchmarkAnalysisSession } from "./useBenchmarkAnalysisSession.js";

import { LEGACY_ANALYSIS_TOOL_VIEWS, normalizeAnalysisView } from "./experimentCatalog.js";

/**
 * @param {object} props
 * @param {"overview"|"results"|"compare"|"workbench"} props.analysisView
 * @param {(view: "overview"|"results"|"compare"|"workbench") => void} props.onAnalysisViewChange
 * @param {(runId: string, caseId?: string | null, opts?: { caseFamily?: string | null, compareBaselineRunId?: string | null, compareMetric?: string | null }) => void} props.onOpenWorkbench
 * @param {string | null} props.selectedRunId
 * @param {string | null} props.selectedCaseId
 * @param {(runId: string | null) => void} props.onSelectRun
 * @param {(caseId: string | null) => void} props.onSelectCase
 * @param {URLSearchParams} props.searchParams
 */
export default function BenchmarkAnalysisTab({
  analysisView,
  onAnalysisViewChange,
  onOpenWorkbench,
  selectedRunId,
  selectedCaseId,
  onSelectRun,
  onSelectCase,
  searchParams,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const view = normalizeAnalysisView(analysisView);
  const { session, loading, error, reload } = useBenchmarkAnalysisSession({ searchParams });
  const [selectedExperimentId, setSelectedExperimentId] = useState(null);
  const [selectedVariantId, setSelectedVariantId] = useState(null);
  const [compareResult, setCompareResult] = useState(null);
  const [compareError, setCompareError] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [toolsMenuAnchor, setToolsMenuAnchor] = useState(null);
  const toolsMenuOpen = Boolean(toolsMenuAnchor);

  const legacyToolOpen = LEGACY_ANALYSIS_TOOL_VIEWS.includes(view);

  useEffect(() => {
    if (!session?.rows?.length) {
      setSelectedExperimentId(null);
      setSelectedVariantId(null);
      return;
    }
    setSelectedExperimentId((prev) => {
      if (prev && session.rows.some((row) => row.experimentId === prev)) return prev;
      return session.rows[0].experimentId;
    });
  }, [session]);

  const selectedRow = useMemo(() => {
    if (!session?.rows?.length || !selectedExperimentId) return session?.rows?.[0] || null;
    return session.rows.find((row) => row.experimentId === selectedExperimentId) || session.rows[0] || null;
  }, [session, selectedExperimentId]);

  useEffect(() => {
    if (!selectedRow?.variants?.length) {
      setSelectedVariantId(null);
      return;
    }
    setSelectedVariantId((prev) => {
      if (prev && selectedRow.variants.some((item) => item.variantId === prev)) return prev;
      const preferred = selectedRow.variants.find((item) => !item.isBaseline && item.runId);
      return preferred?.variantId || selectedRow.variants.find((item) => item.runId)?.variantId || selectedRow.variants[0].variantId;
    });
  }, [selectedRow]);

  const selectedCell = useMemo(() => {
    if (!selectedRow?.variants?.length || !selectedVariantId) return selectedRow?.variants?.[0] || null;
    return selectedRow.variants.find((item) => item.variantId === selectedVariantId) || selectedRow.variants[0] || null;
  }, [selectedRow, selectedVariantId]);

  const compareContext = useMemo(() => {
    const b = searchParams.get("cmpBaseline");
    const mRaw = searchParams.get("cmpMetric");
    if (!b || !mRaw) return null;
    try {
      return { baselineRunId: b, metric: decodeURIComponent(mRaw) };
    } catch {
      return { baselineRunId: b, metric: mRaw };
    }
  }, [searchParams]);

  const caseFamilyParam = useMemo(() => {
    const f = (searchParams.get("caseFamily") || "layer1").trim().toLowerCase();
    if (f === "layer1" || f === "layer2" || f === "graph") return f;
    return "layer1";
  }, [searchParams]);

  const comparePair = useMemo(() => {
    const baseline = selectedRow?.variants?.find((item) => item.isBaseline && item.runId) || null;
    const current = selectedCell?.runId && selectedCell.variantId !== baseline?.variantId ? selectedCell : null;
    if (!baseline?.runId || !current?.runId) return null;
    return {
      baselineRunId: baseline.runId,
      currentRunId: current.runId,
    };
  }, [selectedRow, selectedCell]);

  useEffect(() => {
    let cancelled = false;
    async function loadCompare() {
      if (!comparePair) {
        setCompareResult(null);
        setCompareError(null);
        setCompareLoading(false);
        return;
      }
      setCompareLoading(true);
      setCompareError(null);
      try {
        const resp = await compareBenchmarkRuns(comparePair.baselineRunId, comparePair.currentRunId);
        if (!cancelled) setCompareResult(resp?.data || resp);
      } catch (e) {
        if (!cancelled) {
          setCompareResult(null);
          setCompareError(formatResearchApiError(e) || "compare_failed");
        }
      } finally {
        if (!cancelled) setCompareLoading(false);
      }
    }
    void loadCompare();
    return () => {
      cancelled = true;
    };
  }, [comparePair]);

  function pickLegacyTool(next) {
    onAnalysisViewChange(next);
    setToolsMenuAnchor(null);
  }

  return (
    <Box>
      <BenchmarkAnalysisOverview
        session={session}
        loading={loading}
        error={error}
        onReload={() => reload().catch(() => {})}
        selectedExperimentId={selectedRow?.experimentId || null}
        selectedVariantId={selectedCell?.variantId || null}
        selectedRow={selectedRow}
        selectedCell={selectedCell}
        onSelectCell={(experimentId, variantId) => {
          setSelectedExperimentId(experimentId);
          setSelectedVariantId(variantId);
        }}
        compareResult={compareResult}
        compareLoading={compareLoading}
        compareError={compareError}
        compareCurrentRunId={comparePair?.currentRunId || null}
        onOpenWorkbench={(runId, caseId = null, opts) => {
          onSelectRun?.(runId);
          onSelectCase?.(caseId);
          onOpenWorkbench(runId, caseId, opts);
        }}
        onOpenCompare={() => onAnalysisViewChange("compare")}
        onOpenResults={() => onAnalysisViewChange("results")}
      />
      <Box
        sx={{
          px: 2,
          pt: 1.5,
          pb: 1.25,
          borderBottom: `1px solid ${tk.border.default}`,
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary, maxWidth: 720, lineHeight: 1.5 }}>
          {t("benchmarkPage.analysis.toolsHint")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
          {legacyToolOpen ? (
            <CursorButton size="small" onClick={() => onAnalysisViewChange("overview")}>
              {t("benchmarkPage.analysis.backToOverview")}
            </CursorButton>
          ) : null}
          <CursorButton
            size="small"
            id="benchmark-analysis-tools-button"
            aria-controls={toolsMenuOpen ? "benchmark-analysis-tools-menu" : undefined}
            aria-haspopup="true"
            aria-expanded={toolsMenuOpen ? "true" : undefined}
            title={t("benchmarkPage.analysis.toolsMenu.ariaLabel")}
            onClick={(e) => setToolsMenuAnchor(e.currentTarget)}
          >
            {t("benchmarkPage.analysis.toolsMenu.button")}
          </CursorButton>
          <Menu
            id="benchmark-analysis-tools-menu"
            anchorEl={toolsMenuAnchor}
            open={toolsMenuOpen}
            onClose={() => setToolsMenuAnchor(null)}
            MenuListProps={{ "aria-labelledby": "benchmark-analysis-tools-button" }}
          >
            <MenuItem
              onClick={() => pickLegacyTool("results")}
              selected={view === "results"}
            >
              {t("benchmarkPage.analysis.toolsMenu.results")}
            </MenuItem>
            <MenuItem
              onClick={() => pickLegacyTool("compare")}
              selected={view === "compare"}
            >
              {t("benchmarkPage.analysis.toolsMenu.compare")}
            </MenuItem>
            <MenuItem
              onClick={() => pickLegacyTool("workbench")}
              selected={view === "workbench"}
            >
              {t("benchmarkPage.analysis.toolsMenu.workbench")}
            </MenuItem>
          </Menu>
        </Box>
      </Box>
      {view === "results" ? <ResultsTab onOpenWorkbench={onOpenWorkbench} /> : null}
      {view === "compare" ? (
        <CompareTab
          onOpenWorkbench={onOpenWorkbench}
          initialBaselineId={comparePair?.baselineRunId || ""}
          initialCurrentId={comparePair?.currentRunId || ""}
        />
      ) : null}
      {view === "workbench" ? (
        <BenchmarkWorkbenchTab
          selectedRunId={selectedRunId}
          selectedCaseId={selectedCaseId}
          onSelectRun={onSelectRun}
          onSelectCase={onSelectCase}
          caseFamily={caseFamilyParam}
          compareContext={compareContext}
        />
      ) : null}
    </Box>
  );
}
