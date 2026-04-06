import React, { useEffect, useMemo, useState } from "react";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import { getBenchmarkCaseDetail } from "../../services/benchmarkApi.js";
import { CursorButton } from "../../components/common/index.js";

export default function CaseDetailDialog({ open, caseId, family = "layer1", onClose }) {
  const [tabIdx, setTabIdx] = useState(0);
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const jsonString = useMemo(() => {
    if (!detail?.gold) return "";
    return JSON.stringify(detail.gold, null, 2);
  }, [detail]);

  const graphExpectationsJson = useMemo(() => {
    const ge = detail?.gold?.graph_expectations;
    if (!ge) return "";
    return JSON.stringify(ge, null, 2);
  }, [detail]);

  useEffect(() => {
    if (detail && tabIdx === 2 && !graphExpectationsJson) {
      setTabIdx(0);
    }
  }, [detail, graphExpectationsJson, tabIdx]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!open || !caseId) return;
      setTabIdx(0);
      setDetail(null);
      setError(null);
      setLoading(true);
      try {
        const resp = await getBenchmarkCaseDetail(caseId, { family });
        if (cancelled) return;
        setDetail(resp);
      } catch (e) {
        if (!cancelled) setError(e?.message || "failed_to_fetch_case");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [open, caseId, family]);

  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
      <DialogTitle>
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography sx={{ fontWeight: 700 }}>Case fixtures</Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
              case_id: {caseId || "-"}
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

        {detail && (
          <Box>
            <Tabs value={tabIdx} onChange={(e, v) => setTabIdx(v)}>
              <Tab label="Text (article.md)" />
              <Tab label="Gold (gold.json)" />
              {graphExpectationsJson ? <Tab label="graph_expectations" /> : null}
            </Tabs>

            {tabIdx === 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
                  article.md preview (редактирование не предусмотрено в MVP)
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 2,
                    padding: 2,
                    maxHeight: 520,
                    overflow: "auto",
                    background: "rgba(255,255,255,0.02)",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    fontSize: "12px",
                  }}
                >
                  {detail.article_md}
                </Box>
              </Box>
            )}

            {tabIdx === 1 && (
              <Box sx={{ mt: 2 }}>
                <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
                  gold.json (pretty printed)
                </Typography>
                <Accordion defaultExpanded={true}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography sx={{ fontWeight: 600 }}>gold.json</Typography>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box
                      component="pre"
                      sx={{
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 2,
                        padding: 2,
                        maxHeight: 520,
                        overflow: "auto",
                        background: "rgba(255,255,255,0.02)",
                        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        fontSize: "12px",
                      }}
                    >
                      {jsonString}
                    </Box>
                  </AccordionDetails>
                </Accordion>
              </Box>
            )}

            {graphExpectationsJson && tabIdx === 2 && (
              <Box sx={{ mt: 2 }}>
                <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
                  <code>graph_expectations</code> from gold (graph-v1 benchmark). Run:{" "}
                  <code>science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/&lt;case&gt;</code>
                </Typography>
                <Box
                  component="pre"
                  sx={{
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 2,
                    padding: 2,
                    maxHeight: 520,
                    overflow: "auto",
                    background: "rgba(255,255,255,0.02)",
                    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                    fontSize: "12px",
                  }}
                >
                  {graphExpectationsJson}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}

