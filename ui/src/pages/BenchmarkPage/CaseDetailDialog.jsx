import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import Dialog from "@mui/material/Dialog";
import useMediaQuery from "@mui/material/useMediaQuery";
import { useTheme } from "@mui/material/styles";
import DialogTitle from "@mui/material/DialogTitle";
import DialogContent from "@mui/material/DialogContent";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import Accordion from "@mui/material/Accordion";
import AccordionSummary from "@mui/material/AccordionSummary";
import AccordionDetails from "@mui/material/AccordionDetails";
import Chip from "@mui/material/Chip";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";

import {
  getBenchmarkCaseArtifacts,
  getBenchmarkCaseDetail,
  postGraphSnapshotPreview,
} from "../../services/benchmarkApi.js";
import { formatResearchApiError } from "../../services/researchApi.js";
import { CursorButton, CursorSmallButton } from "../../components/common/index.js";
import {
  compareGraphExpectationsToSnapshot,
  extractGraphSnapshotMetrics,
  graphExpectationRangeRows,
} from "./graphSnapshotCompare.js";

export default function CaseDetailDialog({ open, caseId, family = "layer1", onClose }) {
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const navigate = useNavigate();
  const [tabIdx, setTabIdx] = useState(0);
  const [detail, setDetail] = useState(null);
  const [artifacts, setArtifacts] = useState(null);
  const [goldSource, setGoldSource] = useState("curated_gold");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [snapshotJson, setSnapshotJson] = useState(null);
  const [snapshotLoadError, setSnapshotLoadError] = useState(null);
  const [serverPreview, setServerPreview] = useState(null);
  const [serverPreviewLoading, setServerPreviewLoading] = useState(false);
  const [serverPreviewError, setServerPreviewError] = useState(null);
  const snapshotFileRef = useRef(null);

  const usesLayer1Gold = family === "layer1" || family === "graph";

  const jsonString = useMemo(() => {
    if (!detail?.gold) return "";
    return JSON.stringify(detail.gold, null, 2);
  }, [detail]);

  const graphExpectationsJson = useMemo(() => {
    const ge = detail?.gold?.graph_expectations;
    if (!ge) return "";
    return JSON.stringify(ge, null, 2);
  }, [detail]);

  const graphExpectations = detail?.gold?.graph_expectations;
  const snapshotMetrics = useMemo(() => extractGraphSnapshotMetrics(snapshotJson), [snapshotJson]);
  const graphCompare = useMemo(
    () => compareGraphExpectationsToSnapshot(graphExpectations, snapshotMetrics),
    [graphExpectations, snapshotMetrics],
  );
  const expectationRangeRows = useMemo(() => graphExpectationRangeRows(graphExpectations), [graphExpectations]);

  const snapshotCaseId = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    const inner = snapshotJson.case;
    if (inner && typeof inner === "object" && inner.case_id != null) return String(inner.case_id);
    if (snapshotJson.case_id != null) return String(snapshotJson.case_id);
    return null;
  }, [snapshotJson]);

  const snapshotCaseIdMismatch =
    Boolean(snapshotCaseId) && Boolean(caseId) && snapshotCaseId !== String(caseId);

  const snapshotMetricsRoot = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    const inner = snapshotJson.case;
    if (inner && typeof inner === "object" && inner.metrics != null) return inner.metrics;
    return snapshotJson.metrics ?? null;
  }, [snapshotJson]);

  const snapshotGoldFromFile = useMemo(() => {
    if (!snapshotJson || typeof snapshotJson !== "object") return null;
    return snapshotJson.gold ?? snapshotJson.case?.gold ?? null;
  }, [snapshotJson]);

  useEffect(() => {
    if (detail && tabIdx === 2 && !graphExpectationsJson) {
      setTabIdx(0);
    }
  }, [detail, graphExpectationsJson, tabIdx]);

  useEffect(() => {
    if (!open) {
      setSnapshotJson(null);
      setSnapshotLoadError(null);
    }
  }, [open]);

  useEffect(() => {
    setSnapshotJson(null);
    setSnapshotLoadError(null);
    setServerPreview(null);
    setServerPreviewError(null);
  }, [caseId, family]);

  useEffect(() => {
    setServerPreview(null);
    setServerPreviewError(null);
  }, [snapshotJson]);

  useEffect(() => {
    let cancelled = false;
    async function loadArtifacts() {
      if (!open || !caseId) {
        setArtifacts(null);
        return;
      }
      try {
        const resp = await getBenchmarkCaseArtifacts(caseId, { family });
        if (!cancelled) setArtifacts(resp);
      } catch {
        if (!cancelled) setArtifacts(null);
      }
    }
    loadArtifacts();
    return () => {
      cancelled = true;
    };
  }, [open, caseId, family]);

  useEffect(() => {
    if (!open || !caseId) return;
    setGoldSource("curated_gold");
  }, [open, caseId, family]);

  useEffect(() => {
    if (!artifacts || !usesLayer1Gold) return;
    const cur = artifacts.gold_variants?.find((g) => g.id === "curated_gold");
    const tea = artifacts.gold_variants?.find((g) => g.id === "teacher_gold");
    if (!cur?.present && tea?.present) {
      setGoldSource("teacher_gold");
    }
  }, [artifacts, usesLayer1Gold]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!open || !caseId) return;
      setTabIdx(0);
      setDetail(null);
      setError(null);
      setLoading(true);
      try {
        const resp = await getBenchmarkCaseDetail(caseId, {
          family,
          gold_source: usesLayer1Gold ? goldSource : undefined,
        });
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
  }, [open, caseId, family, goldSource, usesLayer1Gold]);

  const curatedVariant = artifacts?.gold_variants?.find((g) => g.id === "curated_gold");
  const teacherVariant = artifacts?.gold_variants?.find((g) => g.id === "teacher_gold");
  const goldTabLabel =
    usesLayer1Gold && goldSource === "teacher_gold" ? "Gold (teacher)" : "Gold (curated)";

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="lg"
      fullScreen={fullScreen}
      aria-labelledby="benchmark-case-dialog-title"
    >
      <DialogTitle id="benchmark-case-dialog-title">
        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 1 }}>
          <Box>
            <Typography sx={{ fontWeight: 700 }}>Case fixtures</Typography>
            <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
              case_id: {caseId || "-"}
            </Typography>
          </Box>
          <CursorButton onClick={onClose} aria-label="Close case fixtures dialog">
            Close
          </CursorButton>
        </Box>
      </DialogTitle>
      <DialogContent dividers>
        {error && (
          <Typography sx={{ color: "rgba(239, 68, 68, 0.9)", mb: 1 }} role="alert">
            {error}
          </Typography>
        )}

        {loading && <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>Loading...</Typography>}

        {artifacts ? (
          <Box sx={{ mb: 2, display: "flex", flexDirection: "column", gap: 1 }}>
            <Typography sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.6)" }}>Artifacts</Typography>
            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.75, alignItems: "center" }}>
              <Chip
                size="small"
                label={`article ${artifacts.article?.present ? "present" : "missing"}`}
                variant="outlined"
              />
              {usesLayer1Gold ? (
                <>
                  <Chip
                    size="small"
                    label={`curated ${curatedVariant?.present ? "present" : "missing"}`}
                    variant="outlined"
                  />
                  <Chip
                    size="small"
                    label={`teacher ${teacherVariant?.present ? "present" : "missing"}`}
                    variant="outlined"
                  />
                </>
              ) : null}
              {artifacts.semantic_gold ? (
                <Chip
                  size="small"
                  label={`semantic_gold ${artifacts.semantic_gold.present ? "present" : "missing"}`}
                  variant="outlined"
                />
              ) : null}
              {artifacts.semantic_gold_teacher?.present ? (
                <Chip size="small" label="semantic_gold_teacher present" variant="outlined" />
              ) : null}
              {artifacts.last_run_hints?.run_id ? (
                <Chip
                  size="small"
                  label={`last run ${String(artifacts.last_run_hints.run_id).slice(0, 8)}… · ${artifacts.last_run_hints.status ?? "?"}`}
                  variant="outlined"
                  onClick={() => {
                    const rid = artifacts.last_run_hints?.run_id;
                    if (rid) {
                      navigate(`/benchmark?tab=workbench&run=${encodeURIComponent(String(rid))}`);
                      onClose?.();
                    }
                  }}
                  sx={{
                    borderColor: "rgba(99, 102, 241, 0.35)",
                    cursor: "pointer",
                  }}
                />
              ) : null}
            </Box>
            {usesLayer1Gold && (curatedVariant?.present || teacherVariant?.present) ? (
              <FormControl size="small" sx={{ minWidth: 220, mt: 0.5 }}>
                <InputLabel id="case-gold-src">Gold source</InputLabel>
                <Select
                  labelId="case-gold-src"
                  label="Gold source"
                  value={goldSource}
                  onChange={(e) => setGoldSource(e.target.value)}
                >
                  <MenuItem value="curated_gold" disabled={!curatedVariant?.present}>
                    curated_gold (gold.json)
                  </MenuItem>
                  <MenuItem value="teacher_gold" disabled={!teacherVariant?.present}>
                    teacher_gold (gold_teacher.json)
                  </MenuItem>
                </Select>
              </FormControl>
            ) : null}
          </Box>
        ) : null}

        {detail && (
          <Box>
            <Tabs value={tabIdx} onChange={(e, v) => setTabIdx(v)}>
              <Tab label="Text (article.md)" />
              <Tab label={goldTabLabel} />
              {graphExpectationsJson ? <Tab label="graph_expectations" /> : null}
            </Tabs>

            {tabIdx === 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography sx={{ color: "rgba(255,255,255,0.6)", mb: 1 }}>
                  article.md preview (editing not supported in MVP)
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
                  Gold payload (pretty printed)
                </Typography>
                <Accordion defaultExpanded={true}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Typography sx={{ fontWeight: 600 }}>gold</Typography>
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
              <Box sx={{ mt: 2, display: "flex", flexDirection: "column", gap: 2 }}>
                <Typography sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.8125rem" }}>
                  Graph-v1: expectations from <code>gold.json</code>. Fetch graph snapshots via CLI:{" "}
                  <code>science-graphrag-graph-benchmark tests/fixtures/benchmarks/layer1/&lt;case&gt; --json-out …</code>{" "}
                  (see eval/README.md).
                </Typography>

                <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, alignItems: "center" }}>
                  <input
                    ref={snapshotFileRef}
                    type="file"
                    accept="application/json,.json"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      e.target.value = "";
                      if (!f) return;
                      const reader = new FileReader();
                      reader.onload = () => {
                        try {
                          const parsed = JSON.parse(String(reader.result || ""));
                          setSnapshotJson(parsed);
                          setSnapshotLoadError(null);
                        } catch (err) {
                          setSnapshotJson(null);
                          setSnapshotLoadError(err?.message || "invalid_json");
                        }
                      };
                      reader.readAsText(f);
                    }}
                  />
                  <CursorSmallButton onClick={() => snapshotFileRef.current?.click()}>Load snapshot JSON</CursorSmallButton>
                  {snapshotJson ? (
                    <>
                      <CursorSmallButton
                        onClick={() => {
                          setSnapshotJson(null);
                          setSnapshotLoadError(null);
                        }}
                      >
                        Clear snapshot
                      </CursorSmallButton>
                      <CursorSmallButton
                        onClick={async () => {
                          if (!snapshotJson || !caseId) return;
                          setServerPreviewLoading(true);
                          setServerPreviewError(null);
                          try {
                            const resp = await postGraphSnapshotPreview(caseId, snapshotJson, {
                              family: family === "graph" ? "graph" : "layer1",
                            });
                            const payload = resp?.data || resp;
                            setServerPreview(payload);
                          } catch (err) {
                            setServerPreviewError(formatResearchApiError(err) || "server_preview_failed");
                          } finally {
                            setServerPreviewLoading(false);
                          }
                        }}
                        disabled={serverPreviewLoading}
                      >
                        {serverPreviewLoading ? "Server…" : "Preview on server"}
                      </CursorSmallButton>
                    </>
                  ) : null}
                </Box>

                {snapshotLoadError ? (
                  <Typography sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.8125rem" }} role="alert">
                    {snapshotLoadError}
                  </Typography>
                ) : null}

                {snapshotCaseIdMismatch ? (
                  <Box
                    sx={{
                      border: "1px solid rgba(255,200,100,0.45)",
                      borderRadius: 1.5,
                      px: 1.5,
                      py: 1,
                      backgroundColor: "rgba(255,200,100,0.06)",
                    }}
                  >
                    <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,200,100,0.95)" }}>
                      Snapshot <code>case_id</code> ({snapshotCaseId}) does not match this dialog ({caseId}).
                    </Typography>
                  </Box>
                ) : null}

                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: { xs: "1fr", md: "minmax(0,1fr) minmax(0,1fr)" },
                    gap: 2,
                    alignItems: "start",
                  }}
                >
                  <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>Gold graph_expectations</Typography>
                    {expectationRangeRows.length ? (
                      <Box sx={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 1.5, overflow: "hidden" }}>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Constraint</TableCell>
                              <TableCell>Min</TableCell>
                              <TableCell>Max</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {expectationRangeRows.map((row) => (
                              <TableRow key={row.label}>
                                <TableCell sx={{ color: "rgba(255,255,255,0.75)" }}>{row.label}</TableCell>
                                <TableCell>{String(row.low)}</TableCell>
                                <TableCell>{String(row.high)}</TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </Box>
                    ) : null}

                    {graphExpectations?.max_duplicate_work_fingerprints != null ? (
                      <Typography sx={{ fontSize: "0.8125rem" }}>
                        <strong>max_duplicate_work_fingerprints:</strong>{" "}
                        {String(graphExpectations.max_duplicate_work_fingerprints)}
                        {graphExpectations.max_work_dedup_violations != null
                          ? ` | max_work_dedup_violations: ${String(graphExpectations.max_work_dedup_violations)}`
                          : ""}
                      </Typography>
                    ) : null}

                    {Array.isArray(graphExpectations?.expected_cited_arxiv_ids) ? (
                      <Box>
                        <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>
                          expected_cited_arxiv_ids ({graphExpectations.expected_cited_arxiv_ids.length})
                        </Typography>
                        <Typography
                          sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.55)", wordBreak: "break-word" }}
                        >
                          {graphExpectations.expected_cited_arxiv_ids.join(", ")}
                        </Typography>
                      </Box>
                    ) : null}

                    <Accordion defaultExpanded={false}>
                      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                        <Typography sx={{ fontWeight: 600 }}>Raw graph_expectations (JSON)</Typography>
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
                            maxHeight: 320,
                            overflow: "auto",
                            background: "rgba(255,255,255,0.02)",
                            fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                            fontSize: "12px",
                          }}
                        >
                          {graphExpectationsJson}
                        </Box>
                      </AccordionDetails>
                    </Accordion>
                  </Box>

                  <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>Loaded snapshot (CLI JSON)</Typography>
                    {!snapshotJson ? (
                      <Typography sx={{ fontSize: "0.8125rem", color: "rgba(255,255,255,0.45)" }}>
                        Load a graph-benchmark JSON file to inspect metrics and snapshot blocks.
                      </Typography>
                    ) : (
                      <>
                        {snapshotJson && !snapshotMetrics ? (
                          <Typography sx={{ color: "rgba(255,200,100,0.9)", fontSize: "0.8125rem" }}>
                            No <code>metrics.snapshot</code> in this file — range compare uses snapshot metrics only when
                            present.
                          </Typography>
                        ) : null}
                        <Accordion defaultExpanded>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography sx={{ fontWeight: 600 }}>metrics (file)</Typography>
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
                                maxHeight: 280,
                                overflow: "auto",
                                background: "rgba(255,255,255,0.02)",
                                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                fontSize: "11px",
                              }}
                            >
                              {JSON.stringify(snapshotMetricsRoot ?? {}, null, 2)}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                        <Accordion defaultExpanded={false}>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography sx={{ fontWeight: 600 }}>metrics.snapshot</Typography>
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
                                maxHeight: 280,
                                overflow: "auto",
                                background: "rgba(255,255,255,0.02)",
                                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                fontSize: "11px",
                              }}
                            >
                              {JSON.stringify(snapshotMetrics ?? {}, null, 2)}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                        <Accordion defaultExpanded={false}>
                          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                            <Typography sx={{ fontWeight: 600 }}>gold (embedded in file, if any)</Typography>
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
                                maxHeight: 280,
                                overflow: "auto",
                                background: "rgba(255,255,255,0.02)",
                                fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                                fontSize: "11px",
                              }}
                            >
                              {snapshotGoldFromFile != null
                                ? JSON.stringify(snapshotGoldFromFile, null, 2)
                                : "{}"}
                            </Box>
                          </AccordionDetails>
                        </Accordion>
                      </>
                    )}
                  </Box>
                </Box>

                {snapshotJson && graphExpectationsJson ? (
                  <Accordion defaultExpanded={false}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        Side-by-side: canonical graph_expectations vs snapshot file gold (raw)
                      </Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <Box
                        sx={{
                          display: "grid",
                          gridTemplateColumns: { xs: "1fr", md: "minmax(0,1fr) minmax(0,1fr)" },
                          gap: 1.5,
                          alignItems: "stretch",
                        }}
                      >
                        <Box>
                          <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>
                            Case gold (gold.json)
                          </Typography>
                          <Box
                            component="pre"
                            sx={{
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              border: "1px solid rgba(255,255,255,0.08)",
                              borderRadius: 2,
                              padding: 1.5,
                              maxHeight: 320,
                              overflow: "auto",
                              background: "rgba(255,255,255,0.02)",
                              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                              fontSize: "11px",
                              margin: 0,
                            }}
                          >
                            {graphExpectationsJson}
                          </Box>
                        </Box>
                        <Box>
                          <Typography sx={{ fontSize: "0.7rem", color: "rgba(255,255,255,0.5)", mb: 0.5 }}>
                            Snapshot embedded gold (if present)
                          </Typography>
                          <Box
                            component="pre"
                            sx={{
                              whiteSpace: "pre-wrap",
                              wordBreak: "break-word",
                              border: "1px solid rgba(255,255,255,0.08)",
                              borderRadius: 2,
                              padding: 1.5,
                              maxHeight: 320,
                              overflow: "auto",
                              background: "rgba(255,255,255,0.02)",
                              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                              fontSize: "11px",
                              margin: 0,
                            }}
                          >
                            {snapshotGoldFromFile != null
                              ? JSON.stringify(snapshotGoldFromFile, null, 2)
                              : "— (no gold object in loaded snapshot JSON)"}
                          </Box>
                        </Box>
                      </Box>
                    </AccordionDetails>
                  </Accordion>
                ) : null}

                {graphCompare.arxivNotes.length ? (
                  <Box>
                    {graphCompare.arxivNotes.map((line, idx) => (
                      <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mb: 0.5 }}>
                        {line}
                      </Typography>
                    ))}
                  </Box>
                ) : null}

                {graphCompare.rows.length ? (
                  <Box sx={{ border: "1px solid rgba(255,255,255,0.08)", borderRadius: 1.5, overflow: "hidden" }}>
                    <Typography sx={{ px: 1.5, py: 1, fontWeight: 600, fontSize: "0.8125rem" }}>
                      Snapshot vs expectations (metrics.snapshot)
                    </Typography>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Field</TableCell>
                          <TableCell>Snapshot</TableCell>
                          <TableCell>Expected</TableCell>
                          <TableCell>OK</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {graphCompare.rows.map((row) => (
                          <TableRow key={row.field}>
                            <TableCell>{row.field}</TableCell>
                            <TableCell>{row.snapshot}</TableCell>
                            <TableCell>{row.expected}</TableCell>
                            <TableCell sx={{ color: row.ok ? "rgba(129,140,248,0.95)" : "rgba(239,68,68,0.9)" }}>
                              {row.ok ? "yes" : "no"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                ) : null}

                {serverPreviewError ? (
                  <Typography sx={{ color: "rgba(239,68,68,0.9)", fontSize: "0.8125rem" }} role="alert">
                    {serverPreviewError}
                  </Typography>
                ) : null}

                {serverPreview?.arxiv_notes?.length ? (
                  <Box>
                    <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem", mb: 0.5 }}>
                      Server preview — arxiv notes
                    </Typography>
                    {serverPreview.arxiv_notes.map((line, idx) => (
                      <Typography key={idx} sx={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.65)", mb: 0.5 }}>
                        {line}
                      </Typography>
                    ))}
                  </Box>
                ) : null}

                {serverPreview?.rows?.length ? (
                  <Box sx={{ border: "1px solid rgba(99,102,241,0.25)", borderRadius: 1.5, overflow: "hidden" }}>
                    <Typography sx={{ px: 1.5, py: 1, fontWeight: 600, fontSize: "0.8125rem" }}>
                      Server preview — range checks
                    </Typography>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Field</TableCell>
                          <TableCell>Snapshot</TableCell>
                          <TableCell>Expected</TableCell>
                          <TableCell>OK</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {serverPreview.rows.map((row) => (
                          <TableRow key={`srv-${row.field}`}>
                            <TableCell>{row.field}</TableCell>
                            <TableCell>{row.snapshot}</TableCell>
                            <TableCell>{row.expected}</TableCell>
                            <TableCell sx={{ color: row.ok ? "rgba(129,140,248,0.95)" : "rgba(239,68,68,0.9)" }}>
                              {row.ok ? "yes" : "no"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </Box>
                ) : null}
              </Box>
            )}
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}
