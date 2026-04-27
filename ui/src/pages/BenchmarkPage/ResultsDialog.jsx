import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";

import { getBenchmarkRun, getBenchmarkRunSummary } from "../../services/benchmarkApi.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { CursorButton, CursorPrimaryButton } from "../../components/common/index.js";
import BenchmarkRunSummaryCards from "./BenchmarkRunSummaryCards.jsx";
import BenchmarkRunCasesTable from "./BenchmarkRunCasesTable.jsx";

export default function ResultsDialog({ open, runId, onClose, onOpenWorkbench }) {
  const theme = useTheme();
  const tk = theme.appTokens;
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const [runDetail, setRunDetail] = useState(null);
  const [hasFullDetail, setHasFullDetail] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loadingFull, setLoadingFull] = useState(false);

  const benchmarkFamily = runDetail?.benchmark_family || "layer1";

  const terminalSummary = useMemo(() => {
    if (!runDetail) return null;
    return {
      avg_names_f1: runDetail.summary?.avg_names_f1 ?? 0,
      avg_sample_arxiv_f1: runDetail.summary?.avg_sample_arxiv_f1 ?? 0,
      avg_layer2_recall_ratio: runDetail.summary?.avg_layer2_recall_ratio ?? 0,
    };
  }, [runDetail]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!open || !runId) return;
      setError(null);
      setLoading(true);
      setHasFullDetail(false);
      setRunDetail(null);
      try {
        const resp = await getBenchmarkRunSummary(runId);
        const payload = resp?.data || resp;
        if (cancelled) return;
        setRunDetail(payload);
      } catch (e) {
        if (!cancelled) {
          setError(formatResearchApiError(e) || "failed_to_fetch_run");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, runId]);

  async function loadFullDetails() {
    if (!runId) return;
    setLoadingFull(true);
    setError(null);
    try {
      const resp = await getBenchmarkRun(runId);
      const payload = resp?.data || resp;
      setRunDetail(payload);
      setHasFullDetail(true);
    } catch (e) {
      setError(formatResearchApiError(e) || "failed_to_fetch_full_run");
    } finally {
      setLoadingFull(false);
    }
  }

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      fullScreen={fullScreen}
      aria-labelledby="benchmark-results-dialog-title"
    >
      <DialogTitle id="benchmark-results-dialog-title">
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography sx={{ fontWeight: 700 }}>Run details</Typography>
            <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>
              run_id: {runId ? runId : "-"}
            </Typography>
          </Box>
          <CursorButton onClick={onClose} aria-label="Close run details dialog">
            Close
          </CursorButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Typography sx={{ color: tk.state.dangerFg, mb: 1 }} role="alert">
            {error}
          </Typography>
        )}

        {loading && <Typography sx={{ color: tk.text.secondary }}>Loading...</Typography>}

        {runDetail && !hasFullDetail ? (
          <Box sx={{ mb: 2, display: "flex", flexWrap: "wrap", alignItems: "center", gap: 1 }}>
            <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>
              Compact summary (no per-case result blobs). Load full run for complete JSON if needed.
            </Typography>
            {runDetail.full_run_blocked ? (
              <Typography sx={{ color: "rgba(255,200,100,0.9)", fontSize: "0.8125rem", maxWidth: 560 }}>
                Full run disabled: {runDetail.full_run_block_reason || "too_large"} — use paginated cases or CLI.
              </Typography>
            ) : (
              <CursorPrimaryButton onClick={loadFullDetails} disabled={loadingFull}>
                {loadingFull ? "Loading…" : "Load full details"}
              </CursorPrimaryButton>
            )}
          </Box>
        ) : null}

        {runDetail && hasFullDetail ? (
          <Typography sx={{ color: tk.text.muted, fontSize: "0.75rem", mb: 1 }}>
            Full run payload loaded.
          </Typography>
        ) : null}

        {runDetail && terminalSummary && (
          <Box sx={{ mb: 2, display: "flex", flexDirection: "column", gap: 2 }}>
            <Typography sx={{ color: tk.text.secondary }}>
              status: {runDetail.status} | completed: {runDetail.progress?.completed ?? 0}/{runDetail.progress?.total ?? 0}{" "}
              ({(runDetail.progress?.percent ?? 0).toFixed(1)}%)
            </Typography>
            <Typography sx={{ mt: 0.5, color: tk.text.secondary }}>
              family: {benchmarkFamily}
              {benchmarkFamily === "layer2"
                ? ` | avg layer2 recall ratio: ${terminalSummary.avg_layer2_recall_ratio.toFixed(3)}`
                : ` | avg names_f1: ${terminalSummary.avg_names_f1.toFixed(3)} | avg sample_arxiv_f1: ${terminalSummary.avg_sample_arxiv_f1.toFixed(3)}`}
            </Typography>
            <BenchmarkRunSummaryCards run={runDetail} />
          </Box>
        )}

        {runDetail ? (
          <BenchmarkRunCasesTable
            key={runDetail.run_id || runId || "run"}
            run={runDetail}
            onOpenWorkbench={(caseId) => {
              onOpenWorkbench?.(runDetail.run_id, caseId);
              onClose?.();
            }}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
