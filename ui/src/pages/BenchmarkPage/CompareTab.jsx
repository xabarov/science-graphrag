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

import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import CompareDeltaTable from "./CompareDeltaTable.jsx";
import CompareTabSummarySection from "./CompareTabSummarySection.jsx";
import { useCompareTab } from "./useCompareTab.js";

export default function CompareTab({ onOpenWorkbench }) {
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
  } = useCompareTab();

  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 2 }}>Compare runs</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
        Baseline is the reference (older) run; Current is the candidate (newer). Only cases with status ok and metrics
        are compared. Benchmark family must match between runs.
      </Typography>

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, alignItems: "center", mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 280 }}>
          <InputLabel id="cmp-base">Baseline run</InputLabel>
          <Select
            labelId="cmp-base"
            label="Baseline run"
            value={baselineId}
            onChange={(e) => setBaselineId(e.target.value)}
          >
            <MenuItem value="">
              <em>Select</em>
            </MenuItem>
            {items.map((r) => (
              <MenuItem key={r.run_id} value={r.run_id}>
                {r.run_id.slice(0, 8)}… | {r.benchmark_family} | {r.status}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 280 }}>
          <InputLabel id="cmp-cur">Current run</InputLabel>
          <Select
            labelId="cmp-cur"
            label="Current run"
            value={currentId}
            onChange={(e) => setCurrentId(e.target.value)}
          >
            <MenuItem value="">
              <em>Select</em>
            </MenuItem>
            {items.map((r) => (
              <MenuItem key={`c-${r.run_id}`} value={r.run_id}>
                {r.run_id.slice(0, 8)}… | {r.benchmark_family} | {r.status}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <CursorPrimaryButton onClick={runCompare} disabled={loading || !baselineId || !currentId}>
          {loading ? "Comparing…" : "Compare"}
        </CursorPrimaryButton>
        <CursorButton onClick={() => refreshRuns().catch(() => {})}>Refresh list</CursorButton>
      </Box>

      {error ? (
        <Typography sx={{ color: "rgba(239,68,68,0.9)", mb: 2 }} role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </Typography>
      ) : null}

      <CompareTabSummarySection summary={summary} result={result} />

      {metaDelta && Object.keys(metaDelta).length > 0 ? (
        <Box sx={{ mb: 2 }}>
          <Typography sx={{ fontWeight: 600, mb: 0.5 }}>Run metadata delta</Typography>
          <Box
            component="pre"
            sx={{
              fontSize: "11px",
              color: "rgba(255,255,255,0.75)",
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
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 1.5,
            p: 1.5,
            backgroundColor: "#1a1a1a",
          }}
        >
          <TextField
            size="small"
            label="Filter case_id"
            value={caseFilter}
            onChange={(e) => setCaseFilter(e.target.value)}
            sx={{ minWidth: 200 }}
          />
          <TextField
            size="small"
            label="Filter metric"
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
                sx={{ color: "rgba(255,255,255,0.5)" }}
              />
            }
            label={<Typography sx={{ fontSize: "0.8125rem" }}>Show unchanged rows</Typography>}
          />
          <CursorButton onClick={exportCompareJson}>Export JSON</CursorButton>
          <CursorButton onClick={exportCompareMarkdown} disabled={!result.markdown}>
            Export Markdown
          </CursorButton>
        </Box>
      ) : null}

      {result ? (
        <>
          <CompareDeltaTable
            title="Regressions"
            rows={regressionsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
          />
          <CompareDeltaTable
            title="Improvements"
            rows={improvementsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
          />
          {showUnchanged ? (
            <CompareDeltaTable
              title="Unchanged"
              rows={unchangedFiltered}
              onOpenCase={onOpenWorkbench}
              currentRunId={result.current_run_id}
            />
          ) : null}
        </>
      ) : null}
    </Box>
  );
}
