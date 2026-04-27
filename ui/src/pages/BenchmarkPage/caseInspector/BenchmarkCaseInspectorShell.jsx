import React, { useMemo, useState } from "react";
import Accordion from "@mui/material/Accordion";
import AccordionDetails from "@mui/material/AccordionDetails";
import AccordionSummary from "@mui/material/AccordionSummary";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import { useTheme } from "@mui/material/styles";

import { CursorSmallButton } from "../../../components/common/index.js";
import { useI18n } from "../../../i18n/useI18n.js";

import { getHighlightsOrFallback } from "./benchmarkCaseInspectorModel.js";
import { renderFamilyInspectorPanel } from "./caseInspectorRegistry.jsx";

function JsonBlock({ value }) {
  const tk = useTheme().appTokens;
  return (
    <Box
      component="pre"
      sx={{
        whiteSpace: "pre-wrap",
        wordBreak: "break-word",
        maxHeight: 360,
        overflow: "auto",
        margin: 0,
        fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
        fontSize: "12px",
        color: tk.text.primary,
      }}
    >
      {JSON.stringify(value, null, 2)}
    </Box>
  );
}

function formatComparisonCellValue(value, fallback = null) {
  const resolved = value !== undefined ? value : fallback;
  return JSON.stringify(resolved);
}

/**
 * @param {Record<string, unknown>} issue
 * @param {(k: string, p?: Record<string, string>) => string} t
 */
