import React, { useCallback, useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Checkbox from "@mui/material/Checkbox";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import TextField from "@mui/material/TextField";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";

import { compareBenchmarkRuns, listBenchmarkRuns } from "../../services/benchmarkApi.js";
import { CursorButton, CursorPrimaryButton, CursorSmallButton } from "../../components/common/index.js";

const TABLE_CAP = 200;

function filterDeltaRows(rows, caseQ, metricQ) {
  if (!rows?.length) return [];
  const cq = (caseQ || "").trim().toLowerCase();
  const mq = (metricQ || "").trim().toLowerCase();
  return rows.filter((r) => {
    if (cq && !String(r.case_id).toLowerCase().includes(cq)) return false;
    if (mq && !String(r.metric).toLowerCase().includes(mq)) return false;
    return true;
  });
}

function downloadText(filename, text, mime) {
  const blob = new Blob([text], { type: mime || "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function DeltaTable({ title, rows, onOpenCase, currentRunId }) {
  if (!rows?.length) {
    return (
      <Box sx={{ mb: 2 }}>
        <Typography sx={{ fontWeight: 600, mb: 0.5 }}>{title}</Typography>
        <Typography sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.8125rem" }}>None</Typography>
      </Box>
    );
  }
  return (
    <Box sx={{ mb: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 1 }}>{title}</Typography>
      <Box sx={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 1.5, overflow: "hidden" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>case_id</TableCell>
              <TableCell>metric</TableCell>
              <TableCell>baseline</TableCell>
              <TableCell>current</TableCell>
              <TableCell align="right">actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.slice(0, TABLE_CAP).map((row, idx) => (
              <TableRow key={`${row.case_id}-${row.metric}-${idx}`}>
                <TableCell sx={{ wordBreak: "break-word" }}>{row.case_id}</TableCell>
                <TableCell sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.75)" }}>{row.metric}</TableCell>
                <TableCell>{String(row.baseline)}</TableCell>
                <TableCell>
                  {String(row.current)}
                  {row.delta != null ? ` (Δ ${Number(row.delta).toFixed(4)})` : ""}
                </TableCell>
                <TableCell align="right">
                  {onOpenCase && currentRunId ? (
                    <CursorSmallButton onClick={() => onOpenCase(currentRunId, row.case_id)}>Workbench</CursorSmallButton>
                  ) : null}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      {rows.length > TABLE_CAP ? (
        <Typography sx={{ color: "rgba(255,255,255,0.45)", fontSize: "0.75rem", mt: 0.5 }}>
          Showing first {TABLE_CAP} of {rows.length}
        </Typography>
      ) : null}
    </Box>
  );
}

export default function CompareTab({ onOpenWorkbench }) {
  const [runsPayload, setRunsPayload] = useState(null);
  const [baselineId, setBaselineId] = useState("");
  const [currentId, setCurrentId] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [caseFilter, setCaseFilter] = useState("");
  const [metricFilter, setMetricFilter] = useState("");
  const [showUnchanged, setShowUnchanged] = useState(false);

  const refreshRuns = useCallback(async () => {
    const resp = await listBenchmarkRuns();
    setRunsPayload(resp);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await refreshRuns();
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_runs");
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, [refreshRuns]);

  const items = runsPayload?.items || [];

  async function runCompare() {
    if (!baselineId || !currentId) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const resp = await compareBenchmarkRuns(baselineId, currentId);
      setResult(resp?.data || resp);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "compare_failed");
    } finally {
      setLoading(false);
    }
  }

  const summary = result?.summary;
  const metaDelta = result?.run_metadata_delta;

  const regressionsFiltered = useMemo(
    () => filterDeltaRows(result?.regressions, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );
  const improvementsFiltered = useMemo(
    () => filterDeltaRows(result?.improvements, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );
  const unchangedFiltered = useMemo(
    () => filterDeltaRows(result?.unchanged, caseFilter, metricFilter),
    [result, caseFilter, metricFilter],
  );

  function exportCompareJson() {
    if (!result) return;
    downloadText(
      `benchmark-compare-${result.baseline_run_id?.slice(0, 8) || "base"}-${result.current_run_id?.slice(0, 8) || "cur"}.json`,
      JSON.stringify(result, null, 2),
      "application/json",
    );
  }

  function exportCompareMarkdown() {
    if (!result) return;
    const md = result.markdown || "";
    downloadText(
      `benchmark-compare-${result.baseline_run_id?.slice(0, 8) || "base"}-${result.current_run_id?.slice(0, 8) || "cur"}.md`,
      md,
      "text/markdown;charset=utf-8",
    );
  }

  return (
    <Box sx={{ padding: 2 }}>
      <Typography sx={{ fontWeight: 600, mb: 2 }}>Сравнение run-ов</Typography>
      <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 2 }}>
        Baseline = эталон (старый / reference). Current = кандидат (новый). Сравниваются только кейсы со статусом ok и
        наличием metrics. Семейство benchmark должно совпадать.
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
          {loading ? "Сравнение…" : "Сравнить"}
        </CursorPrimaryButton>
        <CursorButton onClick={() => refreshRuns().catch(() => {})}>Обновить список</CursorButton>
      </Box>

      {error ? (
        <Typography sx={{ color: "rgba(239,68,68,0.9)", mb: 2 }} role="alert">
          {typeof error === "string" ? error : JSON.stringify(error)}
        </Typography>
      ) : null}

      {summary ? (
        <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", gap: 2 }}>
          <Box
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Regressions</Typography>
            <Typography sx={{ fontWeight: 600 }}>{summary.regression_count}</Typography>
          </Box>
          <Box
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Improvements</Typography>
            <Typography sx={{ fontWeight: 600 }}>{summary.improvement_count}</Typography>
          </Box>
          <Box
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Unchanged metric rows</Typography>
            <Typography sx={{ fontWeight: 600 }}>{summary.unchanged_count}</Typography>
          </Box>
          <Box
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Missing in current</Typography>
            <Typography sx={{ fontWeight: 600 }}>{(summary.missing_in_current || []).length}</Typography>
          </Box>
          <Box
            sx={{
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 1.5,
              px: 1.5,
              py: 1,
              backgroundColor: "#1a1a1a",
            }}
          >
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.5)" }}>Added in current</Typography>
            <Typography sx={{ fontWeight: 600 }}>{(summary.added_in_current || []).length}</Typography>
          </Box>
        </Box>
      ) : null}

      {summary?.missing_in_current?.length ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>
          Missing in current: {summary.missing_in_current.join(", ")}
        </Typography>
      ) : null}
      {summary?.added_in_current?.length ? (
        <Typography sx={{ color: "rgba(255,255,255,0.55)", fontSize: "0.8125rem", mb: 1 }}>
          Added in current: {summary.added_in_current.join(", ")}
        </Typography>
      ) : null}

      {result?.skipped_baseline?.length ? (
        <Typography sx={{ color: "rgba(255,200,100,0.85)", fontSize: "0.8125rem", mb: 1 }}>
          Skipped baseline cases:{" "}
          {result.skipped_baseline.map((s) => `${s.case_id} (${s.reason})`).join("; ")}
        </Typography>
      ) : null}
      {result?.skipped_current?.length ? (
        <Typography sx={{ color: "rgba(255,200,100,0.85)", fontSize: "0.8125rem", mb: 1 }}>
          Skipped current cases:{" "}
          {result.skipped_current.map((s) => `${s.case_id} (${s.reason})`).join("; ")}
        </Typography>
      ) : null}

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
          <DeltaTable
            title="Regressions"
            rows={regressionsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
          />
          <DeltaTable
            title="Improvements"
            rows={improvementsFiltered}
            onOpenCase={onOpenWorkbench}
            currentRunId={result.current_run_id}
          />
          {showUnchanged ? (
            <DeltaTable
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
