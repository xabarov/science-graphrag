import React from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import { useI18n } from "../../i18n/useI18n.js";
import CompareDeltaTable from "./CompareDeltaTable.jsx";
import CompareTabSummarySection from "./CompareTabSummarySection.jsx";
import { useCompareTab } from "./useCompareTab.js";

export default function CompareTab({ onOpenWorkbench, initialBaselineId, initialCurrentId }) {
  const {
    items,
    baselineId,
    setBaselineId,
    currentId,
    setCurrentId,
    result,
    error,
    loading,
    caseFilter,
    setCaseFilter,
    metricFilter,
    setMetricFilter,
    showUnchanged,
    setShowUnchanged,
    refreshRuns,
    runCompare,
    exportCompareJson,
    exportCompareMarkdown,
    summary,
    metaDelta,
    regressionsFiltered,
    improvementsFiltered,
    unchangedFiltered,
  } = useCompareTab({ initialBaselineId, initialCurrentId });

  const { t } = useI18n();
  const tk = useTheme().appTokens;
  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 2 }}>{t("benchmarkPage.compareTab.title")}</Typography>
      <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem", mb: 2 }}>
        {t("benchmarkPage.compareTab.intro")}
      </Typography>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, alignItems: "center", mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 280 }}>
          <InputLabel id="cmp-base">{t("benchmarkPage.compareTab.baselineRun")}</InputLabel>
          <Select
            labelId="cmp-base"
            label={t("benchmarkPage.compareTab.baselineRun")}
            value={baselineId}
            onChange={(e) => setBaselineId(e.target.value)}
          >
            <MenuItem value="">
              <em>{t("benchmarkPage.compareTab.selectPlaceholder")}</em>
            </MenuItem>
            {items.map((r) => (
              <MenuItem key={r.run_id} value={r.run_id}>
                {r.run_id.slice(0, 8)}… | {r.benchmark_family} | {r.status}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 280 }}>
          <InputLabel id="cmp-cur">{t("benchmarkPage.compareTab.currentRun")}</InputLabel>
          <Select
            labelId="cmp-cur"
            label={t("benchmarkPage.compareTab.currentRun")}
            value={currentId}
            onChange={(e) => setCurrentId(e.target.value)}
          >
            <MenuItem value="">
              <em>{t("benchmarkPage.compareTab.selectPlaceholder")}</em>
            </MenuItem>
            {items.map((r) => (
              <MenuItem key={`c-${r.run_id}`} value={r.run_id}>
                {r.run_id.slice(0, 8)}… | {r.benchmark_family} | {r.status}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <CursorPrimaryButton onClick={runCompare} disabled={loading || !baselineId || !currentId}>
          {loading ? t("benchmarkPage.compareTab.comparing") : t("benchmarkPage.compareTab.compare")}
        </CursorPrimaryButton>
        <CursorButton onClick={() => refreshRuns().catch(() => {})}>{t("benchmarkPage.compareTab.refreshList")}</CursorButton>
      </Box>

      {error ? (
        <Typography sx={{ color: tk.state.dangerFg, mb: 2 }} role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </Typography>
      ) : null}

      <CompareTabSummarySection summary={summary} result={result} />

      {metaDelta && Object.keys(metaDelta).length > 0 ? (
        <Box sx={{ mb: 2 }}>
          <Typography sx={{ fontWeight: 600, mb: 0.5 }}>{t("benchmarkPage.compareTab.metadataDelta")}</Typography>
          <Box
            component="pre"
            sx={{
              fontSize: "11px",
              color: tk.text.secondary,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
            }}
          >
            {JSON.stringify(metaDelta, null, 2)}
          </Box>
        </Box>
      ) : null}

      {result ? (
        <Box
          sx={{
            mb: 2,
            display: "flex",
            flexWrap: "wrap",
            gap: 1.5,
            alignItems: "center",
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            p: 1.5,
            backgroundColor: tk.surface.panel,
          }}
        >
          <TextField
            size="small"
            label={t("benchmarkPage.compareTab.filterCase")}
            value={caseFilter}
            onChange={(e) => setCaseFilter(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <TextField
            size="small"
            label={t("benchmarkPage.compareTab.filterMetric")}
            value={metricFilter}
            onChange={(e) => setMetricFilter(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <FormControlLabel
            control={
              <Checkbox
                size="small"
                checked={showUnchanged}
                onChange={(e) => setShowUnchanged(e.target.checked)}
                sx={{ color: tk.text.muted }}
              />
            }
            label={<Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmarkPage.compareTab.showUnchanged")}</Typography>}
          />
          <CursorButton onClick={exportCompareJson}>{t("benchmarkPage.compareTab.exportJson")}</CursorButton>
          <CursorButton onClick={exportCompareMarkdown} disabled={!result.markdown}>
            {t("benchmarkPage.compareTab.exportMarkdown")}
          </CursorButton>
        </Box>
      ) : null}

      {result ? (
        <>
          <CompareDeltaTable
            title={t("benchmarkPage.compareTab.tableRegressions")}
            rows={regressionsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
            baselineRunId={baselineId}
          />
          <CompareDeltaTable
            title={t("benchmarkPage.compareTab.tableImprovements")}
            rows={improvementsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
            baselineRunId={baselineId}
          />
          {showUnchanged ? (
            <CompareDeltaTable
              title={t("benchmarkPage.compareTab.tableUnchanged")}
              rows={unchangedFiltered}
              onOpenCase={onOpenWorkbench}
              currentRunId={result.current_run_id}
              baselineRunId={baselineId}
            />
          ) : null}
        </>
      ) : null}
    </Box>
  );
}