function formatIssueLine(issue, t) {
  const kind = String(issue.kind || "");
  if (kind === "failed_check" && Array.isArray(issue.checks)) {
    return t("benchmark.inspector.issue.failedChecks", { list: issue.checks.join(", ") });
  }
  if (kind === "case_status") {
    return t("benchmark.inspector.issue.caseStatus", {
      status: String(issue.status || ""),
      message: String(issue.message || "—"),
    });
  }
  if (kind === "metadata_mismatch") {
    return t("benchmark.inspector.issue.metadataMismatch", { field: String(issue.field || "") });
  }
  if (kind === "authorship_mismatch") {
    return t("benchmark.inspector.issue.authorshipMismatch", { pos: String(issue.position ?? "") });
  }
  if (kind === "reference_mismatch") {
    return t("benchmark.inspector.issue.referenceMismatch", { field: String(issue.field || "") });
  }
  if (kind === "layer2_missing_methods") {
    return t("benchmark.inspector.issue.layer2MissMethods", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_extra_methods") {
    return t("benchmark.inspector.issue.layer2ExtraMethods", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_missing_datasets") {
    return t("benchmark.inspector.issue.layer2MissDatasets", { count: String(issue.count ?? 0) });
  }
  if (kind === "layer2_extra_datasets") {
    return t("benchmark.inspector.issue.layer2ExtraDatasets", { count: String(issue.count ?? 0) });
  }
  if (kind === "diagnostics_hint") {
    return t("benchmark.inspector.issue.diagnosticsHint");
  }
  try {
    return JSON.stringify(issue);
  } catch {
    return kind || "issue";
  }
}

/**
 * @param {{
 *   mode: "run" | "fixture",
 *   family: string,
 *   caseId: string | null,
 *   caseDetail: Record<string, unknown> | null,
 *   fixtureDetail: Record<string, unknown> | null,
 *   compareContext: { baselineRunId: string; metric: string } | null,
 *   loading?: boolean,
 *   onOpenRun: (runId: string) => void,
 * }} props
 */
export default function BenchmarkCaseInspectorShell({
  mode,
  family,
  caseId,
  caseDetail,
  fixtureDetail,
  compareContext,
  loading = false,
  onOpenRun,
}) {
  const { t } = useI18n();
  const tk = useTheme().appTokens;
  const [rawOpen, setRawOpen] = useState(false);

  const highlights = useMemo(() => getHighlightsOrFallback(caseDetail), [caseDetail]);
  const headline =
    mode === "fixture" && !(highlights.headline && String(highlights.headline).trim())
      ? t("benchmark.inspector.fixtureHeadline")
      : String(highlights.headline || "");
  const issues = Array.isArray(highlights.issues) ? highlights.issues : [];
  const evidenceLinks = Array.isArray(caseDetail?.evidence_links) ? caseDetail.evidence_links : [];

  const comparisonRows = useMemo(() => {
    const comp = /** @type {Record<string, unknown>} */ (caseDetail?.comparison || {});
    return (
      (Array.isArray(comp.metadata_rows) && comp.metadata_rows) ||
      (Array.isArray(comp.method_rows) && comp.method_rows) ||
      []
    );
  }, [caseDetail]);

  const runCfg = /** @type {Record<string, unknown>} */ (caseDetail?.run_config || {});
  const headlineSeverity = issues.some((i) => i && typeof i === "object" && /** @type {Record<string, unknown>} */ (i).severity === "error")
    ? "error"
    : issues.length
      ? "warning"
      : "success";

  if (loading && !caseDetail) {
    return (
      <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("benchmark.inspector.loading")}</Typography>
    );
  }

  if (!caseDetail) {
    return (
      <Typography sx={{ color: tk.text.secondary, fontSize: "0.8125rem" }}>{t("benchmark.workbench.selectCase")}</Typography>
    );
  }

  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1,
          alignItems: "center",
          borderBottom: `1px solid ${tk.border.default}`,
          pb: 1.5,
        }}
      >
        <Typography sx={{ fontWeight: 700, fontSize: "0.9375rem" }}>{t("benchmark.inspector.title")}</Typography>
        <Chip size="small" label={`case: ${caseId || "-"}`} variant="outlined" />
        {mode === "run" && caseDetail.run_id ? (
          <Chip size="small" label={`run: ${String(caseDetail.run_id).slice(0, 8)}…`} variant="outlined" />
        ) : null}
        <Chip size="small" label={`family: ${family}`} variant="outlined" />
        {caseDetail.status != null ? (
          <Chip size="small" label={`status: ${String(caseDetail.status)}`} variant="outlined" />
        ) : null}
        {runCfg.model_profile ? (
          <Chip size="small" label={String(runCfg.model_profile)} variant="outlined" sx={{ maxWidth: 220 }} />
        ) : null}
        {runCfg.gold_source ? <Chip size="small" label={String(runCfg.gold_source)} variant="outlined" /> : null}
      </Box>

      {compareContext ? (
        <Alert
          severity="info"
          sx={{
            fontSize: "0.8125rem",
            backgroundColor: tk.surface.subtle,
            border: `1px solid ${tk.border.default}`,
            color: tk.text.primary,
            "& .MuiAlert-icon": { color: tk.accent.fg },
          }}
        >
          <Typography sx={{ fontSize: "0.8125rem", lineHeight: 1.5 }}>
            {t("benchmark.inspector.compareBanner", {
              metric: compareContext.metric,
              baseline: compareContext.baselineRunId.slice(0, 8),
            })}
          </Typography>
        </Alert>
      ) : null}

      <Alert
        severity={headlineSeverity === "success" ? "success" : headlineSeverity}
        sx={{
          fontSize: "0.8125rem",
          "& .MuiAlert-message": { width: "100%" },
        }}
      >
        <Typography sx={{ fontWeight: 600, mb: issues.length ? 0.75 : 0 }}>{headline}</Typography>
        {issues.length ? (
          <Box component="ul" sx={{ m: 0, pl: 2.5, mb: 0 }}>
            {issues.map((issue, idx) => (
              <Typography key={idx} component="li" sx={{ fontSize: "0.8125rem", lineHeight: 1.45 }}>
                {formatIssueLine(/** @type {Record<string, unknown>} */ (issue), t)}
              </Typography>
            ))}
          </Box>
        ) : null}
      </Alert>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "minmax(0, 1.4fr) minmax(260px, 0.6fr)" },
          gap: 2,
          alignItems: "start",
        }}
      >
        <Box
          sx={{
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            backgroundColor: tk.surface.panel,
            p: 1.5,
          }}
        >
          {renderFamilyInspectorPanel({
            family,
            caseDetail,
            fixtureDetail,
            caseId,
          })}
        </Box>

        <Box
          sx={{
            border: `1px solid ${tk.border.default}`,
            borderRadius: 1.5,
            backgroundColor: tk.surface.panel,
            p: 1.5,
          }}
        >
          <Typography sx={{ fontWeight: 600, mb: 1, fontSize: "0.8125rem" }}>{t("benchmark.inspector.evidence.title")}</Typography>
          {evidenceLinks.length === 0 ? (
            <Typography sx={{ fontSize: "0.75rem", color: tk.text.muted }}>{t("benchmark.inspector.evidence.empty")}</Typography>
          ) : (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
              {evidenceLinks.map((link, linkIdx) => {
                if (!link || typeof link !== "object") return null;
                const L = /** @type {Record<string, unknown>} */ (link);
                const id = String(L.id || "");
                if (id === "last_completed_run" && L.run_id) {
                  return (
                    <Box key={`${id}-${String(L.run_id)}`} sx={{ display: "flex", flexDirection: "column", gap: 0.5 }}>
                      <Typography sx={{ fontSize: "0.75rem", color: tk.text.secondary }}>{t("benchmark.inspector.evidence.lastRun")}</Typography>
                      <CursorSmallButton onClick={() => onOpenRun(String(L.run_id))}>
                        {t("benchmark.inspector.evidence.openRun", { id: String(L.run_id).slice(0, 8) })}
                      </CursorSmallButton>
                    </Box>
                  );
                }
                return (
                  <Box key={id ? `${id}-${linkIdx}` : `ev-${linkIdx}`}>
                    <Typography sx={{ fontSize: "0.7rem", color: tk.text.muted }}>{String(L.label || L.id)}</Typography>
                    <Typography sx={{ fontSize: "0.75rem", wordBreak: "break-all", fontFamily: "monospace" }}>
                      {L.path_relative_to_repo ? String(L.path_relative_to_repo) : "—"}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          )}
        </Box>
      </Box>

      <Accordion expanded={rawOpen} onChange={(_, exp) => setRawOpen(exp)}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography sx={{ fontWeight: 600, fontSize: "0.8125rem" }}>{t("benchmark.inspector.raw.toggle")}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5 }}>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.sourceArticle")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <Typography component="pre" sx={{ whiteSpace: "pre-wrap", fontSize: "12px", m: 0 }}>
                  {String(/** @type {Record<string, unknown>} */ (caseDetail.article)?.raw_markdown || "")}
                </Typography>
              </AccordionDetails>
            </Accordion>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.goldPayload")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonBlock value={/** @type {Record<string, unknown>} */ (caseDetail.gold)?.payload || {}} />
              </AccordionDetails>
            </Accordion>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.prediction")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonBlock value={/** @type {Record<string, unknown>} */ (caseDetail.predicted)?.payload ?? {}} />
              </AccordionDetails>
            </Accordion>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.metrics")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonBlock value={caseDetail.metrics || {}} />
              </AccordionDetails>
            </Accordion>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>{t("benchmark.workbench.diff")}</Typography>
              </AccordionSummary>
              <AccordionDetails>
                {comparisonRows.length ? (
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell>{t("benchmark.workbench.diffColField")}</TableCell>
                        <TableCell>{t("benchmark.workbench.diffColGold")}</TableCell>
                        <TableCell>{t("benchmark.workbench.diffColPred")}</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {comparisonRows.map((row, idx) => {
                        const r = /** @type {Record<string, unknown>} */ (row);
                        return (
                          <TableRow key={`${r.field || r.value || "row"}-${idx}`}>
                            <TableCell>{String(r.field ?? r.value ?? "-")}</TableCell>
                            <TableCell sx={{ maxWidth: 200, wordBreak: "break-word" }}>
                              {formatComparisonCellValue(r.gold_value, r.source)}
                            </TableCell>
                            <TableCell sx={{ maxWidth: 200, wordBreak: "break-word" }}>
                              {formatComparisonCellValue(r.predicted_value, r.status ?? "-")}
                            </TableCell>
                          </TableRow>
                        );
                      })}
                    </TableBody>
                  </Table>
                ) : (
                  <Typography sx={{ color: tk.text.muted, fontSize: "0.8125rem" }}>{t("benchmark.workbench.noDiff")}</Typography>
                )}
              </AccordionDetails>
            </Accordion>
            <Accordion disableGutters elevation={0} sx={{ border: `1px solid ${tk.border.default}`, borderRadius: 1, "&:before": { display: "none" } }}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Typography sx={{ fontSize: "0.8125rem" }}>diagnostics</Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonBlock value={caseDetail.diagnostics || {}} />
              </AccordionDetails>
            </Accordion>
          </Box>
        </AccordionDetails>
      </Accordion>
    </Box>
  );
}
