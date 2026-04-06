import React, { useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Chip from "@mui/material/Chip";

import { deleteBenchmarkRun, listBenchmarkRuns } from "../../services/benchmarkApi.js";
import ResultsDialog from "./ResultsDialog.jsx";
import { CursorButton, CursorDangerButton } from "../../components/common/index.js";

function _statusChip(status) {
  const normalized = (status || "").toLowerCase();
  if (normalized === "completed") return { label: "COMPLETED", color: "primary" };
  if (normalized === "failed") return { label: "FAILED", color: "error" };
  if (normalized === "cancelled") return { label: "CANCELLED", color: "default" };
  return { label: normalized.toUpperCase() || "RUNNING", color: "default" };
}

export default function ResultsTab() {
  const [runsPayload, setRunsPayload] = useState(null);
  const [error, setError] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function refresh() {
    setError(null);
    const resp = await listBenchmarkRuns();
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
  }, []);

  const items = runsPayload?.items || [];

  return (
    <Box sx={{ padding: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 2 }}>
        <Typography sx={{ fontWeight: 600 }}>Результаты</Typography>
        <Box sx={{ display: "flex", gap: 1 }}>
          <CursorButton onClick={() => refresh()}>
            Обновить
          </CursorButton>
        </Box>
      </Box>

      {error && (
        <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
          {error}
        </Typography>
      )}

      {items.length === 0 ? (
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
          Пока нет runs. Перейдите на вкладку “Запуск”.
        </Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>run_id</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Progress</TableCell>
              <TableCell>avg names_f1</TableCell>
              <TableCell>avg sample_arxiv_f1</TableCell>
              <TableCell align="right">Действия</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {items.map((r) => {
              const st = _statusChip(r.status);
              const pct = r?.progress?.percent ?? 0;
              return (
                <TableRow key={r.run_id}>
                  <TableCell sx={{ wordBreak: "break-all" }}>{r.run_id.slice(0, 8)}…</TableCell>
                  <TableCell>
                    <Chip label={st.label} color={st.color} size="small" />
                  </TableCell>
                  <TableCell>
                    {r.progress.completed}/{r.progress.total} ({pct.toFixed(1)}%)
                  </TableCell>
                  <TableCell>{(r.summary?.avg_names_f1 ?? 0).toFixed(3)}</TableCell>
                  <TableCell>{(r.summary?.avg_sample_arxiv_f1 ?? 0).toFixed(3)}</TableCell>
                  <TableCell align="right">
                    <CursorButton
                      onClick={() => {
                        setSelectedRunId(r.run_id);
                        setDialogOpen(true);
                      }}
                    >
                      Открыть
                    </CursorButton>
                    <CursorDangerButton
                      onClick={async () => {
                        await deleteBenchmarkRun(r.run_id);
                        await refresh();
                      }}
                    >
                      Удалить
                    </CursorDangerButton>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      )}

      <ResultsDialog
        open={dialogOpen}
        runId={selectedRunId}
        onClose={() => {
          setDialogOpen(false);
          setSelectedRunId(null);
          refresh().catch(() => {});
        }}
      />
    </Box>
  );
}


