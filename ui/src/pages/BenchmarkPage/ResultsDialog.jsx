import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { getBenchmarkRun } from "../../services/benchmarkApi.js";
import MetricsCard from "../../components/MetricsCard.jsx";
import ComparisonTable from "../../components/ComparisonTable.jsx";
import SemanticComparisonTable from "../../components/SemanticComparisonTable.jsx";
import { CursorButton } from "../../components/common/index.js";

function _statusLabel(status) {
  const s = (status || "").toLowerCase();
  if (s === "ok") return "OK";
  if (s === "failed") return "FAILED";
  if (s === "cancelled") return "CANCELLED";
  return s ? s.toUpperCase() : "PENDING";
}

export default function ResultsDialog({ open, runId, onClose }) {
  const [runDetail, setRunDetail] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

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
      try {
        const resp = await getBenchmarkRun(runId);
        const payload = resp?.data || resp;
        if (cancelled) return;
        setRunDetail(payload);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_fetch_run");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, runId]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="lg">
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography sx={{ fontWeight: 700 }}>Run details</Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
              run_id: {runId ? runId : "-"}
            </Typography>
          </Box>
          <CursorButton onClick={onClose}>Закрыть</CursorButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
            {error}
          </Typography>
        )}

        {loading && <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Loading...</Typography>}

        {runDetail && terminalSummary && (
          <Box sx={{ mb: 2 }}>
            <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
              status: {runDetail.status} | completed: {runDetail.progress.completed}/{runDetail.progress.total} (
              {runDetail.progress.percent.toFixed(1)}%)
            </Typography>
            <Typography sx={{ mt: 0.5, color: "rgba(255,255,255,0.6)" }}>
              family: {benchmarkFamily}
              {benchmarkFamily === "layer2"
                ? ` | avg layer2 recall ratio: ${terminalSummary.avg_layer2_recall_ratio.toFixed(3)}`
                : ` | avg names_f1: ${terminalSummary.avg_names_f1.toFixed(3)} | avg sample_arxiv_f1: ${terminalSummary.avg_sample_arxiv_f1.toFixed(3)}`}
            </Typography>
          </Box>
        )}

        {runDetail?.cases?.map((c) => {
          const isOk = c.status === "ok" && c.result;
          const metrics = c.result?.metrics;
          const layer2 = benchmarkFamily === "layer2";

          return (
            <Accordion key={c.case_id} defaultExpanded={isOk}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
                  <Typography sx={{ fontWeight: 700 }}>{c.case_id}</Typography>
                  <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>{_statusLabel(c.status)}</Typography>
                  {isOk && !layer2 && (
                    <Typography sx={{ marginLeft: "auto", color: "rgba(255,255,255,0.6)" }}>
                      names_f1: {(metrics?.authorships?.names_f1 ?? 0).toFixed(3)}
                    </Typography>
                  )}
                  {isOk && layer2 && (
                    <Typography sx={{ marginLeft: "auto", color: "rgba(255,255,255,0.6)" }}>
                      p_methods: {(metrics?.precision_methods ?? 0).toFixed(2)}
                    </Typography>
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                {!isOk ? (
                  <Box>
                    {c.error_message && (
                      <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }}>{c.error_message}</Typography>
                    )}
                    <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
                      {c.status === "pending" ? "pending..." : "no_case_result"}
                    </Typography>
                  </Box>
                ) : (
                  <Box>
                    <MetricsCard metrics={metrics} />
                    <Box sx={{ mt: 2 }}>
                      {layer2 ? (
                        <SemanticComparisonTable predicted={c.result.predicted} gold={c.result.gold} />
                      ) : (
                        <ComparisonTable predicted={c.result.predicted} gold={c.result.gold} />
                      )}
                    </Box>
                  </Box>
                )}
              </AccordionDetails>
            </Accordion>
          );
        })}
      </DialogContent>
    </Dialog>
  );
}

