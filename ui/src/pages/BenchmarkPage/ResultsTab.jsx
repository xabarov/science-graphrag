import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";
import { useTheme } from "@mui/material/styles";

import { deleteBenchmarkRun, listBenchmarkRuns } from "../../services/benchmarkApi.js";
import ResultsDialog from "./ResultsDialog.jsx";
import { CursorButton, CursorDangerButton } from "../../components/common/index.js";
import BenchmarkRunSummaryCards from "./BenchmarkRunSummaryCards.jsx";

function _statusChip(status) {
  const normalized = (status || "").toLowerCase();
  if (normalized === "completed") return { label: "COMPLETED", color: "primary" };
  if (normalized === "failed") return { label: "FAILED", color: "error" };
  if (normalized === "cancelled") return { label: "CANCELLED", color: "default" };
  return { label: normalized.toUpperCase() || "RUNNING", color: "default" };
}

export default function ResultsTab({ onOpenWorkbench }) {
  const tk = useTheme().appTokens;
  const [runsPayload, setRunsPayload] = useState(null);
  const [error, setError] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [familyFilter, setFamilyFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [qFilter, setQFilter] = useState("");

  async function refresh() {
    setError(null);
    const resp = await listBenchmarkRuns({
      family: familyFilter || undefined,
      status: statusFilter || undefined,
      q: qFilter || undefined,
    });
    setRunsPayload(resp);
  }

  useEffect(() => {
    let cancelled = false;
    async function init() {
      try {
        await refresh();
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_load_runs");
      }
    }
    init();
    return () => {
      cancelled = true;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- initial load; filters via Apply

  const items = runsPayload?.items || [];
  const latestRun = items[0] || null;

  return (
    <Box sx={{ padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography sx={{ fontWeight: 600 }}>Results</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <CursorButton onClick={() => refresh()}>
            Refresh
          </CursorButton>
        </Box>
      </Box>

      {error && (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      )}

      <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1.5, alignItems: "center", mb: 2 }}>
        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel id="res-fam">Family</InputLabel>
          <Select
            labelId="res-fam"
            label="Family"
            value={familyFilter}
            onChange={(e) => setFamilyFilter(e.target.value)}
          >
            <MenuItem value="">all</MenuItem>
            <MenuItem value="layer1">layer1</MenuItem>
            <MenuItem value="layer2">layer2</MenuItem>
          </Select>
        </FormControl>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id="res-st">Status</InputLabel>
          <Select
            labelId="res-st"
            label="Status"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="">all</MenuItem>
            <MenuItem value="completed">completed</MenuItem>
            <MenuItem value="running">running</MenuItem>
            <MenuItem value="failed">failed</MenuItem>
            <MenuItem value="cancelled">cancelled</MenuItem>
          </Select>
        </FormControl>
        <TextField
          size="small"
          label="run_id / label"
          value={qFilter}
          onChange={(e) => setQFilter(e.target.value)}
          sx={{ minWidth: 220 }}
        />
        <CursorButton onClick={() => refresh().catch(() => {})}>Apply filters</CursorButton>
      </Box>

      {items.length === 0 ? (
        <Typography sx={{ color: tk.text.secondary }}>
          No runs yet. Go to the Launch tab to start one.
        </Typography>
      ) : (
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
          {latestRun ? <BenchmarkRunSummaryCards run={latestRun} /> : null}

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>run_id</TableCell>
                <TableCell>family</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>config</TableCell>
                <TableCell>metrics</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {items.map((r) => {
                const st = _statusChip(r.status);
                const pct = r?.progress?.percent ?? 0;
                const fam = r.benchmark_family || "layer1";
                const metricsCell =
                  fam === "layer2"
                    ? `L2 recall≈ ${(r.summary?.avg_layer2_recall_ratio ?? 0).toFixed(3)}`
                    : `names ${(r.summary?.avg_names_f1 ?? 0).toFixed(3)} / arxiv ${(r.summary?.avg_sample_arxiv_f1 ?? 0).toFixed(3)}`;
                const configCell = [
                  r?.run_config?.model_profile,
                  r?.run_config?.gold_source,
                  r?.run_config?.threshold_profile,
                ]
                  .filter(Boolean)
                  .join(" | ");
                return (
                  <TableRow key={r.run_id}>
                    <TableCell sx={{ wordBreak: "break-all" }}>{r.run_id.slice(0, 8)}…</TableCell>
                    <TableCell>
                      <Chip label={fam} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Chip label={st.label} color={st.color} size="small" />
                    </TableCell>
                    <TableCell>
                      {r.progress.completed}/{r.progress.total} ({pct.toFixed(1)}%)
                    </TableCell>
                    <TableCell sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>
                      {configCell || "default"}
                    </TableCell>
                    <TableCell sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{metricsCell}</TableCell>
                    <TableCell align="right">
                      <CursorButton
                        onClick={() => {
                          setSelectedRunId(r.run_id);
                          setDialogOpen(true);
                        }}
                      >
                        Open
                      </CursorButton>
                      <CursorButton onClick={() => onOpenWorkbench?.(r.run_id, r?.cases?.[0]?.case_id || null)}>
                        Workbench
                      </CursorButton>
                      <CursorDangerButton
                        onClick={async () => {
                          await deleteBenchmarkRun(r.run_id);
                          await refresh();
                        }}
                      >
                        Delete
                      </CursorDangerButton>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </Box>
      )}

      <ResultsDialog
        open={dialogOpen}
        runId={selectedRunId}
        onOpenWorkbench={onOpenWorkbench}
        onClose={() => {
          setDialogOpen(false);
          setSelectedRunId(null);
          refresh().catch(() => {});
        }}
      />
    </Box>
  );
}


